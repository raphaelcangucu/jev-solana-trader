// Simulação retroativa de 30 dias: do summary.json às linhas do placar retroativo. Módulo puro (roda com `node --test`).
import type { BtEquity, BtFamily, BtPortfolio, BtVerdict } from './api.ts'
import { describePortfolio, type Description } from './describe.ts'

export type BtSortKey = 'habilidade' | 'lucro' | 'segurar' | 'veredito'
export const BT_SORTS: { key: BtSortKey; label: string; hint: string }[] = [
  { key: 'habilidade', label: 'Habilidade', hint: 'Lucro menos o que a exposição média ao ativo teria rendido sozinha. É a parte que veio das escolhas, não do mercado.' },
  { key: 'lucro', label: 'Lucro', hint: 'Quanto a carteira teria ganho nos 30 dias, em % do capital inicial.' },
  { key: 'segurar', label: 'Vs. segurar', hint: 'Diferença contra simplesmente segurar o livro inicial do começo ao fim.' },
  { key: 'veredito', label: 'Veredito', hint: 'Vencedoras primeiro, depois inconclusivas, perdedoras por último (mesmo critério do run ao vivo).' },
]

export interface BtEntry {
  p: BtPortfolio
  d: Description
  /** título com o ativo quando não é SOL: "poorjev relaxado + saídas em FARTCOIN" */
  who: string
  pnlPct: number | null
  pnlUsd: number | null
  vsHoldPct: number | null
  vsHoldUsd: number | null
  skillUsd: number | null
  skillPct: number | null
  timingP: number | null
  maxDd: number | null
  trades: number | null
  weeksBeat: number | null
  /** trechos que bateram só segurar: semanas (30 dias) ou meses (6 meses, quando o summary traz `months`) */
  segBeat: number | null
  segOf: number
  segUnit: 'semana' | 'mês'
  verdict: BtVerdict
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

const VERDICT: Record<string, BtVerdict> = {
  vencedora: 'vencedora', vencedor: 'vencedora', winner: 'vencedora',
  perdedora: 'perdedora', perdedor: 'perdedora', loser: 'perdedora',
}
export const normVerdict = (v: unknown): BtVerdict => VERDICT[String(v ?? '').trim().toLowerCase()] ?? 'inconclusiva'

export function whoOf(d: Description): string {
  return d.asset && d.asset !== 'SOL' ? `${d.title} em ${d.asset}` : d.title
}

export function toBtEntry(p: BtPortfolio): BtEntry {
  const d = describePortfolio({ ...p, name: p.name, asset: p.asset ?? null })
  const end = num(p.end_value), vs = num(p.vs_bh), start = num(p.start_value), skill = num(p.skill)
  const bh = end != null && vs != null ? end - vs : null
  const months = Array.isArray(p.months) && p.months.length ? p.months : null
  const seg = months || p.months_beat_bh != null
    ? { segBeat: num(p.months_beat_bh), segOf: months?.length ?? 6, segUnit: 'mês' as const }
    : { segBeat: num(p.weeks_beat_bh), segOf: p.weeks?.length || 4, segUnit: 'semana' as const }
  return {
    ...seg,
    p, d, who: whoOf(d),
    pnlPct: num(p.pnl_pct), pnlUsd: num(p.pnl),
    vsHoldUsd: vs,
    vsHoldPct: num(p.vs_bh_pct) ?? (bh && bh > 0 && end != null ? (end / bh - 1) * 100 : null),
    skillUsd: skill,
    skillPct: num(p.skill_pct) ?? (skill != null && start ? (skill / start) * 100 : null),
    timingP: num(p.timing_p), maxDd: num(p.max_dd_pct), trades: num(p.trades), weeksBeat: num(p.weeks_beat_bh),
    verdict: normVerdict(p.verdict),
  }
}

const VERDICT_RANK: Record<BtVerdict, number> = { vencedora: 0, inconclusiva: 1, perdedora: 2 }

export function btMetric(e: BtEntry, k: BtSortKey): number | null {
  if (k === 'lucro') return e.pnlPct
  if (k === 'segurar') return e.vsHoldPct
  return e.skillUsd // habilidade; no veredito é o desempate dentro de cada grupo
}

export function sortBt(es: BtEntry[], k: BtSortKey): BtEntry[] {
  return [...es].sort((a, b) => {
    if (k === 'veredito') {
      const r = VERDICT_RANK[a.verdict] - VERDICT_RANK[b.verdict]
      if (r) return r
    }
    const x = btMetric(a, k), y = btMetric(b, k)
    if (x == null && y == null) return a.who.localeCompare(b.who)
    if (x == null) return 1
    if (y == null) return -1
    return y - x || a.who.localeCompare(b.who)
  })
}

/** O topo da ordenação ativa ganha marca-texto só quando é mesmo um destaque (positivo, ou vencedora). */
export function isHighlight(e: BtEntry, k: BtSortKey): boolean {
  if (k === 'veredito') return e.verdict === 'vencedora'
  return (btMetric(e, k) ?? 0) > 0
}

// ---------------------------------------------------------------- frase do vencedor com marca-texto

export interface Segment { text: string; mark?: boolean }

/** Troca os ids crus (ex.: "h1_exits_FARTCOIN_poorjev_relaxed") pelo nome humano marcado; marca também o nome humano
 *  quando o texto já o traz. Só casa o id inteiro (sem letra, número ou "_" colado dos lados). */
export function markWinners(text: string, targets: { raw: string; label: string }[]): Segment[] {
  const ts = targets.filter(t => t.raw || t.label)
  if (!text) return []
  const keys = new Map<string, string>()
  for (const t of ts) {
    if (t.raw) keys.set(t.raw, t.label || t.raw)
    if (t.label && !keys.has(t.label)) keys.set(t.label, t.label)
  }
  const pats = [...keys.keys()].sort((a, b) => b.length - a.length).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!pats.length) return [{ text }]
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(${pats.join('|')})(?![\\p{L}\\p{N}_])`, 'gu')
  const out: Segment[] = []
  let last = 0
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0
    if (i > last) out.push({ text: text.slice(last, i) })
    out.push({ text: keys.get(m[0]) ?? m[0], mark: true })
    last = i + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last) })
  return out
}

// ---------------------------------------------------------------- datas (sempre no relógio de Brasília)

const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const BRT_MS = -3 * 3600 * 1000

function brtParts(isoOrTs: string | number | null | undefined) {
  if (isoOrTs == null || isoOrTs === '') return null
  const ms = typeof isoOrTs === 'number' ? isoOrTs * 1000 : Date.parse(isoOrTs)
  if (!Number.isFinite(ms)) return null
  const d = new Date(ms + BRT_MS)
  return { day: d.getUTCDate(), month: d.getUTCMonth(), year: d.getUTCFullYear(), h: d.getUTCHours(), m: d.getUTCMinutes() }
}
/** "6 set" */
export function dayMon(isoOrTs: string | number | null | undefined): string {
  const p = brtParts(isoOrTs)
  return p ? `${p.day} ${MONTHS[p.month]}` : '—'
}
/** "6 set → 6 out" */
export function windowLabel(w: { start_brt?: string | null; end_brt?: string | null } | null | undefined): string {
  return `${dayMon(w?.start_brt)} → ${dayMon(w?.end_brt)}`
}
/** "6 out, 03:12" */
export function stamp(iso: string | null | undefined): string {
  const p = brtParts(iso)
  return p ? `${p.day} ${MONTHS[p.month]}, ${String(p.h).padStart(2, '0')}:${String(p.m).padStart(2, '0')}` : '—'
}

// ---------------------------------------------------------------- semanas

export interface WeekRow { i: number; from: number; to: number; pct: number | null; bhPct: number | null; beat: boolean | null }

/** Divide a janela da curva em `n` trechos iguais e mede carteira e só segurar em cada um (mesma fonte, comparável). */
export function weeksFromEquity(eq: BtEquity | null | undefined, n = 4): WeekRow[] {
  if (!eq || eq.t.length < 2) return []
  const t0 = eq.t[0], t1 = eq.t[eq.t.length - 1]
  const at = (ts: number) => {
    let k = 0
    while (k < eq.t.length - 1 && eq.t[k + 1] <= ts) k++
    return k
  }
  const out: WeekRow[] = []
  for (let i = 0; i < n; i++) {
    const a = t0 + ((t1 - t0) * i) / n, b = t0 + ((t1 - t0) * (i + 1)) / n
    const ia = at(a), ib = i === n - 1 ? eq.t.length - 1 : at(b)
    const e0 = eq.equity[ia], e1 = eq.equity[ib], b0 = eq.bh[ia], b1 = eq.bh[ib]
    const pct = e0 ? (e1 / e0 - 1) * 100 : null
    const bhPct = b0 && b1 != null ? (b1 / b0 - 1) * 100 : null
    out.push({ i: i + 1, from: eq.t[ia], to: eq.t[ib], pct, bhPct, beat: pct != null && bhPct != null ? pct > bhPct : null })
  }
  return out
}

// ---------------------------------------------------------------- famílias e cobertura

/** Famílias como aparecem em summaries, chart.json e no lab ao vivo. Ordem e cores fixas: as seis `--fam-*` do painel,
 *  mais Jev e Forks nos dois slots que sobram da paleta documentada (`--series-6`, `--series-8`). */
export const FAM_LINE: { key: string; label: string; color: string; re: RegExp }[] = [
  { key: 'von', label: 'Modelos von', color: 'var(--fam-von)', re: /^(von|modelos?|models?)$/ },
  { key: 'poorjev', label: 'poorjev', color: 'var(--fam-poorjev)', re: /^poorjev$/ },
  { key: 'laya', label: 'Laya', color: 'var(--fam-laya)', re: /^laya$/ },
  { key: 'lab', label: 'Hipóteses', color: 'var(--fam-lab)', re: /^(lab|hip[oó]teses?( \(lab\))?|hypothes[ie]s|h\d)$/ },
  { key: 'rules', label: 'Regras', color: 'var(--fam-rules)', re: /^(rules?|regras?)$/ },
  { key: 'jev', label: 'Jev', color: 'var(--series-6)', re: /^jev$/ },
  { key: 'hybrid', label: 'Híbridos', color: 'var(--fam-hybrid)', re: /^(hybrids?|h[ií]bridos?)$/ },
  { key: 'forks', label: 'Forks', color: 'var(--series-8)', re: /^forks?$/ },
]
export type FamScope = '' | 'SOL' | 'Memecoins'

/** "SOL · poorjev" → { scope: 'SOL', fam: poorjev }; "meme · regras", "Meme · hipóteses (lab)", "SOL rule", "SOL lab",
 *  "lab", "h1_exits" também. Família desconhecida: fam null e `rest` com o texto sem o prefixo. */
export function parseFamilyKey(key: string): { scope: FamScope; fam: (typeof FAM_LINE)[number] | null; rest: string } {
  const m = /^\s*(sol|memes?|memecoins?)(?:\s*[·:|/-]\s*|\s+)(.+)$/i.exec(key)
  const scope: FamScope = m ? (m[1].toLowerCase() === 'sol' ? 'SOL' : 'Memecoins') : ''
  const rest = (m ? m[2] : key).trim()
  const k = rest.toLowerCase()
  return { scope, rest, fam: FAM_LINE.find(f => f.re.test(k)) ?? FAM_LINE.find(f => f.re.test(k.split(/[_\s]/)[0])) ?? null }
}

/** Rótulo humano, cor da família e escopo (SOL / Memecoins) de uma chave de família de qualquer fonte. */
export function familyInfo(key: string): { label: string; color: string; scope: FamScope; key: string | null } {
  const p = parseFamilyKey(key)
  return p.fam ? { label: p.fam.label, color: p.fam.color, scope: p.scope, key: p.fam.key }
    : { label: p.rest || key, color: 'var(--ink-3)', scope: p.scope, key: null }
}

/** Cobertura pode vir como fração (0,98) ou porcentagem (98): sempre devolve porcentagem. */
export function asPct(v: number | null | undefined): number | null {
  if (typeof v !== 'number' || !Number.isFinite(v)) return null
  return v <= 1 ? v * 100 : v
}

export function familySorted(fs: BtFamily[]): BtFamily[] {
  return [...fs].sort((a, b) => (b.median_pnl_pct ?? -Infinity) - (a.median_pnl_pct ?? -Infinity))
}
