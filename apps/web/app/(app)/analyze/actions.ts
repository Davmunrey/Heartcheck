"use server";

import { auth } from "@clerk/nextjs/server";
import { parseAnalysisResponse, type AnalysisResponse } from "@heartscan/api-client";

export async function analyzeImageAction(formData: FormData): Promise<AnalysisResponse> {
  const { userId, orgId, getToken } = await auth();
  if (!userId) throw new Error("Unauthorized");
  if (!orgId) throw new Error("Selecciona una organización (Clerk) antes de analizar.");

  const file = formData.get("file");
  if (!(file instanceof Blob)) {
    throw new Error("Falta el archivo de imagen.");
  }

  const mlUrl = process.env.ML_API_URL;
  if (!mlUrl) {
    throw new Error("ML_API_URL no está configurado.");
  }

  const token = await getToken();
  if (!token) throw new Error("No se pudo obtener el token de sesión.");

  const internal = process.env.ML_API_INTERNAL_TOKEN;
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${mlUrl.replace(/\/$/, "")}/api/v1/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Organization-Id": orgId,
      ...(internal ? { "X-Internal-Token": internal } : {}),
      "Accept-Language": "es",
    },
    body: fd,
  });

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
