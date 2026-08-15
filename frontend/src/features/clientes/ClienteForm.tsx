import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import { Textarea } from '@/components/ui/textarea'
import { CLIENT_TYPE_LABELS, type Client, type ClientInput } from './api'

const EMPTY: ClientInput = {
  nombre: '',
  tipo: 'artista',
  telefono: '',
  instagram: '',
  observaciones: '',
}

export function ClienteForm({
  client,
  onSubmit,
  isSubmitting,
  error,
}: {
  client: Client | null
  onSubmit: (payload: ClientInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<ClientInput>(EMPTY)

  useEffect(() => {
    setForm(
      client
        ? {
            nombre: client.nombre,
            tipo: client.tipo,
            telefono: client.telefono,
            instagram: client.instagram ?? '',
            observaciones: client.observaciones ?? '',
          }
        : EMPTY,
    )
  }, [client])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      instagram: form.instagram?.trim() || null,
      observaciones: form.observaciones?.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente-nombre">Nombre</Label>
        <Input
          id="cliente-nombre"
          required
          value={form.nombre}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente-tipo">Tipo</Label>
        <SelectNative
          id="cliente-tipo"
          required
          value={form.tipo}
          onChange={(e) => setForm({ ...form, tipo: e.target.value as ClientInput['tipo'] })}
        >
          {Object.entries(CLIENT_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </SelectNative>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente-telefono">Teléfono</Label>
        <Input
          id="cliente-telefono"
          required
          value={form.telefono}
          onChange={(e) => setForm({ ...form, telefono: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente-instagram">Instagram (opcional)</Label>
        <Input
          id="cliente-instagram"
          value={form.instagram ?? ''}
          onChange={(e) => setForm({ ...form, instagram: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente-observaciones">Notas internas (opcional)</Label>
        <Textarea
          id="cliente-observaciones"
          rows={3}
          placeholder="Solo visible para el equipo…"
          value={form.observaciones ?? ''}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {client ? 'Guardar cambios' : 'Crear cliente'}
      </Button>
    </form>
  )
}
