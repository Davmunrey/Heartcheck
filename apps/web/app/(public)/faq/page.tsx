import Link from "next/link";

import { Reveal } from "../_components/reveal";

const faqs = [
  {
    q: "¿Axis diagnostica por mí?",
    a: "No. Axis es un copiloto: lee el ECG, señala lo que ve y su nivel de confianza. La decisión y el diagnóstico son siempre tuyos. Es una segunda opinión, no un veredicto.",
  },
  {
    q: "¿Qué detecta exactamente?",
    a: "Sobre un ECG de 12 derivaciones, Axis revisa 27 afecciones a la vez —arritmias, bloqueos, signos de infarto, cambios isquémicos y más— y te las presenta priorizadas, marcando lo que conviene revisar primero.",
  },
  {
    q: "¿Cuánto tarda?",
    a: "Unos 20 segundos por ECG. Subes la imagen, Axis la lee y te devuelve un informe claro. Sin esperas, sin instalaciones.",
  },
  {
    q: "¿Están seguros mis datos?",
    a: "Sí. Cada clínica trabaja aislada, los archivos se guardan cifrados y nada sensible aparece en los registros. Lo contamos en lenguaje claro en la página de Seguridad.",
  },
  {
    q: "¿Puedo usarlo con pacientes reales?",
    a: "El trial es para que lo pruebes a fondo. Para uso clínico en producción lo validamos sobre tus propios casos y cerramos el contrato y los permisos necesarios. Te acompañamos en todo.",
  },
];

export default function FaqPage() {
  return (
    <section className="px-5 py-24 md:py-32">
      <div className="mx-auto max-w-3xl">
        <Reveal variant="stagger">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">FAQ</p>
          <h1 className="mt-4 text-[clamp(2.4rem,5vw,4.25rem)] font-black leading-[0.98] tracking-[-0.045em] text-ink">
            Preguntas frecuentes
          </h1>
          <p className="mt-5 text-lg leading-8 text-ink-2">
            Lo esencial, sin letra pequeña. Axis te ayuda a leer ECG más rápido —
            tú siempre tienes la última palabra.
          </p>
        </Reveal>
        <Reveal variant="stagger" as="dl" className="mt-12 divide-y-2 divide-line border-y-2 border-line">
          {faqs.map((item) => (
            <div key={item.q} className="py-6">
              <dt className="text-lg font-bold text-ink">{item.q}</dt>
              <dd className="mt-2 leading-7 text-ink-2">{item.a}</dd>
            </div>
          ))}
        </Reveal>
        <Reveal className="mt-12 flex flex-wrap items-center gap-4">
          <Link href="/sign-up" className="bg-brand px-6 py-3 font-semibold text-white transition-colors hover:bg-brand-strong">
            Empezar trial 7 días
          </Link>
          <Link href="/copilot" className="font-semibold text-ink underline-offset-4 hover:text-brand hover:underline">
            Ver cómo funciona
          </Link>
        </Reveal>
      </div>
    </section>
  );
}
