import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // text-base (16px), not text-sm — below 16px, iOS/Android browsers
        // zoom the page in on focus, which is what "se amplia la página"
        // was. sm: back to text-sm keeps the existing compact desktop look.
        //
        // block, not flex — an <input> never has children, so flex vs
        // block makes no visual difference in Chrome, but iOS Safari's
        // shadow-DOM internals for type=date (the calendar icon + value
        // text) render as a blank box when the host element is a flex
        // container. Confirmed on iPhone Safari: the field went from
        // overflowing (min-w-0 fixed that) to rendering completely empty.
        'block h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-colors outline-none sm:text-sm',
        'placeholder:text-muted-foreground',
        'focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30',
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
