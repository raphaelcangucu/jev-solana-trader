// Nomes humanos para os ids dos portfólios. Módulo puro (sem React, sem aliases) para rodar com `node --test`.
// Exemplos (testados em describe.test.ts):
//   h1_exits_FARTCOIN_poorjev_relaxed → "poorjev relaxado + saídas"   [FARTCOIN] [hipótese H1]
//   meme_WIF_relaxed / WIF_relaxed    → "von relaxado"                [WIF] [modelo]
//   WIF_poorjev_baseline              → "poorjev artigo"              [WIF] [modelo]
//   BONK_rule_donch_regime_full       → "Donchian + regime, 100%"     [BONK] [regra]
//   hybrid_von_relaxed_cap2           → "von relaxado + regime"       [SOL] [híbrido]
//   h2_ensemble_sol                   → "Ensemble dos 3 modelos"      [SOL] [hipótese H2]
//   relaxed_expcap50                  → "von relaxado, exposição ≤ 50%" [SOL] [teste de exposição]
//   grid_sol_2pct / rsi_sol_1h        → "Grade de 2%" / "RSI de 1 hora" [SOL] [regra]
//   laya_baseline                     → "Laya artigo"                 [SOL] [modelo]
//   relaxed__fork2                    → "von relaxado, ajuste 2"      [SOL] [fork]
import type { ParamsBrief } from './api'

export type FamilyKey = 'von' | 'poorjev' | 'laya' | 'lab' | 'rules' | 'hybrid'

/** Ordem = ordem da paleta documentada (cor segue a família, nunca a posição). */
export const FAMILIES: { key: FamilyKey; label: string; color: string }[] = [
  { key: 'von', label: 'Modelos von', color: 'var(--fam-von)' },
  { key: 'poorjev', label: 'poorjev', color: 'var(--fam-poorjev)' },
  { key: 'laya', label: 'Laya', color: 'var(--fam-laya)' },
  { key: 'lab', label: 'Hipóteses', color: 'var(--fam-lab)' },
  { key: 'rules', label: 'Regras', color: 'var(--fam-rules)' },
  { key: 'hybrid', label: 'Híbridos', color: 'var(--fam-hybrid)' },
]
export const familyOf = (k: FamilyKey) => FAMILIES.find(f => f.key === k)!

export const MEMES = ['BONK', 'FARTCOIN', 'GOAT', 'MEW', 'PNUT', 'POPCAT', 'WIF']

export interface DescribeInput {
  name: string
  asset?: string | null
  model?: string | null
  kind?: string | null
  hyp?: string | null
  profile?: string | null
  parent?: string | null
  label?: string | null
  params_diff?: Record<string, Record<string, unknown>> | null
  params_brief?: ParamsBrief | null
  /** quem criou o fork: "nightly" (tuner) ou "claude-night" (revisão autónoma) */
  fork_who?: string | null
  /** resumo dos critérios de texto próprios (forks de critérios) */
  criteria_summary?: string | null
}

export interface Description {
  title: string
  asset: string
  /** chip de família/hipótese: "modelo", "regra", "híbrido", "hipótese H1", "fork"… */
  tag: string
  family: FamilyKey
  isFork: boolean
  forkN: number | null
  explain: string
  /** texto curto para a busca (título, ativo, id, rótulos) */
  search: string
}

const PROFILE: Record<string, string> = { baseline: 'artigo', article: 'artigo', relaxed: 'relaxado', v2: 'critérios v2' }
const BRAIN: Record<string, string> = { von: 'von', laya: 'Laya', poorjev: 'poorjev', jev: 'Jev' }

const n2 = (v: number, d = 2) => v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: d })
const pc = (v: number | undefined | null, d = 1) => (v == null ? '?' : `${n2(v * 100, d)}%`)
const fracTxt = (v: number | null | undefined) => (v == null ? 'um quarto' : v >= 0.999 ? 'todo o caixa' : `${pc(v, 0)} do caixa`)

function gateTxt(brain: string, p: ParamsBrief | null | undefined, profile: string | null): string {
  const conf = p?.min_confidence ?? (profile === 'baseline' ? 0.6 : 0.35)
  const margin = p?.margin_gate ? p?.min_prob_margin ?? 0.2 : profile === 'relaxed' || profile === 'v2' ? (p ? null : 0.2) : null
  return `o ${brain} tem confiança ≥ ${n2(conf)}` + (margin ? ` e margem ≥ ${n2(margin)}` : '')
}

const DIFF_LABEL: Record<string, string> = {
  'gates.min_confidence': 'confiança mínima', 'gates.min_prob_margin': 'margem mínima', 'gates.max_skip_noul': 'incerteza máxima',
  'gates.cooldown_seconds': 'pausa entre trades (s)', 'gates.max_trades_per_hour': 'trades por hora', 'gates.buy_fraction_usdt': 'fração por compra',
  'exits.tp': 'take-profit', 'exits.sl': 'stop-loss', 'exits.trail': 'trailing', 'exits.trail_arm': 'armar trailing',
  'exits.reentry_cooldown_min': 'reentrada (min)', 'exec.offset_bps': 'distância da ordem limite (bps)', 'exec.ttl_min': 'validade da ordem (min)',
  'ensemble.pct_threshold': 'percentil mínimo',
}
export function diffText(diff: Record<string, Record<string, unknown>> | null | undefined): string {
  if (!diff) return ''
  const out: string[] = []
  for (const [g, vals] of Object.entries(diff)) {
    if (g === 'criteria') continue // critérios de texto: descritos à parte (forks de critérios)
    if (!vals || typeof vals !== 'object') continue
    for (const [k, v] of Object.entries(vals)) {
      const label = DIFF_LABEL[`${g}.${k}`] || `${g}.${k}`
      out.push(`${label} ${typeof v === 'number' ? n2(v, 3) : String(v)}`)
    }
  }
  return out.join(', ')
}

function detectAsset(tokens: string[], given?: string | null): string {
  if (given) return given
  const t = tokens.find(x => MEMES.includes(x))
  return t || 'SOL'
}

/** Núcleo sem forks. */
function describeBase(inp: DescribeInput): Omit<Description, 'search' | 'isFork' | 'forkN'> {
  let name = inp.name
  const p = inp.params_brief
  if (name.startsWith('meme_')) name = name.slice(5)
  const toks = name.split('_')
  const asset = detectAsset(toks, inp.asset)
  const rest = toks.filter(t => t !== asset && t !== 'sol')
  const last = rest[rest.length - 1]
  const profile = inp.profile || (last && PROFILE[last] ? last : null)
  const prof = profile ? PROFILE[profile] ?? profile : ''
  const brainKey = rest.find(t => BRAIN[t]) || (rest[0] && PROFILE[rest[0]] ? 'von' : undefined)
  const brain = BRAIN[brainKey || ''] || 'von'

  // ---- hipóteses do lab
  const hyp = inp.hyp || (rest[0] === 'h1' ? 'H1' : rest[0] === 'h2' ? 'H2' : rest[0] === 'h3' ? 'H3' : rest[0] === 'h4' ? 'H4' : null)
  if (hyp && /^H[1-4]$/.test(hyp)) {
    const onHybrid = rest.includes('hybrid')
    const base = onHybrid ? `híbrido ${brain}` : `${brain} ${prof || 'relaxado'}`.trim()
    const tag = `hipótese ${hyp}`
    if (hyp === 'H1') {
      const ex = p?.exits
      const levels = ex ? ` (${pc(ex.tp)} / ${pc(ex.sl)} / ${pc(ex.trail)})` : ''
      return {
        title: `${base} + saídas`, asset, tag, family: 'lab',
        explain: onHybrid
          ? `Usa as decisões do híbrido von (só compra com SOL em alta) e vende por take-profit, stop-loss ou trailing${levels}.`
          : `Compra quando ${gateTxt(brain, p, profile || 'relaxed')} e vende por take-profit, stop-loss ou trailing${levels}.`,
      }
    }
    if (hyp === 'H2') {
      const en = p?.ensemble
      return {
        title: 'Ensemble dos 3 modelos', asset, tag, family: 'lab',
        explain: `Opera quando pelo menos ${en?.min_agree ?? 2} dos 3 modelos (von, poorjev, Laya) concordam e a confiança deles está acima do percentil ${en?.pct_threshold != null ? n2(en.pct_threshold * 100, 0) : 80} das próprias decisões recentes.`,
      }
    }
    if (hyp === 'H3') {
      return {
        title: `${base} + ordem limite`, asset, tag, family: 'lab',
        explain: `Segue as decisões do ${base}, mas em vez de comprar a mercado deixa uma ordem limite um pouco melhor que o preço, que só executa se o preço chegar lá.`,
      }
    }
    const hrs = p?.hours?.length ? p.hours.map(h => `${h}h`).join(', ') : 'algumas horas fixas'
    return {
      title: `${base} + janela de horário`, asset, tag, family: 'lab',
      explain: `Segue as decisões do ${base}, mas só opera às ${hrs} (horário de Brasília).`,
    }
  }
  if (name === 'relaxed_expcap50' || inp.hyp === 'EXP') {
    const cap = p?.max_exposure_frac ?? 0.5
    return {
      title: `von relaxado, exposição ≤ ${pc(cap, 0)}`, asset, tag: 'teste de exposição', family: 'lab',
      explain: `Igual ao von relaxado, mas nunca deixa mais de ${pc(cap, 0)} do valor em ${asset}: mostra quanto do resultado vem da exposição.`,
    }
  }

  // ---- regras clássicas
  if (rest[0] === 'grid') {
    const g = (p?.rule?.grid_pct as number) ?? 0.02
    return {
      title: `Grade de ${pc(g, 0)}`, asset, tag: 'regra', family: 'rules',
      explain: `Compra a cada queda de ${pc(g, 0)} e vende a cada alta de ${pc(g, 0)} em barras de 1 hora, com ${p?.rule?.levels ?? 4} níveis.`,
    }
  }
  if (rest[0] === 'rsi') {
    const r = p?.rule || {}
    return {
      title: 'RSI de 1 hora', asset, tag: 'regra', family: 'rules',
      explain: `Compra quando o RSI(${r.rsi_period ?? 14}) de 1 hora volta a subir acima de ${r.lo ?? 30} e vende quando cai de volta abaixo de ${r.hi ?? 70}.`,
    }
  }
  if (rest[0] === 'rule') {
    const full = rest[rest.length - 1] === 'full'
    const donch = rest.includes('donch')
    const r = p?.rule || {}
    const ema = `EMA ${r.ema_fast ?? 12} > EMA ${r.ema_slow ?? 26} em 1 h`
    const size = full ? ' Entra com todo o caixa.' : ` Cada entrada usa ${fracTxt(p?.buy_fraction_usdt)}.`
    return {
      title: (donch ? 'Donchian + regime' : 'Regime de SOL') + (full ? ', 100%' : ''), asset, tag: 'regra', family: 'rules',
      explain: donch
        ? `Compra quando ${asset} rompe a máxima de ${r.donchian ?? 20} horas com SOL em alta (${ema}); sai no rompimento para baixo ou quando o regime vira.${size}`
        : `Fica comprado em ${asset} enquanto SOL está em alta (${ema}) e vende quando a tendência vira.${size}`,
    }
  }

  // ---- híbridos
  if (rest.includes('hybrid')) {
    const cap = p?.max_trades_per_hour
    return {
      title: `${brain} relaxado + regime`, asset, tag: 'híbrido', family: 'hybrid',
      explain: `Segue o ${brain} relaxado (${gateTxt(brain, p, 'relaxed').replace(`o ${brain} tem `, '')}), mas só compra quando SOL está em tendência de alta (EMA 12 > 26 em 1 h)` +
        (cap != null && cap <= 4 ? `, no máximo ${cap} trades por hora.` : '.'),
    }
  }

  // ---- modelos com portões
  const fam: FamilyKey = brainKey === 'laya' ? 'laya' : brainKey === 'poorjev' ? 'poorjev' : 'von'
  const v2 = profile === 'v2' ? ' Os critérios de leitura são os reescritos pela revisão noturna.' : ''
  const article = profile === 'baseline' ? ' (critério do artigo)' : ''
  return {
    title: `${brain} ${prof}`.trim(), asset, tag: 'modelo', family: fam,
    explain: `Compra ou vende quando ${gateTxt(brain, p, profile)}${article}; cada compra usa ${fracTxt(p?.buy_fraction_usdt)}.${v2}`,
  }
}

export function describePortfolio(inp: DescribeInput): Description {
  const m = /^(.*)__fork(\d+)$/.exec(inp.name)
  if (m) {
    const base = describeBase({ ...inp, name: m[1], hyp: inp.hyp ?? null })
    const n = Number(m[2])
    const diff = diffText(inp.params_diff)
    const crit = Boolean(inp.params_diff && 'criteria' in inp.params_diff)
    const who = inp.fork_who === 'claude-night' ? 'pela revisão noturna do Claude' : 'pelo ajuste noturno'
    const what = [crit ? 'critérios de leitura reescritos' : '', diff ? `com ${diff}` : ''].filter(Boolean).join(', ')
    return {
      ...base, title: `${base.title}, ajuste ${n}`, tag: 'fork', isFork: true, forkN: n,
      explain: `Cópia do ${base.title} criada ${who}${what ? `: ${what}` : ''}. O original continua rodando sem mudanças.`,
      search: `${base.title} ajuste ${n} fork ${base.asset} ${inp.name}`.toLowerCase(),
    }
  }
  const d = describeBase(inp)
  return { ...d, isFork: false, forkN: null, search: `${d.title} ${d.asset} ${d.tag} ${inp.name} ${inp.label ?? ''}`.toLowerCase() }
}

/** Camadas de params.json com nome simples (selo de proveniência). */
export function layerName(prov: string): string {
  if (prov === 'defaults') return 'padrão'
  if (prov === 'overlay') return 'ajuste manual'
  if (prov.startsWith('profiles.')) return 'perfil'
  if (prov.startsWith('types.')) return 'tipo'
  if (prov.startsWith('models.')) return 'modelo'
  if (prov.startsWith('assets.')) return 'ativo'
  if (prov.startsWith('portfolios.')) return 'portfólio'
  if (prov.startsWith('fork:')) return 'fork'
  return prov
}
