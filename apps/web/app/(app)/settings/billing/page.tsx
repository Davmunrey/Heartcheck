/** Placeholder — connect Clerk Billing or Stripe (see docs/adr/002-stripe-billing-plan.md). */
export default function BillingSettingsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Facturación</h1>
      <p className="mt-2 text-zinc-600">
        Los planes y límites por organización se derivan del plan activo (roadmap).
      </p>
      <p className="mt-4 text-sm text-zinc-500">
        Roadmap: integración Stripe / Clerk Billing documentada en el repo (
        <code className="rounded bg-zinc-100 px-1">docs/adr/002-stripe-billing-plan.md</code>
        ).
      </p>
    </div>
  );
}
