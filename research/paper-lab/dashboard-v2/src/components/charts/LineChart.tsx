// Multi-series line chart (equity curves vs benchmarks) with crosshair legend.
// Patterns: Ghostfolio (performance vs benchmark), Jesse (equity curve), lightweight-charts legend tutorial.
import { useEffect, useMemo, useRef, useState } from 'react'
import { LineSeries, LineStyle, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts'
import { baseOptions, toChartTime } from './base'
import { num } from '@/lib/format'

export interface LineDef { id: string; label: string; color: string; data: { t: number; v: number }[]; dashed?: boolean; width?: number }

interface Props { series: LineDef[]; height?: number; format?: (v: number) => string; ariaLabel: string; legendMax?: number; legend?: 'overlay' | 'above'; hidden?: Set<string>; onToggle?: (id: string) => void }

export function LineChart({ series, height = 320, format = v => num(v, 2), ariaLabel, legendMax = 14, legend = 'overlay', hidden, onToggle }: Props) {
  const all = series
  series = useMemo(() => (hidden ? all.filter(s => !hidden.has(s.id)) : all), [all, hidden])
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef(new Map<string, ISeriesApi<'Line'>>())
  const [hover, setHover] = useState<Record<string, number> | null>(null)
  const fmtRef = useRef(format); fmtRef.current = format

  useEffect(() => {
    if (!ref.current) return
    const chart = createChart(ref.current, baseOptions(height))
    chart.applyOptions({ rightPriceScale: { scaleMargins: { top: 0.12, bottom: 0.08 } } })
    chartRef.current = chart
    chart.subscribeCrosshairMove(p => {
      if (!p.time) { setHover(null); return }
      const out: Record<string, number> = {}
      seriesRef.current.forEach((s, id) => { const d = p.seriesData.get(s) as any; if (d && d.value != null) out[id] = d.value })
      setHover(out)
    })
    const map = seriesRef.current
    return () => { chart.remove(); chartRef.current = null; map.clear() }
  }, [height])

  const sig = useMemo(() => series.map(s => `${s.id}:${s.color}:${s.dashed ? 1 : 0}`).join('|'), [series])
  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return
    const map = seriesRef.current
    const ids = new Set(series.map(s => s.id))
    map.forEach((s, id) => { if (!ids.has(id)) { chart.removeSeries(s); map.delete(id) } })
    for (const s of series) {
      let ls = map.get(s.id)
      if (!ls) {
        ls = chart.addSeries(LineSeries, {
          color: s.color, lineWidth: (s.width ?? (s.dashed ? 1 : 2)) as any, lineStyle: s.dashed ? LineStyle.Dashed : LineStyle.Solid,
          priceLineVisible: false, lastValueVisible: !s.dashed && series.length <= 6, crosshairMarkerRadius: 3,
          priceFormat: { type: 'custom', formatter: (v: number) => fmtRef.current(v), minMove: 1e-6 },
        })
        map.set(s.id, ls)
      } else {
        ls.applyOptions({ color: s.color })
      }
      const seen = new Set<number>(); const data: { time: UTCTimestamp; value: number }[] = []
      for (const p of s.data) {
        const t = toChartTime(p.t)
        if (seen.has(t) || !Number.isFinite(p.v)) continue
        if (data.length && t < data[data.length - 1].time) continue
        seen.add(t); data.push({ time: t, value: p.v })
      }
      ls.setData(data)
    }
    chart.timeScale().fitContent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, series])

  const lastVals = useMemo(() => Object.fromEntries(series.map(s => [s.id, s.data.length ? s.data[s.data.length - 1].v : NaN])), [series])
  const vals = hover ?? lastVals
  return (
    <div className="relative w-full" role="img" aria-label={ariaLabel}>
      <div className={legend === 'overlay' ? 'pointer-events-none absolute left-2 top-1 z-10 flex max-w-[85%] flex-wrap gap-x-3 gap-y-0.5 text-[11px] num' : 'mb-1 flex min-h-[2.25rem] flex-wrap content-start gap-x-3 gap-y-0.5 text-[11px] num'}>
        {(onToggle ? all : series).slice(0, legendMax).map(s => {
          const off = hidden?.has(s.id)
          const inner = <><i className="inline-block h-0.5 w-3 rounded" style={{ background: s.color, opacity: s.dashed ? 0.7 : 1 }} />{s.label} <b className="text-foreground">{!off && Number.isFinite(vals[s.id]) ? format(vals[s.id]) : '—'}</b></>
          return onToggle
            ? <button key={s.id} type="button" aria-pressed={!off} onClick={() => onToggle(s.id)} className={'flex items-center gap-1 rounded px-0.5 text-muted-foreground hover:bg-accent ' + (off ? 'opacity-40 line-through' : '')}>{inner}</button>
            : <span key={s.id} className="flex items-center gap-1 text-muted-foreground">{inner}</span>
        })}
        {(onToggle ? all : series).length > legendMax && <span className="text-muted-foreground">+{(onToggle ? all : series).length - legendMax}</span>}
      </div>
      <div ref={ref} style={{ height }} className="w-full" />
    </div>
  )
}
