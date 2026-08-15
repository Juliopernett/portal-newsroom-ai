export function formatMoneda(valor: string | number): string {
  return '$' + Number(valor).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

export function formatFecha(iso: string): string {
  return iso ? iso.slice(0, 10) : ''
}
