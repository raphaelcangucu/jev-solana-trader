import { ColorType, CrosshairMode, type DeepPartial, type ChartOptions, type UTCTimestamp } from 'lightweight-charts'

/** Charts display BRT wall-clock: lightweight-charts renders UTC, so shift epoch by −3h. */
export const BRT_SHIFT = -3 * 3600
export const toChartTime = (ts: number) => (ts + BRT_SHIFT) as UTCTimestamp

export function baseOptions(height: number): DeepPartial<ChartOptions> {
  return {
    height,
    autoSize: true,
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b95a7', fontSize: 11, attributionLogo: false },
    grid: { vertLines: { color: 'rgba(148,163,184,0.06)' }, horzLines: { color: 'rgba(148,163,184,0.06)' } },
    rightPriceScale: { borderColor: 'rgba(148,163,184,0.15)' },
    timeScale: { borderColor: 'rgba(148,163,184,0.15)', timeVisible: true, secondsVisible: false },
    crosshair: { mode: CrosshairMode.Normal },
    localization: { locale: 'pt-BR' },
  }
}
