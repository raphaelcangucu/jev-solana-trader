// Gráfico de tempo (lightweight-charts): um eixo y, linhas finas, grade recessiva, legenda com leitura no cursor.
// Carregado sob demanda (chunk "charts"); nunca entra no JS inicial do placar.
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ColorType, CrosshairMode, LineSeries, LineStyle, createChart, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type SeriesMarker, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import { cssVar, useThemeMode } from '@/lib/theme'
import { tsTime } from '@/lib/format'

export interface SeriesDef { id: string; label: string; color: string; width?: 1 | 2 | 3; data: { t: number; v: number }[] }
export interface MarkDef { t: number; side: 'buy' | 'sell' }

const BRT_SHIFT = -3 * 3600 // o gráfico desenha em UTC; desloca para o relógio de Brasília
const toTime = (ts: number) => (ts + BRT_SHIFT) as UTCTimestamp
const resolve = (c: string) => (c.startsWith('var(') ? cssVar(c.slice(4, -1)) : c)

export default function TimeChart({ series, markers, format, height = 300, ariaLabel, zeroLine, idleLabel = 'agora' }: {
  series: SeriesDef[]; markers?: MarkDef[]; format: (v: number) => string; height?: number; ariaLabel: string; zeroLine?: number
  /** rótulo do canto direito quando o cursor não está no gráfico (série histórica: "fim da janela") */
  idleLabel?: string
}) {
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const lines = useRef(new Map<string, ISeriesApi<'Line'>>())
  const [hover, setHover] = useState<{ t: number; vals: Record<string, number> } | null>(null)
  const mode = useThemeMode()
  const fmt = useRef(format); fmt.current = format
  const sig = useMemo(() => series.map(s => `${s.id}:${s.data.length}:${s.data[s.data.length - 1]?.v ?? ''}`).join('|') + `|${markers?.length ?? 0}`, [series, markers])

  useEffect(() => {
    if (!box.current) return
    const ink3 = cssVar('--ink-3'), rule = cssVar('--rule')
    const c = createChart(box.current, {
      height, autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: ink3, fontSize: 11, fontFamily: '"Archivo Variable", system-ui, sans-serif', attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: rule } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.1 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: { mode: CrosshairMode.Magnet, vertLine: { color: cssVar('--ink-3'), width: 1, style: LineStyle.Solid, labelVisible: false }, horzLine: { visible: false, labelVisible: false } },
      localization: { locale: 'pt-BR', priceFormatter: (v: number) => fmt.current(v) },
      handleScale: { mouseWheel: false, pinch: true }, handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
    })
    chart.current = c
    c.subscribeCrosshairMove(p => {
      if (!p.time) { setHover(null); return }
      const vals: Record<string, number> = {}
      lines.current.forEach((s, id) => { const d = p.seriesData.get(s) as { value?: number } | undefined; if (d?.value != null) vals[id] = d.value })
      setHover({ t: (p.time as number) - BRT_SHIFT, vals })
    })
    const map = lines.current
    return () => { c.remove(); chart.current = null; map.clear() }
  }, [height, mode])

  useEffect(() => {
    const c = chart.current
    if (!c) return
    const map = lines.current
    map.forEach(s => c.removeSeries(s)); map.clear()
    series.forEach((s, i) => {
      const ls = c.addSeries(LineSeries, {
        color: resolve(s.color), lineWidth: s.width ?? 2, priceLineVisible: false, lastValueVisible: i === 0,
        crosshairMarkerRadius: 4, crosshairMarkerBorderColor: cssVar('--surface'), crosshairMarkerBorderWidth: 2,
        priceFormat: { type: 'custom', formatter: (v: number) => fmt.current(v), minMove: 1e-6 },
      })
      const data: { time: UTCTimestamp; value: number }[] = []
      for (const p of s.data) {
        const t = toTime(p.t)
        if (!Number.isFinite(p.v) || (data.length && t <= data[data.length - 1].time)) continue
        data.push({ time: t, value: p.v })
      }
      ls.setData(data)
      if (i === 0 && zeroLine != null) ls.createPriceLine({ price: zeroLine, color: cssVar('--rule-strong'), lineWidth: 1, lineStyle: LineStyle.Solid, axisLabelVisible: false })
      if (i === 0 && markers?.length && data.length) {
        const first = data[0].time, last = data[data.length - 1].time
        const ms: SeriesMarker<Time>[] = markers
          .map(m => ({ ...m, time: toTime(m.t) }))
          .filter(m => m.time >= first && m.time <= last)
          .sort((a, b) => (a.time as number) - (b.time as number))
          .map(m => ({ time: m.time, position: m.side === 'buy' ? 'belowBar' : 'aboveBar', shape: m.side === 'buy' ? 'arrowUp' : 'arrowDown', color: cssVar(m.side === 'buy' ? '--gain' : '--loss'), size: 0.6 }))
        createSeriesMarkers(ls, ms)
      }
      map.set(s.id, ls)
    })
    c.timeScale().fitContent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, mode])

  const last = useMemo(() => Object.fromEntries(series.map(s => [s.id, s.data[s.data.length - 1]?.v])), [series])
  const vals = hover?.vals ?? last
  return (
    <figure className="m-0" aria-label={ariaLabel}>
      <figcaption className="mb-2 flex min-h-[22px] flex-wrap items-baseline gap-x-5 gap-y-1 text-[12.5px] text-ink-3">
        {series.map(s => (
          <span key={s.id} className="inline-flex items-baseline gap-1.5">
            <i aria-hidden className="inline-block w-4 translate-y-[-3px] rounded-full" style={{ height: s.width === 1 ? 1.5 : 2.5, background: s.color }} />
            <b className="t-num text-[14px] text-ink">{vals[s.id] != null && Number.isFinite(vals[s.id]) ? format(vals[s.id] as number) : '—'}</b>
            <span>{s.label}</span>
          </span>
        ))}
        {markers?.length ? <span className="inline-flex items-baseline gap-2"><span className="text-gain">▲ compra</span><span className="text-loss">▼ venda</span></span> : null}
        <span className="ml-auto t-tab">{hover ? tsTime(hover.t, true) : idleLabel}</span>
      </figcaption>
      <div ref={box} style={{ height }} className="w-full" />
    </figure>
  )
}
