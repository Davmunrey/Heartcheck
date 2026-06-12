import { cookies } from "next/headers";
import { dictionaries, defaultLocale, type Locale } from "./dictionaries";

export type { Locale } from "./dictionaries";
export { locales, defaultLocale } from "./dictionaries";

export const LOCALE_COOKIE = "locale";

/** Read the active locale from the cookie (server-side). Defaults to Spanish. */
export async function getLocale(): Promise<Locale> {
  const store = await cookies();
  const value = store.get(LOCALE_COOKIE)?.value;
  return value === "en" ? "en" : defaultLocale;
}

export function getDictionary(locale: Locale) {
  return dictionaries[locale];
}

/** Convenience: resolve locale + dictionary in one call for server components. */
export async function getT() {
  const locale = await getLocale();
  return { locale, t: dictionaries[locale] };
}
