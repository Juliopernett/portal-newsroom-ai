import * as React from 'react'

import { Input } from '@/components/ui/input'

/**
 * A money input that displays with thousands separators (es-CO) while
 * typing, but hands the caller a plain digit string — no separators,
 * no decimals (matches how money is actually entered/shown everywhere
 * else in this app: `formatMoneda` never shows cents either).
 */
function CurrencyInput({
  value,
  onValueChange,
  ...props
}: Omit<React.ComponentProps<typeof Input>, 'value' | 'onChange' | 'type'> & {
  value: string
  onValueChange: (digits: string) => void
}) {
  const display = value ? Number(value).toLocaleString('es-CO') : ''

  return (
    <Input
      {...props}
      type="text"
      inputMode="numeric"
      value={display}
      onChange={(e) => onValueChange(e.target.value.replace(/\D/g, ''))}
    />
  )
}

export { CurrencyInput }
