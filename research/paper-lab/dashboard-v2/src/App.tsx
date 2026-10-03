import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, Bot, Coins, FlaskConical, Gauge, LayoutDashboard, Percent, SlidersHorizontal } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { LoadingBlock, StatusDot } from '@/components/common'
import { HealthFooter } from '@/components/HealthFooter'
import { api } from '@/lib/api'
import { useLive, usePollInterval } from '@/lib/live'
import { price } from '@/lib/format'
import { Tip } from '@/components/ui/tooltip'

const Overview = lazy(() => import('./tabs/Overview'))
const SolTab = lazy(() => import('./tabs/SolTab'))
const MemesTab = lazy(() => import('./tabs/MemesTab'))
const LabTab = lazy(() => import('./tabs/LabTab'))
const ModelsTab = lazy(() => import('./tabs/ModelsTab'))
const FundingTab = lazy(() => import('./tabs/FundingTab'))
const ControlsTab = lazy(() => import('./tabs/ControlsTab'))

const TABS = [
  { id: 'visao-geral', label: 'Visão geral', icon: LayoutDashboard, C: Overview },
  { id: 'sol', label: 'Portfólios SOL', icon: Activity, C: SolTab },
  { id: 'memes', label: 'Memecoins', icon: Coins, C: MemesTab },
  { id: 'regras-lab', label: 'Regras & Lab', icon: FlaskConical, C: LabTab },
  { id: 'modelos', label: 'Modelos', icon: Bot, C: ModelsTab },
  { id: 'funding', label: 'Funding', icon: Percent, C: FundingTab },
  { id: 'controles', label: 'Controles', icon: SlidersHorizontal, C: ControlsTab },
] as const

function useHashTab() {
  const get = () => { const h = window.location.hash.replace('#', ''); return TABS.some(t => t.id === h) ? h : 'visao-geral' }
  const [tab, setTab] = useState(get)
  useEffect(() => { const f = () => setTab(get()); window.addEventListener('hashchange', f); return () => window.removeEventListener('hashchange', f) }, [])
  return [tab, (t: string) => { window.history.replaceState(null, '', `#${t}`); setTab(t) }] as const
}

export default function App() {
  const [tab, setTab] = useHashTab()
  const live = useLive()
  const poll = usePollInterval()
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: poll })
  const px = live.price ?? health.data?.price_usd
  const src = live.priceSource ?? health.data?.price_source
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-primary focus:px-3 focus:py-1 focus:text-primary-foreground">Pular para o conteúdo</a>
      <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-3 py-2.5 sm:px-5">
          <div className="flex items-center gap-2">
            <Gauge className="size-5 text-primary" aria-hidden />
            <h1 className="text-sm font-semibold tracking-tight sm:text-base">Paper Trader</h1>
            <Tip content="Simulação: nenhuma ordem real, nenhuma chave é lida."><Badge variant="warn" className="uppercase">paper</Badge></Tip>
          </div>
          <div className="ml-auto flex items-center gap-3 text-xs">
            <div className="text-right num" aria-live="polite">
              <span className="text-muted-foreground">SOL </span><b className="text-sm">${price(px)}</b>
              <span className="hidden text-muted-foreground sm:inline"> · {src || '—'}</span>
            </div>
            <Tip content={live.connected ? 'Atualização ao vivo via SSE' : 'Stream indisponível — atualizando a cada 12s'}>
              <span className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px]">
                <StatusDot level={live.connected ? 'ok' : 'warn'} />{live.connected ? 'ao vivo' : 'polling'}
              </span>
            </Tip>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-[1600px] flex-1 px-3 pb-6 pt-3 sm:px-5">
        <Tabs value={tab} onValueChange={setTab}>
          <div className="-mx-3 overflow-x-auto px-3 sm:mx-0 sm:px-0">
            <TabsList aria-label="Seções do painel" className="w-max">
              {TABS.map(t => <TabsTrigger key={t.id} value={t.id}><t.icon aria-hidden />{t.label}</TabsTrigger>)}
            </TabsList>
          </div>
          {TABS.map(t => (
            <TabsContent key={t.id} value={t.id}>
              {tab === t.id && <Suspense fallback={<LoadingBlock h={420} />}><t.C /></Suspense>}
            </TabsContent>
          ))}
        </Tabs>
      </main>
      <HealthFooter health={health.data} />
    </div>
  )
}
