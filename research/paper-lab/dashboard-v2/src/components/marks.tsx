// Marcas finas do placar: sparkline, barra divergente "vs. segurar", progresso do veredito.
import { memo } from 'react'
import type { Spark } from '@/lib/api'
import { signedPct, tone } from '@/lib/format'
import { cn } from '@/lib/utils'

export const Sparkline = memo(function Sparkline({ s, w = 104, h = 30, label }: { s?: Spark | null; w?: number; h?: number; label: string }) {
  if (!s || s.v.length < 2) return <span className="block text-[12px] text-ink-3" style={{ width: w }}>sem curva</span>
  const vs = s.v
  let lo = Math.min(0, ...vs), hi = Math.max(0, ...vs)
  if (hi - lo < 1) { const c = (hi + lo) / 2; lo = c - 0.5; hi = c + 0.5 } // sem amplificar ruído: faixa mínima de 1 p.p.
  const pad = 3
  const x = (i: number) => pad + (i / (vs.length - 1)) * (w - pad * 2)
  const y = (v: number) => pad + (1 - (v - lo) / (hi - lo)) * (h - pad * 2)
  const d = vs.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')
  const last = vs[vs.length - 1]
  const c = tone(last) === 'gain' ? 'var(--gain)' : tone(last) === 'loss' ? 'var(--loss)' : 'var(--ink-3)'
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`${label}: ${signedPct(last)} desde o início`} className="block overflow-visible">
      <line x1={pad} x2={w - pad} y1={y(0)} y2={y(0)} stroke="var(--rule-strong)" strokeWidth={1} />
      <path d={d} fill="none" stroke="var(--ink-2)" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(vs.length - 1)} cy={y(last)} r={3} fill={c} stroke="var(--surface)" strokeWidth={2} />
    </svg>
  )
})

/** Barra centrada em zero; o domínio (±max) é o mesmo para todas as linhas visíveis. */
export function Diverging({ v, max, w = 64 }: { v: number | null | undefined; max: number; w?: number }) {
  const ok = v != null && Number.isFinite(v)
  const frac = ok ? Math.max(-1, Math.min(1, v! / (max || 1))) : 0
  const half = w / 2
  const len = Math.abs(frac) * half
  const t = tone(v)
  return (
    <span className="inline-flex items-center gap-2">
      <svg width={w} height={14} viewBox={`0 0 ${w} 14`} aria-hidden className="block shrink-0">
        <rect x={0} y={6} width={w} height={2} rx={1} fill="var(--sunk)" />
        {ok && len > 0.5 && (
          <rect x={frac >= 0 ? half : half - len} y={3} width={len} height={8} rx={2}
            fill={t === 'gain' ? 'var(--gain)' : t === 'loss' ? 'var(--loss)' : 'var(--ink-3)'} />
        )}
        <line x1={half} x2={half} y1={0} y2={14} stroke="var(--ink-3)" strokeWidth={1} />
      </svg>
    </span>
  )
}

/** Progresso para o veredito: dias e round trips fechados contra os mínimos. */
export function VerdictProgress({ days, minDays, rt, minRt, verdict, compact }: { days: number | null; minDays: number; rt: number | null; minRt: number; verdict: string; compact?: boolean }) {
  if (verdict === 'vencedora' || verdict === 'perdedora') {
    return <span className={cn('t-semi text-[13px]', verdict === 'vencedora' ? 'text-gain' : 'text-loss')}>{verdict === 'vencedora' ? '▲ vencedora' : '▼ perdedora'}</span>
  }
  const bar = (v: number, m: number) => (
    <span className="relative block h-[3px] w-full overflow-hidden rounded-full bg-sunk">
      <span className="absolute inset-y-0 left-0 rounded-full bg-ink-2" style={{ width: `${Math.min(100, (v / m) * 100)}%` }} />
    </span>
  )
  const d = Math.floor(days ?? 0), r = rt ?? 0
  return (
    <span className={cn('grid gap-[5px] text-[11.5px] leading-none text-ink-3 t-cond', compact ? 'w-[70px]' : 'w-[84px]')} aria-label={`${d} de ${minDays} dias e ${r} de ${minRt} operações fechadas`}>
      <span className="grid grid-cols-[1fr_auto] items-center gap-1.5">{bar(days ?? 0, minDays)}<span className="t-tab">{d}/{minDays} d</span></span>
      <span className="grid grid-cols-[1fr_auto] items-center gap-1.5">{bar(r, minRt)}<span className="t-tab">{r}/{minRt} RT</span></span>
    </span>
  )
}
