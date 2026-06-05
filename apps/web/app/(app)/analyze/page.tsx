import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { AnalyzeClient } from "./ui/analyze-client";
import { getBillingStatus } from "@/lib/billing/status";

export default async function AnalyzePage() {
  const { orgId } = await auth();
  if (!orgId) redirect("/onboarding/create-organization");
  const billing = await getBillingStatus();

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Analizar ECG</h1>
      <p className="mt-2 text-zinc-600">
        Sube una foto de tira de electrocardiograma. Resultado educativo; no es
        diagnóstico.
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
