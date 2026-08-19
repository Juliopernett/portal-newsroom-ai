import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { CurrencyInput } from '@/components/ui/currency-input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { PlanPauta, PlanPautaInput } from './api'

function emptyForm(siguienteOrden: number): PlanPautaInput {
  return { nombre: '', cantidad_publicaciones: 1, valor: '', dias_vigencia: 1, orden: siguienteOrden }
}

export function PlanPautaForm({
  plan,
  siguienteOrden,
  onSubmit,
  isSubmitting,
  error,
}: {
  plan: PlanPauta | null
  siguienteOrden: number
  onSubmit: (payload: PlanPautaInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<PlanPautaInput>(emptyForm(siguienteOrden))

  useEffect(() => {
    setForm(
      plan
        ? {
            nombre: plan.nombre,
            cantidad_publicaciones: plan.cantidad_publicaciones,
            valor: plan.valor,
            dias_vigencia: plan.dias_vigencia,
            orden: plan.orden,
          }
        : emptyForm(siguienteOrden),
    )
  }, [plan, siguienteOrden])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="plan-nombre">Nombre</Label>
        <Input
          id="plan-nombre"
          required
          autoComplete="off"
          placeholder="Ej: 1 mes, 3 publicaciones…"
          value={form.nombre}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="plan-cantidad">Publicaciones incluidas</Label>
        <Input
          id="plan-cantidad"
          type="number"
          min={1}
          step={1}
          required
          value={form.cantidad_publicaciones}
          onChange={(e) => setForm({ ...form, cantidad_publicaciones: Number(e.target.value) })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="plan-valor">Valor</Label>
        <CurrencyInput
          id="plan-valor"
          required
          value={form.valor}
          onValueChange={(digits) => setForm({ ...form, valor: digits })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="plan-dias">Vigencia (días)</Label>
        <Input
          id="plan-dias"
          type="number"
          min={1}
          step={1}
          required
          value={form.dias_vigencia}
          onChange={(e) => setForm({ ...form, dias_vigencia: Number(e.target.value) })}
        />
        <p className="text-xs text-muted-foreground">
          Al elegir este plan en Contratos, se suma a la fecha de inicio para calcular la fecha de fin.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="plan-orden">Orden</Label>
        <Input
          id="plan-orden"
          type="number"
          step={1}
          required
          value={form.orden}
          onChange={(e) => setForm({ ...form, orden: Number(e.target.value) })}
        />
        <p className="text-xs text-muted-foreground">Posición en la lista — menor primero.</p>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {plan ? 'Guardar cambios' : 'Crear plan'}
      </Button>
    </form>
  )
}
