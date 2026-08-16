import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { CurrencyInput } from '@/components/ui/currency-input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { OtroIngreso, OtroIngresoInput } from './otrosIngresosApi'

const EMPTY: OtroIngresoInput = {
  origen: '',
  monto: '',
  monto_usd: '',
  fecha_cobro: '',
  observaciones: '',
}

export function OtroIngresoForm({
  ingreso,
  onSubmit,
  isSubmitting,
  error,
}: {
  ingreso: OtroIngreso | null
  onSubmit: (payload: OtroIngresoInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<OtroIngresoInput>(EMPTY)

  useEffect(() => {
    setForm(
      ingreso
        ? {
            origen: ingreso.origen,
            monto: ingreso.monto,
            monto_usd: ingreso.monto_usd ?? '',
            fecha_cobro: ingreso.fecha_cobro,
            observaciones: ingreso.observaciones ?? '',
          }
        : EMPTY,
    )
  }, [ingreso])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      monto_usd: form.monto_usd?.trim() || null,
      observaciones: form.observaciones?.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="ingreso-origen">Origen</Label>
        <Input
          id="ingreso-origen"
          required
          placeholder="Facebook, AdSense…"
          autoComplete="off"
          value={form.origen}
          onChange={(e) => setForm({ ...form, origen: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ingreso-monto">Valor recibido (COP)</Label>
        <CurrencyInput
          id="ingreso-monto"
          required
          value={form.monto}
          onValueChange={(digits) => setForm({ ...form, monto: digits })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ingreso-monto-usd">Valor en USD (opcional)</Label>
        <Input
          id="ingreso-monto-usd"
          type="number"
          step="0.01"
          min="0"
          placeholder="Solo si lo tienes a la mano"
          value={form.monto_usd ?? ''}
          onChange={(e) => setForm({ ...form, monto_usd: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ingreso-fecha">Fecha de cobro</Label>
        <Input
          id="ingreso-fecha"
          type="date"
          required
          value={form.fecha_cobro}
          onChange={(e) => setForm({ ...form, fecha_cobro: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ingreso-observaciones">Notas (opcional)</Label>
        <Textarea
          id="ingreso-observaciones"
          rows={2}
          value={form.observaciones ?? ''}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {ingreso ? 'Guardar cambios' : 'Registrar ingreso'}
      </Button>
    </form>
  )
}
