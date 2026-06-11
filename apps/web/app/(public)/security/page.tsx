import Link from "next/link";

import { Reveal } from "../_components/reveal";

const controls = [
  {
    title: "Cada clínica, en su propia caja fuerte",
    body: "Los datos de una organización nunca se cruzan con los de otra. Aislamiento total, por diseño.",
    tag: "Aislamiento por organización",
  },
  {
    title: "Tus archivos, solo tuyos",
    body: "Los ECG se guardan en almacenamiento privado y cifrado. Nadie de fuera puede verlos.",
    tag: "Storage privado",
  },
  {
    title: "Todo queda registrado",
    body: "Cada acción deja huella en un registro a prueba de manipulación. Sabes quién hizo qué y cuándo.",
    tag: "Audit log append-only",
  },
  {
    title: "Nadie entra sin permiso",
    body: "Acceso por roles y tokens. Cada persona ve solo lo que le corresponde.",
    tag: "Roles + JWT",
  },
  {
    title: "Sin datos sensibles a la vista",
    body: "Los registros técnicos nunca incluyen información de pacientes. Cero PHI en los logs.",
    tag: "Cero PHI en logs",
  },
  {
    title: "Tú decides cuánto se guarda",
    body: "Retención y borrado bajo tu control, con límites de tamaño y velocidad para evitar abusos.",
    tag: "Retención configurable",
  },
];

export default function SecurityPage() {
  return (
    <section className="px-5 py-24 md:py-32">
      <div className="mx-auto max-w-5xl">
        <Reveal variant="stagger">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">Seguridad</p>
          <h1 className="mt-4 max-w-3xl text-[clamp(2.4rem,5vw,4.25rem)] font-black leading-[0.98] tracking-[-0.045em] text-ink">
            Tus datos, protegidos de verdad.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
            No hace falta ser experto para confiar. Esto es lo que hacemos para
            que la información de tu clínica esté segura desde el primer día — sin
            que tengas que pensar en ello.
          </p>
        </Reveal>
        <Reveal variant="stagger" as="div" className="mt-12 grid gap-4 md:grid-cols-3">
          {controls.map((c) => (
            <div key={c.title} className="flex flex-col border-2 border-line bg-surface p-6 transition-all hover:-translate-y-1 hover:border-brand hover:shadow-xl hover:shadow-brand/10">
              <h2 className="text-lg font-bold leading-snug text-ink">{c.title}</h2>
              <p className="mt-2 flex-1 text-sm leading-6 text-ink-2">{c.body}</p>
              <span className="mt-4 inline-flex self-start bg-brand-tint px-3 py-1 font-mono text-xs text-brand">{c.tag}</span>
            </div>
          ))}
        </Reveal>
        <Reveal className="mt-12 border-2 border-line bg-paper-2 p-8">
          <p className="text-lg leading-8 text-ink-2">
            Para uso clínico en producción te acompañamos en lo serio: evaluación
            de seguridad, contratos de tratamiento de datos y validación del
            modelo sobre tus propios casos.{" "}
            <Link href="/enterprise" className="font-semibold text-brand underline-offset-4 hover:underline">
              Hablar con ventas →
            </Link>
          </p>
        </Reveal>
      </div>
    </section>
  );
}
