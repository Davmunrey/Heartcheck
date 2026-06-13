"use client";

import { UserButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";

/** Auth-aware nav actions for the public header. Client component using
 *  useAuth() (Clerk 7 doesn't export SignedIn/SignedOut). Public pages stay
 *  static; the auth UI hydrates client-side. */
export function AuthNav() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <div className="h-9 w-16" aria-hidden />;
  return isSignedIn ? (
    <>
      <Link href="/dashboard" className="text-ink-2 transition-colors hover:text-brand">
        Panel
      </Link>
      <UserButton />
    </>
  ) : (
    <>
      <Link href="/sign-in" className="text-ink-2 transition-colors hover:text-brand">
        Entrar
      </Link>
      <Link
        href="/sign-up"
        className="bg-brand px-4 py-2 font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        Trial 7 días
      </Link>
    </>
  );
}

export function AuthNavMobile() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return null;
  return isSignedIn ? (
    <Link href="/dashboard" className="px-3 py-2 text-sm font-semibold text-brand hover:bg-paper-2">
      Ir al panel →
    </Link>
  ) : (
    <>
      <Link href="/sign-in" className="px-3 py-2 text-sm text-ink-2 hover:bg-paper-2 hover:text-brand">
        Entrar
      </Link>
      <Link
        href="/sign-up"
        className="mt-1 bg-brand px-3 py-2 text-center text-sm font-semibold text-white hover:bg-brand-strong"
      >
        Trial 7 días
      </Link>
    </>
  );
}
