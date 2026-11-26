import type { ColoresMarca } from './api'

// Contraste entre dos colores #RRGGBB según WCAG (de 1 a 21).
export function contraste(a: string, b: string): number {
  const luminancia = (hex: string) => {
    const [r, g, bl] = [1, 3, 5].map((i) => {
      const c = parseInt(hex.slice(i, i + 2), 16) / 255
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl
  }
  const [claro, oscuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (claro + 0.05) / (oscuro + 0.05)
}

export function avisosDeContraste(c: ColoresMarca): string[] {
  const avisos: string[] = []
  if (contraste('#FFFFFF', c.fondo) < 4.5)
    avisos.push('El texto blanco se lee mal sobre ese fondo: usa un fondo más oscuro.')
  if (contraste(c.texto_destacado, c.destacado) < 4.5)
    avisos.push('El texto del botón se confunde con el destacado: usa colores más distintos.')
  if (contraste(c.destacado, c.fondo) < 3)
    avisos.push('El destacado resalta poco sobre el fondo.')
  return avisos
}
