import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Gasto, GastoInput } from './api'

const EMPTY: GastoInput = { descripcion: '', valor: '', fecha: '' }

export function GastoForm({
  gasto,
  onSubmit,
  isSubmitting,
  error,
}: {
  gasto: Gasto | null
  onSubmit: (payload: GastoInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<GastoInput>(EMPTY)

  useEffect(() => {
    setForm(gasto ? { descripcion: gasto.descripcion, valor: gasto.valor, fecha: gasto.fecha } : EMPTY)
  }, [gasto])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="gasto-descripcion">Descripción</Label>
        <Input
          id="gasto-descripcion"
          required
          autoComplete="off"
          value={form.descripcion}
          onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="gasto-valor">Valor</Label>
        <Input
          id="gasto-valor"
          type="number"
          min="0"
          step="0.01"
          required
          value={form.valor}
          onChange={(e) => setForm({ ...form, valor: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="gasto-fecha">Fecha</Label>
        <Input
          id="gasto-fecha"
          type="date"
          required
          value={form.fecha}
          onChange={(e) => setForm({ ...form, fecha: e.target.value })}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {gasto ? 'Guardar cambios' : 'Registrar gasto'}
      </Button>
    </form>
  )
}
