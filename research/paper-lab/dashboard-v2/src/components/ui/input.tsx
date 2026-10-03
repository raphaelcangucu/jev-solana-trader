// shadcn/ui-style Input + Label (MIT, https://ui.shadcn.com)
import * as React from 'react'
import * as L from '@radix-ui/react-label'
import { cn } from '@/lib/utils'
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn('flex h-9 w-full rounded-md border border-input bg-background/50 px-2.5 py-1 text-sm num shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 aria-[invalid=true]:border-down aria-[invalid=true]:ring-down/40', className)} {...p} />
))
Input.displayName = 'Input'
export const Label = React.forwardRef<React.ElementRef<typeof L.Root>, React.ComponentPropsWithoutRef<typeof L.Root>>(({ className, ...p }, ref) => (
  <L.Root ref={ref} className={cn('text-xs font-medium text-muted-foreground', className)} {...p} />
))
Label.displayName = 'Label'
