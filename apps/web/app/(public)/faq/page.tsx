import Link from "next/link";

export default function FaqPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <Link href="/" className="text-sm text-rose-600 hover:underline">
        ← Inicio
      </Link>
      <h1 className="mt-4 text-3xl font-bold">FAQ</h1>
      <p className="mt-4 text-zinc-600">
        HeartScan ofrece una lectura orientativa y educativa. No sustituye una
        valoración médica. Consulta{" "}
        <a
          href="https://github.com/heartscan/heartscan/blob/main/docs/WHEN_NOT_TO_USE.md"
          className="text-rose-600 underline"
        >
          cuándo no usarlo
        </a>
        .
      </p>
    </div>
  );
}
