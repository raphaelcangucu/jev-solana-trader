// Histórico da simulação retroativa: meses de 30 dias lado a lado e a janela de 6 meses. Módulo puro (roda com `node --test`).
import type { BtChart, BtIndex, BtIndexRun } from './api.ts'
import { FAM_LINE, parseFamilyKey, whoOf } from './backtest.ts'
import { describePortfolio, type Description } from './describe.ts'

const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const BRT_MS = -3 * 3600 * 1000
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const fin = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

function brt(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const ms = Date.parse(iso)
  return Number.isFinite(ms) ? new Date(ms + BRT_MS) : null
}
const dm = (d: Date) => `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`

/** Nome humano a partir só do id (o índice não traz metadados): "poorjev relaxado em FARTCOIN". */
export function describeName(name: string): Description { return describePortfolio({ name }) }
export function whoName(name: string): string { return whoOf(describeName(name)) }

// ---------------------------------------------------------------- seletor de período

export interface RunPill { run_id: string; kind: BtIndexRun['kind']; label: string; sub: string; title: string }

/** Mês de 30 dias leva o nome do mês em que começa ("Set" = 6 set → 6 out); a janela longa é "6 meses". */
export function runPill(r: BtIndexRun): RunPill {
  const a = brt(r.start_brt), b = brt(r.end_brt)
  const sub = a && b ? `${dm(a)} → ${dm(b)}` : r.run_id
  if (r.kind === '180d') {
    const months = r.days ? Math.round(r.days / 30.4) : 6
    return { run_id: r.run_id, kind: r.kind, label: `${months} meses`, sub, title: `${months} meses, ${sub}` }
  }
  // o mês que cobre a maior parte da janela: o do meio dela
  const mid = a && b ? new Date((a.getTime() + b.getTime()) / 2) : a
  const label = mid ? cap(MONTHS[mid.getUTCMonth()]) : r.run_id
  return { run_id: r.run_id, kind: r.kind, label, sub, title: `${label}: ${sub}` }
}

const byEndDesc = (a: BtIndexRun, b: BtIndexRun) => String(b.end_brt ?? '').localeCompare(String(a.end_brt ?? '')) || b.run_id.localeCompare(a.run_id)

/** Ordem dos botões: meses de 30 dias do mais recente para o mais antigo, depois as janelas longas. Só runs que existem. */
export function orderRuns(idx: BtIndex | null | undefined): BtIndexRun[] {
  const rs = (idx?.runs ?? []).filter(r => r.available !== false)
  return [...rs.filter(r => r.kind !== '180d').sort(byEndDesc), ...rs.filter(r => r.kind === '180d').sort(byEndDesc)]
}

/** Os `n` meses de 30 dias mais recentes, em ordem cronológica (mais antigo à esquerda). */
export function monthlyRuns(idx: BtIndex | null | undefined, n = 3): BtIndexRun[] {
  return (idx?.runs ?? []).filter(r => r.kind === '30d' && r.available !== false).sort(byEndDesc).slice(0, n).reverse()
}

/** Variação média da cesta de memecoins (todos os ativos menos SOL). */
export function memesRet(assets: Record<string, number | null> | null | undefined): number | null {
  const vs = Object.entries(assets ?? {}).filter(([k, v]) => k !== 'SOL' && fin(v)).map(([, v]) => v as number)
  return vs.length ? vs.reduce((a, b) => a + b, 0) / vs.length : null
}

// ---------------------------------------------------------------- consistência entre meses

export interface MonthHit { run_id: string; skillRank: number | null; pnlRank: number | null }
export interface Consistency { name: string; count: number; hits: MonthHit[]; best: number }

/** Quem aparece no top `n` (por habilidade ou por lucro) de cada mês; ordenado por nº de meses, depois pela melhor posição. */
export function consistency(runs: BtIndexRun[], n = 5): Consistency[] {
  const m = new Map<string, Consistency>()
  for (const r of runs) {
    const sk = (r.top_skill ?? []).slice(0, n).map(t => t.name)
    const pn = (r.top_pnl ?? []).slice(0, n).map(t => t.name)
    for (const name of new Set([...sk, ...pn])) {
      const c = m.get(name) ?? { name, count: 0, hits: [], best: Infinity }
      const si = sk.indexOf(name), pi = pn.indexOf(name)
      const hit = { run_id: r.run_id, skillRank: si >= 0 ? si + 1 : null, pnlRank: pi >= 0 ? pi + 1 : null }
      c.count += 1
      c.hits.push(hit)
      c.best = Math.min(c.best, hit.skillRank ?? Infinity, hit.pnlRank ?? Infinity)
      m.set(name, c)
    }
  }
  return [...m.values()].sort((a, b) => b.count - a.count || a.best - b.best || a.name.localeCompare(b.name))
}

// ---------------------------------------------------------------- linhas do gráfico de 6 meses

/** Paleta categórica documentada, ordem fixa (tokens --series-N em index.css, claro e escuro validados). */
export const SERIES = Array.from({ length: 8 }, (_, i) => `var(--series-${i + 1})`)
export type LineStyleKey = 'solid' | 'dashed' | 'dotted' | 'longdash'

export interface LineDef {
  id: string; label: string; color: string; style: LineStyleKey; group: 'bench' | 'strategy' | 'family'
  /** nome do portfólio (abre o detalhe) */
  name?: string
  data: (number | null)[]
}

/** Benchmarks em tinta neutra e tracejados (nunca uma cor de série): só segurar SOL, cesta de memecoins, USDC 6%/ano. */
export const BENCH: { key: 'sol_bh' | 'memes_bh' | 'usdc'; label: string; color: string; style: LineStyleKey }[] = [
  { key: 'sol_bh', label: 'Só segurar SOL', color: 'var(--ink-2)', style: 'dashed' },
  { key: 'memes_bh', label: 'Cesta de memecoins', color: 'var(--ink-3)', style: 'longdash' },
  { key: 'usdc', label: 'USDC a 6% ao ano', color: 'var(--ink-3)', style: 'dotted' },
]

export function benchLines(ch: BtChart): LineDef[] {
  return BENCH.flatMap(b => {
    const data = ch.benchmarks?.[b.key]
    return Array.isArray(data) ? [{ id: `bench:${b.key}`, label: b.label, color: b.color, style: b.style, group: 'bench' as const, data }] : []
  })
}

export interface PoolItem extends LineDef { defaultOn: boolean; why: string }

/** Até 8 linhas de estratégia, cada uma com a sua cor fixa (pela posição no conjunto, nunca pela visibilidade).
 *  Ligadas por padrão: top 3 por habilidade, top 2 por lucro (sem repetir) e o bot real A e B. */
export function strategyPool(ch: BtChart, run?: BtIndexRun | null, max = 8): PoolItem[] {
  const top = ch.top ?? {}
  const has = (n: string) => Array.isArray(top[n])
  const skill = (run?.top_skill ?? []).map(t => t.name).filter(has)
  const pnl = (run?.top_pnl ?? []).map(t => t.name).filter(has)
  const keys = Object.keys(top)
  const picked: { name: string; why: string; on: boolean }[] = []
  const add = (name: string, why: string, on: boolean) => { if (!picked.some(p => p.name === name)) picked.push({ name, why, on }) }
  const sk = skill.length ? skill : keys
  sk.slice(0, 3).forEach((n, i) => add(n, `${i + 1}º em habilidade`, true))
  let k = 0
  for (const n of pnl.length ? pnl : keys) {
    if (k >= 2) break
    if (picked.some(p => p.name === n)) continue
    add(n, `${pnl.indexOf(n) + 1 || k + 1}º em lucro`, true); k++
  }
  const bots = Object.keys(ch.realbot ?? {}).filter(b => Array.isArray(ch.realbot[b])).sort()
  const rest = [...skill, ...pnl, ...keys]
  const room = Math.max(0, max - Math.min(bots.length, 2))
  for (const n of rest) { if (picked.length >= room) break; add(n, skill.includes(n) ? `${skill.indexOf(n) + 1}º em habilidade` : pnl.includes(n) ? `${pnl.indexOf(n) + 1}º em lucro` : 'no topo', false) }
  const out: PoolItem[] = picked.slice(0, room).map(p => ({
    id: `top:${p.name}`, name: p.name, label: whoName(p.name), color: '', style: 'solid', group: 'strategy', data: top[p.name], defaultOn: p.on, why: p.why,
  }))
  for (const b of bots.slice(0, 2)) {
    out.push({ id: `bot:${b}`, label: `Bot real, livro ${b}`, color: '', style: 'solid', group: 'strategy', data: ch.realbot[b], defaultOn: true,
      why: b === 'A' ? 'como roda hoje' : b === 'B' ? 'saídas mecânicas' : 'bot real' })
  }
  return out.slice(0, max).map((p, i) => ({ ...p, color: SERIES[i] }))
}

export { parseFamilyKey }

/** Escopos presentes nas chaves de família (para o seletor SOL / Memecoins quando o gerador separa os dois). */
export function familyScopes(ch: BtChart): ('' | 'SOL' | 'Memecoins')[] {
  const s = new Set(Object.keys(ch.families ?? {}).map(k => parseFamilyKey(k).scope))
  return (['SOL', 'Memecoins', ''] as const).filter(x => s.has(x))
}

export function familyLines(ch: BtChart, scope: '' | 'SOL' | 'Memecoins'): LineDef[] {
  const out: (LineDef & { ord: number })[] = []
  const used = new Set<string>()
  for (const [key, data] of Object.entries(ch.families ?? {})) {
    if (!Array.isArray(data)) continue
    const p = parseFamilyKey(key)
    if (p.scope !== scope) continue
    const f = p.fam
    // família desconhecida, ou repetida no mesmo escopo: o primeiro slot livre da paleta (nunca um 9º tom)
    let color = f && !used.has(f.key) ? f.color : ''
    const ord = f ? FAM_LINE.indexOf(f) : 99
    if (!color) {
      const free = FAM_LINE.find(x => !used.has(x.key))
      if (!free) continue
      color = free.color; used.add(free.key)
    } else used.add(f!.key)
    out.push({ id: `fam:${key}`, label: f ? f.label : p.rest, color, style: 'solid', group: 'family', data, ord })
  }
  return out.sort((a, b) => a.ord - b.ord).map(({ ord: _o, ...l }) => l)
}

// ---------------------------------------------------------------- leitura

export const asReturn = (v: number | null | undefined): number | null => (fin(v) ? (v / 1000 - 1) * 100 : null)
export function lastValue(d: (number | null)[]): number | null {
  for (let i = d.length - 1; i >= 0; i--) if (fin(d[i])) return d[i] as number
  return null
}
/** Pior queda do pico ao vale (%), para a tabela. */
export function maxDrawdown(d: (number | null)[]): number | null {
  let peak = -Infinity, dd = 0, seen = false
  for (const v of d) {
    if (!fin(v)) continue
    seen = true
    peak = Math.max(peak, v)
    dd = Math.min(dd, (v / peak - 1) * 100)
  }
  return seen ? dd : null
}

/** Rótulos diretos no fim das linhas: mantém, por prioridade, só os que não encostam num já mantido (nunca empurra
 *  um rótulo para longe da linha; o que não cabe fica com a legenda e o tooltip). */
export function placeEndLabels(items: { id: string; y: number | null; priority: number }[], gap: number, top: number, bottom: number): Map<string, number> {
  const kept = new Map<string, number>()
  for (const it of [...items].sort((a, b) => a.priority - b.priority)) {
    if (it.y == null || !Number.isFinite(it.y) || it.y < top || it.y > bottom) continue
    let ok = true
    for (const y of kept.values()) if (Math.abs(y - it.y) < gap) { ok = false; break }
    if (ok) kept.set(it.id, it.y)
  }
  return kept
}

/** "2026-04" → "abr"; com o ano quando a faixa cruza anos. */
export function monthShort(m: string, withYear = false): string {
  const x = /^(\d{4})-(\d{2})/.exec(m)
  if (!x) return m
  const s = MONTHS[Number(x[2]) - 1] ?? m
  return withYear ? `${s}/${x[1].slice(2)}` : s
}

/** O run mensal de 30 dias que cobre o mesmo mês (início a até 4 dias de distância), para ligar a faixa mensal ao run. */
export function runForMonth(idx: BtIndex | null | undefined, start: string | null | undefined): string | null {
  const a = start ? Date.parse(start) : NaN
  if (!Number.isFinite(a)) return null
  const r = (idx?.runs ?? []).find(r => r.kind === '30d' && r.available !== false && r.start_brt && Math.abs(Date.parse(r.start_brt) - a) < 4 * 86400_000)
  return r?.run_id ?? null
}
