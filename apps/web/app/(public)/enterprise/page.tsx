export default function EnterprisePage() {
  return (
    <main className="min-h-full bg-[#17211f] px-5 py-16 text-[#f4f0e8]">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm uppercase tracking-[0.25em] text-[#d7ff63]">Enterprise</p>
        <h1 className="mt-3 text-5xl font-black tracking-[-0.04em]">
          Paquete hospitalario.
        </h1>
        <p className="mt-5 leading-7 text-white/70">
          Para compra enterprise: evaluación seguridad, contrato DPA/BAA-ready,
          integración SSO, despliegue cloud privado/on-prem, validación modelo
          sobre cohorte local, soporte SLA.
        </p>
        <div className="mt-10 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="font-semibold">Contacto comercial</p>
          <p className="mt-2 text-sm text-white/70">
            Define email corporativo en `NEXT_PUBLIC_SALES_EMAIL`.
          </p>
          <a
            className="mt-5 inline-flex rounded-full bg-[#d7ff63] px-5 py-3 font-semibold text-[#17211f]"
            href={`mailto:${process.env.NEXT_PUBLIC_SALES_EMAIL ?? "sales@heartscan.local"}?subject=HeartScan Enterprise`}
          >
            Solicitar evaluación
          </a>
        </div>
      </div>
    </main>
  );
}

