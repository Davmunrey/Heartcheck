import { auth, currentUser } from "@clerk/nextjs/server";
import Link from "next/link";
import { getRecentAnalyses } from "@/lib/analyze/history";
import { getBillingStatus } from "@/lib/billing/status";

interface Analysis {
  id: string;
  created_at: string;
  status: string;
  class_label: string | null;
  confidence: string | null;
  request_id: string;
}

const STATUS: Record<string, { label: string; cls: string }> = {
  green: { label: "Normal", cls: "border-ok/40 bg-ok-tint text-ok" },
  yellow: { label: "Revisar", cls: "border-warn/40 bg-warn-tint text-warn" },
  red: { label: "Atención", cls: "border-crit/40 bg-crit-tint text-crit" },
};

const STEPS = [
  ["01", "Quality gate", "Cada ECG pasa un control de calidad antes de interpretarse."],
  ["02", "Copiloto IA", "Lectura calibrada de 27 afecciones con AUROC por hallazgo."],
  ["03", "Revisión médica", "Las salidas son apoyo a la decisión — el criterio clínico decide."],
];

export default async function DashboardPage() {
  const { orgId, userId } = await auth();
  const user = await currentUser();
  const billing = await getBillingStatus();

  const tenant = orgId ?? (userId ? `clerk-user:${userId}` : null);
  const analyses: Analysis[] = tenant ? await getRecentAnalyses(tenant) : [];
  const email = user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses?.[0]?.emailAddress;
  const tenantLabel = orgId ? "Equipo" : "Cuenta personal";

  return (
    <div className="mx-auto max-w-5xl px-5 py-12">
      {/* Header */}
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">Panel</p>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-[clamp(2rem,4vw,3rem)] leading-[1.02]">Tu copiloto ECG</h1>
          <p className="mt-3 text-ink-2">
            {email && <span className="font-medium text-ink">{email}</span>}
            <span className="ml-2 font-mono text-xs uppercase tracking-wider text-ink-3">· {tenantLabel}</span>
          </p>
        </div>
        <Link
          href="/analyze"
          className="group inline-flex items-center gap-2.5 bg-brand px-6 py-3.5 font-semibold text-white shadow-lg shadow-brand/20 transition-all hover:bg-brand-strong hover:shadow-brand/30"
        >
          Nuevo análisis
          <span className="transition-transform group-hover:translate-x-1">→</span>
        </Link>
      </div>

      {/* Plan strip */}
      <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-4 border-2 border-line bg-surface px-6 py-5">
        {[
          ["Plan", billing.plan],
          ["Estado", billing.subscriptionStatus],
          ["Trial", billing.trialDaysLeft != null ? `${billing.trialDaysLeft} días` : "—"],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">{k}</p>
            <p className="mt-1 font-semibold capitalize text-ink">{v}</p>
          </div>
        ))}
        <Link
          href="/settings/billing"
          className="ml-auto text-sm font-semibold text-brand underline-offset-4 hover:underline"
        >
          Gestionar facturación →
        </Link>
      </div>

      {/* Recent analyses */}
      <section className="mt-12">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Análisis recientes</h2>
          {analyses.length > 0 && (
            <span className="font-mono text-xs text-ink-3">{analyses.length} registro{analyses.length === 1 ? "" : "s"}</span>
          )}
        </div>

        {analyses.length === 0 ? (
          <div className="mt-4 border-2 border-dashed border-line-2 bg-surface px-6 py-14 text-center">
            <p className="text-ink-2">Aún no has analizado ningún ECG.</p>
            <Link
              href="/analyze"
              className="mt-5 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong"
            >
              Subir tu primer ECG
            </Link>
          </div>
        ) : (
          <ul className="mt-4 divide-y-2 divide-line border-2 border-line bg-surface">
            {analyses.map((a) => {
              const s = STATUS[a.status] ?? { label: a.status, cls: "border-line-2 bg-paper-2 text-ink-2" };
              return (
                <li key={a.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${s.cls}`}>
                    <span className="size-1.5 rounded-full bg-current" />
                    {s.label}
                  </span>
                  <span className="font-medium text-ink">{a.class_label ?? "—"}</span>
                  {a.confidence && <span className="text-sm text-ink-3">conf. {a.confidence}</span>}
                  <span className="ml-auto font-mono text-xs text-ink-3">
                    {new Date(a.created_at).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" })}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* How it works */}
      <section className="mt-12">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">Cómo trabaja Axis</p>
        <div className="mt-4 grid gap-px border-2 border-line bg-line md:grid-cols-3">
          {STEPS.map(([n, title, body]) => (
            <div key={n} className="bg-surface p-6">
              <span className="font-mono text-sm text-signal">{n}</span>
              <h3 className="mt-2 text-base font-bold text-ink">{title}</h3>
              <p className="mt-2 text-sm text-ink-2">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-ink-3">
          Apoyo a la decisión clínica, probabilístico, con revisión humana — no es un diagnóstico
          autónomo ni sustituye un ECG clínico completo.
        </p>
      </section>
    </div>
  );
}
