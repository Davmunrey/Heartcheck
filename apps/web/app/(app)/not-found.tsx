import Link from "next/link";
import { getT } from "@/lib/i18n";

export default async function AppNotFound() {
  const { t } = await getT();
  const s = t.states;
  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">{s.notFoundEyebrow}</p>
      <h1 className="mt-3 text-[clamp(2rem,5vw,3rem)] leading-[1.04]">{s.notFoundTitle}</h1>
      <p className="mt-3 text-ink-2">{s.notFoundBody}</p>
      <Link
        href="/dashboard"
        className="mt-6 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        {s.notFoundCta}
      </Link>
    </div>
  );
}
