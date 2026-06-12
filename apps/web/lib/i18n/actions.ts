"use server";

import { cookies } from "next/headers";
import { LOCALE_COOKIE } from "./index";
import type { Locale } from "./dictionaries";

/** Set the locale cookie server-side so the next render reads the new language. */
export async function setLocaleAction(locale: Locale) {
  const store = await cookies();
  store.set(LOCALE_COOKIE, locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
}
