const faqs = [
  {
    q: "¿Axis diagnostica?",
    a: "No. Axis es un copilot clínico: ofrece probabilidades y ayuda interpretativa orientativa. La decisión y el diagnóstico son siempre del médico. No sustituye una valoración clínica.",
  },
  {
    q: "¿Qué predice el modelo?",
    a: "Sobre ECG de 12 derivaciones, probabilidades calibradas para las superclases diagnósticas NORM, MI, STTC, CD e HYP, con umbrales por clase y revisión humana.",
  },
  {
    q: "¿Cómo se protegen los datos?",
    a: "Aislamiento por organización con Clerk + RLS de Supabase, almacenamiento privado, audit log append-only, y sin PHI en los logs de aplicación. Ver la página de Seguridad.",
  },
  {
    q: "¿Puedo usarlo en producción clínica?",
    a: "Requiere contrato, validación local sobre tu cohorte, DPA/BAA y revisión regulatoria. El trial es para evaluación técnica.",
  },
];

export default function FaqPage() {
  return (
    <section className="px-5 py-20">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">FAQ</p>
        <h1 className="mt-3 text-5xl font-black tracking-[-0.04em] text-ink">Preguntas frecuentes</h1>
        <p className="mt-4 text-ink-2">
          Axis ofrece una lectura orientativa y educativa. No sustituye una valoración médica.
        </p>
        <dl className="mt-10 divide-y-2 divide-line border-y-2 border-line">
          {faqs.map((item) => (
            <div key={item.q} className="py-6">
              <dt className="text-lg font-bold text-ink">{item.q}</dt>
              <dd className="mt-2 leading-7 text-ink-2">{item.a}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
