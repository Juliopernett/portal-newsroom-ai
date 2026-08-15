export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex h-full flex-col gap-2">
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="text-sm text-muted-foreground">
        Este módulo todavía no se migró — sigue disponible en la app anterior (
        <a className="underline" href="/ui/">
          /ui/
        </a>
        ) mientras avanza la migración incremental.
      </p>
    </div>
  )
}
