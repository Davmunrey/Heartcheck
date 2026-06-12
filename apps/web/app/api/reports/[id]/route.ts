import { auth } from "@clerk/nextjs/server";
import { getAnalysisById } from "@/lib/analyze/history";

/**
 * Stream a PDF report for a saved photo analysis. Fetches the stored result
 * (tenant-scoped) and proxies it to the ML API /reports/pdf with the Clerk
 * session token + internal token, then streams the PDF back as a download.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { userId, orgId, getToken } = await auth();
  if (!userId) return new Response("Unauthorized", { status: 401 });

  const tenant = orgId ?? `clerk-user:${userId}`;
  const analysis = await getAnalysisById(tenant, id);
  if (!analysis) return new Response("Not found", { status: 404 });

  const rj = analysis.result_json as Record<string, unknown>;
  if (Array.isArray(rj?.findings)) {
    return new Response("El informe PDF está disponible para análisis por foto.", { status: 400 });
  }

  const token = await getToken();
  if (!token) return new Response("Unauthorized", { status: 401 });

  const mlUrl = (process.env.ML_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const internal = process.env.ML_API_INTERNAL_TOKEN;

  const res = await fetch(`${mlUrl}/api/v1/reports/pdf`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(orgId ? { "X-Organization-Id": orgId } : {}),
      ...(internal ? { "X-Internal-Token": internal } : {}),
    },
    body: JSON.stringify({ analysis: rj, app_version: "web", locale: "es" }),
  });

  if (!res.ok) {
    return new Response("No se pudo generar el informe PDF.", { status: 502 });
  }

  return new Response(await res.arrayBuffer(), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="axis-${id}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}
