import { useEffect, useRef, useState } from 'react'
import { Search, X } from 'lucide-react'

import { Input } from '@/components/ui/input'
import type { Pauta } from '@/features/contratos/api'
import { pautaOptionLabel } from './utils'

export function PautaCombobox({
  pautas,
  clientesById,
  value,
  onChange,
}: {
  pautas: Pauta[]
  clientesById: Map<string, string>
  value: string
  onChange: (pautaId: string) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const selected = value ? (pautas.find((p) => p.id === value) ?? null) : null
  const termino = query.trim().toLowerCase()
  const filtradas = termino
    ? pautas.filter((p) => (clientesById.get(p.client_id) ?? '').toLowerCase().includes(termino))
    : pautas

  const displayValue = open ? query : (selected ? pautaOptionLabel(selected, clientesById.get(selected.client_id) ?? '(cliente desconocido)') : '')

  return (
    <div ref={containerRef} className="relative w-72">
      <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        className="h-9 pr-7 pl-8 text-xs"
        placeholder="Buscar cliente y elegir pauta…"
        value={displayValue}
        onFocus={() => {
          setQuery('')
          setOpen(true)
        }}
        onChange={(e) => setQuery(e.target.value)}
      />
      {selected && !open && (
        <button
          type="button"
          className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          aria-label="Quitar pauta seleccionada"
          onClick={() => onChange('')}
        >
          <X className="size-3.5" />
        </button>
      )}
      {open && (
        <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-border bg-popover text-xs shadow-md">
          <button
            type="button"
            className="block w-full px-3 py-2 text-left text-muted-foreground hover:bg-accent"
            onClick={() => {
              onChange('')
              setQuery('')
              setOpen(false)
            }}
          >
            (sin pauta todavía — se vincula después)
          </button>
          {filtradas.length === 0 ? (
            <p className="px-3 py-2 text-muted-foreground">Sin resultados.</p>
          ) : (
            filtradas.map((p) => (
              <button
                key={p.id}
                type="button"
                className="block w-full px-3 py-2 text-left hover:bg-accent"
                onClick={() => {
                  onChange(p.id)
                  setQuery('')
                  setOpen(false)
                }}
              >
                {pautaOptionLabel(p, clientesById.get(p.client_id) ?? '(cliente desconocido)')}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
