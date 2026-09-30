const nf = (d: number) => new Intl.NumberFormat('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })
const cache: Record<number, Intl.NumberFormat> = {}
export function num(v: number | null | undefined, d = 2): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return (cache[d] ??= nf(d)).format(v)
}
export function usd(v: number | null | undefined, d = 2): string { return v == null || !Number.isFinite(v) ? '—' : `$${num(v, d)}` }
export function signed(v: number | null | undefined, d = 2, suffix = ''): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const s = v > 0 ? '+' : v < 0 ? '−' : '±'
  return `${s}${num(Math.abs(v), d)}${suffix}`
}
export function signedUsd(v: number | null | undefined, d = 2): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const s = v > 0 ? '+' : v < 0 ? '−' : '±'
  return `${s}$${num(Math.abs(v), d)}`
}
export function pct(v: number | null | undefined, d = 2): string { return v == null || !Number.isFinite(v) ? '—' : `${num(v, d)}%` }
export function price(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const a = Math.abs(v)
  const d = a >= 100 ? 2 : a >= 1 ? 3 : a >= 0.01 ? 5 : a >= 0.0001 ? 7 : 10
  return num(v, d)
}
export function ago(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec)) return '—'
  if (sec < 60) return `${Math.round(sec)}s`
  if (sec < 3600) return `${Math.round(sec / 60)}min`
  if (sec < 86400) return `${(sec / 3600).toFixed(1)}h`
  return `${(sec / 86400).toFixed(1)}d`
}
export function brtTime(iso?: string | null, withDate = false): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit', ...(withDate ? { day: '2-digit', month: '2-digit' } : {}) })
}
export function tsBrt(ts?: number | null, withDate = true): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', ...(withDate ? { day: '2-digit', month: '2-digit' } : {}) })
}
export const toneOf = (v: number | null | undefined, eps = 1e-9) => (v == null ? 'text-muted-foreground' : v > eps ? 'text-up' : v < -eps ? 'text-down' : 'text-muted-foreground')
