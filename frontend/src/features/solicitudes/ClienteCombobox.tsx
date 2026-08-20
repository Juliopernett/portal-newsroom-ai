import { useEffect, useRef, useState } from 'react'
import { Search, X } from 'lucide-react'

import { Input } from '@/components/ui/input'
import type { Client } from '@/features/clientes/api'

export function ClienteCombobox({
  clients,
  value,
  onChange,
  placeholder = '¿De quién es este material? (opcional)',
  className = 'w-full sm:w-64',
}: {
  clients: Client[]
  value: string
  onChange: (clientId: string) => void
  placeholder?: string
  className?: string
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

  const selected = value ? (clients.find((c) => c.id === value) ?? null) : null
  const termino = query.trim().toLowerCase()
  const filtrados = termino ? clients.filter((c) => c.nombre.toLowerCase().includes(termino)) : clients

  const displayValue = open ? query : (selected ? selected.nombre : '')

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        className="h-9 pr-7 pl-8 text-base sm:text-xs"
        placeholder={placeholder}
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
          aria-label="Quitar cliente seleccionado"
          onClick={() => onChange('')}
        >
          <X className="size-3.5" />
        </button>
      )}
      {open && (
        <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-border bg-popover text-xs shadow-md">
          {filtrados.length === 0 ? (
            <p className="px-3 py-2 text-muted-foreground">Sin resultados.</p>
          ) : (
            filtrados.map((c) => (
              <button
                key={c.id}
                type="button"
                className="block w-full px-3 py-2 text-left hover:bg-accent"
                onClick={() => {
                  onChange(c.id)
                  setQuery('')
                  setOpen(false)
                }}
              >
                {c.nombre}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
