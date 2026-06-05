import { auth } from "@clerk/nextjs/server";
import { createClient } from "@supabase/supabase-js";
import { daysLeft, trialEndsAt } from "./plans";

export interface BillingStatus {
  orgId: string | null;
  plan: string;
  subscriptionStatus: string;
  trialEndsAt: string | null;
  trialDaysLeft: number | null;
  stripeCustomerId: string | null;
  canAnalyze: boolean;
}

function serviceClient() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

export async function getBillingStatus(): Promise<BillingStatus> {
  const { orgId } = await auth();
  if (!orgId) {
    return {
      orgId: null,
      plan: "none",
      subscriptionStatus: "missing_org",
      trialEndsAt: null,
      trialDaysLeft: null,
      stripeCustomerId: null,
      canAnalyze: false,
    };
  }

  const fallbackEnd = trialEndsAt().toISOString();
  const fallback: BillingStatus = {
    orgId,
    plan: "trial",
    subscriptionStatus: "trialing",
    trialEndsAt: fallbackEnd,
    trialDaysLeft: daysLeft(fallbackEnd),
    stripeCustomerId: null,
    canAnalyze: true,
  };

  const supabase = serviceClient();
  if (!supabase) return fallback;

  const { data } = await supabase
    .from("companies")
    .select("plan, stripe_customer_id, subscription_status, trial_ends_at")
    .eq("id", orgId)
    .maybeSingle();

  if (!data) return fallback;

  const trialDaysLeft = daysLeft(data.trial_ends_at);
  const status = String(data.subscription_status ?? "trialing");
  const plan = String(data.plan ?? "trial");

  return {
    orgId,
    plan,
    subscriptionStatus: status,
    trialEndsAt: data.trial_ends_at ?? fallbackEnd,
    trialDaysLeft,
    stripeCustomerId: data.stripe_customer_id ?? null,
    canAnalyze:
      status === "active" ||
      status === "trialing" ||
      (plan === "trial" && (trialDaysLeft ?? 0) > 0),
  };
}

