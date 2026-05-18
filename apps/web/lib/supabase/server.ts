import { auth } from "@clerk/nextjs/server";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase client using Clerk JWT template `supabase` (must include `org_id` for RLS).
 */
export async function createSupabaseForUser(): Promise<SupabaseClient | null> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) return null;
  const { getToken } = await auth();
  const token = await getToken({ template: "supabase" });
  if (!token) return null;
  return createClient(url, anon, {
    global: {
      headers: { Authorization: `Bearer ${token}` },
    },
  });
}

/**
 * Anon server client for Server Components that don't need per-user RLS.
 * Uses NEXT_PUBLIC_SUPABASE_ANON_KEY without Clerk JWT injection.
 */
export function createSupabaseServerClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set"
    );
  }
  return createClient(url, anonKey, {
    auth: { persistSession: false },
  });
}
