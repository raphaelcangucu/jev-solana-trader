// Tiny accessible SVG histogram (confidence distributions etc).
export function Histogram({ bins, height = 90, color = '#60a5fa', thresholds = [], label }: { bins: number[]; height?: number; color?: string; thresholds?: { at: number; label: string; color?: string }[]; label: string }) {
  const max = Math.max(1, ...bins)
  const total = bins.reduce((a, b) => a + b, 0)
  const w = 100 / bins.length
  return (
    <figure className="w-full">
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }} role="img" aria-label={`${label}: ${total} decisões`}>
        {bins.map((b, i) => {
          const h = (b / max) * (height - 12)
          return <rect key={i} x={i * w + 0.3} y={height - 10 - h} width={w - 0.6} height={h} fill={color} opacity={0.85}><title>{`${(i / bins.length).toFixed(2)}–${((i + 1) / bins.length).toFixed(2)}: ${b}`}</title></rect>
        })}
        {thresholds.map(t => (
          <g key={t.label}>
            <line x1={t.at * 100} x2={t.at * 100} y1={0} y2={height - 10} stroke={t.color || '#fbbf24'} strokeWidth={0.4} strokeDasharray="1.5 1" vectorEffect="non-scaling-stroke" />
          </g>
        ))}
        <line x1={0} x2={100} y1={height - 10} y2={height - 10} stroke="rgba(148,163,184,.3)" strokeWidth={0.3} />
      </svg>
      <figcaption className="mt-0.5 flex justify-between text-[10px] text-muted-foreground num">
        <span>0</span>
        {thresholds.map(t => <span key={t.label} style={{ color: t.color || '#fbbf24' }}>{t.label}</span>)}
        <span>1.0 · n={total}</span>
      </figcaption>
    </figure>
  )
}
