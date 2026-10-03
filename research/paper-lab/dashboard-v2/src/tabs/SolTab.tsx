import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EquityOverlay } from '@/components/EquityOverlay'
import { ErrorBlock, LoadingBlock, Pnl, SectionTitle, VerdictBadge, VerdictProgress } from '@/components/common'
import { useDrawer } from '@/components/drawer-context'
import { colorFor } from '@/lib/colors'
import { num, pct, usd } from '@/lib/format'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/input'

export default function SolTab() {
  const poll = usePollInterval()
  const [withLab, setWithLab] = useState(false)
  const ov = useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: poll })
  const eq = useQuery({ queryKey: ['equity', 'sol'], queryFn: () => api.equity({ group: 'sol', points: 700 }), refetchInterval: poll })
  const labEq = useQuery({ queryKey: ['equity', 'lab-sol'], queryFn: () => api.equity({ group: 'lab', asset: 'SOL', points: 700 }), enabled: withLab, refetchInterval: poll })
  const { open } = useDrawer()
  const rows = (ov.data?.rows || []).filter(r => r.asset === 'SOL' && (r.group === 'sol' || withLab))
  const data = { ...(eq.data || {}), ...(withLab ? labEq.data || {} : {}) }
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div><CardTitle>Curvas de patrimônio · SOL</CardTitle><CardDescription>Cada portfólio normalizado pelo próprio capital inicial · tracejado = buy-and-hold e 100% USDT</CardDescription></div>
          <div className="flex items-center gap-2"><Switch id="withlab" checked={withLab} onCheckedChange={setWithLab} /><Label htmlFor="withlab">incluir hipóteses do lab (SOL)</Label></div>
        </CardHeader>
        <CardContent>{eq.isLoading ? <LoadingBlock h={360} /> : eq.error ? <ErrorBlock error={eq.error} /> : <EquityOverlay data={data} />}</CardContent>
      </Card>
      <section>
        <SectionTitle desc="Clique num cartão para abrir os detalhes (parâmetros, trades, histograma de confiança, fills).">Portfólios SOL</SectionTitle>
        {ov.isLoading ? <LoadingBlock h={240} /> : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {rows.sort((a, b) => (b.vs_bh_pct ?? -1e9) - (a.vs_bh_pct ?? -1e9)).map(r => (
              <button key={r.name} onClick={() => open(r.name)} className="rounded-xl border bg-card p-3 text-left transition-colors hover:border-primary/50 hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <div className="flex items-center gap-2">
                  <i className="inline-block size-2.5 rounded-full" style={{ background: colorFor(r.name) }} aria-hidden />
                  <span className="truncate font-medium">{r.name}</span>
                  <Badge variant="outline" className="ml-auto">{r.model}</Badge>
                  {r.paused && <Badge variant="warn">pausado</Badge>}
                </div>
                <div className="mt-2 flex items-baseline justify-between"><span className="text-lg font-semibold num">{usd(r.equity)}</span><Pnl v={r.pnl} pctV={r.pnl_pct} /></div>
                <dl className="mt-1 grid grid-cols-3 gap-1 text-[11px] text-muted-foreground num">
                  <div><dt>vs B&H</dt><dd><Pnl v={r.vs_bh} /></dd></div>
                  <div><dt>trades</dt><dd className="text-foreground">{num(r.trades ?? 0, 0)}</dd></div>
                  <div><dt>max DD</dt><dd className="text-foreground">{pct(r.max_dd_pct, 2)}</dd></div>
                </dl>
                <div className="mt-2 flex items-center gap-2"><VerdictBadge v={r.verdict} /><VerdictProgress p={r.progress} text={r.progress_text} /></div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
