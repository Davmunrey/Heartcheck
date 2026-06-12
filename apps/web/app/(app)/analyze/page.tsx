import { AnalyzeClient } from "./ui/analyze-client";
import { getBillingStatus } from "@/lib/billing/status";
import { getT } from "@/lib/i18n";

export default async function AnalyzePage() {
  // Org-optional: no Clerk Organization required. getBillingStatus() falls back
  // to a per-user tenant, and the ML API derives the tenant from the Clerk user.
  const billing = await getBillingStatus();
  const { t } = await getT();
  const a = t.analyze;

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">{a.eyebrow}</p>
      <h1 className="mt-3 text-[clamp(2rem,4vw,3rem)] leading-[1.02]">{a.title}</h1>
      <p className="mt-3 text-ink-2">{a.intro}</p>
      {!billing.canAnalyze ? (
        <div className="mt-8 border-2 border-warn/40 bg-warn-tint p-4 text-sm text-warn">
          {a.inactive}{" "}
          <a href="/settings/billing" className="font-semibold underline">
            {a.seePlans}
          </a>
          .
        </div>
      ) : (
        <AnalyzeClient t={a} result={t.result} />
      )}
      <p className="mt-10 border-t-2 border-line pt-4 text-xs leading-5 text-ink-3">{a.privacy}</p>
    </div>
  );
}
