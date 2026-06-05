import Link from "next/link";
import { plans } from "@/lib/billing/plans";

export default function PricingPage() {
  return (
    <main className="min-h-full bg-[#f4f0e8] px-5 py-16 text-[#17211f]">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm uppercase tracking-[0.25em] text-[#b54708]">Pricing</p>
        <h1 className="mt-3 max-w-3xl text-5xl font-black tracking-[-0.04em]">
          Trial 7 días. Luego plan por organización.
        </h1>
        <p className="mt-4 max-w-2xl text-[#46534f]">
          Facturación por hospital/clínica. Uso médico real requiere contrato,
          validación local, privacidad, seguridad, aprobación regulatoria.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-4">
          {plans.map((plan) => (
            <article key={plan.id} className="rounded-3xl border border-[#17211f]/10 bg-white/70 p-6 shadow-sm">
              <h2 className="text-xl font-black">{plan.name}</h2>
              <p className="mt-2 text-3xl font-black">{plan.price}</p>
              <p className="mt-2 text-sm text-[#46534f]">{plan.tagline}</p>
              <p className="mt-4 rounded-full bg-[#d7ff63] px-3 py-1 text-sm font-semibold">
                {plan.quota}
              </p>
              <ul className="mt-5 space-y-2 text-sm text-[#46534f]">
                {plan.features.map((feature) => (
                  <li key={feature}>✓ {feature}</li>
                ))}
              </ul>
              <Link
                href={plan.id === "enterprise" ? "/enterprise" : "/sign-up"}
                className="mt-6 inline-flex rounded-full bg-[#17211f] px-4 py-2 text-sm font-semibold text-[#f4f0e8]"
              >
                {plan.id === "enterprise" ? "Contactar" : "Empezar"}
              </Link>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}

