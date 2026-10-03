import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { PriceChart } from './charts/PriceChart'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { ErrorBlock, LoadingBlock } from './common'
import { colorFor } from '@/lib/colors'
import { cn } from '@/lib/utils'

const TF = [{ id: '6h', h: 6, res: 120 }, { id: '24h', h: 24, res: 300 }, { id: '3d', h: 72, res: 900 }, { id: '7d', h: 168, res: 3600 }]

export function PricePanel({ asset, title, height = 360 }: { asset: string; title?: string; height?: number }) {
  const [tf, setTf] = useState(TF[1])
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const poll = usePollInterval(15_000)
  const q = useQuery({ queryKey: ['candles', asset, tf.res, tf.h], queryFn: () => api.candles(asset, tf.res, tf.h), refetchInterval: poll })
  const ports = useMemo(() => [...new Set((q.data?.markers || []).map(m => m.portfolio))].sort(), [q.data])
  const markers = useMemo(() => (q.data?.markers || []).filter(m => !hidden.has(m.portfolio)), [q.data, hidden])
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{title || `${asset}/USD`}</CardTitle>
          <CardDescription>Velas {tf.res >= 3600 ? `${tf.res / 3600}h` : `${tf.res / 60}min`} (marks reais) · ▲ compra ▼ venda por portfólio · barras = nº de trades paper · BRT</CardDescription>
        </div>
        <div role="radiogroup" aria-label="Janela de tempo" className="inline-flex rounded-lg bg-muted p-0.5">
          {TF.map(t => (
            <button key={t.id} role="radio" aria-checked={tf.id === t.id} onClick={() => setTf(t)} className={cn('rounded-md px-2 py-0.5 text-xs font-medium', tf.id === t.id ? 'bg-background shadow' : 'text-muted-foreground hover:text-foreground')}>{t.id}</button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {q.isLoading ? <LoadingBlock h={height} /> : q.error ? <ErrorBlock error={q.error} /> : <PriceChart candles={q.data!.candles} markers={markers} height={height} label={`${asset}/USD`} />}
        {ports.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1" aria-label="Filtrar marcadores por portfólio">
            {ports.map(p => {
              const off = hidden.has(p)
              const n = (q.data?.markers || []).filter(m => m.portfolio === p).length
              return (
                <button key={p} aria-pressed={!off} onClick={() => setHidden(s => { const x = new Set(s); off ? x.delete(p) : x.add(p); return x })}
                  className={cn('inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px]', off ? 'opacity-40' : '')}>
                  <i className="inline-block size-2 rounded-full" style={{ background: colorFor(p) }} />{p}<span className="text-muted-foreground num">{n}</span>
                </button>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
