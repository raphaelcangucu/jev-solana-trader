// Distinguishable series palette (dark background). Stable per name via hash.
export const PALETTE = ['#60a5fa', '#34d399', '#f472b6', '#fbbf24', '#a78bfa', '#22d3ee', '#fb7185', '#a3e635', '#f97316', '#c084fc', '#2dd4bf', '#facc15', '#93c5fd', '#e879f9', '#4ade80', '#fda4af']
const FIXED: Record<string, string> = { baseline: '#60a5fa', relaxed: '#34d399', v2: '#f472b6', laya_baseline: '#a78bfa', laya_relaxed: '#c4b5fd', poorjev_baseline: '#fbbf24', poorjev_relaxed: '#fde68a', grid_sol_2pct: '#22d3ee', rsi_sol_1h: '#fb7185', hybrid_von_relaxed_cap2: '#a3e635', p1000: '#60a5fa', p1000_pons: '#f472b6' }
export function colorFor(name: string): string {
  if (FIXED[name]) return FIXED[name]
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}
export const UP = '#22c55e'
export const DOWN = '#ef4444'
