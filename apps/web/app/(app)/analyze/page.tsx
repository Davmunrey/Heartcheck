import { AnalyzeClient } from "./ui/analyze-client";
import { getBillingStatus } from "@/lib/billing/status";

export default async function AnalyzePage() {
  // Org-optional: no Clerk Organization required. getBillingStatus() falls back
  // to a per-user tenant, and the ML API derives the tenant from the Clerk user.
  const billing = await getBillingStatus();

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">Copiloto ECG</p>
      <h1 className="mt-3 text-[clamp(2rem,4vw,3rem)] leading-[1.02]">Analizar ECG</h1>
      <p className="mt-3 text-ink-2">
        Sube una <strong className="font-semibold text-ink">señal 12 derivaciones</strong> (.npy/.csv)
        o una <strong className="font-semibold text-ink">foto</strong> de tira. Axis es apoyo a la
        decisión clínica: las salidas son probabilísticas y requieren revisión de un profesional —
        no es un diagnóstico autónomo ni sustituye un ECG clínico completo.
      </p>
      {!billing.canAnalyze ? (
        <div className="mt-8 border-2 border-warn/40 bg-warn-tint p-4 text-sm text-warn">
          Trial o plan inactivo. Activa un plan antes de analizar —{" "}
          <a href="/settings/billing" className="font-semibold underline">ver planes</a>.
        </div>
      ) : (
        <AnalyzeClient />
      )}
    </div>
  );
}
