import { AnalyzeClient } from "./ui/analyze-client";

export default function AnalyzePage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Analizar ECG</h1>
      <p className="mt-2 text-zinc-600">
        Sube una foto de tira de electrocardiograma. Resultado educativo; no es
        diagnóstico.
      </p>
      <AnalyzeClient />
    </div>
  );
}
