import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { AnalysisResponse } from "@heartscan/api-client";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";
import { getAnalysisById } from "@/lib/analyze/history";
import { getT } from "@/lib/i18n";
import { PhotoResult, SignalResult } from "../ui/analysis-result";

export default async function AnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { orgId, userId } = await auth();
  const { locale, t } = await getT();
  const tenant = orgId ?? (userId ? `clerk-user:${userId}` : null);
  const analysis = tenant ? await getAnalysisById(tenant, id) : null;
  if (!analysis) notFound();

  const rj = analysis.result_json as Record<string, unknown>;
  const isSignal = Array.isArray(rj?.findings);

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <Link href="/dashboard" className="text-sm font-medium text-ink-2 transition-colors hover:text-brand">
        {t.common.back}
      </Link>

      <p className="mt-5 text-xs font-semibold uppercase tracking-[0.25em] text-brand">{t.detail.eyebrow}</p>
      <h1 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.04]">
        {isSignal ? t.detail.signal : t.detail.photo}
      </h1>
      <p className="mt-3 font-mono text-xs text-ink-3">
        {new Date(analysis.created_at).toLocaleString(locale === "en" ? "en-GB" : "es-ES", { dateStyle: "full", timeStyle: "short" })}
        {" · "}
        {analysis.request_id}
      </p>

      <div className="mt-8">
        {isSignal ? (
          <SignalResult data={rj as unknown as DiagnosticResponse} t={t.result} />
        ) : (
          <PhotoResult data={rj as unknown as AnalysisResponse} t={t.result} />
        )}
      </div>

      {!isSignal && (
        <a
          href={`/api/reports/${analysis.id}`}
          className="mt-6 inline-flex border-2 border-ink px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-ink hover:text-white"
        >
          {t.detail.downloadPdf}
        </a>
      )}
    </div>
  );
}
