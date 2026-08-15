import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { CurrencyInput } from '@/components/ui/currency-input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import type { Client } from '@/features/clientes/api'
import { fechaNegocioISO, sumarDiasFecha } from '@/lib/format'
import { PLANES_CATALOGO, type Pauta, type PautaInput } from './api'

function emptyForm(preselectClientId?: string): PautaInput {
  return {
    client_id: preselectClientId ?? '',
    fecha_inicio: '',
    fecha_fin: '',
    publicaciones_contratadas: 1,
    valor_pagado: '',
    fecha_pago: '',
    observaciones: '',
  }
}

export function PautaForm({
  pauta,
  clients,
  preselectClientId,
  onSubmit,
  isSubmitting,
  error,
}: {
  pauta: Pauta | null
  clients: Client[]
  preselectClientId?: string
  onSubmit: (payload: PautaInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<PautaInput>(emptyForm(preselectClientId))
  const [plan, setPlan] = useState('')

  useEffect(() => {
    setPlan('')
    setForm(
      pauta
        ? {
            client_id: pauta.client_id,
            fecha_inicio: pauta.fecha_inicio,
            fecha_fin: pauta.fecha_fin,
            publicaciones_contratadas: pauta.publicaciones_contratadas,
            valor_pagado: pauta.valor_pagado,
            fecha_pago: pauta.fecha_pago,
            observaciones: pauta.observaciones ?? '',
          }
        : emptyForm(preselectClientId),
    )
  }, [pauta, preselectClientId])

  function applyPlan(planId: string) {
    setPlan(planId)
    const plan = PLANES_CATALOGO.find((p) => p.id === planId)
    if (!plan) return
    const inicio = form.fecha_inicio || fechaNegocioISO()
    setForm({
      ...form,
      fecha_inicio: inicio,
      fecha_fin: sumarDiasFecha(inicio, plan.dias),
      publicaciones_contratadas: plan.cantidad,
      valor_pagado: String(plan.valor),
    })
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ ...form, observaciones: form.observaciones?.trim() || null })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4 overflow-y-auto">
      {!pauta && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="pauta-plan">Plan (opcional — autocompleta cantidad y valor)</Label>
          <SelectNative id="pauta-plan" value={plan} onChange={(e) => applyPlan(e.target.value)}>
            <option value="">Elegir del catálogo…</option>
            {PLANES_CATALOGO.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </SelectNative>
        </div>
      )}
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-cliente">Cliente</Label>
        <SelectNative
          id="pauta-cliente"
          required
          value={form.client_id}
          onChange={(e) => setForm({ ...form, client_id: e.target.value })}
        >
          <option value="">Selecciona un cliente…</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </SelectNative>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-fecha-inicio">Fecha de inicio</Label>
        <Input
          id="pauta-fecha-inicio"
          type="date"
          required
          value={form.fecha_inicio}
          onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-fecha-fin">Fecha de fin</Label>
        <Input
          id="pauta-fecha-fin"
          type="date"
          required
          value={form.fecha_fin}
          onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-cantidad">Publicaciones contratadas</Label>
        <Input
          id="pauta-cantidad"
          type="number"
          min={1}
          step={1}
          required
          value={form.publicaciones_contratadas}
          onChange={(e) => setForm({ ...form, publicaciones_contratadas: Number(e.target.value) })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-valor">Valor pagado</Label>
        <CurrencyInput
          id="pauta-valor"
          required
          value={form.valor_pagado}
          onValueChange={(digits) => setForm({ ...form, valor_pagado: digits })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-fecha-pago">Fecha de pago</Label>
        <Input
          id="pauta-fecha-pago"
          type="date"
          required
          value={form.fecha_pago}
          onChange={(e) => setForm({ ...form, fecha_pago: e.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="pauta-observaciones">Observaciones (opcional)</Label>
        <Input
          id="pauta-observaciones"
          value={form.observaciones ?? ''}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {pauta ? 'Guardar cambios' : 'Crear pauta'}
      </Button>
    </form>
  )
}
