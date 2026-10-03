// Peças pequenas do caderno: chip, marca-texto, delta com seta, medidor, ponto de status, dica, switch, botões, estados.
import * as React from 'react'
import * as T from '@radix-ui/react-tooltip'
import * as S from '@radix-ui/react-switch'
import * as A from '@radix-ui/react-alert-dialog'
import { cn } from '@/lib/utils'
import { arrow, tone, toneClass } from '@/lib/format'

export function Chip({ children, className, color, title }: { children: React.ReactNode; className?: string; color?: string; title?: string }) {
  return (
    <span title={title} className={cn('inline-flex h-[20px] items-center gap-1 whitespace-nowrap rounded-[5px] border border-rule bg-surface px-1.5 text-[11.5px] leading-none text-ink-2 t-cond', className)}>
      {color && <i aria-hidden className="inline-block size-[7px] rounded-full" style={{ background: color }} />}
      {children}
    </span>
  )
}

/** O único elemento ousado: marca-texto amarelo atrás de quem lidera. */
export function Mark({ children, on = true, sweep = false, className }: { children: React.ReactNode; on?: boolean; sweep?: boolean; className?: string }) {
  if (!on) return <>{children}</>
  return <mark className={cn('marker bg-transparent', sweep && 'marker-sweep', className)}>{children}</mark>
}

/** Valor com sinal e seta: nunca só cor. */
export function Delta({ v, children, className, arrowOn = true }: { v: number | null | undefined; children: React.ReactNode; className?: string; arrowOn?: boolean }) {
  const a = arrow(v)
  return (
    <span className={cn('whitespace-nowrap', toneClass[tone(v)], className)}>
      {arrowOn && a && <span aria-hidden className="mr-[0.2em] inline-block translate-y-[-0.08em] text-[0.62em]">{a}</span>}
      {children}
    </span>
  )
}

export function Meter({ value, max = 100, className, label, warnAt }: { value: number | null | undefined; max?: number; className?: string; label?: string; warnAt?: number }) {
  const v = value == null || !Number.isFinite(value) ? 0 : Math.max(0, Math.min(1, value / max))
  return (
    <span role="meter" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value ?? 0} aria-label={label} className={cn('relative block h-[4px] w-full overflow-hidden rounded-full bg-sunk', className)}>
      <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${v * 100}%`, background: warnAt != null && (value ?? 0) >= warnAt ? 'var(--ink)' : 'var(--ink-2)' }} />
    </span>
  )
}

export function Dot({ level, className }: { level: 'ok' | 'warn' | 'bad' | 'off'; className?: string }) {
  const c = level === 'ok' ? 'var(--gain)' : level === 'warn' ? '#d49a00' : level === 'bad' ? 'var(--loss)' : 'var(--ink-3)'
  return <i aria-hidden className={cn('inline-block size-2 shrink-0 rounded-full', className)} style={{ background: c, boxShadow: `0 0 0 3px color-mix(in srgb, ${c} 18%, transparent)` }} />
}

export const TipProvider = T.Provider
export function Tip({ content, children, side = 'top', className }: { content: React.ReactNode; children: React.ReactNode; side?: 'top' | 'bottom' | 'left' | 'right'; className?: string }) {
  return (
    <T.Root delayDuration={150}>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content side={side} sideOffset={6} collisionPadding={12} className={cn('pop z-[70] max-w-[300px] rounded-md px-2.5 py-1.5 text-[12.5px] leading-snug', className)}>
          {content}
        </T.Content>
      </T.Portal>
    </T.Root>
  )
}

export const Switch = React.forwardRef<React.ElementRef<typeof S.Root>, React.ComponentPropsWithoutRef<typeof S.Root>>(({ className, ...p }, ref) => (
  <S.Root ref={ref} className={cn('peer inline-flex h-[22px] w-[38px] shrink-0 cursor-pointer items-center rounded-full border border-rule-strong bg-sunk transition-colors disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-ink data-[state=checked]:bg-ink', className)} {...p}>
    <S.Thumb className="pointer-events-none block size-[16px] translate-x-[2px] rounded-full bg-surface shadow ring-1 ring-rule-strong transition-transform data-[state=checked]:translate-x-[18px]" />
  </S.Root>
))
Switch.displayName = 'Switch'

type BtnVariant = 'ink' | 'line' | 'ghost' | 'danger'
export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: 'sm' | 'md' }>(
  ({ className, variant = 'line', size = 'md', ...p }, ref) => (
    <button ref={ref} className={cn(
      'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-[560] transition-colors disabled:pointer-events-none disabled:opacity-45 [&_svg]:size-4',
      size === 'sm' ? 'h-8 px-2.5 text-[13px]' : 'h-9 px-3.5 text-[14px]',
      variant === 'ink' && 'bg-ink text-surface hover:opacity-90',
      variant === 'line' && 'border border-rule-strong bg-surface text-ink hover:border-ink-3',
      variant === 'ghost' && 'text-ink-2 hover:bg-sunk hover:text-ink',
      variant === 'danger' && 'bg-loss text-white hover:opacity-90',
      className)} {...p} />
  ))
Button.displayName = 'Button'

/** Confirmação antes de qualquer gravação. */
export function Confirm({ open, onOpenChange, title, children, confirmLabel = 'Confirmar', onConfirm, busy, danger }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; children?: React.ReactNode; confirmLabel?: string; onConfirm: () => void; busy?: boolean; danger?: boolean
}) {
  return (
    <A.Root open={open} onOpenChange={onOpenChange}>
      <A.Portal>
        <A.Overlay className="fixed inset-0 z-[80] bg-[rgba(10,18,32,0.45)]" />
        <A.Content className="pop fixed left-1/2 top-1/2 z-[81] grid w-[calc(100%-32px)] max-w-[440px] -translate-x-1/2 -translate-y-1/2 gap-3 rounded-xl p-5">
          <A.Title className="t-title text-[18px]">{title}</A.Title>
          <A.Description asChild><div className="text-[14px] text-ink-2">{children}</div></A.Description>
          <div className="mt-1 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <A.Cancel asChild><Button variant="line">Cancelar</Button></A.Cancel>
            <Button variant={danger ? 'danger' : 'ink'} disabled={busy} onClick={onConfirm}>{busy ? 'Salvando…' : confirmLabel}</Button>
          </div>
        </A.Content>
      </A.Portal>
    </A.Root>
  )
}

export function SectionHead({ title, children, id, className }: { title: React.ReactNode; children?: React.ReactNode; id?: string; className?: string }) {
  return (
    <div className={cn('mb-3 flex flex-wrap items-end justify-between gap-x-6 gap-y-1', className)}>
      <h2 id={id} className="t-title text-[21px] sm:text-[23px]">{title}</h2>
      {children && <div className="max-w-[640px] text-[13.5px] text-ink-2">{children}</div>}
    </div>
  )
}

export function Note({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn('rounded-lg border border-dashed border-rule-strong px-4 py-6 text-center text-[14px] text-ink-2', className)}>{children}</p>
}

export function ErrorNote({ error, what }: { error: unknown; what: string }) {
  const status = (error as { status?: number })?.status
  const msg = status === 401 ? 'A sessão expirou. Recarregue a página e entre de novo.'
    : status === 404 ? 'Esse endpoint ainda não existe neste servidor. Atualize o backend do lab.'
      : 'Não consegui falar com o servidor do lab. Ele tenta de novo sozinho em alguns segundos.'
  return <Note className="border-loss/40 text-ink">Sem {what} agora. {msg}</Note>
}

export function Loading({ h = 240, label = 'Carregando…' }: { h?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" className="grid place-items-center rounded-lg border border-rule bg-surface/60 text-[13px] text-ink-3" style={{ minHeight: h }}>
      {label}
    </div>
  )
}

/** Rótulo pequeno com valor ao lado (definição) — usado em listas de números. */
export function Stat({ label, children, sub, className }: { label: React.ReactNode; children: React.ReactNode; sub?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('min-w-0', className)}>
      <dt className="text-[12.5px] text-ink-3">{label}</dt>
      <dd className="t-num mt-0.5 text-[19px] leading-tight">{children}</dd>
      {sub && <dd className="mt-0.5 text-[12px] text-ink-3 t-tab">{sub}</dd>}
    </div>
  )
}
