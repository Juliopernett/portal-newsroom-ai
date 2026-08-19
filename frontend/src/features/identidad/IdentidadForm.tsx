import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { IdentidadComercial, IdentidadComercialInput } from './api'

const EMPTY: IdentidadComercialInput = {
  nombre_comercial: '',
  razon_social: null,
  nit: null,
  telefono: null,
  email: null,
  sitio_web: null,
  instagram: null,
  facebook: null,
  otras_redes: null,
}

function toInput(identidad: IdentidadComercial): IdentidadComercialInput {
  return {
    nombre_comercial: identidad.nombre_comercial,
    razon_social: identidad.razon_social,
    nit: identidad.nit,
    telefono: identidad.telefono,
    email: identidad.email,
    sitio_web: identidad.sitio_web,
    instagram: identidad.instagram,
    facebook: identidad.facebook,
    otras_redes: identidad.otras_redes,
  }
}

export function IdentidadForm({
  identidad,
  onSubmit,
  isSubmitting,
  error,
}: {
  identidad: IdentidadComercial | null
  onSubmit: (payload: IdentidadComercialInput) => void
  isSubmitting: boolean
  error: string | null
}) {
  const [form, setForm] = useState<IdentidadComercialInput>(identidad ? toInput(identidad) : EMPTY)

  useEffect(() => {
    setForm(identidad ? toInput(identidad) : EMPTY)
  }, [identidad])

  function campo(key: keyof IdentidadComercialInput) {
    return form[key] ?? ''
  }

  function setCampo(key: keyof IdentidadComercialInput, valor: string) {
    setForm({ ...form, [key]: valor.trim() ? valor : null })
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="flex max-w-2xl flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="identidad-nombre">Nombre comercial</Label>
        <Input
          id="identidad-nombre"
          required
          value={form.nombre_comercial}
          onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-razon-social">Razón social</Label>
          <Input
            id="identidad-razon-social"
            value={campo('razon_social')}
            onChange={(e) => setCampo('razon_social', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-nit">NIT</Label>
          <Input id="identidad-nit" value={campo('nit')} onChange={(e) => setCampo('nit', e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-telefono">Teléfono / WhatsApp</Label>
          <Input
            id="identidad-telefono"
            value={campo('telefono')}
            onChange={(e) => setCampo('telefono', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-email">Correo electrónico</Label>
          <Input
            id="identidad-email"
            type="email"
            value={campo('email')}
            onChange={(e) => setCampo('email', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-sitio-web">Sitio web</Label>
          <Input
            id="identidad-sitio-web"
            value={campo('sitio_web')}
            onChange={(e) => setCampo('sitio_web', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-instagram">Instagram</Label>
          <Input
            id="identidad-instagram"
            value={campo('instagram')}
            onChange={(e) => setCampo('instagram', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="identidad-facebook">Facebook</Label>
          <Input
            id="identidad-facebook"
            value={campo('facebook')}
            onChange={(e) => setCampo('facebook', e.target.value)}
          />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="identidad-otras-redes">Otras redes sociales</Label>
        <Textarea
          id="identidad-otras-redes"
          rows={2}
          placeholder="Ej: TikTok: @portalvallenato, YouTube: /portalvallenato"
          value={campo('otras_redes')}
          onChange={(e) => setCampo('otras_redes', e.target.value)}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={isSubmitting} className="mt-1 w-fit">
        Guardar identidad comercial
      </Button>
    </form>
  )
}
