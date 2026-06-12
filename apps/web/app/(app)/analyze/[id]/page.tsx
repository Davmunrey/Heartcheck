import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { AnalysisResponse } from "@heartscan/api-client";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";
import { getAnalysisById } from "@/lib/analyze/history";
import { PhotoResult, SignalResult } from "../ui/analysis-result";

export default async function AnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { orgId, userId } = await auth();
  const tenant = orgId ?? (userId ? `clerk-user:${userId}` : null);
  const analysis = tenant ? await getAnalysisById(tenant, id) : null;
  if (!analysis) notFound();

  const rj = analysis.result_json as Record<string, unknown>;
  const isSignal = Array.isArray(rj?.findings);

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <Link href="/dashboard" className="text-sm font-medium text-ink-2 transition-colors hover:text-brand">
        ← Panel
      </Link>

      <p className="mt-5 text-xs font-semibold uppercase tracking-[0.25em] text-brand">Análisis</p>
      <h1 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.04]">
        {isSignal ? "Señal 12 derivaciones" : "Cribado por foto"}
      </h1>
      <p className="mt-3 font-mono text-xs text-ink-3">
        {new Date(analysis.created_at).toLocaleString("es-ES", { dateStyle: "full", timeStyle: "short" })}
        {" · "}
        {analysis.request_id}
      </p>

      <div className="mt-8">
        {isSignal ? (
          <SignalResult data={rj as unknown as DiagnosticResponse} />
        ) : (
          <PhotoResult data={rj as unknown as AnalysisResponse} />
        )}
      </div>

      {!isSignal && (
        <a
          href={`/api/reports/${analysis.id}`}
          className="mt-6 inline-flex border-2 border-ink px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-ink hover:text-white"
        >
          Descargar informe PDF
        </a>
      )}
    </div>
  );
}
