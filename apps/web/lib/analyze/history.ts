import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Analysis history persistence + read.
 *
 * Writes use the **service-role** client (trusted server context) so they work
 * in both org and org-optional tenancy: the tenant is computed server-side from
 * the Clerk session, not from RLS. RLS still protects direct table access.
 *
 * Degrades gracefully: when Supabase service-role env vars are unset (local dev
 * without a Supabase project), every call is a no-op and the analyze flow is
 * unaffected.
 */

export interface AnalysisRecord {
  tenantId: string; // companies.id — orgId or `clerk-user:<userId>`
  userId: string;
  requestId: string;
  status: string; // green | yellow | red
  classLabel: string | null;
  confidence: string | null;
  pipelineVersion: string;
  modelVersion: string;
  resultJson: unknown;
}

export interface RecentAnalysis {
  id: string;
  created_at: string;
  status: string;
  class_label: string | null;
  confidence: string | null;
  request_id: string;
}

function serviceClient(): SupabaseClient | null {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

/** Persist one analysis. Never throws — a storage failure must not break the
 *  user's result. Returns true when written. */
export async function persistAnalysis(rec: AnalysisRecord): Promise<boolean> {
  const supabase = serviceClient();
  if (!supabase) return false;
  try {
    // Ensure a companies row exists so the analyses FK holds. For org tenants
    // the row already exists (synced by the Clerk webhook); for single-tenant
    // `clerk-user:*` this creates it. ignoreDuplicates keeps existing data.
    await supabase.from("companies").upsert(
      {
        id: rec.tenantId,
        name: rec.tenantId.startsWith("clerk-user:") ? "Personal" : rec.tenantId,
      },
      { onConflict: "id", ignoreDuplicates: true },
    );
    const { error } = await supabase.from("analyses").insert({
      company_id: rec.tenantId,
      clerk_user_id: rec.userId,
      request_id: rec.requestId,
      status: rec.status,
      class_label: rec.classLabel,
      confidence: rec.confidence,
      pipeline_version: rec.pipelineVersion,
      model_version: rec.modelVersion,
      result_json: rec.resultJson,
    });
    if (error) {
      console.error("persistAnalysis insert failed", error.message);
      return false;
    }
    return true;
  } catch (err) {
    console.error("persistAnalysis error", err instanceof Error ? err.message : err);
    return false;
  }
}

export interface AnalysisDetail extends RecentAnalysis {
  clerk_user_id: string;
  pipeline_version: string;
  model_version: string;
  result_json: unknown;
}

/** One analysis by id, scoped to the tenant. null when not found / Supabase unset. */
export async function getAnalysisById(
  tenantId: string,
  id: string,
): Promise<AnalysisDetail | null> {
  const supabase = serviceClient();
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("analyses")
    .select(
      "id, created_at, status, class_label, confidence, request_id, clerk_user_id, pipeline_version, model_version, result_json",
    )
    .eq("company_id", tenantId)
    .eq("id", id)
    .maybeSingle();
  if (error) {
    console.error("getAnalysisById failed", error.message);
    return null;
  }
  return (data as AnalysisDetail | null) ?? null;
}

/** Recent analyses for a tenant (newest first). [] when Supabase is unset. */
export async function getRecentAnalyses(
  tenantId: string,
  limit = 20,
): Promise<RecentAnalysis[]> {
  const supabase = serviceClient();
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("analyses")
    .select("id, created_at, status, class_label, confidence, request_id")
    .eq("company_id", tenantId)
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) {
    console.error("getRecentAnalyses failed", error.message);
    return [];
  }
  return (data ?? []) as RecentAnalysis[];
}
