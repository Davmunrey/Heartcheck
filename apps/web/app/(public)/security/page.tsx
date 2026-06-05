const controls = [
  "Clerk Organizations como tenant boundary",
  "Supabase RLS por `org_id`",
  "Private storage, path `{org_id}/{uuid}`",
  "Audit log hash-chain append-only",
  "JWT + optional internal API token",
  "Rate limits y límites archivo 10MB",
  "No PHI en logs de app",
  "Retention/disposal SQL helpers",
  "Webhook signatures Clerk/Stripe",
];

export default function SecurityPage() {
  return (
    <main className="min-h-full bg-[#f4f0e8] px-5 py-16 text-[#17211f]">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm uppercase tracking-[0.25em] text-[#b54708]">Security</p>
        <h1 className="mt-3 text-5xl font-black tracking-[-0.04em]">
          Ciberseguridad B2B desde día cero.
        </h1>
        <p className="mt-5 max-w-3xl leading-7 text-[#46534f]">
          Base preparada para clínicas/hospitales, pero producción sanitaria
          exige pentest, DPA/BAA, DPIA, validación clínica, controles SOC2/ISO.
        </p>
        <div className="mt-10 grid gap-3 md:grid-cols-3">
          {controls.map((control) => (
            <div key={control} className="rounded-2xl border border-[#17211f]/10 bg-white/70 p-4 text-sm font-semibold">
              {control}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

