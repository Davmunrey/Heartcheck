import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

export default async function DashboardPage() {
  const { orgId, userId } = await auth();
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold">Panel</h1>
      <p className="mt-2 text-zinc-600">
        Usuario: <code className="rounded bg-zinc-100 px-1">{userId}</code>
      </p>
      <p className="mt-1 text-zinc-600">
        Organización activa:{" "}
        <code className="rounded bg-zinc-100 px-1">{orgId ?? "ninguna"}</code>
      </p>
      {!orgId && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
          Crea o selecciona una organización para usar cuotas y almacenamiento
          multi-tenant.
          <Link
            href="/onboarding/create-organization"
            className="ml-2 font-medium underline"
          >
            Ir a organizaciones
          </Link>
        </p>
      )}
      <div className="mt-8">
        <Link
          href="/analyze"
          className="inline-flex rounded-lg bg-rose-600 px-4 py-2 text-white hover:bg-rose-700"
        >
          Nuevo análisis
        </Link>
      </div>
      <p className="mt-8 text-sm text-zinc-500">
        El listado de análisis persistidos en Supabase se conecta aquí cuando
        RLS + plantilla JWT estén configurados.
      </p>
    </div>
  );
}
