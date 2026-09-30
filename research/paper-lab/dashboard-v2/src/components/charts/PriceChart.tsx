// Candles + per-portfolio trade markers + trades-per-bar histogram, crosshair OHLC legend.
// Patterns: FreqUI (trade markers on candles), lightweight-charts docs (legend via subscribeCrosshairMove,
// volume-style histogram overlay with scaleMargins), react-financial-charts (OHLC tooltip). No code copied.
import { useEffect, useRef, useState } from 'react'
import { CandlestickSeries, HistogramSeries, createChart, createSeriesMarkers, type IChartApi, type ISeriesApi, type SeriesMarker, type Time } from 'lightweight-charts'
import type { Candle, Marker } from '@/lib/api'
import { baseOptions, toChartTime } from './base'
import { colorFor, UP, DOWN } from '@/lib/colors'
import { price as fp } from '@/lib/format'

interface Props { candles: Candle[]; markers: Marker[]; height?: number; label: string; showMarkerText?: boolean }

export function PriceChart({ candles, markers, height = 340, label, showMarkerText = false }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const histRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)
  const [legend, setLegend] = useState<{ o?: number; h?: number; l?: number; c?: number; n?: number } | null>(null)
  const byTime = useRef(new Map<number, number>())

  useEffect(() => {
    if (!ref.current) return
    const chart = createChart(ref.current, baseOptions(height))
    const cs = chart.addSeries(CandlestickSeries, { upColor: UP, downColor: DOWN, borderVisible: false, wickUpColor: UP, wickDownColor: DOWN, priceFormat: { type: 'custom', formatter: (p: number) => fp(p), minMove: 1e-10 } })
    cs.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } })
    const hs = chart.addSeries(HistogramSeries, { priceScaleId: 'trades', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
    chart.priceScale('trades').applyOptions({ scaleMargins: { top: 0.84, bottom: 0 }, visible: false })
    chartRef.current = chart; candleRef.current = cs; histRef.current = hs
    markersRef.current = createSeriesMarkers(cs, [])
    chart.subscribeCrosshairMove(p => {
      if (!p.time) { setLegend(null); return }
      const d = p.seriesData.get(cs) as any
      if (d) setLegend({ o: d.open, h: d.high, l: d.low, c: d.close, n: byTime.current.get(p.time as number) ?? 0 })
    })
    return () => { chart.remove(); chartRef.current = null }
  }, [height])

  useEffect(() => {
    const cs = candleRef.current, hs = histRef.current
    if (!cs || !hs) return
    cs.setData(candles.map(c => ({ time: toChartTime(c.time), open: c.open, high: c.high, low: c.low, close: c.close })))
    const counts = new Map<number, { b: number; s: number }>()
    for (const m of markers) {
      const k = m.time; const e = counts.get(k) || { b: 0, s: 0 }
      if (m.side === 'buy') e.b++; else e.s++
      counts.set(k, e)
    }
    byTime.current = new Map([...counts].map(([k, v]) => [toChartTime(k) as number, v.b + v.s]))
    hs.setData(candles.map(c => {
      const e = counts.get(c.time)
      const n = e ? e.b + e.s : 0
      return { time: toChartTime(c.time), value: n, color: !e ? 'rgba(0,0,0,0)' : e.b >= e.s ? 'rgba(34,197,94,0.45)' : 'rgba(239,68,68,0.45)' }
    }))
    const ms: SeriesMarker<Time>[] = [...markers].sort((a, b) => a.ts - b.ts).map(m => ({
      time: toChartTime(m.time), position: m.side === 'buy' ? 'belowBar' : 'aboveBar', shape: m.side === 'buy' ? 'arrowUp' : 'arrowDown',
      color: colorFor(m.portfolio), text: showMarkerText ? m.portfolio : undefined, size: 0.8,
    }))
    markersRef.current?.setMarkers(ms)
    chartRef.current?.timeScale().fitContent()
  }, [candles, markers, showMarkerText])

  const last = candles[candles.length - 1]
  const L = legend ?? (last ? { o: last.open, h: last.high, l: last.low, c: last.close, n: undefined } : null)
  return (
    <div className="relative w-full" role="img" aria-label={`Gráfico de preço ${label} com marcadores de trades`}>
      <div className="pointer-events-none absolute left-2 top-1 z-10 flex flex-wrap gap-x-3 text-[11px] num text-muted-foreground">
        <span className="font-semibold text-foreground">{label}</span>
        {L && <>
          <span>A <b className="text-foreground">{fp(L.o)}</b></span><span>Máx <b className="text-foreground">{fp(L.h)}</b></span>
          <span>Mín <b className="text-foreground">{fp(L.l)}</b></span><span>F <b className={L.c! >= L.o! ? 'text-up' : 'text-down'}>{fp(L.c)}</b></span>
          {L.n != null && <span>trades <b className="text-foreground">{L.n}</b></span>}
        </>}
      </div>
      <div ref={ref} style={{ height }} className="w-full" />
    </div>
  )
}
