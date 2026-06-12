import Link from "next/link";

export default function AppNotFound() {
  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">404</p>
      <h1 className="mt-3 text-[clamp(2rem,5vw,3rem)] leading-[1.04]">No encontrado</h1>
      <p className="mt-3 text-ink-2">
        Ese recurso no existe o no pertenece a tu cuenta.
      </p>
      <Link
        href="/dashboard"
        className="mt-6 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        Volver al panel
      </Link>
    </div>
  );
}
