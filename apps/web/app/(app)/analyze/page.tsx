import { AnalyzeClient } from "./ui/analyze-client";
import { getBillingStatus } from "@/lib/billing/status";

export default async function AnalyzePage() {
  // Org-optional: no Clerk Organization required. getBillingStatus() falls back
  // to a per-user tenant, and the ML API derives the tenant from the Clerk user.
  const billing = await getBillingStatus();

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Analizar ECG</h1>
      <p className="mt-2 text-ink-2">
        Sube una <strong>foto</strong> de tira de ECG o una <strong>señal 12
        derivaciones</strong> (.npy/.csv). Axis es un copilot de apoyo a la
        decisión clínica: las salidas son probabilísticas y requieren revisión
        de un profesional. No es un diagnóstico autónomo ni sustituye un ECG
        clínico completo.
      </p>
      {!billing.canAnalyze ? (
        <div className="mt-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
          Trial/plan inactivo. Activa plan antes de analizar.
        </div>
      ) : (
        <AnalyzeClient />
      )}
    </div>
  );
}
