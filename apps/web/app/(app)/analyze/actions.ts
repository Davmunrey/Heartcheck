"use server";

import { auth } from "@clerk/nextjs/server";
import { parseAnalysisResponse, type AnalysisResponse } from "@heartscan/api-client";
import { validateAnalyzeFile } from "@/lib/analyze/validation";
import { parseDiagnosticResponse, type DiagnosticResponse } from "@/lib/analyze/diagnostic";

const SIGNAL_MAX_BYTES = 10 * 1024 * 1024;

export async function analyzeImageAction(formData: FormData): Promise<AnalysisResponse> {
  const { userId, orgId, getToken } = await auth();
  if (!userId) throw new Error("Unauthorized");
  if (!orgId) throw new Error("Selecciona una organización (Clerk) antes de analizar.");

  const file = validateAnalyzeFile(formData.get("file"));

  const mlUrl = process.env.ML_API_URL;
  if (!mlUrl) {
    throw new Error("ML_API_URL no está configurado.");
  }

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
        "X-Organization-Id": orgId,
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
  return parseAnalysisResponse(json);
}

export async function analyzeSignalAction(formData: FormData): Promise<DiagnosticResponse> {
  const { userId, orgId, getToken } = await auth();
  if (!userId) throw new Error("Unauthorized");
  if (!orgId) throw new Error("Selecciona una organización (Clerk) antes de analizar.");

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

  const mlUrl = process.env.ML_API_URL;
  if (!mlUrl) throw new Error("ML_API_URL no está configurado.");

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
        "X-Organization-Id": orgId,
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

  return parseDiagnosticResponse(await res.json());
}
