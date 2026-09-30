// shadcn/ui-style Progress (MIT, https://ui.shadcn.com)
import * as P from '@radix-ui/react-progress'
import { cn } from '@/lib/utils'
export function Progress({ value, className, indicatorClassName, label }: { value: number; className?: string; indicatorClassName?: string; label?: string }) {
  const v = Math.max(0, Math.min(100, value || 0))
  return (
    <P.Root value={v} aria-label={label} className={cn('relative h-1.5 w-full overflow-hidden rounded-full bg-muted', className)}>
      <P.Indicator className={cn('h-full bg-primary transition-transform', indicatorClassName)} style={{ transform: `translateX(-${100 - v}%)` }} />
    </P.Root>
  )
}
