// Números pt-BR (vírgula decimal). Sinal tipográfico "−" (U+2212) e seta ▲/▼ para ganho/perda: nunca só cor.
const cache = new Map<string, Intl.NumberFormat>()
function nf(min: number, max = min, compact = false): Intl.NumberFormat {
  const k = `${min}:${max}:${compact}`
  let f = cache.get(k)
  if (!f) {
    f = new Intl.NumberFormat('pt-BR', compact ? { notation: 'compact', maximumFractionDigits: max } : { minimumFractionDigits: min, maximumFractionDigits: max })
    cache.set(k, f)
  }
  return f
}
const ok = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
export const DASH = '—'

export function num(v: number | null | undefined, d = 2): string { return ok(v) ? nf(d).format(v) : DASH }
export function int(v: number | null | undefined): string { return ok(v) ? nf(0).format(Math.round(v)) : DASH }

/** Sinal explícito: +1,23 / −1,23 / 0,00. */
export function signed(v: number | null | undefined, d = 2, suffix = ''): string {
  if (!ok(v)) return DASH
  const r = Number(v.toFixed(d))
  const s = r > 0 ? '+' : r < 0 ? '−' : ''
  return `${s}${nf(d).format(Math.abs(v))}${suffix}`
}
export function pct(v: number | null | undefined, d = 1): string { return ok(v) ? `${nf(d).format(v)}%` : DASH }
export function signedPct(v: number | null | undefined, d = 1): string { return signed(v, d, '%') }
export function usd(v: number | null | undefined, d = 2): string { return ok(v) ? `US$ ${nf(d).format(v)}` : DASH }
export function signedUsd(v: number | null | undefined, d = 2): string {
  if (!ok(v)) return DASH
  const r = Number(v.toFixed(d))
  const s = r > 0 ? '+' : r < 0 ? '−' : ''
  return `${s}US$ ${nf(d).format(Math.abs(v))}`
}
/** Dólares com casas adaptadas ao tamanho (US$ 0,042 / US$ 12,3 / US$ 1.204). */
export function smartUsd(v: number | null | undefined, signedOut = false): string {
  if (!ok(v)) return DASH
  const a = Math.abs(v)
  const d = a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 3
  return signedOut ? signedUsd(v, d) : usd(v, d)
}
export function price(v: number | null | undefined): string {
  if (!ok(v)) return DASH
  const a = Math.abs(v)
  const d = a >= 100 ? 2 : a >= 1 ? 3 : a >= 0.01 ? 5 : a >= 0.0001 ? 7 : 10
  return nf(d).format(v)
}
export function arrow(v: number | null | undefined, eps = 1e-9): '▲' | '▼' | '' {
  if (!ok(v)) return ''
  return v > eps ? '▲' : v < -eps ? '▼' : ''
}
export type Tone = 'gain' | 'loss' | 'flat'
export function tone(v: number | null | undefined, eps = 1e-9): Tone {
  if (!ok(v)) return 'flat'
  return v > eps ? 'gain' : v < -eps ? 'loss' : 'flat'
}
export const toneClass: Record<Tone, string> = { gain: 'text-gain', loss: 'text-loss', flat: 'text-ink-3' }

export function ago(sec: number | null | undefined): string {
  if (!ok(sec)) return DASH
  if (sec < 60) return `${Math.max(0, Math.round(sec))} s`
  if (sec < 3600) return `${Math.round(sec / 60)} min`
  if (sec < 86400) return `${nf(0, 1).format(sec / 3600)} h`
  return `${nf(0, 1).format(sec / 86400)} dias`
}
const TZ = 'America/Sao_Paulo'
export function tsTime(ts?: number | null, withDate = false): string {
  if (!ok(ts)) return DASH
  return new Date(ts * 1000).toLocaleString('pt-BR', { timeZone: TZ, hour: '2-digit', minute: '2-digit', ...(withDate ? { day: '2-digit', month: '2-digit' } : {}) })
}
export function isoTime(iso?: string | null, withDate = false): string {
  if (!iso) return DASH
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('pt-BR', { timeZone: TZ, hour: '2-digit', minute: '2-digit', ...(withDate ? { day: '2-digit', month: '2-digit' } : {}) })
}
export function dayMonth(ts?: number | null): string {
  if (!ok(ts)) return DASH
  return new Date(ts * 1000).toLocaleDateString('pt-BR', { timeZone: TZ, day: 'numeric', month: 'short' }).replace('.', '')
}
/** p-valor legível: "p 0,03" */
export function pval(p: number | null | undefined): string { return ok(p) ? `p ${nf(2).format(p)}` : DASH }
export function frac(v: number | null | undefined, d = 0): string { return ok(v) ? `${nf(d).format(v * 100)}%` : DASH }
