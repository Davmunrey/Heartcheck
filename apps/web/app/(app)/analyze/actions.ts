"use server";

import { auth } from "@clerk/nextjs/server";
import { parseAnalysisResponse, type AnalysisResponse } from "@heartscan/api-client";
import { validateAnalyzeFile } from "@/lib/analyze/validation";
import { parseDiagnosticResponse, type DiagnosticResponse } from "@/lib/analyze/diagnostic";
import { persistAnalysis } from "@/lib/analyze/history";

/** Tenant key for storage: active Clerk org, or per-user in single-tenant mode. */
function tenantKey(orgId: string | null | undefined, userId: string): string {
  return orgId ?? `clerk-user:${userId}`;
}

const SIGNAL_MAX_BYTES = 10 * 1024 * 1024;

export async function analyzeImageAction(formData: FormData): Promise<AnalysisResponse> {
  const { userId, orgId, getToken } = await auth();
  if (!userId) throw new Error("Unauthorized");
  // Org is optional (single-tenant mode): when no Clerk Organization is active
  // the ML API derives the tenant from the verified Clerk user id.

  const file = validateAnalyzeFile(formData.get("file"));

  const mlUrl = process.env.ML_API_URL ?? "http://localhost:8000";

  const token = await getToken();
  if (!token) throw new Error("No se pudo obtener el token de sesión.");

  const internal = process.env.ML_API_INTERNAL_TOKEN;
  const fd = new FormData();
  fd.append("file", file);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  let res: Response;
  try {
    res = await fetch(`${mlUrl.replace(/\/$/, "")}/api/v1/analyze`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(orgId ? { "X-Organization-Id": orgId } : {}),
        ...(internal ? { "X-Internal-Token": internal } : {}),
        "Accept-Language": "es",
      },
      body: fd,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("El análisis tardó demasiado. Intenta de nuevo.");
    }
    throw err;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: { message?: string } })?.detail;
    const msg =
      typeof detail === "object" && detail && "message" in detail
        ? String(detail.message)
        : res.statusText;
    throw new Error(msg || `Error ${res.status}`);
  }

  const json = await res.json();
  const analysis = await parseAnalysisResponse(json);
  await persistAnalysis({
    tenantId: tenantKey(orgId, userId),
    userId,
    requestId: analysis.request_id,
    status: analysis.status,
    classLabel: analysis.class_label,
    confidence: `${Math.round(analysis.confidence_score * 100)}%`,
    pipelineVersion: analysis.pipeline_version,
    modelVersion: analysis.model_version,
    resultJson: analysis,
  });
  return analysis;
}

export async function analyzeSignalAction(formData: FormData): Promise<DiagnosticResponse> {
  const { userId, orgId, getToken } = await auth();
  if (!userId) throw new Error("Unauthorized");
  // Org is optional (single-tenant mode): when no Clerk Organization is active
  // the ML API derives the tenant from the verified Clerk user id.

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("Adjunta una señal ECG (.npy o .csv).");
  }
  if (file.size > SIGNAL_MAX_BYTES) {
    throw new Error(`La señal supera ${SIGNAL_MAX_BYTES / (1024 * 1024)} MB.`);
  }

  const samplingRaw = formData.get("sampling_rate_hz");
  const samplingHz = Number(samplingRaw ?? 500);
  if (!Number.isFinite(samplingHz) || samplingHz < 1 || samplingHz > 5000) {
    throw new Error("Frecuencia de muestreo inválida (1–5000 Hz).");
  }

  // Internal ML backend URL. Defaults to localhost:8000 for dev so the app
  // works out of the box; set ML_API_URL to the private backend in prod.
  const mlUrl = process.env.ML_API_URL ?? "http://localhost:8000";

  const token = await getToken();
  if (!token) throw new Error("No se pudo obtener el token de sesión.");

  const internal = process.env.ML_API_INTERNAL_TOKEN;
  const fd = new FormData();
  fd.append("file", file);
  fd.append("sampling_rate_hz", String(Math.round(samplingHz)));

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  let res: Response;
  try {
    res = await fetch(`${mlUrl.replace(/\/$/, "")}/api/v1/analyze/signal`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(orgId ? { "X-Organization-Id": orgId } : {}),
        ...(internal ? { "X-Internal-Token": internal } : {}),
        "Accept-Language": "es",
      },
      body: fd,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("El análisis tardó demasiado. Intenta de nuevo.");
    }
    throw err;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: { message?: string } })?.detail;
    const msg =
      typeof detail === "object" && detail && "message" in detail
        ? String(detail.message)
        : res.statusText;
    throw new Error(msg || `Error ${res.status}`);
  }

  const diag = parseDiagnosticResponse(await res.json());
  const top = diag.findings
    .filter((f) => f.positive)
    .sort((a, b) => b.probability - a.probability)[0];
  await persistAnalysis({
    tenantId: tenantKey(orgId, userId),
    userId,
    requestId: diag.request_id,
    status: diag.abnormal ? "red" : diag.requires_review ? "yellow" : "green",
    classLabel: top ? top.label : "normal",
    confidence: top ? top.confidence : null,
    pipelineVersion: diag.pipeline_version,
    modelVersion: diag.model_version,
    resultJson: diag,
  });
  return diag;
}
