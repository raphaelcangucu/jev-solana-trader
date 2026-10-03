import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, BarChart3, HeartPulse, Layers } from 'lucide-react'
import { api } from '@/lib/api'
import { useLive, usePollInterval } from '@/lib/live'
import { Kpi, ErrorBlock, LoadingBlock, SectionTitle, StatusDot } from '@/components/common'
import { RankingTable } from '@/components/RankingTable'
import { PricePanel } from '@/components/PricePanel'
import { num, price, signedUsd } from '@/lib/format'

export default function Overview() {
  const poll = usePollInterval()
  const live = useLive()
  const q = useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: poll })
  if (q.isLoading) return <LoadingBlock h={600} />
  if (q.error) return <ErrorBlock error={q.error} />
  const o = q.data!
  const best = [...o.rows].sort((a, b) => (b.vs_bh_pct ?? -1e9) - (a.vs_bh_pct ?? -1e9))[0]
  const beating = o.rows.filter(r => (r.vs_bh ?? 0) > 0.005).length
  return (
    <div className="flex flex-col gap-4">
      <section aria-label="Indicadores" className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">
        <Kpi icon={<Activity className="size-3.5" />} label="Preço SOL" value={`$${price(live.price ?? o.price_usd)}`} sub={o.price_source || ''} />
        <Kpi icon={<Layers className="size-3.5" />} label="Portfólios" value={num(o.portfolios_total, 0)} sub={`${beating} batendo B&H · líder ${best?.name ?? '—'} ${best ? signedUsd(best.vs_bh) : ''}`} />
        <Kpi icon={<BarChart3 className="size-3.5" />} label="Trades hoje" value={num(o.trades_today, 0)} sub="desde 00:00 BRT (SOL + memes + lab)" />
        <Kpi icon={<AlertTriangle className="size-3.5" />} label="Erros" value={num(o.errors, 0)} tone={o.errors ? 'text-down' : undefined} sub="soma dos contadores dos bots" />
        <Kpi icon={<HeartPulse className="size-3.5" />} label="Saúde" value={<span className="flex items-center gap-2"><StatusDot level={o.health} />{o.health === 'ok' ? 'OK' : o.health === 'warn' ? 'Atenção' : 'Problema'}</span>} sub="processos + heartbeats (rodapé)" />
      </section>
      <PricePanel asset="SOL" title="SOL/USD · trades de todos os portfólios" />
      <section>
        <SectionTitle desc={o.verdict_rule}>Ranking de portfólios</SectionTitle>
        <RankingTable rows={o.rows} />
      </section>
    </div>
  )
}
