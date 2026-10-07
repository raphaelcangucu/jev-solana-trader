// Cliente tipado do backend Python. Mesma origem → o navegador reenvia o cookie de sessão / Basic auth.
export class ApiError extends Error {
  status: number
  constructor(status: number, msg: string) { super(msg); this.status = status }
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
  if (!r.ok) throw new ApiError(r.status, (await r.text()) || r.statusText)
  return r.json() as Promise<T>
}

export async function getText(url: string): Promise<string> {
  const r = await fetch(url, { headers: { Accept: 'text/markdown, text/plain' }, credentials: 'same-origin' })
  if (!r.ok) throw new ApiError(r.status, (await r.text()) || r.statusText)
  return r.text()
}

export async function postJSON<T = unknown>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!r.ok) {
    let msg = r.statusText
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j) } catch { /* corpo vazio */ }
    throw new ApiError(r.status, msg)
  }
  return r.json() as Promise<T>
}

export type Verdict = 'inconclusivo' | 'vencedora' | 'perdedora' | string
export interface Progress { closed_rt?: number | null; min_closed_rt?: number | null; days?: number | null; min_days?: number | null }

export interface Skill {
  exposure_pct: number | null; static_usd: number | null; timing_usd: number | null; timing_p: number | null
  ex_exposure: number | null; ex_exposure_pct: number | null; ex_bh: number | null; bh_pnl: number | null
  trades: number | null; buys: number | null; sells: number | null; rt_wins: number | null
  fees: number | null; cost_vs_mark: number | null; mdd_pct: number | null; hours: number | null
}

export interface ParamsBrief {
  min_confidence?: number | null; min_prob_margin?: number | null; margin_gate?: boolean; max_skip_noul?: number | null
  buy_fraction_usdt?: number | null; max_trades_per_hour?: number | null; cooldown_seconds?: number | null; max_exposure_frac?: number | null
  exits?: { tp?: number; sl?: number; trail?: number } | null; hours?: number[] | null
  ensemble?: { min_agree?: number; pct_threshold?: number } | null; rule?: Record<string, number | string> | null
  regime_filter?: boolean; exec_mode?: string; paused?: boolean; errors?: number
}

export interface Row {
  name: string; group: 'sol' | 'meme' | 'lab'; asset: string; model?: string | null; kind?: string | null; strategy?: string | null
  hyp?: string | null; label?: string | null; parent?: string | null; lineage?: string | null; report_label?: string | null
  catalog?: string | null; profile?: string | null; test_type?: string | null; variant?: string | null; rule?: string | null; source?: string | null
  params_diff?: Record<string, Record<string, unknown>> | null; created_brt?: string | null
  fork_who?: string | null; fork_summary?: string | null; fork_reason?: string | null; criteria_summary?: string | null
  equity: number | null; start_value: number | null; pnl: number | null; pnl_pct: number | null; vs_bh: number | null; vs_bh_pct: number | null
  vs_usdt: number | null; bh_equity: number | null; trades: number | null; exposure_pct: number | null; max_dd_pct: number | null
  points: number; last_ts: number | null; started_brt: string | null; started_ts: number | null
  verdict: Verdict; verdict_reason?: string | null; progress_text?: string | null; progress?: Progress | null
  control: string | null; paused: boolean | null
  skill?: Skill | null; params_brief?: ParamsBrief | null
}

export interface Experiment {
  start_ts: number | null; end_ts?: number; first_verdict_ts?: number; elapsed_days?: number; day: number | null
  days_total: number; first_verdict_day: number; min_closed_rt: number
}

export interface Overview {
  ts_brt: string; price_usd: number | null; price_source: string | null; portfolios_total: number; trades_today: number
  errors: number; health: 'ok' | 'warn' | 'bad'; rows: Row[]; verdict_rule: string
  experiment?: Experiment; skill_status?: { computed_ts: number | null; ttl_s: number; error: string | null; computing: boolean }
}

export interface Proc { name: string; pid: number | null; running: boolean | null; expected?: boolean }
export interface Beat { name: string; age_s: number | null; ts_brt?: string | null; cycles?: number | null; errors?: number | null }
export interface Health {
  ts: number; ts_brt: string; level: 'ok' | 'warn' | 'bad'; errors: number; stale: string[]; down: string[]
  processes: Proc[]; heartbeats: Beat[]
  nightly: { next_run_brt?: string; last_run?: unknown; next_rotation_brt?: string; last_rotation?: unknown }
  last_review: { name: string; path: string } | null; reviews: string[]; reports: string[]; criteria: string[]
  review_done?: boolean; price_usd: number | null; price_source: string | null; dashboard_url: string
  extras?: {
    disk?: { free_gb: number; total_gb: number; used_frac: number | null } | null
    restarts_24h?: Record<string, number>
    fills_24h?: { market_fills?: number; mark_fallbacks?: number; fallback_rate?: number | null; reasons?: Record<string, number>; error?: string }
  }
}

export interface Spark { t: number[]; v: number[]; h: (number | null)[] }
export type Sparks = Record<string, Spark>

export interface EqSeries { group: string; asset: string; model?: string; t: number[]; equity: (number | null)[]; bh: (number | null)[]; usdt: (number | null)[] }
export type EquityMap = Record<string, EqSeries>

export interface Trade {
  ts: number | null; ts_brt: string | null; portfolio: string; side: string; mark: number | null; fill_price: number | null
  slippage_bps: number | null; fill_mode?: string | null; quote_error?: string | null; strategy?: string | null
  usdt?: number | null; fee_usdt?: number | null; equity_after?: number | null
}

export interface PortfolioDetail {
  row: Row; params: Record<string, unknown> | null; portfolio_file: Record<string, unknown>
  decisions: {
    n: number; conf_hist: number[]; chosen: Record<string, number>; final: Record<string, number>; reasons: Record<string, number>
    latency_p50: number | null; latency_p95: number | null
    recent: { ts_brt: string; chosen: string; final: string; confidence: number | null; skip_noul: number | null; reasons: string[] | null; model?: string }[]
  }
  trades: Trade[]
}

export interface EffectiveParams {
  portfolio: string; meta: Record<string, unknown>; effective: Record<string, unknown>
  provenance: Record<string, string>; errors: string[]; summary: string
}

export interface ParamsTypes {
  types: Record<string, { effective: Record<string, unknown>; provenance: Record<string, string>; errors: string[]; summary: string; layer?: Record<string, unknown> }>
  doc_errors: string[]; profiles?: Record<string, Record<string, unknown>>; defaults?: Record<string, unknown>
}

export interface Params {
  bots: Record<string, boolean>
  portfolios: Record<string, Record<string, unknown> & { paused: boolean; is_baseline_control: boolean }>
  editable: string[]
  models: Record<string, { enabled: boolean; memes_enabled: boolean; label?: string; kind?: string }>
  bounds: Record<string, [number | null, number | null]>
  tuning_bounds: Record<string, [number, number]>
  ints: string[]
}

export interface ModelDist { n: number; conf_hist: number[]; chosen: Record<string, number>; errors: number; latency_p50: number | null; latency_p95: number | null }
export interface ModelInfo {
  id: string; label?: string; kind?: string; enabled: boolean; memes_enabled: boolean; sol_portfolios: string[]; port?: number
  process: Proc; latency_ms: number | null; meme_latency_ms: number | null; status?: string; note?: string; sol: ModelDist; meme: ModelDist
}
export interface Models { models: Record<string, ModelInfo>; cycle_wall_ms?: number; meme_cycle_wall_ms?: number }

export interface Lab { lab_paused: boolean; rules_paused: boolean; status: Record<string, unknown>; nightly: Record<string, unknown> }

export interface RealBot {
  available: boolean; reason?: string; run_id?: string; start_t?: string; n_decisions?: number; last_t?: string | null; last_px?: number | null
  start_book?: { sol: number; usdt: number }; paper_book?: { sol: number; usdt: number }
  pnl_vs_hold?: { usd: number | null; pct: number | null; paper_value_usd: number | null; base_value_usd: number | null }
  pnl_vs_start?: { usd: number | null; pct: number | null; paper_value_usd: number | null; base_value_usd: number | null; ref_sol_usd?: number | null }
  hit_rate?: { hits: number; misses: number; resolved: number; unresolved: number; rate: number | null; horizon_min: number }
  hit_recent?: { t: string; side: string; status: string; ret?: number }[]
  drawdown?: { usd: number | null; pct: number | null; peak_t: string | null; trough_t: string | null; points: number }
  trades?: { total: number; buy: number; sell: number }
  series?: { cols: string[]; rows: [number, number, number, number][] }
  recent_decisions?: { t: string; action: string; model_action?: string; conf: number | null; skip: number | null; reason?: string | null; px: number | null; paper_fill: boolean; source?: string }[]
  recent_trades?: { t: string; side: string; conf: number | null; px: number | null; fill_px: number | null; in_ui: number | null; out_ui: number | null; fill_mode?: string }[]
  composition?: { sol_usd: number; usdt_usd: number; sol_frac: number | null }
}

export interface FundingPos { size: number; funding_accrued: number; current_funding_ann: number }
export interface FundingPort { capital: number; nav: number; cash: number; ret_pct: number; apr_simple_pct: number | null; funding: number; fees: number; max_dd_pct: number; positions: Record<string, FundingPos>; bench?: Record<string, number> }
export interface Funding {
  available: boolean; service?: string; run_mode?: string; heartbeat?: string; heartbeat_age_s?: number | null; started_at?: string; start_ts?: number | null
  end_at?: string | null; counters?: Record<string, number>; last_error?: string | null
  benchmarks?: Record<string, { apy?: number; apy_spot_now?: number; stale?: boolean }>
  portfolios?: Record<string, FundingPort>; usdc_bar_apr?: number; cum_funding?: Record<string, [number, number][]>; nav_series?: Record<string, [number, number][]>
  trades?: { ts: string; portfolio: string; coin: string; leg: string; venue: string; side: string; size: number; vwap_px_usdc: number; fee: number; reason?: string }[]
  shown?: string[]
}

// ---- simulação retroativa de 30 dias (data/backtest; contrato de scripts/backtest_30d.py)
export type BtVerdict = 'vencedora' | 'perdedora' | 'inconclusiva'
export interface BtPortfolio {
  name: string; family?: string | null; asset?: string | null; model?: string | null; test_type?: string | null; profile?: string | null
  parent?: string | null; is_fork?: boolean | null; label?: string | null
  start_value: number | null; end_value: number | null; pnl: number | null; pnl_pct: number | null
  /** US$ contra só segurar o livro inicial (vs_bh_pct é derivado pelo backend) */
  vs_bh: number | null; vs_bh_pct?: number | null; vs_usdt?: number | null
  /** habilidade sem beta em US$ (skill_pct derivado pelo backend) */
  skill: number | null; skill_pct?: number | null; timing?: number | null; timing_p: number | null
  max_dd_pct: number | null; trades: number | null; buys?: number | null; sells?: number | null; closed_rt?: number | null; exposure_pct?: number | null
  weeks?: (number | null)[] | null; weeks_beat_bh?: number | null
  /** runs de 6 meses: retorno de cada mês e em quantos bateu só segurar (o veredito pede ≥ 4 de 6) */
  months?: (number | null)[] | null; months_beat_bh?: number | null; look_ahead?: boolean | null
  verdict: BtVerdict; verdict_reason?: string | null; p_bh?: number | null; p_usdc?: number | null
  // metadados do placar ao vivo (para describePortfolio) e o nome da linha ao vivo, se existir
  hyp?: string | null; kind?: string | null; catalog?: string | null; params_diff?: Record<string, Record<string, unknown>> | null
  params_brief?: ParamsBrief | null; fork_who?: string | null; criteria_summary?: string | null; live_name?: string | null
}
export interface BtFamily { family: string; n: number; median_pnl_pct: number | null; best?: string | null; worst?: string | null; beat_bh?: number | null }
export interface BtBook {
  book: string; profile?: string | null; start_value?: number | null; end_value?: number | null; pnl?: number | null; pnl_pct?: number | null
  vs_hold?: number | null; hit_15m?: number | null; max_dd_pct?: number | null; trades?: number | null; exits?: number | Record<string, number> | null
}
export interface BtSummary {
  run_id: string; generated_brt?: string | null
  window: { start_brt: string; end_brt: string; days?: number | null; step_s?: number | null }
  assets: Record<string, { source?: string | null; coverage?: number | null; start_px?: number | null; end_px?: number | null; ret_pct?: number | null }>
  assumptions?: string[]
  models?: Record<string, { calls?: number | null; cache_hits?: number | null; coverage?: number | null; conf_p50?: number | null; conf_p90?: number | null }>
  winner: { by_skill?: string | null; by_pnl?: string | null; by_verdict?: string | null; text?: string | null }
  families: BtFamily[]; portfolios: BtPortfolio[]; realbot: BtBook[]
}
export interface BtRun { run_id: string; generated_brt?: string | null; start_brt?: string | null; end_brt?: string | null; days?: number | null; portfolios?: number }
export interface BtPayload {
  available: boolean; reason?: string; hint?: string; run_id: string | null; latest: string | null; runs: BtRun[]
  has_report?: boolean; summary?: BtSummary
}
export interface BtEquity { t: number[]; equity: number[]; bh: (number | null)[] }

// ---- histórico: runs mensais de 30 dias + janela de 6 meses (data/backtest/index.json e <run>/chart.json)
export type BtKind = '30d' | '180d'
export interface BtTop { name: string; skill: number | null; pnl_pct: number | null }
export interface BtIndexRun {
  run_id: string; kind: BtKind; start_brt?: string | null; end_brt?: string | null; days?: number | null; generated_brt?: string | null
  n_portfolios?: number | null; n_winners?: number | null; n_losers?: number | null; n_inconclusive?: number | null
  winner?: { by_skill?: string | null; by_pnl?: string | null; by_verdict?: string | null } | null
  top_skill?: BtTop[] | null; top_pnl?: BtTop[] | null
  realbot?: { book: string; pnl_pct: number | null; vs_hold: number | null }[] | null
  assets?: Record<string, number | null> | null; look_ahead_forks?: string[] | null
  /** false quando o índice cita um run cuja pasta não existe (mais) em disco */
  available?: boolean
}
export interface BtIndex { runs: BtIndexRun[]; source?: 'index' | 'runs'; latest?: string | null; has_history?: boolean }
export interface BtMonth { month: string; start_brt?: string | null; end_brt?: string | null; top_by_pnl?: string | null; top_by_skill?: string | null; sol_ret?: number | null; memes_ret?: number | null }
export interface BtChart {
  run_id: string; t: number[]; start_brt?: string; end_brt?: string; normalized_to?: number
  benchmarks: { sol_bh?: (number | null)[]; memes_bh?: (number | null)[]; usdc?: (number | null)[]; memes_in_basket?: string[] }
  families: Record<string, (number | null)[]>
  top: Record<string, (number | null)[]>; realbot: Record<string, (number | null)[]>
  monthly: BtMonth[]
}

export interface ParamChange { ts: number; ts_brt: string; portfolio?: string; layer?: string; field: string; old: unknown; new: unknown; who?: string; type?: string }

export const api = {
  overview: () => getJSON<Overview>('/api/v2/overview'),
  health: () => getJSON<Health>('/api/v2/health'),
  sparks: (points = 60) => getJSON<Sparks>(`/api/v2/sparks?points=${points}`),
  equity: (names: string[], points = 900) => getJSON<EquityMap>(`/api/v2/equity?names=${encodeURIComponent(names.join(','))}&points=${points}`),
  portfolio: (name: string) => getJSON<PortfolioDetail>(`/api/v2/portfolio/${encodeURIComponent(name)}`),
  effective: (name: string) => getJSON<EffectiveParams>(`/api/v2/params/effective/${encodeURIComponent(name)}`),
  paramsTypes: () => getJSON<ParamsTypes>('/api/params/types'),
  params: () => getJSON<Params>('/api/v2/params'),
  models: () => getJSON<Models>('/api/v2/models'),
  lab: () => getJSON<Lab>('/api/v2/lab'),
  paramChanges: () => getJSON<ParamChange[]>('/api/v2/param_changes?limit=60'),
  realbot: () => getJSON<RealBot>('/api/v2/realbot'),
  funding: () => getJSON<Funding>('/api/v2/funding'),
  backtest: (run?: string | null) => getJSON<BtPayload>(`/api/v2/backtest${run ? `?run=${encodeURIComponent(run)}` : ''}`),
  backtestEquity: (run: string, name: string, points = 1500) =>
    getJSON<BtEquity>(`/api/v2/backtest/${encodeURIComponent(run)}/equity/${encodeURIComponent(name)}?points=${points}`),
  backtestSparks: (run: string, points = 60) => getJSON<Sparks>(`/api/v2/backtest/${encodeURIComponent(run)}/sparks?points=${points}`),
  backtestReport: (run: string) => getText(`/api/v2/backtest/${encodeURIComponent(run)}/report`),
  backtestIndex: () => getJSON<BtIndex>('/api/v2/backtest/index'),
  backtestChart: (run: string, points = 2000) => getJSON<BtChart>(`/api/v2/backtest/${encodeURIComponent(run)}/chart?points=${points}`),
  backtestHistory: () => getText('/api/v2/backtest/history'),
  // ---- gravações (endpoints de controle do app.py; sempre com confirmação na UI) ----
  setParams: (portfolio: string, body: Record<string, unknown>) =>
    postJSON<{ ok: boolean; changes: unknown[]; warning?: string | null }>(`/api/params/${encodeURIComponent(portfolio)}`, body),
  restore: (portfolio: string) => postJSON(`/api/params/${encodeURIComponent(portfolio)}/restore`),
  setLayer: (section: string, key: string, body: Record<string, unknown>) =>
    postJSON<{ ok: boolean; changes: Record<string, { old: unknown; new: unknown }> }>(`/api/params/layer/${encodeURIComponent(section)}/${encodeURIComponent(key)}`, body),
  pauseBot: (bot: 'sol' | 'meme' | 'rules' | 'lab', paused: boolean) => postJSON(`/api/bots/${bot}/pause`, { paused }),
  modelEnable: (id: string, body: { enabled?: boolean; memes_enabled?: boolean }) =>
    postJSON<{ ok: boolean; note?: string | null }>(`/api/models/${encodeURIComponent(id)}/enable`, body),
}
