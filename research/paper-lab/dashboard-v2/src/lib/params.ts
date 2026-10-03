// Rótulos em português simples para os parâmetros de params.json, com unidade e formato.
import { num } from './format'

export type Kind = 'ratio' | 'pct' | 'int' | 'num' | 'bool' | 'hours' | 'text' | 'mode'
export interface ParamDef { label: string; kind: Kind; unit?: string; help?: string; min?: number; max?: number; step?: number }

export const PARAM_DEFS: Record<string, ParamDef> = {
  'gates.min_confidence': { label: 'Confiança mínima para operar', kind: 'ratio', min: 0, max: 1, step: 0.01, help: 'O modelo só age quando a confiança dele passa deste valor.' },
  'gates.min_prob_margin': { label: 'Margem mínima entre a 1ª e a 2ª opção', kind: 'ratio', min: 0, max: 1, step: 0.01 },
  'gates.margin_gate': { label: 'Exigir margem mínima', kind: 'bool' },
  'gates.max_skip_noul': { label: 'Incerteza máxima aceita', kind: 'ratio', min: 0, max: 1, step: 0.01 },
  'gates.cooldown_seconds': { label: 'Pausa mínima entre trades', kind: 'int', unit: 's', min: 15, step: 15 },
  'gates.max_trades_per_hour': { label: 'Máximo de trades por hora', kind: 'int', min: 1, max: 8, step: 1 },
  'gates.buy_fraction_usdt': { label: 'Fração do caixa por compra', kind: 'pct', min: 0.05, max: 0.5, step: 0.01 },
  'gates.min_usdt_trade': { label: 'Compra mínima', kind: 'num', unit: 'US$' },
  'gates.min_sol_trade': { label: 'Venda mínima', kind: 'num', unit: 'SOL' },
  'gates.max_exposure_frac': { label: 'Exposição máxima ao ativo', kind: 'pct', min: 0, max: 1, step: 0.05, help: 'Vazio = sem teto.' },
  'exec.mode': { label: 'Tipo de ordem', kind: 'mode' },
  'exec.extra_slippage_bps': { label: 'Slippage extra simulado', kind: 'num', unit: 'bps' },
  'exec.slippage_bps': { label: 'Slippage máximo aceito', kind: 'num', unit: 'bps' },
  'exec.network_fee_sol': { label: 'Taxa de rede', kind: 'num', unit: 'SOL' },
  'exec.offset_bps': { label: 'Distância da ordem limite', kind: 'num', unit: 'bps', min: 0, max: 1000, step: 1 },
  'exec.ttl_min': { label: 'Validade da ordem limite', kind: 'num', unit: 'min', min: 1, max: 1440, step: 1 },
  'exec.fee_bps': { label: 'Taxa da ordem limite', kind: 'num', unit: 'bps', min: 0, max: 1000, step: 1 },
  'exits.enabled': { label: 'Saídas automáticas', kind: 'bool' },
  'exits.tp': { label: 'Take-profit', kind: 'pct', min: 0.001, max: 1, step: 0.005 },
  'exits.sl': { label: 'Stop-loss', kind: 'pct', min: 0.001, max: 1, step: 0.005 },
  'exits.trail': { label: 'Trailing stop', kind: 'pct', min: 0.001, max: 1, step: 0.005 },
  'exits.trail_arm': { label: 'Armar o trailing a partir de', kind: 'pct', min: 0, max: 1, step: 0.005 },
  'exits.reentry_cooldown_min': { label: 'Espera para voltar a comprar', kind: 'int', unit: 'min', min: 0, max: 10080, step: 5 },
  hours: { label: 'Horas em que opera (Brasília)', kind: 'hours' },
  'ensemble.min_agree': { label: 'Modelos que precisam concordar', kind: 'int', min: 1, max: 3, step: 1 },
  'ensemble.pct_threshold': { label: 'Percentil mínimo de confiança', kind: 'pct', min: 0, max: 1, step: 0.05 },
  'ensemble.min_window': { label: 'Decisões mínimas na janela', kind: 'int', min: 1, step: 10 },
  'rule.grid_pct': { label: 'Passo da grade', kind: 'pct', min: 0.001, max: 0.5, step: 0.005 },
  'rule.levels': { label: 'Níveis da grade', kind: 'int', min: 1, max: 1000, step: 1 },
  'rule.timeframe': { label: 'Barras', kind: 'text' },
  'rule.rsi_period': { label: 'Período do RSI', kind: 'int', min: 1, max: 1000, step: 1 },
  'rule.lo': { label: 'RSI que liga a compra', kind: 'int', min: 0, max: 100, step: 1 },
  'rule.hi': { label: 'RSI que liga a venda', kind: 'int', min: 0, max: 100, step: 1 },
  'rule.ema_fast': { label: 'Média rápida (EMA)', kind: 'int', min: 1, max: 1000, step: 1 },
  'rule.ema_slow': { label: 'Média lenta (EMA)', kind: 'int', min: 1, max: 1000, step: 1 },
  'rule.donchian': { label: 'Janela do rompimento (barras)', kind: 'int', min: 1, max: 1000, step: 1 },
  'regime_filter.enabled': { label: 'Só comprar com SOL em alta', kind: 'bool' },
  'regime_filter.require_bull_for_buy': { label: 'Exigir alta para comprar', kind: 'bool' },
  'regime_filter.block_if_unknown': { label: 'Bloquear se o regime for desconhecido', kind: 'bool' },
}

/** Grupos mostrados no detalhe (tuning e limits ficam em "mais"). */
export const SHOWN_GROUPS: { key: string; label: string }[] = [
  { key: 'gates', label: 'Portões e tamanho' }, { key: 'exits', label: 'Saídas' }, { key: 'exec', label: 'Execução' },
  { key: 'hours', label: 'Horário' }, { key: 'ensemble', label: 'Ensemble' }, { key: 'rule', label: 'Regra' }, { key: 'regime_filter', label: 'Filtro de regime' },
]

export function fmtParam(path: string, v: unknown): string {
  const def = PARAM_DEFS[path]
  if (v === null || v === undefined) return def?.kind === 'pct' && path.endsWith('max_exposure_frac') ? 'sem teto' : '—'
  if (typeof v === 'boolean') return v ? 'sim' : 'não'
  if (Array.isArray(v)) return path === 'hours' ? v.map(h => `${h}h`).join(', ') : v.join(', ')
  if (typeof v === 'number') {
    if (def?.kind === 'pct') return `${num(v * 100, v * 100 % 1 ? 1 : 0)}%`
    if (def?.kind === 'ratio') return num(v, 2)
    const u = def?.unit
    const s = Number.isInteger(v) ? num(v, 0) : num(v, Math.abs(v) < 0.001 ? 6 : 3)
    return u === 'US$' ? `US$ ${s}` : u ? `${s} ${u}` : s
  }
  if (path === 'exec.mode') return v === 'limit' ? 'limite' : v === 'market' ? 'a mercado' : String(v)
  return String(v)
}

export function flatten(obj: Record<string, unknown>, prefix = ''): [string, unknown][] {
  const out: [string, unknown][] = []
  for (const [k, v] of Object.entries(obj || {})) {
    const p = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) out.push(...flatten(v as Record<string, unknown>, p))
    else out.push([p, v])
  }
  return out
}

/** Campos editáveis no "ajuste manual" de um portfólio (overlay do dashboard; o servidor valida tudo de novo). */
export const OVERLAY_FIELDS = ['min_confidence', 'min_prob_margin', 'max_skip_noul', 'buy_fraction_usdt', 'cooldown_seconds', 'max_trades_per_hour'] as const

export const TYPE_NAMES: Record<string, string> = {
  model_gated: 'Modelos com portão de confiança', hybrid: 'Híbridos: modelo + regime de SOL', rule_grid: 'Regra: grade',
  rule_rsi: 'Regra: RSI', rule_regime: 'Regra: regime de SOL', rule_donchian: 'Regra: Donchian + regime',
  lab_h1_exits: 'H1: saídas por take-profit, stop e trailing', lab_h2_ensemble: 'H2: ensemble por percentil', lab_h3_limit: 'H3: ordens limite',
  lab_h4_hours: 'H4: janelas de horário', real_bot: 'Bot real (referência)', funding_carry: 'Funding carry',
}
/** Campos que valem a pena por tipo (o resto continua visível no detalhe de cada teste). */
export const TYPE_FIELDS: Record<string, string[]> = {
  // confiança e incerteza ficam no perfil (artigo/relaxado/v2): mudar no tipo apagaria a diferença entre eles
  model_gated: ['gates.buy_fraction_usdt', 'gates.max_trades_per_hour', 'gates.cooldown_seconds'],
  hybrid: ['gates.buy_fraction_usdt', 'gates.max_trades_per_hour', 'gates.cooldown_seconds', 'regime_filter.enabled'],
  rule_grid: ['rule.grid_pct', 'rule.levels', 'gates.buy_fraction_usdt'],
  rule_rsi: ['rule.rsi_period', 'rule.lo', 'rule.hi', 'gates.buy_fraction_usdt'],
  rule_regime: ['rule.ema_fast', 'rule.ema_slow', 'gates.buy_fraction_usdt'],
  rule_donchian: ['rule.donchian', 'rule.ema_fast', 'rule.ema_slow', 'gates.buy_fraction_usdt'],
  lab_h1_exits: ['exits.tp', 'exits.sl', 'exits.trail', 'exits.trail_arm', 'exits.reentry_cooldown_min'],
  lab_h2_ensemble: ['ensemble.min_agree', 'ensemble.pct_threshold', 'ensemble.min_window', 'gates.buy_fraction_usdt'],
  lab_h3_limit: ['exec.offset_bps', 'exec.ttl_min', 'exec.fee_bps'],
  lab_h4_hours: ['hours'],
}
export const READ_ONLY_TYPES = new Set(['real_bot', 'funding_carry'])

export function getPath(obj: Record<string, unknown> | undefined, path: string): unknown {
  let cur: unknown = obj
  for (const k of path.split('.')) {
    if (!cur || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[k]
  }
  return cur
}

/** Valor do input (texto) → valor do JSON, ou erro em português. pct é digitado em % (25 → 0,25). */
export function parseInput(path: string, raw: string, limits?: { min?: number; max?: number }): { ok: true; v: unknown } | { ok: false; err: string } {
  const def = PARAM_DEFS[path]
  const s = raw.trim().replace(',', '.')
  if (def?.kind === 'hours') {
    if (!s) return { ok: true, v: null }
    const hs = s.split(/[\s;]+|,(?=\s*\d)/).map(x => x.replace(/h$/i, '')).filter(Boolean).map(Number)
    if (hs.some(h => !Number.isInteger(h) || h < 0 || h > 23)) return { ok: false, err: 'Use horas inteiras de 0 a 23, separadas por espaço.' }
    return { ok: true, v: [...new Set(hs)].sort((a, b) => a - b) }
  }
  if (s === '' && path.endsWith('max_exposure_frac')) return { ok: true, v: null }
  const n = Number(s)
  if (s === '' || !Number.isFinite(n)) return { ok: false, err: 'Digite um número.' }
  const v = def?.kind === 'pct' ? n / 100 : n
  if ((def?.kind === 'int') && !Number.isInteger(v)) return { ok: false, err: 'Tem de ser um número inteiro.' }
  const min = limits?.min ?? def?.min, max = limits?.max ?? def?.max
  const show = (x: number) => (def?.kind === 'pct' ? `${num(x * 100, 0)}%` : num(x, def?.kind === 'ratio' ? 2 : 0))
  if (min != null && v < min) return { ok: false, err: `Mínimo ${show(min)}.` }
  if (max != null && v > max) return { ok: false, err: `Máximo ${show(max)}.` }
  return { ok: true, v: def?.kind === 'pct' ? Number(v.toFixed(6)) : v }
}

export function toInput(path: string, v: unknown): string {
  const def = PARAM_DEFS[path]
  if (v == null) return ''
  if (Array.isArray(v)) return v.join(' ')
  if (typeof v === 'number') return def?.kind === 'pct' ? String(Number((v * 100).toFixed(4))).replace('.', ',') : String(v).replace('.', ',')
  return String(v)
}

/** Mensagem de erro do servidor (400 da escrita de params.json traz {layer, portfolios}). */
export function serverErrorText(msg: string): string {
  try {
    const j = JSON.parse(msg) as { layer?: string[]; portfolios?: Record<string, string[]> }
    const parts = [...(j.layer || [])]
    for (const [n, es] of Object.entries(j.portfolios || {}).slice(0, 4)) parts.push(`${n}: ${es.join('; ')}`)
    if (parts.length) return parts.join('\n')
  } catch { /* texto simples */ }
  return msg
}
