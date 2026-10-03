// Virtualized, sortable ranking of all portfolios (100+ rows).
// Patterns: FreqUI multi-bot overview list, OpenBB dense data tables (tabular numerals, compact rows).
import { useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, Pause, Search } from 'lucide-react'
import type { Row } from '@/lib/api'
import { Badge } from './ui/badge'
import { Input } from './ui/input'
import { Pnl, VerdictBadge, VerdictProgress } from './common'
import { num, pct, usd } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useDrawer } from './drawer-context'
import { useMedia } from '@/lib/useMedia'

type Key = 'rank' | 'name' | 'equity' | 'pnl' | 'vs_bh' | 'vs_usdt' | 'trades' | 'exposure_pct' | 'max_dd_pct' | 'verdict'
const COLS: { key: Key; label: string; align?: 'right'; title?: string }[] = [
  { key: 'rank', label: '#' },
  { key: 'name', label: 'Portfólio' },
  { key: 'equity', label: 'Valor', align: 'right' },
  { key: 'pnl', label: 'PnL', align: 'right' },
  { key: 'vs_bh', label: 'vs B&H', align: 'right', title: 'Diferença para buy-and-hold do mesmo ativo desde o início do portfólio' },
  { key: 'vs_usdt', label: 'vs USDT', align: 'right', title: 'Diferença para ficar 100% em USDT' },
  { key: 'trades', label: 'Trades', align: 'right' },
  { key: 'exposure_pct', label: 'Exposição', align: 'right' },
  { key: 'max_dd_pct', label: 'Max DD', align: 'right' },
  { key: 'verdict', label: 'Veredito · progresso' },
]
const GRID = 'grid grid-cols-[2.5rem_minmax(14rem,1.8fr)_6.5rem_8.5rem_7.5rem_6.5rem_4rem_5.5rem_5rem_minmax(11rem,1fr)] items-center gap-x-3'
const GROUPS = [{ id: 'all', label: 'Todos' }, { id: 'sol', label: 'SOL' }, { id: 'meme', label: 'Memes' }, { id: 'lab', label: 'Lab' }] as const

export function RankingTable({ rows, height = 520, defaultGroup = 'all' }: { rows: Row[]; height?: number; defaultGroup?: 'all' | 'sol' | 'meme' | 'lab' }) {
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'vs_bh', dir: -1 })
  const [group, setGroup] = useState<string>(defaultGroup)
  const [q, setQ] = useState('')
  const { open } = useDrawer()
  const parentRef = useRef<HTMLDivElement>(null)
  const desktop = useMedia('(min-width: 768px)')

  const ranked = useMemo(() => {
    // rank = by vs B&H %, independent of current sort
    const byBh = [...rows].sort((a, b) => (b.vs_bh_pct ?? -1e9) - (a.vs_bh_pct ?? -1e9) || a.name.localeCompare(b.name))
    const rk = new Map(byBh.map((r, i) => [r.name, i + 1]))
    return rows.map(r => ({ ...r, rank: rk.get(r.name)! }))
  }, [rows])

  const view = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const f = ranked.filter(r => (group === 'all' || r.group === group) && (!ql || `${r.name} ${r.asset} ${r.model} ${r.strategy} ${r.label || ''}`.toLowerCase().includes(ql)))
    const k = sort.key
    const val = (r: any) => k === 'verdict' ? (r.verdict === 'vencedora' ? 2 : r.verdict === 'perdedora' ? 0 : 1) * 1000 + (r.progress?.closed_rt ?? 0)
      : k === 'name' ? r.name : k === 'pnl' ? r.pnl_pct : k === 'vs_bh' ? r.vs_bh_pct : r[k]
    return f.sort((a, b) => {
      const va = val(a), vb = val(b)
      if (typeof va === 'string') return va.localeCompare(vb) * sort.dir
      return ((va ?? -Infinity) - (vb ?? -Infinity)) * sort.dir || a.name.localeCompare(b.name)
    })
  }, [ranked, group, q, sort])

  const v = useVirtualizer({ count: view.length, getScrollElement: () => parentRef.current, estimateSize: () => (desktop ? 48 : 76), overscan: 12 })
  useEffect(() => { v.measure() }, [desktop, v])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Filtrar grupo" className="inline-flex rounded-lg bg-muted p-0.5">
          {GROUPS.map(g => (
            <button key={g.id} role="radio" aria-checked={group === g.id} onClick={() => setGroup(g.id)}
              className={cn('rounded-md px-2.5 py-1 text-xs font-medium', group === g.id ? 'bg-background text-foreground shadow' : 'text-muted-foreground hover:text-foreground')}>
              {g.label} <span className="num opacity-60">{g.id === 'all' ? rows.length : rows.filter(r => r.group === g.id).length}</span>
            </button>
          ))}
        </div>
        {!desktop && (
          <select aria-label="Ordenar por" value={`${sort.key}:${sort.dir}`} onChange={e => { const [k, d] = e.target.value.split(':'); setSort({ key: k as Key, dir: Number(d) as 1 | -1 }) }}
            className="h-8 rounded-md border bg-background px-2 text-xs">
            {COLS.filter(c => c.key !== 'rank').flatMap(c => [<option key={c.key + '-1'} value={`${c.key}:-1`}>{c.label} ↓</option>, <option key={c.key + '1'} value={`${c.key}:1`}>{c.label} ↑</option>])}
          </select>
        )}
        <div className="relative ml-auto w-full sm:w-64">
          <Search className="pointer-events-none absolute left-2 top-2.5 size-4 text-muted-foreground" aria-hidden />
          <Input aria-label="Buscar portfólio" placeholder="Buscar (nome, ativo, modelo)…" value={q} onChange={e => setQ(e.target.value)} className="pl-8" />
        </div>
      </div>
      {desktop ? (<>
      <div className="rounded-xl border bg-card">
        <div ref={parentRef} className="overflow-auto" style={{ height }} role="table" aria-label="Ranking de portfólios" aria-rowcount={view.length + 1}>
          <div className="min-w-[1080px]">
            <div role="row" className={cn(GRID, 'sticky top-0 z-10 border-b bg-card/95 px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground backdrop-blur')}>
              {COLS.map(c => (
                <div key={c.key} role="columnheader" aria-sort={sort.key === c.key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'} className={c.align === 'right' ? 'text-right' : ''}>
                  <button title={c.title} className="inline-flex items-center gap-0.5 hover:text-foreground" onClick={() => setSort(s => ({ key: c.key, dir: s.key === c.key ? (s.dir === 1 ? -1 : 1) : (c.key === 'name' || c.key === 'rank' ? 1 : -1) }))}>
                    {c.label}{sort.key === c.key && (sort.dir === 1 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
                  </button>
                </div>
              ))}
            </div>
            <div style={{ height: v.getTotalSize(), position: 'relative' }}>
              {v.getVirtualItems().map(vi => {
                const r = view[vi.index]
                return (
                  <div key={r.name} role="row" tabIndex={0} aria-rowindex={vi.index + 2}
                    onClick={() => open(r.name)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(r.name) } }}
                    className={cn(GRID, 'absolute left-0 right-0 cursor-pointer border-b border-border/50 px-3 text-[13px] hover:bg-accent/50 focus-visible:bg-accent/60 focus-visible:outline-none')}
                    style={{ top: 0, transform: `translateY(${vi.start}px)`, height: vi.size }}>
                    <div role="cell" className="text-muted-foreground num">{r.rank}</div>
                    <div role="cell" className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate font-medium" title={r.name}>{r.name}</span>
                        {r.paused && <Badge variant="warn"><Pause className="size-3" />pausado</Badge>}
                      </div>
                      <div className="flex gap-1 text-[10px] text-muted-foreground">
                        <span className="uppercase">{r.group}</span>·<span>{r.asset}</span>·<span className="truncate">{r.model}</span>
                        {r.report_label && <Badge variant="warn" className="py-0">{r.report_label}</Badge>}
                      </div>
                    </div>
                    <div role="cell" className="text-right num">{usd(r.equity)}</div>
                    <div role="cell" className="text-right"><Pnl v={r.pnl} pctV={r.pnl_pct} /></div>
                    <div role="cell" className="text-right"><Pnl v={r.vs_bh} pctV={r.vs_bh_pct} /></div>
                    <div role="cell" className="text-right"><Pnl v={r.vs_usdt} /></div>
                    <div role="cell" className="text-right num">{num(r.trades ?? 0, 0)}</div>
                    <div role="cell" className="text-right num text-muted-foreground">{pct(r.exposure_pct, 0)}</div>
                    <div role="cell" className={cn('text-right num', (r.max_dd_pct ?? 0) > 5 ? 'text-down' : 'text-muted-foreground')}>{pct(r.max_dd_pct, 2)}</div>
                    <div role="cell" className="flex items-center gap-2">
                      <VerdictBadge v={r.verdict} />
                      <VerdictProgress p={r.progress} text={r.progress_text} compact />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
      </>) : (<>
      <div className="rounded-xl border bg-card">
        <div ref={parentRef} className="overflow-auto" style={{ height: Math.min(height, 560) }} role="list" aria-label="Ranking de portfólios">
          <div style={{ height: v.getTotalSize(), position: 'relative' }}>
            {v.getVirtualItems().map(vi => {
              const r = view[vi.index]
              return (
                <div key={r.name} role="listitem" tabIndex={0} onClick={() => open(r.name)} onKeyDown={e => { if (e.key === 'Enter') open(r.name) }}
                  className="absolute left-0 right-0 flex cursor-pointer flex-col justify-center gap-0.5 border-b border-border/50 px-3 text-[13px] active:bg-accent/50"
                  style={{ top: 0, transform: `translateY(${vi.start}px)`, height: vi.size }}>
                  <div className="flex items-center gap-2">
                    <span className="w-6 text-muted-foreground num">{r.rank}</span>
                    <span className="min-w-0 flex-1 truncate font-medium">{r.name}</span>
                    <span className="num">{usd(r.equity)}</span>
                  </div>
                  <div className="flex items-center gap-2 pl-8 text-[11px]">
                    <span className="truncate text-muted-foreground">{r.group.toUpperCase()} · {r.asset} · {num(r.trades ?? 0, 0)} tr</span>
                    <span className="ml-auto">B&H <Pnl v={r.vs_bh} pctV={r.vs_bh_pct} /></span>
                  </div>
                  <div className="flex items-center gap-2 pl-8">
                    <VerdictBadge v={r.verdict} />{r.paused && <Badge variant="warn">pausado</Badge>}
                    <span className="truncate text-[10px] text-muted-foreground num">{r.progress_text}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
      </>)}
      <p className="text-[11px] text-muted-foreground">{view.length} de {rows.length} portfólios · clique numa linha para ver detalhes · # = posição por vs B&H (%)</p>
    </div>
  )
}
