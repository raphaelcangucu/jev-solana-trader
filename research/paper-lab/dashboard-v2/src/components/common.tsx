import { useState, type ReactNode } from 'react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Badge } from './ui/badge'
import { Button, type ButtonProps } from './ui/button'
import { Progress } from './ui/progress'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from './ui/alert-dialog'
import { Skeleton } from './ui/skeleton'
import { cn } from '@/lib/utils'
import { signed, signedUsd, toneOf } from '@/lib/format'
import type { Progress as Prog } from '@/lib/api'

export function Kpi({ label, value, sub, tone, icon }: { label: string; value: ReactNode; sub?: ReactNode; tone?: string; icon?: ReactNode }) {
  return (
    <div className="rounded-xl border bg-card px-3.5 py-3">
      <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{icon}{label}</div>
      <div className={cn('mt-1 text-xl font-semibold num leading-tight', tone)}>{value}</div>
      {sub && <div className="mt-0.5 truncate text-[11px] text-muted-foreground num">{sub}</div>}
    </div>
  )
}

export function Pnl({ v, pctV, d = 2, className }: { v: number | null | undefined; pctV?: number | null; d?: number; className?: string }) {
  return (
    <span className={cn('num', toneOf(v), className)}>
      {signedUsd(v, d)}{pctV != null && <span className="ml-1 text-[11px] opacity-80">({signed(pctV, 2, '%')})</span>}
    </span>
  )
}

export function VerdictBadge({ v }: { v?: string | null }) {
  const variant = v === 'vencedora' ? 'up' : v === 'perdedora' ? 'down' : 'secondary'
  return <Badge variant={variant as any}>{v || 'inconclusivo'}</Badge>
}

export function VerdictProgress({ p, text, compact }: { p?: Prog | null; text?: string | null; compact?: boolean }) {
  const rt = p && p.min_closed_rt ? Math.min(100, ((p.closed_rt || 0) / p.min_closed_rt) * 100) : 0
  const dd = p && p.min_days ? Math.min(100, ((p.days || 0) / p.min_days) * 100) : 0
  const v = Math.min(rt, dd)
  return (
    <div className={cn('flex flex-col gap-0.5', compact ? 'w-40' : 'w-full')}>
      <Progress value={v} label={`Progresso rumo aos mínimos: ${text || ''}`} indicatorClassName={v >= 100 ? 'bg-up' : 'bg-primary'} />
      <span className="truncate text-[10px] text-muted-foreground num" title={text || ''}>{text || '—'}</span>
    </div>
  )
}

export function StatusDot({ level, label }: { level: 'ok' | 'warn' | 'bad' | 'off'; label?: string }) {
  const c = level === 'ok' ? 'bg-up' : level === 'warn' ? 'bg-warn' : level === 'bad' ? 'bg-down' : 'bg-muted-foreground'
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('relative inline-block size-2 rounded-full', c)} aria-hidden>
        {level === 'ok' && <span className={cn('absolute inset-0 animate-ping rounded-full opacity-40', c)} />}
      </span>
      {label && <span className="sr-only">{label}</span>}
    </span>
  )
}

export function SectionTitle({ children, right, desc }: { children: ReactNode; right?: ReactNode; desc?: ReactNode }) {
  return (
    <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 className="text-base font-semibold tracking-tight">{children}</h2>
        {desc && <p className="text-xs text-muted-foreground">{desc}</p>}
      </div>
      {right}
    </div>
  )
}

export function LoadingBlock({ h = 200 }: { h?: number }) {
  return <Skeleton className="w-full" style={{ height: h }} />
}

export function ErrorBlock({ error }: { error: unknown }) {
  return (
    <div role="alert" className="flex items-center gap-2 rounded-lg border border-down/40 bg-down/10 p-3 text-sm text-down">
      <AlertTriangle className="size-4" /> Erro ao carregar: {String((error as any)?.message || error).slice(0, 200)}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">{children}</div>
}

/** Every control goes through an explicit confirmation dialog (FreqUI-style start/stop confirmation). */
export function ConfirmAction({ title, description, confirmLabel = 'Confirmar', destructive, onConfirm, children, disabled, variant = 'outline', size = 'sm', ariaLabel }: {
  title: string; description: ReactNode; confirmLabel?: string; destructive?: boolean; onConfirm: () => Promise<any>; children: ReactNode; disabled?: boolean
  variant?: ButtonProps['variant']; size?: ButtonProps['size']; ariaLabel?: string
}) {
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant={variant} size={size} disabled={disabled || busy} aria-label={ariaLabel}>{busy ? <Loader2 className="animate-spin" /> : null}{children}</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription asChild><div>{description}</div></AlertDialogDescription>
        </AlertDialogHeader>
        <p className="text-[11px] text-muted-foreground">Simulação (paper) — nenhuma ordem real é enviada.</p>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction destructive={destructive} onClick={async (e) => {
            e.preventDefault(); setBusy(true)
            try {
              const r = await onConfirm()
              toast.success(title, { description: r?.note || r?.warning || 'Aplicado.' })
              setOpen(false)
              qc.invalidateQueries()
            } catch (err: any) {
              toast.error('Falhou', { description: String(err?.message || err) })
            } finally { setBusy(false) }
          }}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
