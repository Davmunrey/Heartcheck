export default function EnterprisePage() {
  const salesEmail = process.env.NEXT_PUBLIC_SALES_EMAIL ?? "sales@axis.health";
  return (
    <section className="bg-scope px-5 py-20 text-scope-ink">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">Enterprise</p>
        <h1 className="mt-3 text-5xl font-black tracking-[-0.04em] text-white">
          Paquete hospitalario.
        </h1>
        <p className="mt-5 leading-7 text-scope-ink/70">
          Para compra enterprise: evaluación seguridad, contrato DPA/BAA-ready,
          integración SSO, despliegue cloud privado/on-prem, validación modelo
          sobre cohorte local, soporte SLA.
        </p>
        <div className="mt-10 border-2 border-white/10 bg-white/5 p-6">
          <p className="font-semibold text-white">Contacto comercial</p>
          <p className="mt-2 text-sm text-scope-ink/70">
            Escríbenos para coordinar la evaluación de seguridad y el contrato.
          </p>
          <a
            className="mt-5 inline-flex bg-brand px-5 py-3 font-semibold text-white transition-colors hover:bg-brand-bright"
            href={`mailto:${salesEmail}?subject=Axis Enterprise`}
          >
            Solicitar evaluación
          </a>
        </div>
      </div>
    </section>
  );
}
