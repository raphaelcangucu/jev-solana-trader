// Typed client for the Python backend. Same-origin fetches → the browser re-sends the cached Basic-auth credentials.
export class ApiError extends Error { status: number; constructor(status: number, msg: string) { super(msg); this.status = status } }

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
  if (!r.ok) throw new ApiError(r.status, (await r.text()) || r.statusText)
  return r.json() as Promise<T>
}

export async function postJSON<T = any>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!r.ok) {
    let msg = r.statusText
    try { const j = await r.json(); msg = j.detail || JSON.stringify(j) } catch { /* noop */ }
    throw new ApiError(r.status, msg)
  }
  return r.json() as Promise<T>
}

export type Verdict = 'inconclusivo' | 'vencedora' | 'perdedora' | string

export interface Progress { closed_rt?: number | null; min_closed_rt?: number | null; days?: number | null; min_days?: number | null }

export interface Row {
  name: string; group: 'sol' | 'meme' | 'lab'; asset: string; model?: string | null; kind?: string | null; strategy?: string | null
  hyp?: string | null; label?: string | null; parent?: string | null; lineage?: string | null; report_label?: string | null
  equity: number | null; start_value: number | null; pnl: number | null; pnl_pct: number | null; vs_bh: number | null; vs_bh_pct: number | null
  vs_usdt: number | null; bh_equity: number | null; trades: number | null; exposure_pct: number | null; max_dd_pct: number | null
  points: number; last_ts: number | null; started_brt: string | null; started_ts: number | null
  verdict: Verdict; verdict_reason?: string | null; progress_text?: string | null; progress?: Progress | null
  control: string | null; paused: boolean | null
}

export interface Overview { ts_brt: string; price_usd: number | null; price_source: string | null; portfolios_total: number; trades_today: number; errors: number; health: 'ok' | 'warn' | 'bad'; rows: Row[]; verdict_rule: string }

export interface Proc { name: string; pid: number | null; running: boolean | null; expected?: boolean }
export interface Beat { name: string; age_s: number | null; ts_brt?: string | null; cycles?: number | null; errors?: number | null }
export interface Health {
  ts: number; ts_brt: string; level: 'ok' | 'warn' | 'bad'; errors: number; stale: string[]; down: string[]
  processes: Proc[]; heartbeats: Beat[]
  nightly: { next_run_brt?: string; last_run?: any; next_rotation_brt?: string; last_rotation?: any }
  last_review: { name: string; path: string } | null; reviews: string[]; reports: string[]; criteria: string[]
  review_done?: boolean; price_usd: number | null; price_source: string | null; dashboard_url: string
}

export interface Candle { time: number; open: number; high: number; low: number; close: number; ticks: number }
export interface Marker { time: number; ts: number; portfolio: string; side: 'buy' | 'sell'; price: number | null; fill_price: number | null }
export interface Candles { asset: string; res: number; candles: Candle[]; markers: Marker[] }

export interface EqSeries { group: string; asset: string; model?: string; t: number[]; equity: (number | null)[]; bh: (number | null)[]; usdt: (number | null)[] }
export type EquityMap = Record<string, EqSeries>

export interface Params {
  bots: Record<string, boolean>
  portfolios: Record<string, Record<string, any> & { paused: boolean; is_baseline_control: boolean }>
  editable: string[]
  models: Record<string, { enabled: boolean; memes_enabled: boolean; label?: string; kind?: string }>
  jev?: any
  bounds: Record<string, [number | null, number | null]>
  tuning_bounds: Record<string, [number, number]>
  ints: string[]
}

export interface Trade { ts: number | null; ts_brt: string | null; portfolio: string; side: string; mark: number | null; fill_price: number | null; slippage_bps: number | null; fill_mode?: string | null; quote_error?: string | null; strategy?: string | null; usdt?: number | null; fee_usdt?: number | null; equity_after?: number | null }

export interface PortfolioDetail {
  row: Row; params: Record<string, any> | null; portfolio_file: Record<string, any>
  decisions: { n: number; conf_hist: number[]; chosen: Record<string, number>; final: Record<string, number>; reasons: Record<string, number>; latency_p50: number | null; latency_p95: number | null; recent: { ts_brt: string; chosen: string; final: string; confidence: number | null; skip_noul: number | null; reasons: string[] | null; model?: string }[] }
  trades: Trade[]
}

export interface MemeCell { name: string; equity: number | null; vs_bh: number | null; vs_bh_pct: number | null; pnl_pct: number | null; trades: number | null; verdict: string; progress_text?: string | null; max_dd_pct?: number | null; exposure_pct?: number | null }
export interface Memes { symbols: string[]; strategies: string[]; labels: Record<string, string>; grid: Record<string, Record<string, MemeCell>>; tokens: Record<string, { price: number | null; price_source: string | null }>; meta: Record<string, any> }

export interface ModelDist { n: number; conf_hist: number[]; chosen: Record<string, number>; errors: number; latency_p50: number | null; latency_p95: number | null }
export interface ModelInfo { id: string; label?: string; kind?: string; enabled: boolean; memes_enabled: boolean; sol_portfolios: string[]; port?: number; process: Proc; latency_ms: number | null; meme_latency_ms: number | null; status?: string; note?: string; sol: ModelDist; meme: ModelDist }
export interface Models { models: Record<string, ModelInfo>; jev?: any; cycle_wall_ms?: number; meme_cycle_wall_ms?: number; memes_allow_other_models?: boolean }

export interface LabMember { name: string; asset?: string; equity_usd?: number; pnl?: number; vs_bh?: number; trades?: number; status?: string; verdict?: string; progress?: string | null; is_lead?: boolean; report_label?: string | null; parent?: string | null; params_diff?: any; is_original?: boolean; max_dd_pct?: number | null; vs_bh_pct?: number | null; pnl_pct?: number | null; progress_obj?: Progress | null }
export interface LabHyp extends LabMember { label?: string; hyp?: string; kind?: string; lineage?: string; params?: any; created_brt?: string; paused?: boolean; exposure_pct?: number | null; open_order?: boolean; start_value?: number }
export interface Lab {
  status: Record<string, any>; hypotheses: LabHyp[]; lineages: { lineage: string; lead: string | null; members: LabMember[] }[]
  verdicts_ts_brt?: string; original_verdicts: { name: string; verdict: string; progress?: string; reason?: string }[]
  nightly: Record<string, any>; lab_paused: boolean; verdict_rule: string
  rules_status: Record<string, any>; rule_rows: Row[]; caps?: any; tuning_hard_bounds?: Record<string, [number, number]> | null; rules_paused: boolean
}

export interface FundingPos { size: number; funding_accrued: number; current_funding_ann: number }
export interface FundingPort { capital: number; nav: number; cash: number; ret_pct: number; apr_simple_pct: number | null; funding: number; fees: number; max_dd_pct: number; positions: Record<string, FundingPos>; bench?: Record<string, number> }
export interface Funding {
  available: boolean; service?: string; run_mode?: string; heartbeat?: string; heartbeat_age_s?: number | null; started_at?: string; start_ts?: number | null
  end_at?: string | null; counters?: Record<string, number>; last_error?: string | null; benchmarks?: Record<string, any>
  portfolios?: Record<string, FundingPort>; usdc_bar_apr?: number; cum_funding?: Record<string, [number, number][]>; nav_series?: Record<string, [number, number][]>
  trades?: any[]; shown?: string[]
}

export interface ParamChange { ts: number; ts_brt: string; portfolio: string; field: string; old: any; new: any; who?: string; reason?: string }

export const api = {
  overview: () => getJSON<Overview>('/api/v2/overview'),
  health: () => getJSON<Health>('/api/v2/health'),
  candles: (asset: string, res: number, hours: number) => getJSON<Candles>(`/api/v2/candles?asset=${encodeURIComponent(asset)}&res=${res}&hours=${hours}`),
  equity: (q: { group?: string; asset?: string; names?: string[]; points?: number }) => {
    const p = new URLSearchParams()
    if (q.group) p.set('group', q.group)
    if (q.asset) p.set('asset', q.asset)
    if (q.names) p.set('names', q.names.join(','))
    p.set('points', String(q.points ?? 600))
    return getJSON<EquityMap>(`/api/v2/equity?${p}`)
  },
  portfolio: (name: string) => getJSON<PortfolioDetail>(`/api/v2/portfolio/${encodeURIComponent(name)}`),
  memes: () => getJSON<Memes>('/api/v2/memes'),
  models: () => getJSON<Models>('/api/v2/models'),
  lab: () => getJSON<Lab>('/api/v2/lab'),
  params: () => getJSON<Params>('/api/v2/params'),
  paramChanges: () => getJSON<ParamChange[]>('/api/v2/param_changes?limit=300'),
  funding: () => getJSON<Funding>('/api/v2/funding'),
  // ---- controls (legacy endpoints, unchanged) ----
  setParams: (portfolio: string, body: Record<string, unknown>) => postJSON<{ ok: boolean; changes: any[]; warning?: string | null }>(`/api/params/${encodeURIComponent(portfolio)}`, body),
  restore: (portfolio: string) => postJSON(`/api/params/${encodeURIComponent(portfolio)}/restore`),
  pauseBot: (bot: 'sol' | 'meme' | 'rules' | 'lab', paused: boolean) => postJSON(`/api/bots/${bot}/pause`, { paused }),
  modelEnable: (id: string, body: { enabled?: boolean; memes_enabled?: boolean }) => postJSON<{ ok: boolean; note?: string | null; enabled: boolean; memes_enabled: boolean }>(`/api/models/${encodeURIComponent(id)}/enable`, body),
}
