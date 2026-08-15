import * as React from 'react'
import { ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

/**
 * A plain <select>, styled to match Input — not the Radix Select
 * primitive. For a fixed set of options (enum dropdowns) this is
 * simpler and just as accessible; reach for a Radix-based Select
 * instead if a future field needs custom option rendering.
 */
function SelectNative({ className, children, ...props }: React.ComponentProps<'select'>) {
  return (
    <div className="relative">
      <select
        data-slot="select-native"
        className={cn(
          'flex h-9 w-full appearance-none rounded-md border border-input bg-transparent px-3 py-1 pr-8 text-sm shadow-xs transition-colors outline-none',
          'focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30',
          'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  )
}

export { SelectNative }
