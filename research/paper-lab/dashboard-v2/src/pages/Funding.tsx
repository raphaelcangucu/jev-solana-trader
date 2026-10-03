// Funding carry (Hyperliquid, papel): o que o funding pagou contra a barra de 6% a.a. em USDC.
import { lazy, Suspense, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { ago, isoTime, num, pct, price, signedPct, signedUsd, usd } from '@/lib/format'
import { Delta, Dot, ErrorNote, Loading, Note, SectionHead, Stat } from '@/components/ui'
import { cn } from '@/lib/utils'

const TimeChart = lazy(() => import('@/components/charts/TimeChart'))
const NAMES: Record<string, string> = { p1000: 'Carteira de US$ 1.000', p1000_pons: 'Carteira de US$ 1.000 (variante pons)' }

export default function Funding() {
  const poll = usePollInterval(20_000)
  const q = useQuery({ queryKey: ['funding'], queryFn: api.funding, refetchInterval: poll || 60_000 })
  const F = q.data
  const bar = F?.usdc_bar_apr ?? 0.06
  const charts = useMemo(() => {
    if (!F?.available || !F.portfolios) return []
    const now = Date.now() / 1000, start = F.start_ts || now
    return Object.entries(F.portfolios).map(([name, p]) => {
      const cum = (F.cum_funding?.[name] ?? []).map(([t, v]) => ({ t, v }))
      const ts: number[] = []
      for (let t = start; t <= now; t += Math.max(600, (now - start) / 120)) ts.push(t)
      ts.push(now)
      return {
        name,
        series: [
          { id: 'f', label: 'funding recebido', color: 'var(--ink)', width: 2 as const, data: [{ t: start, v: 0 }, ...cum] },
          { id: 'b', label: `o que ${pct(bar * 100, 0)} a.a. em USDC renderia`, color: 'var(--ink-3)', width: 1 as const, data: ts.map(t => ({ t, v: p.capital * bar * (t - start) / (365 * 86400) })) },
        ],
      }
    })
  }, [F, bar])
  if (q.isLoading) return <Loading h={420} />
  if (q.error && !F) return <ErrorNote error={q.error} what="funding" />
  if (!F?.available) return <Note>O serviço de funding carry ainda não gravou nada (funding/data/status.json).</Note>
  const stale = (F.heartbeat_age_s ?? 999) > 180
  const kam = F.benchmarks?.kamino_usdc
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
        <h1 className="t-title text-[26px]">Funding carry</h1>
        <p className="flex items-center gap-2 text-[13.5px] text-ink-2"><Dot level={stale ? 'warn' : 'ok'} />Sinal há {ago(F.heartbeat_age_s)}; começou {isoTime(F.started_at, true)}. Só papel, endpoints públicos.</p>
      </div>
      <p className="max-w-[860px] text-[14px] text-ink-2">
        Compra o ativo à vista e vende o perpétuo do mesmo tamanho: o preço se anula e sobra o funding. Só vale a pena se render mais que deixar o dinheiro em USDC (barra de {pct(bar * 100, 0)} a.a.; a Kamino paga {kam?.apy != null ? pct(kam.apy * 100, 1) : '—'} hoje).
      </p>
      {Object.entries(F.portfolios ?? {}).map(([name, p]) => {
        const ch = charts.find(c => c.name === name)
        return (
          <section key={name} className="sheet rounded-xl p-4 sm:p-6" aria-label={NAMES[name] ?? name}>
            <SectionHead title={NAMES[name] ?? name}>caixa livre {usd(p.cash)} de {usd(p.capital)}</SectionHead>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-5 border-y border-rule py-4 sm:grid-cols-3 lg:grid-cols-6">
              <Stat label="Valor" sub={p.bench?.kamino_usdc != null ? `vs Kamino ${signedUsd(p.nav - p.bench.kamino_usdc)}` : undefined}>{usd(p.nav)}</Stat>
              <Stat label="Retorno"><Delta v={p.ret_pct}>{signedPct(p.ret_pct, 2)}</Delta></Stat>
              <Stat label="Funding recebido">{usd(p.funding, 2)}</Stat>
              <Stat label="Taxas pagas">{usd(p.fees, 2)}</Stat>
              <Stat label="Ritmo anual" sub={p.apr_simple_pct == null ? 'pouco histórico ainda' : 'inclui o custo de entrada'}>{p.apr_simple_pct == null ? '—' : <Delta v={p.apr_simple_pct} arrowOn={false}>{signedPct(p.apr_simple_pct, 1)}</Delta>}</Stat>
              <Stat label="Maior queda">{pct(p.max_dd_pct, 2)}</Stat>
            </dl>
            <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
              <div>
                {ch && ch.series[0].data.length > 1 ? (
                  <Suspense fallback={<Loading h={240} />}>
                    <TimeChart series={ch.series} format={v => usd(v, 2)} height={240} ariaLabel={`Funding acumulado de ${name} contra a barra de USDC`} />
                  </Suspense>
                ) : <Note>Sem pagamentos de funding ainda.</Note>}
              </div>
              <table className="w-full self-start text-[13.5px] t-tab">
                <thead><tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3"><th className="py-1.5 font-normal">Ativo</th><th className="text-right font-normal">Tamanho</th><th className="text-right font-normal">Recebido</th><th className="text-right font-normal">Funding hoje (a.a.)</th></tr></thead>
                <tbody>
                  {Object.entries(p.positions ?? {}).sort((a, b) => b[1].current_funding_ann - a[1].current_funding_ann).map(([c, x]) => {
                    const above = x.current_funding_ann >= bar
                    return (
                      <tr key={c} className="border-b border-rule">
                        <td className="py-1.5 t-semi">{c}</td>
                        <td className="text-right">{price(x.size)}</td>
                        <td className="text-right">{usd(x.funding_accrued, 3)}</td>
                        <td className={cn('text-right', above ? 'text-gain' : 'text-loss')}>{above ? '▲' : '▼'} {pct(x.current_funding_ann * 100, 1)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )
      })}
      <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="f-tr">
        <SectionHead id="f-tr" title="Últimos trades" />
        {(F.trades ?? []).length ? (
          <ul className="divide-y divide-rule border-y border-rule text-[13.5px]">
            {F.trades!.slice(0, 16).map((t, i) => (
              <li key={i} className="grid grid-cols-[92px_60px_86px_minmax(0,1fr)_auto] items-baseline gap-3 py-1.5 t-tab">
                <span className="text-ink-3">{isoTime(t.ts, true)}</span>
                <span className="t-semi">{t.coin}</span>
                <span className={t.side === 'buy' ? 'text-gain' : 'text-loss'}>{t.side === 'buy' ? '▲ compra' : '▼ venda'}</span>
                <span className="truncate text-ink-2">{t.leg === 'perp' ? 'perpétuo' : 'à vista'} a {price(t.vwap_px_usdc)}</span>
                <span className="text-ink-3">taxa {num(t.fee, 3)}</span>
              </li>
            ))}
          </ul>
        ) : <Note>Sem trades ainda.</Note>}
      </section>
    </div>
  )
}
