// Overlaid equity curves (normalized % or US$) vs buy-and-hold and 100% USDT.
import { useMemo, useState } from 'react'
import type { EquityMap } from '@/lib/api'
import { LineChart, type LineDef } from './charts/LineChart'
import { colorFor } from '@/lib/colors'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Empty } from './common'

export function EquityOverlay({ data, height = 360, bhLabel = 'Buy & hold' }: { data: EquityMap; height?: number; bhLabel?: string }) {
  const [mode, setMode] = useState<'pct' | 'usd'>('pct')
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const names = useMemo(() => Object.keys(data).filter(n => data[n].t.length > 0).sort(), [data])
  const series = useMemo<LineDef[]>(() => {
    const out: LineDef[] = []
    let ref: string | null = null
    for (const n of names) if (!ref || data[n].t.length > data[ref].t.length || (data[n].t[0] ?? 0) < (data[ref].t[0] ?? 0)) ref = n
    for (const n of names) {
      const s = data[n]
      const base = s.usdt.find(v => v != null) ?? s.equity.find(v => v != null) ?? 1
      out.push({ id: n, label: n, color: colorFor(n), data: s.t.map((t, i) => ({ t, v: s.equity[i] == null ? NaN : mode === 'pct' ? ((s.equity[i]! / (base as number)) - 1) * 100 : s.equity[i]! })) })
    }
    if (ref) {
      const s = data[ref]
      const base = s.usdt.find(v => v != null) ?? s.bh.find(v => v != null) ?? 1
      out.push({ id: '__bh', label: `${bhLabel} (${ref})`, color: '#cbd5e1', dashed: true, data: s.t.map((t, i) => ({ t, v: s.bh[i] == null ? NaN : mode === 'pct' ? ((s.bh[i]! / (base as number)) - 1) * 100 : s.bh[i]! })) })
      out.push({ id: '__usdt', label: '100% USDT', color: '#64748b', dashed: true, width: 1, data: s.t.map((t, i) => ({ t, v: s.usdt[i] == null ? NaN : mode === 'pct' ? 0 : s.usdt[i]! })) })
    }
    return out
  }, [data, names, mode])
  if (!names.length) return <Empty>Sem curvas de patrimônio ainda.</Empty>
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Unidade" className="inline-flex rounded-lg bg-muted p-0.5">
          {(['pct', 'usd'] as const).map(m => <button key={m} role="radio" aria-checked={mode === m} onClick={() => setMode(m)} className={cn('rounded-md px-2 py-0.5 text-xs font-medium', mode === m ? 'bg-background shadow' : 'text-muted-foreground')}>{m === 'pct' ? '% retorno' : 'US$'}</button>)}
        </div>
      </div>
      <LineChart series={series} height={height} ariaLabel="Curvas de patrimônio sobrepostas versus buy-and-hold" format={v => (mode === 'pct' ? `${num(v, 2)}%` : `$${num(v, 2)}`)} legendMax={40} legend="above" hidden={hidden} onToggle={id => setHidden(s => { const x = new Set(s); x.has(id) ? x.delete(id) : x.add(id); return x })} />
    </div>
  )
}
