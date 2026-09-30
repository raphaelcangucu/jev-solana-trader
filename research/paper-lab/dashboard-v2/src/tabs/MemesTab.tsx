import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type MemeCell } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorBlock, LoadingBlock, Empty } from '@/components/common'
import { PricePanel } from '@/components/PricePanel'
import { EquityOverlay } from '@/components/EquityOverlay'
import { useDrawer } from '@/components/drawer-context'
import { num, price, signed, signedUsd } from '@/lib/format'
import { cn } from '@/lib/utils'

type Metric = 'vs_bh_pct' | 'vs_bh' | 'pnl_pct'
const METRICS: { id: Metric; label: string }[] = [{ id: 'vs_bh_pct', label: 'excesso vs B&H %' }, { id: 'vs_bh', label: 'excesso vs B&H US$' }, { id: 'pnl_pct', label: 'PnL %' }]

function cellColor(v: number | null | undefined, max: number) {
  if (v == null || !Number.isFinite(v)) return 'transparent'
  const a = Math.min(1, Math.abs(v) / (max || 1)) * 0.75 + 0.06
  return v >= 0 ? `rgba(34,197,94,${a})` : `rgba(239,68,68,${a})`
}

export default function MemesTab() {
  const poll = usePollInterval()
  const q = useQuery({ queryKey: ['memes'], queryFn: api.memes, refetchInterval: poll })
  const [metric, setMetric] = useState<Metric>('vs_bh_pct')
  const [coin, setCoin] = useState<string | null>(null)
  const { open } = useDrawer()
  const m = q.data
  const sym = coin ?? m?.symbols[0] ?? null
  const max = useMemo(() => {
    let x = 0
    if (m) for (const s of m.symbols) for (const k of m.strategies) { const v = m.grid[s]?.[k]?.[metric]; if (v != null && Number.isFinite(v)) x = Math.max(x, Math.abs(v)) }
    return x
  }, [m, metric])
  const eqM = useQuery({ queryKey: ['equity', 'meme', sym], queryFn: () => api.equity({ group: 'meme', asset: sym!, points: 500 }), enabled: !!sym, refetchInterval: poll })
  const eqL = useQuery({ queryKey: ['equity', 'lab', sym], queryFn: () => api.equity({ group: 'lab', asset: sym!, points: 500 }), enabled: !!sym, refetchInterval: poll })
  if (q.isLoading) return <LoadingBlock h={500} />
  if (q.error) return <ErrorBlock error={q.error} />
  if (!m || !m.symbols.length) return <Empty>Sem memecoins configuradas.</Empty>
  const fmt = (c?: MemeCell) => !c ? '' : metric === 'vs_bh' ? signedUsd(c.vs_bh) : signed(c[metric], 2, '%')
  const label = (k: string) => m.labels[k] || k.replace(/^h\d:/, '').replace(/_/g, ' ')
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div><CardTitle>Mapa de calor · moeda × estratégia</CardTitle><CardDescription>Verde = acima do buy-and-hold da própria moeda · clique numa célula para detalhes · {m.meta.meme_models_enabled ? `modelos: ${(m.meta.meme_models_enabled || []).join(', ')}` : ''}</CardDescription></div>
          <div role="radiogroup" aria-label="Métrica" className="inline-flex rounded-lg bg-muted p-0.5">
            {METRICS.map(x => <button key={x.id} role="radio" aria-checked={metric === x.id} onClick={() => setMetric(x.id)} className={cn('rounded-md px-2 py-0.5 text-xs font-medium', metric === x.id ? 'bg-background shadow' : 'text-muted-foreground')}>{x.label}</button>)}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {m.strategies.length === 0 ? <Empty>Aguardando os portfólios de memecoins (reinício em andamento?).</Empty> : (
            <table className="w-full border-separate border-spacing-0.5 text-xs num" aria-label="Mapa de calor de excesso sobre buy-and-hold">
              <thead>
                <tr>
                  <th scope="col" className="sticky left-0 z-10 bg-card p-1 text-left text-[11px] font-medium text-muted-foreground">Moeda</th>
                  {m.strategies.map(k => <th key={k} scope="col" className="min-w-[84px] p-1 text-center text-[10px] font-medium leading-tight text-muted-foreground">{label(k)}</th>)}
                </tr>
              </thead>
              <tbody>
                {m.symbols.map(s => (
                  <tr key={s}>
                    <th scope="row" className="sticky left-0 z-10 bg-card p-1 text-left">
                      <button className={cn('rounded px-1 font-semibold hover:underline', sym === s && 'text-primary')} onClick={() => setCoin(s)}>{s}</button>
                      <div className="text-[10px] font-normal text-muted-foreground">${price(m.tokens[s]?.price)}</div>
                    </th>
                    {m.strategies.map(k => {
                      const c = m.grid[s]?.[k]
                      return (
                        <td key={k} className="p-0">
                          {c ? (
                            <button onClick={() => open(c.name)} title={`${c.name}\nvalor $${num(c.equity, 2)} · trades ${c.trades ?? 0} · ${c.verdict} ${c.progress_text || ''}`}
                              className="h-11 w-full rounded-md px-1 text-center font-medium text-foreground ring-inset hover:ring-2 hover:ring-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              style={{ background: cellColor(c[metric], max) }}>
                              <div>{fmt(c)}</div><div className="text-[10px] font-normal opacity-70">{c.trades ?? 0} tr</div>
                            </button>
                          ) : <div className="h-11 rounded-md bg-muted/30" aria-label="sem dados" />}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-1" role="radiogroup" aria-label="Moeda">
        {m.symbols.map(s => <button key={s} role="radio" aria-checked={sym === s} onClick={() => setCoin(s)} className={cn('rounded-md border px-2.5 py-1 text-xs font-medium', sym === s ? 'border-primary bg-primary/15 text-primary' : 'text-muted-foreground hover:text-foreground')}>{s}</button>)}
      </div>
      {sym && (
        <div className="grid gap-4 xl:grid-cols-2">
          <PricePanel asset={sym} title={`${sym}/USD · trades por portfólio`} height={320} />
          <Card>
            <CardHeader><div><CardTitle>{sym} · patrimônio por estratégia</CardTitle><CardDescription>normalizado · tracejado = B&H de {sym}</CardDescription></div></CardHeader>
            <CardContent>{eqM.isLoading ? <LoadingBlock h={320} /> : <EquityOverlay data={{ ...(eqM.data || {}), ...(eqL.data || {}) }} height={320} bhLabel={`B&H ${sym}`} />}</CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
