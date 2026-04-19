import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2 font-semibold">
            <span aria-hidden>♡</span>
            HeartScan
            <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
              BETA
            </span>
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/faq" className="text-zinc-600 hover:text-zinc-900">
              FAQ
            </Link>
            <Link href="/sign-in" className="text-zinc-600 hover:text-zinc-900">
              Entrar
            </Link>
            <Link
              href="/sign-up"
              className="rounded-lg bg-zinc-900 px-3 py-1.5 text-white hover:bg-zinc-800"
            >
              Crear cuenta
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto flex max-w-3xl flex-1 flex-col gap-8 px-4 py-16">
        <h1 className="text-4xl font-bold tracking-tight">
          ECG en la nube, listo para integrar
        </h1>
        <p className="text-lg text-zinc-600">
          Informe educativo a partir de una foto de electrocardiograma. Misma API
          para web y móvil.{" "}
          <strong className="text-zinc-800">No es diagnóstico clínico.</strong>
        </p>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/dashboard"
            className="rounded-lg bg-rose-600 px-5 py-2.5 font-medium text-white hover:bg-rose-700"
          >
            Abrir consola
          </Link>
          <a
            href="https://github.com"
            className="rounded-lg border border-zinc-300 px-5 py-2.5 font-medium hover:bg-zinc-100"
          >
            Documentación
          </a>
        </div>
        <p className="text-sm text-zinc-500">
          Multi-tenant con Clerk Organizations + Supabase. Despliegue: Next.js en
          Vercel, ML API aparte (Fly.io).
        </p>
      </main>
    </div>
  );
}
