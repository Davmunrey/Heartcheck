import { Reveal } from "../_components/reveal";

const value = [
  {
    title: "Despliegue a tu medida",
    body: "Cloud privado u on-prem. Tus datos se quedan donde tú quieras, con tu SSO y tus políticas.",
  },
  {
    title: "Validado con tus casos",
    body: "Ajustamos y medimos el modelo sobre tu propia cohorte antes de ir a producción. Sin sorpresas.",
  },
  {
    title: "Contrato y soporte serios",
    body: "DPA/BAA listos, evaluación de seguridad y soporte con SLA. Acompañamiento real, no un email genérico.",
  },
];

export default function EnterprisePage() {
  const salesEmail = process.env.NEXT_PUBLIC_SALES_EMAIL ?? "sales@axis.health";
  return (
    <section className="relative overflow-hidden bg-scope px-5 py-24 text-scope-ink md:py-32">
      <div className="orb-a pointer-events-none absolute -left-20 top-10 h-72 w-72 rounded-full bg-brand/20 blur-[100px]" />
      <div className="orb-b pointer-events-none absolute -right-16 bottom-10 h-64 w-64 rounded-full bg-signal/15 blur-[100px]" />
      <div className="relative mx-auto max-w-5xl">
        <Reveal variant="stagger">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">Enterprise</p>
          <h1 className="mt-4 max-w-3xl text-[clamp(2.4rem,5.5vw,4.5rem)] font-black leading-[0.98] tracking-[-0.045em] text-white">
            Axis para tu hospital, sin fricción.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-scope-ink/70">
            Lo montamos a tu medida y lo validamos con tus casos. Tú pones las
            reglas; nosotros hacemos que funcione el primer día.
          </p>
        </Reveal>
        <Reveal variant="stagger" as="div" className="mt-12 grid gap-4 md:grid-cols-3">
          {value.map((v) => (
            <div key={v.title} className="border-2 border-white/10 bg-white/5 p-6 transition-colors hover:border-brand-bright/40 hover:bg-white/[0.08]">
              <h2 className="text-xl font-bold text-white">{v.title}</h2>
              <p className="mt-2 text-sm leading-6 text-scope-ink/65">{v.body}</p>
            </div>
          ))}
        </Reveal>
        <Reveal className="mt-12 border-2 border-white/10 bg-white/5 p-8">
          <p className="text-xl font-semibold text-white">¿Hablamos?</p>
          <p className="mt-2 max-w-xl text-sm leading-6 text-scope-ink/70">
            Cuéntanos tu caso y coordinamos una demo, la evaluación de seguridad y
            el contrato. Respondemos rápido.
          </p>
          <a
            className="mt-6 inline-flex bg-white px-6 py-3 font-semibold text-scope transition-colors hover:bg-scope-ink"
            href={`mailto:${salesEmail}?subject=Axis Enterprise`}
          >
            Solicitar demo
          </a>
        </Reveal>
      </div>
    </section>
  );
}
