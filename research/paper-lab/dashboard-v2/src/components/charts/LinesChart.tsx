// Gráfico de várias linhas num eixo só (lightweight-charts): patrimônio normalizado, 1000 = início.
// Rótulos diretos no fim das linhas quando cabem (sem empurrar rótulo para longe da linha), cursor com régua vertical e
// tooltip com todas as linhas na data. Carregado sob demanda (chunk "charts").
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ColorType, CrosshairMode, LineSeries, LineStyle, createChart,
  type IChartApi, type ISeriesApi, type UTCTimestamp,
} from 'lightweight-charts'
import { placeEndLabels, type LineStyleKey } from '@/lib/history'
import { cssVar, useThemeMode } from '@/lib/theme'
import { useMedia } from '@/lib/useMedia'
import { LineKey } from './LineKey'
import { cn } from '@/lib/utils'

export interface ChartLine { id: string; label: string; color: string; style: LineStyleKey; width?: 1 | 2 | 3; data: (number | null)[] }

const BRT_SHIFT = -3 * 3600
const toTime = (ts: number) => (ts + BRT_SHIFT) as UTCTimestamp
const resolve = (c: string) => (c.startsWith('var(') ? cssVar(c.slice(4, -1)) : c)
const STYLE: Record<LineStyleKey, LineStyle> = { solid: LineStyle.Solid, dotted: LineStyle.Dotted, dashed: LineStyle.Dashed, longdash: LineStyle.LargeDashed }
const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const dayLabel = (ts: number) => { const d = new Date((ts + BRT_SHIFT) * 1000); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}` }

interface Hover { x: number; t: number; rows: { id: string; v: number }[] }
interface EndLabel { id: string; y: number }

export default function LinesChart({ t, lines, height = 420, format, valueNote, ariaLabel, endLabels = true, baseline }: {
  t: number[]; lines: ChartLine[]; height?: number
  /** eixo e tooltip */
  format: (v: number) => string
  /** texto secundário do valor (ex.: "+8,4%") */
  valueNote?: (v: number) => string
  ariaLabel: string; endLabels?: boolean
  /** linha de referência horizontal (1000 = início) */
  baseline?: number
}) {
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const series = useRef(new Map<string, ISeriesApi<'Line'>>())
  const [hover, setHover] = useState<Hover | null>(null)
  const [labels, setLabels] = useState<EndLabel[]>([])
  const mode = useThemeMode()
  const wide = useMedia('(min-width: 640px)')
  const xl = useMedia('(min-width: 1100px)')
  const gutter = endLabels && wide ? (xl ? 200 : 156) : 0
  const fmt = useRef(format); fmt.current = format
  const byId = useMemo(() => new Map(lines.map(l => [l.id, l])), [lines])
  const last = useMemo(() => new Map(lines.map(l => {
    for (let i = l.data.length - 1; i >= 0; i--) { const v = l.data[i]; if (v != null && Number.isFinite(v)) return [l.id, v] as const }
    return [l.id, null] as const
  })), [lines])
  const sig = useMemo(() => `${t.length}:${t[0]}:${t[t.length - 1]}|` + lines.map(l => `${l.id}:${l.color}:${l.style}:${l.data.length}`).join('|'), [t, lines])

  const relabel = useCallback(() => {
    const c = chart.current
    if (!c || !gutter) { setLabels([]); return }
    const items = lines.map((l, i) => {
      const s = series.current.get(l.id), v = last.get(l.id)
      const y = s && v != null ? s.priceToCoordinate(v) : null
      return { id: l.id, y: y == null ? null : Number(y), priority: i }
    })
    const plotH = height - (c.timeScale().height() || 26)
    const kept = placeEndLabels(items, 17, 6, plotH - 4)
    setLabels([...kept.entries()].map(([id, y]) => ({ id, y })))
  }, [lines, last, gutter, height])
  const relabelRef = useRef(relabel); relabelRef.current = relabel

  useEffect(() => {
    if (!box.current) return
    const ink3 = cssVar('--ink-3'), rule = cssVar('--rule')
    const c = createChart(box.current, {
      height, autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: ink3, fontSize: 11, fontFamily: '"Archivo Variable", system-ui, sans-serif', attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: rule } },
      leftPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.06, bottom: 0.06 } },
      rightPriceScale: { visible: false },
      timeScale: { borderVisible: false, timeVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: ink3, width: 1, style: LineStyle.Solid, labelVisible: false }, horzLine: { visible: false, labelVisible: false } },
      localization: { locale: 'pt-BR', priceFormatter: (v: number) => fmt.current(v) },
      handleScale: { mouseWheel: false, pinch: true }, handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
    })
    chart.current = c
    c.subscribeCrosshairMove(p => {
      if (!p.time || !p.point) { setHover(null); return }
      const rows: Hover['rows'] = []
      series.current.forEach((s, id) => { const d = p.seriesData.get(s) as { value?: number } | undefined; if (d?.value != null) rows.push({ id, v: d.value }) })
      rows.sort((a, b) => b.v - a.v)
      setHover({ x: p.point.x, t: (p.time as number) - BRT_SHIFT, rows })
    })
    const onRange = () => requestAnimationFrame(() => relabelRef.current())
    c.timeScale().subscribeVisibleLogicalRangeChange(onRange)
    const ro = new ResizeObserver(onRange)
    ro.observe(box.current)
    const map = series.current
    return () => { ro.disconnect(); c.remove(); chart.current = null; map.clear() }
  }, [height, mode])

  useEffect(() => {
    const c = chart.current
    if (!c) return
    const map = series.current
    map.forEach(s => c.removeSeries(s)); map.clear()
    const surface = cssVar('--surface')
    // desenha de trás para frente: benchmarks e linhas finais por baixo, a primeira linha da lista por cima
    ;[...lines].reverse().forEach(l => {
      const s = c.addSeries(LineSeries, {
        color: resolve(l.color), lineWidth: l.width ?? 2, lineStyle: STYLE[l.style], priceScaleId: 'left',
        priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerRadius: 4, crosshairMarkerBorderColor: surface, crosshairMarkerBorderWidth: 2,
        priceFormat: { type: 'custom', formatter: (v: number) => fmt.current(v), minMove: 0.01 },
      })
      const data: { time: UTCTimestamp; value: number }[] = []
      for (let i = 0; i < t.length; i++) {
        const v = l.data[i]
        if (v == null || !Number.isFinite(v)) continue
        const tt = toTime(t[i])
        if (data.length && tt <= data[data.length - 1].time) continue
        data.push({ time: tt, value: v })
      }
      s.setData(data)
      map.set(l.id, s)
    })
    const first = lines.length ? map.get(lines[lines.length - 1].id) : undefined
    if (first && baseline != null) first.createPriceLine({ price: baseline, color: cssVar('--rule-strong'), lineWidth: 1, lineStyle: LineStyle.Solid, axisLabelVisible: false })
    c.timeScale().fitContent()
    // o gráfico só sabe as coordenadas depois de desenhar a escala nova: mede no próximo quadro e de novo logo depois
    const raf = requestAnimationFrame(() => relabelRef.current())
    const tm = setTimeout(() => relabelRef.current(), 80)
    return () => { cancelAnimationFrame(raf); clearTimeout(tm) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, mode, baseline])

  useEffect(() => { requestAnimationFrame(() => relabelRef.current()) }, [gutter, relabel])

  const boxW = box.current?.clientWidth ?? 0
  const tipLeft = hover ? (hover.x > boxW / 2 ? undefined : hover.x + 16) : undefined
  const tipRight = hover && hover.x > boxW / 2 ? Math.max(0, boxW - hover.x + 16) + gutter : undefined
  return (
    <figure className="relative m-0" aria-label={ariaLabel} onMouseLeave={() => setHover(null)}>
      <div className="relative" style={{ paddingRight: gutter }}>
        <div ref={box} style={{ height }} className="w-full" />
        {gutter > 0 && (
          <div aria-hidden className="pointer-events-none absolute inset-y-0 right-0" style={{ width: gutter }}>
            {labels.map(lb => {
              const l = byId.get(lb.id), v = last.get(lb.id)
              if (!l || v == null) return null
              return (
                <span key={lb.id} className="absolute left-1.5 flex max-w-full -translate-y-1/2 items-center gap-1.5 whitespace-nowrap text-[11.5px] leading-none" style={{ top: lb.y }}>
                  <LineKey color={l.color} style={l.style} w={10} />
                  <span className="min-w-0 truncate text-ink-2">{l.label}</span>
                  <span className="t-tab text-ink-3">{valueNote ? valueNote(v) : format(v)}</span>
                </span>
              )
            })}
          </div>
        )}
        {hover && hover.rows.length > 0 && (
          <div role="status" aria-live="off"
            className="pointer-events-none absolute top-2 z-10 w-[min(330px,calc(100%-24px))] rounded-lg border border-rule-strong bg-surface px-3 py-2.5 text-[12.5px] shadow-[var(--shadow)]"
            style={{ left: tipLeft, right: tipRight }}>
            <p className="mb-1.5 t-semi text-ink">{dayLabel(hover.t)}</p>
            <ul className="grid gap-[3px]">
              {hover.rows.map(r => {
                const l = byId.get(r.id)
                if (!l) return null
                return (
                  <li key={r.id} className={cn('grid grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-2', l.style !== 'solid' && 'text-ink-3')}>
                    <LineKey color={l.color} style={l.style} />
                    <span className="truncate text-ink-2">{l.label}</span>
                    <span className="t-tab text-right text-ink">{format(r.v)}{valueNote && <span className="ml-1.5 text-ink-3">{valueNote(r.v)}</span>}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </figure>
  )
}
