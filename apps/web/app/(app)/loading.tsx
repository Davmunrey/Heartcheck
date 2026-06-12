export default function AppLoading() {
  return (
    <div className="mx-auto max-w-5xl px-5 py-12" aria-busy="true" aria-label="Cargando">
      <div className="h-3 w-24 animate-pulse bg-line" />
      <div className="mt-4 h-12 w-80 max-w-full animate-pulse bg-line-2" />
      <div className="mt-8 h-20 animate-pulse border-2 border-line bg-surface" />
      <div className="mt-12 h-48 animate-pulse border-2 border-line bg-surface" />
    </div>
  );
}
