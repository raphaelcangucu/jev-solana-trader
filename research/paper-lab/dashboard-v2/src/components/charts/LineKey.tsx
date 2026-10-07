// Chave de linha (legenda, tooltip, tabela): espelha o traço da série, cheio, tracejado ou pontilhado. Sem lightweight-charts.
import type { LineStyleKey } from '@/lib/history'

const DASH: Record<LineStyleKey, string> = { solid: 'none', dotted: '1.5 3', dashed: '5 3', longdash: '9 4' }

/** A chave de linha da legenda/tooltip espelha o traço (cheio, tracejado, pontilhado). */
export function LineKey({ color, style, w = 18 }: { color: string; style: LineStyleKey; w?: number }) {
  return (
    <svg aria-hidden width={w} height="6" className="shrink-0 overflow-visible">
      <line x1="1" y1="3" x2={w - 1} y2="3" style={{ stroke: color }} strokeWidth={2} strokeDasharray={DASH[style]} strokeLinecap="round" />
    </svg>
  )
}
