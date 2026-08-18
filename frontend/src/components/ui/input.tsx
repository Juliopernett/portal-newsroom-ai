import * as React from 'react'

import { cn } from '@/lib/utils'

// text-base (16px), not text-sm — below 16px, iOS/Android browsers zoom the
// page in on focus. sm: back to text-sm keeps the compact desktop look.
const BOX_CLASSES =
  'h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-colors outline-none sm:text-sm placeholder:text-muted-foreground'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  if (type === 'date') {
    // iOS Safari renders type=date completely blank (no calendar icon, no
    // dd/mm/yyyy value) whenever the input itself carries a custom
    // border/padding/background — its shadow-DOM date-value renderer
    // doesn't coexist with a heavily-reset host element, a well-documented
    // WebKit quirk. Neither the flex→block fix nor the min-w-0 overflow
    // fix (both still correct, kept elsewhere) resolved this — confirmed
    // blank on a real iPhone after both. The fix: move all box styling to
    // a wrapper div and leave the <input> itself almost bare (no border,
    // no padding, no background) so Safari's internals render at their
    // own natural size inside a plain container. has-* (not the plain
    // state variants below) because the state now lives on a descendant.
    return (
      <div
        data-slot="input"
        className={cn(
          BOX_CLASSES,
          'flex items-center',
          'has-[:focus-visible]:border-ring has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring/30',
          'has-[:disabled]:pointer-events-none has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50',
          'has-[[aria-invalid="true"]]:border-destructive has-[[aria-invalid="true"]]:ring-destructive/20',
          className,
        )}
      >
        <input
          type="date"
          // color-scheme:light pins the native picker to light even if the
          // OS is in dark mode — the app has no working dark theme today
          // (see index.css's unused .dark block), so without this the
          // picker alone could render dark against an otherwise-light page.
          className="min-w-0 flex-1 bg-transparent text-base outline-none sm:text-sm [color-scheme:light]"
          {...props}
        />
      </div>
    )
  }

  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        BOX_CLASSES,
        'block',
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
