import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { createSupabaseForUser } from "@/lib/supabase/server";

interface Analysis {
  id: string;
  created_at: string;
  status: string;
  class_label: string | null;
  confidence: string | null;
  request_id: string;
}

export default async function DashboardPage() {
  const { orgId, userId } = await auth();

  let analyses: Analysis[] | null = null;
  let fetchError: string | null = null;

  if (orgId) {
    const supabase = await createSupabaseForUser();
    if (supabase) {
      const { data, error } = await supabase
        .from("analyses")
        .select("id, created_at, status, class_label, confidence, request_id")
        .order("created_at", { ascending: false })
        .limit(20);
      if (error) {
        fetchError = error.message;
      } else {
        analyses = data as Analysis[];
      }
    }
  }

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
      {orgId && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Análisis recientes</h2>
          {fetchError && (
            <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              Error al cargar análisis: {fetchError}
            </p>
          )}
          {!fetchError && analyses && analyses.length === 0 && (
            <p className="mt-3 text-sm text-zinc-500">
              Aún no hay análisis. Sube tu primer ECG.
            </p>
          )}
          {!fetchError && analyses && analyses.length > 0 && (
            <ul className="mt-3 divide-y divide-zinc-100 rounded-lg border border-zinc-200">
              {analyses.map((a) => (
                <li key={a.id} className="flex items-center justify-between px-4 py-3 text-sm">
                  <div>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        a.status === "green"
                          ? "bg-green-100 text-green-800"
                          : a.status === "red"
                          ? "bg-red-100 text-red-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {a.status}
                    </span>
                    <span className="ml-2 text-zinc-700">{a.class_label ?? "—"}</span>
                    {a.confidence && (
                      <span className="ml-2 text-zinc-400">({a.confidence})</span>
                    )}
                  </div>
                  <span className="text-zinc-400">
                    {new Date(a.created_at).toLocaleString("es-ES", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
