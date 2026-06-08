import { BillingControls } from "./ui/billing-controls";
import { plans } from "@/lib/billing/plans";
import { getBillingStatus } from "@/lib/billing/status";

export default async function BillingSettingsPage() {
  const status = await getBillingStatus();
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-bold">Facturación</h1>
      <p className="mt-2 text-ink-2">
        Trial 7 días, checkout Stripe, portal cliente.
      </p>
      <div className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-sm">
        <p className="font-semibold">Plan actual: {status.plan}</p>
        <p className="mt-1 text-sm text-ink-2">Estado: {status.subscriptionStatus}</p>
        <p className="mt-1 text-sm text-ink-2">
          Trial restante: {status.trialDaysLeft ?? "—"} días
        </p>
        <BillingControls />
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {plans.filter((p) => p.id !== "trial").map((plan) => (
          <div key={plan.id} className="rounded-2xl border border-line bg-white p-5 shadow-sm">
            <h2 className="font-bold">{plan.name}</h2>
            <p className="mt-2 text-2xl font-bold">{plan.price}</p>
            <p className="mt-2 text-sm text-ink-2">{plan.quota}</p>
            <BillingControls planId={plan.id} />
          </div>
        ))}
      </div>
    </div>
  );
}
