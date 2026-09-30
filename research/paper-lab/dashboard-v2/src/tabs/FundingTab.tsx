// Hyperliquid funding-carry (paper). Read-only view of paper/funding/data + logs.
// Pattern: Ghostfolio "performance vs benchmark" — cumulative funding vs the 6% USDC bar.
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Empty, ErrorBlock, Kpi, LoadingBlock, Pnl, SectionTitle, StatusDot } from '@/components/common'
import { LineChart, type LineDef } from '@/components/charts/LineChart'
import { colorFor } from '@/lib/colors'
import { ago, brtTime, num, pct, price, signed, usd } from '@/lib/format'

export default function FundingTab() {
  const poll = usePollInterval(20_000)
  const q = useQuery({ queryKey: ['funding'], queryFn: api.funding, refetchInterval: poll })
  const F = q.data
  const fundingSeries = useMemo<LineDef[]>(() => {
    if (!F?.available || !F.portfolios) return []
    const out: LineDef[] = []
    const start = F.start_ts || 0
    const bar = F.usdc_bar_apr ?? 0.06
    const nowT = Date.now() / 1000
    for (const [name, p] of Object.entries(F.portfolios)) {
      const pts = (F.cum_funding?.[name] || []).map(([t, v]) => ({ t, v }))
      out.push({ id: name, label: `${name} funding`, color: colorFor(name), data: [{ t: start, v: 0 }, ...pts] })
      const ts: number[] = []
      for (let t = start; t <= nowT; t += Math.max(300, (nowT - start) / 200)) ts.push(t)
      ts.push(nowT)
      out.push({ id: `${name}_bar`, label: `${name} barra USDC ${Math.round(bar * 100)}%`, color: colorFor(name), dashed: true, width: 1, data: ts.map(t => ({ t, v: p.capital * bar * (t - start) / (365 * 86400) })) })
    }
    return out
  }, [F])
  const navSeries = useMemo<LineDef[]>(() => {
    if (!F?.available || !F.portfolios) return []
    const out: LineDef[] = []
    for (const name of Object.keys(F.portfolios)) out.push({ id: name, label: name, color: colorFor(name), data: (F.nav_series?.[name] || []).map(([t, v]) => ({ t, v })) })
    return out
  }, [F])
  if (q.isLoading) return <LoadingBlock h={500} />
  if (q.error) return <ErrorBlock error={q.error} />
  if (!F?.available) return <Empty>Serviço de funding-carry ainda sem dados (paper/funding/data/status.json).</Empty>
  const kam = F.benchmarks?.kamino_usdc || {}
  const jito = F.benchmarks?.jitosol || {}
  const stale = (F.heartbeat_age_s ?? 999) > 180
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="flex items-center gap-2"><StatusDot level={stale ? 'warn' : 'ok'} />Hyperliquid funding-carry · paper</CardTitle>
            <CardDescription className="num">heartbeat {ago(F.heartbeat_age_s)} atrás · início {brtTime(F.started_at, true)} BRT · modo {F.run_mode}{F.end_at ? ` · fim ${F.end_at}` : ' · sem data de fim'} · exibindo {F.shown?.join(', ')}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(F.counters || {}).map(([k, v]) => <Badge key={k} variant={v ? 'warn' : 'secondary'}>{k.replace('http_429_', '429 ')}: {v}</Badge>)}
            {F.last_error && <Badge variant="down" title={F.last_error}>último erro</Badge>}
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <div className="rounded-lg bg-muted/40 p-2"><div className="text-muted-foreground">Kamino USDC (média 24h)</div><div className="text-base font-semibold num">{pct((kam.apy ?? 0) * 100, 2)}</div><div className="text-[10px] text-muted-foreground num">spot {pct((kam.apy_spot_now ?? 0) * 100, 1)} {kam.stale ? '· stale' : ''}</div></div>
          <div className="rounded-lg bg-muted/40 p-2"><div className="text-muted-foreground">JitoSOL</div><div className="text-base font-semibold num">{pct((jito.apy ?? 0) * 100, 2)}</div><div className="text-[10px] text-muted-foreground">{jito.stale ? 'stale' : 'ok'}</div></div>
          <div className="rounded-lg bg-muted/40 p-2"><div className="text-muted-foreground">Barra de entrada/saída</div><div className="text-base font-semibold num">{pct((F.usdc_bar_apr ?? 0.06) * 100, 0)} APR</div><div className="text-[10px] text-muted-foreground">regra da estratégia</div></div>
          <div className="rounded-lg bg-muted/40 p-2"><div className="text-muted-foreground">Paper only</div><div className="text-base font-semibold">sim</div><div className="text-[10px] text-muted-foreground">só endpoints públicos</div></div>
        </CardContent>
      </Card>

      {Object.entries(F.portfolios || {}).map(([name, p]) => (
        <section key={name}>
          <SectionTitle desc={`capital ${usd(p.capital)} · caixa ${usd(p.cash)}`}><span className="inline-flex items-center gap-2"><i className="inline-block size-2.5 rounded-full" style={{ background: colorFor(name) }} />{name}</span></SectionTitle>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            <Kpi label="NAV" value={usd(p.nav)} sub={`vs Kamino ${p.bench?.kamino_usdc != null ? signed(p.nav - p.bench.kamino_usdc, 2) : '—'}`} />
            <Kpi label="Retorno" value={<Pnl v={p.nav - p.capital} />} sub={signed(p.ret_pct, 3, '%')} />
            <Kpi label="APR simples" value={p.apr_simple_pct == null ? '—' : pct(p.apr_simple_pct, 2)} sub={p.apr_simple_pct == null ? 'aguardando histórico mínimo' : ''} />
            <Kpi label="Funding recebido" value={usd(p.funding, 4)} tone="text-up" />
            <Kpi label="Taxas" value={usd(p.fees, 4)} tone="text-down" />
            <Kpi label="Max drawdown" value={pct(p.max_dd_pct, 3)} />
          </div>
          <Card className="mt-2">
            <CardContent className="overflow-x-auto pt-3">
              <table className="w-full min-w-[520px] text-xs num">
                <thead className="text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Ativo</th><th className="text-right">Tamanho</th><th className="text-right">Funding acumulado</th><th className="text-right">Funding atual (APR)</th><th className="pl-3">vs barra</th></tr></thead>
                <tbody>{Object.entries(p.positions || {}).sort((a, b) => b[1].current_funding_ann - a[1].current_funding_ann).map(([c, x]) => (
                  <tr key={c} className="border-t border-border/50"><td className="py-1.5 font-medium">{c}</td><td className="text-right">{price(x.size)}</td><td className="text-right">{usd(x.funding_accrued, 5)}</td>
                    <td className={x.current_funding_ann >= (F.usdc_bar_apr ?? 0.06) ? 'text-right text-up' : 'text-right text-down'}>{pct(x.current_funding_ann * 100, 2)}</td>
                    <td className="pl-3">{x.current_funding_ann >= (F.usdc_bar_apr ?? 0.06) ? <Badge variant="up">acima</Badge> : <Badge variant="down">abaixo</Badge>}</td></tr>
                ))}</tbody>
              </table>
            </CardContent>
          </Card>
        </section>
      ))}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader><div><CardTitle>Funding acumulado vs barra USDC {Math.round((F.usdc_bar_apr ?? 0.06) * 100)}%</CardTitle><CardDescription>US$ · tracejado = o que {Math.round((F.usdc_bar_apr ?? 0.06) * 100)}% a.a. sobre o capital teria rendido</CardDescription></div></CardHeader>
          <CardContent>{fundingSeries.some(s => s.data.length > 1) ? <LineChart series={fundingSeries} height={300} ariaLabel="Funding acumulado versus barra de 6% USDC" format={v => '$' + num(v, 4)} /> : <Empty>Sem pagamentos de funding ainda.</Empty>}</CardContent>
        </Card>
        <Card>
          <CardHeader><div><CardTitle>NAV (snapshots)</CardTitle><CardDescription>inclui custos de entrada simulados</CardDescription></div></CardHeader>
          <CardContent>{navSeries.some(s => s.data.length > 1) ? <LineChart series={navSeries} height={300} ariaLabel="NAV dos portfólios de funding" format={v => '$' + num(v, 2)} /> : <Empty>Sem snapshots ainda.</Empty>}</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Trades (paper)</CardTitle></CardHeader>
        <CardContent className="max-h-[360px] overflow-auto">
          {(F.trades || []).length ? (
            <table className="w-full min-w-[700px] text-xs num">
              <thead className="sticky top-0 bg-card text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Hora</th><th>Portfólio</th><th>Ativo</th><th>Perna</th><th>Lado</th><th className="text-right">Tamanho</th><th className="text-right">Preço</th><th className="text-right">Taxa</th><th>Motivo</th></tr></thead>
              <tbody>{(F.trades || []).map((t: any, i: number) => (
                <tr key={i} className="border-t border-border/50"><td className="py-1.5">{brtTime(t.ts, true)}</td><td>{t.portfolio}</td><td className="font-medium">{t.coin}</td><td>{t.leg}·{t.venue}</td><td className={t.side === 'buy' ? 'text-up' : 'text-down'}>{t.side}</td><td className="text-right">{price(t.size)}</td><td className="text-right">{price(t.vwap_px_usdc)}</td><td className="text-right">{num(t.fee, 4)}</td><td className="text-muted-foreground">{t.reason}</td></tr>
              ))}</tbody>
            </table>
          ) : <Empty>Sem trades.</Empty>}
        </CardContent>
      </Card>
    </div>
  )
}
