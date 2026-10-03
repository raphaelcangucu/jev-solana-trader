import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Dialog, DialogDescription, DialogTitle, SheetContent } from './ui/dialog'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Kpi, Pnl, VerdictBadge, VerdictProgress, LoadingBlock, ErrorBlock, Empty } from './common'
import { LineChart, type LineDef } from './charts/LineChart'
import { Histogram } from './charts/Histogram'
import { ParamEditor } from './ParamEditor'
import { brtTime, num, pct, price, signed, usd, toneOf } from '@/lib/format'
import { cn } from '@/lib/utils'

export default function PortfolioDrawer({ name, onClose }: { name: string; onClose: () => void }) {
  const poll = usePollInterval()
  const d = useQuery({ queryKey: ['portfolio', name], queryFn: () => api.portfolio(name), refetchInterval: poll })
  const eq = useQuery({ queryKey: ['equity', 'one', name], queryFn: () => api.equity({ names: [name], points: 900 }), refetchInterval: poll })
  const series = useMemo<LineDef[]>(() => {
    const s = eq.data?.[name]
    if (!s) return []
    const mk = (arr: (number | null)[]) => s.t.map((t, i) => ({ t, v: arr[i] as number })).filter(p => p.v != null)
    return [
      { id: 'eq', label: 'Portfólio', color: '#60a5fa', data: mk(s.equity) },
      { id: 'bh', label: 'Buy & hold', color: '#94a3b8', data: mk(s.bh), dashed: true },
      { id: 'usdt', label: '100% USDT', color: '#64748b', data: mk(s.usdt), dashed: true, width: 1 },
    ]
  }, [eq.data, name])
  const r = d.data?.row
  const minConf = d.data?.params?.min_confidence
  const trades = d.data?.trades || []
  const slips = trades.filter(t => t.slippage_bps != null)
  const avgSlip = slips.length ? slips.reduce((a, t) => a + (t.slippage_bps || 0), 0) / slips.length : null
  return (
    <Dialog open onOpenChange={o => { if (!o) onClose() }}>
      <SheetContent aria-describedby="drawer-desc">
        <div className="border-b px-5 py-4 pr-12">
          <DialogTitle className="flex flex-wrap items-center gap-2 text-lg font-semibold">
            {name} {r && <VerdictBadge v={r.verdict} />} {r?.paused && <Badge variant="warn">pausado</Badge>}
          </DialogTitle>
          <DialogDescription id="drawer-desc" className="text-xs text-muted-foreground">
            {r ? <>{r.group.toUpperCase()} · {r.asset} · modelo {r.model || '—'} · {r.label || r.strategy} · início {brtTime(r.started_brt, true)} BRT</> : 'carregando…'}
          </DialogDescription>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {d.isLoading && <LoadingBlock h={300} />}
          {d.error && <ErrorBlock error={d.error} />}
          {r && d.data && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Kpi label="Valor" value={usd(r.equity)} sub={`início ${usd(r.start_value)}`} />
                <Kpi label="PnL" value={<Pnl v={r.pnl} />} sub={signed(r.pnl_pct, 2, '%')} />
                <Kpi label="vs Buy&Hold" value={<Pnl v={r.vs_bh} />} sub={signed(r.vs_bh_pct, 2, '%')} />
                <Kpi label="vs USDT" value={<Pnl v={r.vs_usdt} />} />
                <Kpi label="Trades" value={num(r.trades ?? 0, 0)} />
                <Kpi label="Exposição" value={pct(r.exposure_pct, 1)} />
                <Kpi label="Max drawdown" value={pct(r.max_dd_pct, 2)} tone={(r.max_dd_pct ?? 0) > 5 ? 'text-down' : undefined} />
                <div className="rounded-xl border bg-card px-3.5 py-3">
                  <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Rumo aos mínimos</div>
                  <div className="mt-2"><VerdictProgress p={r.progress} text={r.progress_text} /></div>
                </div>
              </div>

              <Card>
                <CardHeader><CardTitle>Curva de patrimônio vs benchmarks</CardTitle><CardDescription>US$ · horário BRT</CardDescription></CardHeader>
                <CardContent>{series.length && series[0].data.length ? <LineChart series={series} height={240} ariaLabel={`Patrimônio de ${name} versus buy-and-hold`} format={v => '$' + num(v, 2)} /> : <Empty>Sem pontos de equity ainda.</Empty>}</CardContent>
              </Card>

              {r.control && (
                <Card>
                  <CardHeader><CardTitle>Parâmetros e controles</CardTitle><CardDescription>chave de controle: <code>{r.control}</code></CardDescription></CardHeader>
                  <CardContent><ParamEditor portfolio={r.control} /></CardContent>
                </Card>
              )}

              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle>Distribuição de confiança das decisões</CardTitle><CardDescription>{d.data.decisions.n} decisões recentes · p50 lat. {num(d.data.decisions.latency_p50, 0)} ms · p95 {num(d.data.decisions.latency_p95, 0)} ms</CardDescription></CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <Histogram bins={d.data.decisions.conf_hist} label={`Confiança de ${name}`} thresholds={minConf != null ? [{ at: Number(minConf), label: `min ${minConf}` }] : []} />
                    <div className="flex flex-wrap gap-1 text-[11px]">
                      {Object.entries(d.data.decisions.final).map(([k, v]) => <Badge key={k} variant="secondary">final {k}: {v}</Badge>)}
                      {Object.entries(d.data.decisions.chosen).map(([k, v]) => <Badge key={k} variant="outline">escolha {k}: {v}</Badge>)}
                    </div>
                    <div className="flex flex-wrap gap-1 text-[11px]">
                      {Object.entries(d.data.decisions.reasons).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => <Badge key={k} variant="warn">{k}: {v}</Badge>)}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Fills: cotação vs mark</CardTitle><CardDescription>slippage médio {avgSlip == null ? '—' : `${num(avgSlip, 1)} bps`} (+ = pior que o mark)</CardDescription></CardHeader>
                  <CardContent>
                    {slips.length ? (
                      <div className="flex h-[112px] items-end gap-px" role="img" aria-label="Slippage por trade em bps">
                        {slips.slice(0, 60).reverse().map((t, i) => {
                          const m = Math.max(5, ...slips.map(s => Math.abs(s.slippage_bps || 0)))
                          const h = (Math.abs(t.slippage_bps || 0) / m) * 100
                          return <div key={i} title={`${brtTime(t.ts_brt)} ${t.side} ${num(t.slippage_bps, 1)} bps (${t.fill_mode})`} className={cn('flex-1 rounded-t-sm', (t.slippage_bps || 0) > 0 ? 'bg-down/70' : 'bg-up/70')} style={{ height: `${Math.max(2, h)}%` }} />
                        })}
                      </div>
                    ) : <Empty>Sem fills ainda.</Empty>}
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader><CardTitle>Trades ({trades.length})</CardTitle></CardHeader>
                <CardContent className="overflow-x-auto">
                  {trades.length ? (
                    <table className="w-full min-w-[640px] text-xs num">
                      <thead className="text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Hora (BRT)</th><th>Lado</th><th className="text-right">Mark</th><th className="text-right">Fill</th><th className="text-right">Slip (bps)</th><th className="text-right">US$</th><th>Fonte</th></tr></thead>
                      <tbody>
                        {trades.slice(0, 200).map((t, i) => (
                          <tr key={i} className="border-t border-border/50">
                            <td className="py-1.5">{brtTime(t.ts_brt, true)}</td>
                            <td className={t.side === 'buy' ? 'text-up' : 'text-down'}>{t.side === 'buy' ? 'compra' : 'venda'}</td>
                            <td className="text-right">{price(t.mark)}</td><td className="text-right">{price(t.fill_price)}</td>
                            <td className={cn('text-right', toneOf(-(t.slippage_bps ?? 0)))}>{num(t.slippage_bps, 1)}</td>
                            <td className="text-right">{num(t.usdt, 2)}</td>
                            <td className="text-muted-foreground" title={t.quote_error || ''}>{t.fill_mode}{t.quote_error ? ' ⚠' : ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : <Empty>Nenhum trade ainda.</Empty>}
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Decisões recentes</CardTitle></CardHeader>
                <CardContent className="overflow-x-auto">
                  {d.data.decisions.recent.length ? (
                    <table className="w-full min-w-[560px] text-xs num">
                      <thead className="text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Hora</th><th>Escolha</th><th className="text-right">Conf.</th><th className="text-right">Skip</th><th>Final</th><th>Motivos</th></tr></thead>
                      <tbody>
                        {d.data.decisions.recent.map((x, i) => (
                          <tr key={i} className="border-t border-border/50">
                            <td className="py-1.5">{brtTime(x.ts_brt)}</td><td>{x.chosen}</td><td className="text-right">{num(x.confidence, 3)}</td><td className="text-right">{num(x.skip_noul, 3)}</td>
                            <td className={x.final === 'buy' ? 'text-up' : x.final === 'sell' ? 'text-down' : ''}>{x.final}</td>
                            <td className="text-muted-foreground">{(x.reasons || []).join(', ') || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : <Empty>Sem decisões registradas.</Empty>}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </SheetContent>
    </Dialog>
  )
}
