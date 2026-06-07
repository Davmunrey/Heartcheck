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
    <section className="px-5 py-20">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">Security</p>
        <h1 className="mt-3 text-5xl font-black tracking-[-0.04em] text-ink">
          Ciberseguridad B2B desde día cero.
        </h1>
        <p className="mt-5 max-w-3xl leading-7 text-ink-2">
          Base preparada para clínicas/hospitales, pero producción sanitaria
          exige pentest, DPA/BAA, DPIA, validación clínica, controles SOC2/ISO.
        </p>
        <div className="mt-10 grid gap-3 md:grid-cols-3">
          {controls.map((control) => (
            <div key={control} className="border-2 border-line bg-surface p-4 text-sm font-semibold text-ink">
              {control}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
