// shadcn/ui-style component (MIT, https://ui.shadcn.com)
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const badgeVariants = cva('inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-none whitespace-nowrap', {
  variants: {
    variant: {
      default: 'border-transparent bg-primary/15 text-primary',
      secondary: 'border-transparent bg-secondary text-secondary-foreground',
      outline: 'text-muted-foreground',
      up: 'border-transparent bg-up/15 text-up',
      down: 'border-transparent bg-down/15 text-down',
      warn: 'border-transparent bg-warn/15 text-warn',
    },
  },
  defaultVariants: { variant: 'default' },
})
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}
export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
