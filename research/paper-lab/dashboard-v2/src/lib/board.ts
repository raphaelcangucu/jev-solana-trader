// Do JSON do backend para as linhas do placar: nome humano, métricas, ordenação e filtros.
import type { Row } from './api'
import { describePortfolio, MEMES, type Description, type FamilyKey } from './describe'

export type SortKey = 'lucro' | 'habilidade' | 'segurar'
export const SORTS: { key: SortKey; label: string; hint: string }[] = [
  { key: 'lucro', label: 'Lucro', hint: 'Lucro desde o início, em % do capital inicial.' },
  { key: 'habilidade', label: 'Habilidade (sem beta)', hint: 'Lucro menos o que a exposição média ao ativo teria rendido sozinha. Perto de zero = o ganho veio do mercado, não da escolha.' },
  { key: 'segurar', label: 'Vs. segurar', hint: 'Diferença contra simplesmente segurar o livro inicial do começo ao fim.' },
]

export type FamilyFilter = 'all' | FamilyKey | 'forks'
export type AssetFilter = 'all' | 'SOL' | 'memes' | string

export interface Entry {
  row: Row
  d: Description
  pnlPct: number | null
  pnlUsd: number | null
  skillUsd: number | null
  skillPct: number | null
  timingP: number | null
  vsHoldPct: number | null
  vsHoldUsd: number | null
  exposure: number | null
  buys: number | null
  sells: number | null
  days: number | null
  minDays: number
  rt: number | null
  minRt: number
}

export function toEntry(row: Row): Entry {
  const sk = row.skill
  const pr = row.progress || {}
  return {
    row,
    d: describePortfolio(row),
    pnlPct: row.pnl_pct,
    pnlUsd: row.pnl,
    skillUsd: sk?.ex_exposure ?? null,
    skillPct: sk?.ex_exposure_pct ?? null,
    timingP: sk?.timing_p ?? null,
    vsHoldPct: row.vs_bh_pct,
    vsHoldUsd: row.vs_bh,
    exposure: sk?.exposure_pct ?? row.exposure_pct,
    buys: sk?.buys ?? null,
    sells: sk?.sells ?? null,
    days: pr.days ?? null,
    minDays: pr.min_days ?? 21,
    rt: pr.closed_rt ?? null,
    minRt: pr.min_closed_rt ?? 30,
  }
}

export function metric(e: Entry, k: SortKey): number | null {
  return k === 'lucro' ? e.pnlPct : k === 'habilidade' ? e.skillUsd : e.vsHoldPct
}

export function sortEntries(es: Entry[], k: SortKey): Entry[] {
  return [...es].sort((a, b) => {
    const x = metric(a, k), y = metric(b, k)
    if (x == null && y == null) return a.d.title.localeCompare(b.d.title)
    if (x == null) return 1
    if (y == null) return -1
    return y - x || a.d.title.localeCompare(b.d.title)
  })
}

export function matches(e: Entry, fam: FamilyFilter, asset: AssetFilter, q: string): boolean {
  if (fam === 'forks' ? !e.d.isFork : fam !== 'all' && e.d.family !== fam) return false
  if (asset === 'memes' ? !MEMES.includes(e.d.asset) : asset !== 'all' && e.d.asset !== asset) return false
  if (q) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    if (!words.every(w => e.d.search.includes(w))) return false
  }
  return true
}

/** Quem lidera em lucro e em habilidade (para a frase da faixa do experimento). */
export function leaders(es: Entry[]) {
  const byPnl = sortEntries(es.filter(e => e.pnlPct != null), 'lucro')[0] ?? null
  const bySkill = sortEntries(es.filter(e => e.skillUsd != null), 'habilidade')[0] ?? null
  return { byPnl, bySkill }
}

export const median = (xs: number[]) => {
  if (!xs.length) return null
  const s = [...xs].sort((a, b) => a - b)
  const m = s.length >> 1
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}
