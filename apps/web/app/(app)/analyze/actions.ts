"use server";

import { auth } from "@clerk/nextjs/server";
import type { AnalysisResponse } from "@heartscan/api-client";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";
import { persistAnalysis } from "@/lib/analyze/history";

/**
 * Persistence-only server actions. The ECG file is uploaded by the browser
 * DIRECTLY to the ML API (via the /ml-api proxy) so it never passes through a
 * server action / serverless function — avoiding the platform body-size limit.
 * The client then calls these with the small parsed result JSON to store it.
 */

function tenant(orgId: string | null | undefined, userId: string): string {
  return orgId ?? `clerk-user:${userId}`;
}

export async function persistPhotoResult(result: AnalysisResponse): Promise<void> {
  const { userId, orgId } = await auth();
  if (!userId) throw new Error("Unauthorized");
  await persistAnalysis({
    tenantId: tenant(orgId, userId),
    userId,
    requestId: result.request_id,
    status: result.status,
    classLabel: result.class_label,
    confidence: `${Math.round(result.confidence_score * 100)}%`,
    pipelineVersion: result.pipeline_version,
    modelVersion: result.model_version,
    resultJson: result,
  });
}

export async function persistSignalResult(result: DiagnosticResponse): Promise<void> {
  const { userId, orgId } = await auth();
  if (!userId) throw new Error("Unauthorized");
  const top = result.findings
    .filter((f) => f.positive)
    .sort((a, b) => b.probability - a.probability)[0];
  await persistAnalysis({
    tenantId: tenant(orgId, userId),
    userId,
    requestId: result.request_id,
    status: result.abnormal ? "red" : result.requires_review ? "yellow" : "green",
    classLabel: top ? top.label : "normal",
    confidence: top ? top.confidence : null,
    pipelineVersion: result.pipeline_version,
    modelVersion: result.model_version,
    resultJson: result,
  });
}
