import { auth, currentUser } from "@clerk/nextjs/server";
import Link from "next/link";
import { getRecentAnalyses } from "@/lib/analyze/history";
import { getBillingStatus } from "@/lib/billing/status";
import { getT } from "@/lib/i18n";

interface Analysis {
  id: string;
  created_at: string;
  status: string;
  class_label: string | null;
  confidence: string | null;
  request_id: string;
}

export default async function DashboardPage() {
  const { orgId, userId } = await auth();
  const user = await currentUser();
  const billing = await getBillingStatus();
  const { locale, t } = await getT();
  const d = t.dashboard;

  const tenant = orgId ?? (userId ? `clerk-user:${userId}` : null);
  const analyses: Analysis[] = tenant ? await getRecentAnalyses(tenant) : [];
  const email = user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses?.[0]?.emailAddress;
  const tenantLabel = orgId ? d.team : d.personal;

  const STATUS: Record<string, { label: string; cls: string }> = {
    green: { label: d.status_green, cls: "border-ok/40 bg-ok-tint text-ok" },
    yellow: { label: d.status_yellow, cls: "border-warn/40 bg-warn-tint text-warn" },
    red: { label: d.status_red, cls: "border-crit/40 bg-crit-tint text-crit" },
  };

  return (
    <div className="mx-auto max-w-5xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">{d.eyebrow}</p>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-[clamp(2rem,4vw,3rem)] leading-[1.02]">{d.title}</h1>
          <p className="mt-3 text-ink-2">
            {email && <span className="font-medium text-ink">{email}</span>}
            <span className="ml-2 font-mono text-xs uppercase tracking-wider text-ink-3">· {tenantLabel}</span>
          </p>
        </div>
        <Link
          href="/analyze"
          className="group inline-flex items-center gap-2.5 bg-brand px-6 py-3.5 font-semibold text-white shadow-lg shadow-brand/20 transition-all hover:bg-brand-strong hover:shadow-brand/30"
        >
          {d.newAnalysis}
          <span className="transition-transform group-hover:translate-x-1">→</span>
        </Link>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-4 border-2 border-line bg-surface px-6 py-5">
        {[
          [d.plan, billing.plan],
          [d.status, billing.subscriptionStatus],
          [d.trial, billing.trialDaysLeft != null ? `${billing.trialDaysLeft} ${d.days}` : "—"],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">{k}</p>
            <p className="mt-1 font-semibold capitalize text-ink">{v}</p>
          </div>
        ))}
        <Link href="/settings/billing" className="ml-auto text-sm font-semibold text-brand underline-offset-4 hover:underline">
          {d.manageBilling}
        </Link>
      </div>

      <section className="mt-12">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">{d.recent}</h2>
          {analyses.length > 0 && (
            <span className="font-mono text-xs text-ink-3">{d.records(analyses.length)}</span>
          )}
        </div>

        {analyses.length === 0 ? (
          <div className="mt-4 border-2 border-dashed border-line-2 bg-surface px-6 py-14 text-center">
            <p className="text-ink-2">{d.emptyTitle}</p>
            <Link href="/analyze" className="mt-5 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong">
              {d.emptyCta}
            </Link>
          </div>
        ) : (
          <ul className="mt-4 divide-y-2 divide-line border-2 border-line bg-surface">
            {analyses.map((a) => {
              const s = STATUS[a.status] ?? { label: a.status, cls: "border-line-2 bg-paper-2 text-ink-2" };
              return (
                <li key={a.id}>
                  <Link
                    href={`/analyze/${a.id}`}
                    className="group flex flex-wrap items-center gap-x-4 gap-y-2 px-6 py-4 transition-colors hover:bg-paper-2"
                  >
                    <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${s.cls}`}>
                      <span className="size-1.5 rounded-full bg-current" />
                      {s.label}
                    </span>
                    <span className="font-medium text-ink">{a.class_label ?? "—"}</span>
                    {a.confidence && <span className="text-sm text-ink-3">{d.confidence} {a.confidence}</span>}
                    <span className="ml-auto flex items-center gap-2 font-mono text-xs text-ink-3">
                      {new Date(a.created_at).toLocaleString(locale === "en" ? "en-GB" : "es-ES", { dateStyle: "medium", timeStyle: "short" })}
                      <span className="text-ink-2 transition-transform group-hover:translate-x-0.5">→</span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="mt-12">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">{d.howEyebrow}</p>
        <div className="mt-4 grid gap-px border-2 border-line bg-line md:grid-cols-3">
          {d.steps.map(([n, title, body]) => (
            <div key={n} className="bg-surface p-6">
              <span className="font-mono text-sm text-signal">{n}</span>
              <h3 className="mt-2 text-base font-bold text-ink">{title}</h3>
              <p className="mt-2 text-sm text-ink-2">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-ink-3">{d.disclaimer}</p>
      </section>
    </div>
  );
}
