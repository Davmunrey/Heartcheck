import { auth } from "@clerk/nextjs/server";
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

export default async function DashboardPage() {
  const { orgId, userId } = await auth();
  const billing = await getBillingStatus();

  // Single-tenant friendly: read history for the active org or, when no org is
  // active, the per-user tenant. Uses the service-role read in
  // lib/analyze/history (returns [] when Supabase isn't configured).
  const tenant = orgId ?? (userId ? `clerk-user:${userId}` : null);
  const analyses: Analysis[] = tenant ? await getRecentAnalyses(tenant) : [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Panel Axis</h1>
          <p className="mt-2 text-ink-2">
            Copilot ECG, auditoría, cuotas, trial.
          </p>
        </div>
        <div className="rounded-2xl border border-line bg-white p-4 text-sm shadow-sm">
          <p className="font-semibold">Plan: {billing.plan}</p>
          <p className="mt-1 text-ink-2">Estado: {billing.subscriptionStatus}</p>
          <p className="mt-1 text-ink-2">
            Trial: {billing.trialDaysLeft ?? "—"} días restantes
          </p>
          <Link href="/settings/billing" className="mt-3 inline-flex text-signal-700 underline">
            Gestionar billing
          </Link>
        </div>
      </div>
      <p className="mt-2 text-ink-2">
        Usuario: <code className="rounded bg-paper-2 px-1">{userId}</code>
      </p>
      <p className="mt-1 text-ink-2">
        Organización activa:{" "}
        <code className="rounded bg-paper-2 px-1">{orgId ?? "ninguna"}</code>
      </p>
      {!orgId && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
          Crea o selecciona una organización para usar cuotas y almacenamiento
          multi-tenant.
          <Link
            href="/onboarding/create-organization"
            className="ml-2 font-medium underline"
          >
            Ir a organizaciones
          </Link>
        </p>
      )}
      <div className="mt-8">
        <Link
          href="/analyze"
          className={`inline-flex rounded-lg px-4 py-2 text-white ${
            billing.canAnalyze ? "bg-brand hover:bg-brand-strong" : "bg-ink-3"
          }`}
        >
          Nuevo análisis
        </Link>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          ["Security", "RLS tenant, private storage, audit chain"],
          ["Workflow", "quality gate → AI assist → doctor review"],
          ["Data", "retention, delete helpers, no PHI logs"],
        ].map(([title, body]) => (
          <div key={title} className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <h2 className="font-semibold">{title}</h2>
            <p className="mt-2 text-sm text-ink-2">{body}</p>
          </div>
        ))}
      </div>
      {tenant && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Análisis recientes</h2>
          {analyses.length === 0 && (
            <p className="mt-3 text-sm text-ink-3">
              Aún no hay análisis. Sube tu primer ECG.
            </p>
          )}
          {analyses.length > 0 && (
            <ul className="mt-3 divide-y divide-line rounded-lg border border-line">
              {analyses.map((a) => (
                <li key={a.id} className="flex items-center justify-between px-4 py-3 text-sm">
                  <div>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        a.status === "green"
                          ? "bg-green-100 text-green-800"
                          : a.status === "red"
                          ? "bg-red-100 text-red-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {a.status}
                    </span>
                    <span className="ml-2 text-ink-2">{a.class_label ?? "—"}</span>
                    {a.confidence && (
                      <span className="ml-2 text-ink-3">({a.confidence})</span>
                    )}
                  </div>
                  <span className="text-ink-3">
                    {new Date(a.created_at).toLocaleString("es-ES", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
