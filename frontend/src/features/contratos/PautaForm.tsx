import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { CurrencyInput } from '@/components/ui/currency-input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import type { Client } from '@/features/clientes/api'
import { planesPautaApi } from '@/features/configuracion/api'
import { fechaNegocioISO, formatMoneda, sumarDiasFecha } from '@/lib/format'
import type { Pauta, PautaInput } from './api'

function emptyForm(preselectClientId?: string): PautaInput {
  return {
    client_id: preselectClientId ?? '',
    fecha_inicio: '',
    fecha_fin: '',
    publicaciones_contratadas: 1,
    valor_pagado: '',
    fecha_pago: '',
    saldo_pendiente: '0',
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
  const planesQuery = useQuery({ queryKey: ['planes-pauta'], queryFn: planesPautaApi.list })
  const planes = planesQuery.data ?? []

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
            saldo_pendiente: pauta.saldo_pendiente,
            observaciones: pauta.observaciones ?? '',
          }
        : emptyForm(preselectClientId),
    )
  }, [pauta, preselectClientId])

  function applyPlan(planId: string) {
    setPlan(planId)
    const plan = planes.find((p) => p.id === planId)
    if (!plan) return
    const inicio = form.fecha_inicio || fechaNegocioISO()
    setForm({
      ...form,
      fecha_inicio: inicio,
      fecha_fin: sumarDiasFecha(inicio, plan.dias_vigencia),
      publicaciones_contratadas: plan.cantidad_publicaciones,
      valor_pagado: plan.valor,
    })
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      saldo_pendiente: form.saldo_pendiente || '0',
      observaciones: form.observaciones?.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4 overflow-y-auto">
      {!pauta && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="pauta-plan">Plan (opcional — autocompleta cantidad y valor)</Label>
          <SelectNative id="pauta-plan" value={plan} onChange={(e) => applyPlan(e.target.value)}>
            <option value="">Elegir del catálogo…</option>
            {planes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre} — {formatMoneda(p.valor)}
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
        <Label htmlFor="pauta-saldo">Saldo pendiente (opcional)</Label>
        <CurrencyInput
          id="pauta-saldo"
          value={form.saldo_pendiente}
          onValueChange={(digits) => setForm({ ...form, saldo_pendiente: digits })}
        />
        <p className="text-xs text-muted-foreground">
          Lo que el cliente todavía debe de esta pauta — cuentas por cobrar.
        </p>
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
