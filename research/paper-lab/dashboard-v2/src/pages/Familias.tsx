// Pequenos múltiplos: um painel por família, mesma escala em todos; o melhor de cada família em destaque.
import { useMemo, useState } from 'react'
import { FilterBar } from '@/components/FilterBar'
import { Chip, Delta, ErrorNote, Loading, Mark, Note } from '@/components/ui'
import type { Sparks } from '@/lib/api'
import { matches, median, sortEntries, type Entry, type FamilyFilter } from '@/lib/board'
import { FAMILIES } from '@/lib/describe'
import { useFilters } from '@/lib/filters'
import { signedPct } from '@/lib/format'
import { useEntries, useSparks } from '@/lib/queries'
import { openPortfolio } from '@/lib/router'

const PANELS: { key: FamilyFilter; label: string; color: string; what: string }[] = [
  { key: 'von', label: 'Modelos von', color: 'var(--fam-von)', what: 'o classificador von com os portões do artigo, relaxado e v2' },
  { key: 'laya', label: 'Laya', color: 'var(--fam-laya)', what: 'o modelo Laya com os mesmos portões' },
  { key: 'poorjev', label: 'poorjev', color: 'var(--fam-poorjev)', what: 'o modelo poorjev com os mesmos portões' },
  { key: 'rules', label: 'Regras', color: 'var(--fam-rules)', what: 'regras clássicas sem modelo: grade, RSI, regime, Donchian' },
  { key: 'hybrid', label: 'Híbridos', color: 'var(--fam-hybrid)', what: 'modelo + filtro de regime de SOL' },
  { key: 'lab', label: 'Hipóteses', color: 'var(--fam-lab)', what: 'H1 saídas, H2 ensemble, H3 ordens limite, H4 horários e o teto de exposição' },
  { key: 'forks', label: 'Forks', color: 'var(--ink-2)', what: 'cópias criadas pelo ajuste noturno' },
]

const W = 400, H = 150, PAD_L = 46, PAD_R = 8, PAD_T = 8, PAD_B = 18

function Panel({ p, members, sparks, lo, hi }: { p: (typeof PANELS)[number]; members: Entry[]; sparks?: Sparks; lo: number; hi: number }) {
  const [hot, setHot] = useState<{ name: string; v: number } | null>(null)
  const ranked = sortEntries(members, 'lucro')
  const best = ranked[0], worst = ranked[ranked.length - 1]
  const med = median(members.map(m => m.pnlPct).filter((x): x is number => x != null))
  const beat = members.filter(m => (m.vsHoldPct ?? 0) > 0).length
  const y = (v: number) => PAD_T + (1 - (v - lo) / (hi - lo)) * (H - PAD_T - PAD_B)
  const lines = members.map(m => ({ e: m, s: sparks?.[m.row.name] })).filter(x => x.s && x.s.v.length > 1)
  const x = (i: number, n: number) => PAD_L + (i / (n - 1)) * (W - PAD_L - PAD_R)
  const path = (v: number[]) => v.map((val, i) => `${i ? 'L' : 'M'}${x(i, v.length).toFixed(1)},${y(val).toFixed(1)}`).join('')
  const onMove = (ev: React.PointerEvent<SVGSVGElement>) => {
    const r = ev.currentTarget.getBoundingClientRect()
    const px = ((ev.clientX - r.left) / r.width) * W, py = ((ev.clientY - r.top) / r.height) * H
    let bestD = Infinity, pick: { name: string; v: number } | null = null
    for (const l of lines) {
      const v = l.s!.v
      const i = Math.max(0, Math.min(v.length - 1, Math.round(((px - PAD_L) / (W - PAD_L - PAD_R)) * (v.length - 1))))
      const d = Math.abs(y(v[i]) - py)
      if (d < bestD) { bestD = d; pick = { name: l.e.row.name, v: v[i] } }
    }
    setHot(bestD < 24 ? pick : null)
  }
  const hotE = hot ? members.find(m => m.row.name === hot.name) : null
  const fmtAxis = (v: number) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
  return (
    <section className="sheet flex flex-col rounded-xl p-4 sm:p-5" aria-label={`Família ${p.label}`}>
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="t-title flex items-center gap-2 text-[19px]"><i aria-hidden className="inline-block size-2.5 rounded-full" style={{ background: p.color }} />{p.label}</h3>
        <span className="text-[12.5px] text-ink-3 t-tab">{members.length} {members.length === 1 ? 'teste' : 'testes'}</span>
      </header>
      <p className="mt-0.5 text-[13px] text-ink-2">{p.what}</p>
      <div className="mt-3 grid grid-cols-3 gap-3 border-y border-rule py-2.5 text-[12.5px]">
        <div><div className="text-ink-3">Mediana</div><Delta v={med} className="t-num text-[17px]">{signedPct(med)}</Delta></div>
        <div><div className="text-ink-3">Batem segurar</div><div className="t-num text-[17px]">{beat} <span className="text-ink-3">de {members.length}</span></div></div>
        <div><div className="text-ink-3">Pior</div><Delta v={worst?.pnlPct} className="t-num text-[17px]">{signedPct(worst?.pnlPct)}</Delta></div>
      </div>
      {best && (
        <p className="mt-3 text-[14px] leading-snug">
          <span className="mr-1.5 text-ink-3">Melhor:</span>
          <button type="button" className="rounded-sm text-left hover:underline hover:underline-offset-4" onClick={() => openPortfolio(best.row.name)}>
            <Mark on={(best.pnlPct ?? 0) >= 0.05}><span className="t-semi">{best.d.title}</span></Mark>
          </button>{' '}
          <Chip className="translate-y-[-1px]">{best.d.asset}</Chip>{' '}
          <Delta v={best.pnlPct} className="t-num">{signedPct(best.pnlPct)}</Delta>
        </p>
      )}
      <div className="relative mt-2">
        <p className="min-h-[19px] text-[12.5px] text-ink-2 t-tab" aria-live="polite">
          {hotE ? <><b className="text-ink t-semi">{signedPct(hot!.v)}</b> {hotE.d.title} <span className="text-ink-3">({hotE.d.asset})</span></> : <span className="sr-only">Passe o mouse numa curva para ver o nome.</span>}
        </p>
        <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full touch-none" role="img" aria-label={`Curvas da família ${p.label} em % desde o início; melhor: ${best?.d.title ?? 'nenhum'}`}
          onPointerMove={onMove} onPointerLeave={() => setHot(null)}
          onClick={() => hot && openPortfolio(hot.name)} style={{ cursor: hot ? 'pointer' : 'default' }}>
          {[hi, 0, lo].map(v => (
            <g key={v}>
              <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)} stroke={v === 0 ? 'var(--rule-strong)' : 'var(--rule)'} strokeWidth={1} vectorEffect="non-scaling-stroke" />
              <text x={PAD_L - 5} y={y(v) + 3.5} textAnchor="end" fontSize="10" fill="var(--ink-3)" style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtAxis(v)}</text>
            </g>
          ))}
          <text x={PAD_L} y={H - 4} fontSize="10" fill="var(--ink-3)">início</text>
          <text x={W - PAD_R} y={H - 4} fontSize="10" fill="var(--ink-3)" textAnchor="end">agora</text>
          {lines.filter(l => l.e !== best && l.e.row.name !== hot?.name).map(l => (
            <path key={l.e.row.name} d={path(l.s!.v)} fill="none" stroke="var(--ink-3)" strokeOpacity={0.42} strokeWidth={1.1} vectorEffect="non-scaling-stroke" />
          ))}
          {lines.filter(l => l.e === best).map(l => (
            <path key="best" d={path(l.s!.v)} fill="none" stroke={p.color} strokeWidth={2.2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          ))}
          {hot && hot.name !== best?.row.name && lines.filter(l => l.e.row.name === hot.name).map(l => (
            <path key="hot" d={path(l.s!.v)} fill="none" stroke="var(--ink)" strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          ))}
        </svg>
      </div>
    </section>
  )
}

export default function Familias() {
  const { ov, entries } = useEntries()
  const sparks = useSparks()
  const f = useFilters()
  const visible = useMemo(() => entries.filter(e => matches(e, 'all', f.asset, f.q)), [entries, f.asset, f.q])
  const panels = useMemo(() => PANELS
    .filter(p => f.fam === 'all' || f.fam === p.key)
    .map(p => ({ p, members: visible.filter(e => (p.key === 'forks' ? e.d.isFork : !e.d.isFork && e.d.family === p.key)) }))
    .filter(x => x.members.length), [visible, f.fam])
  const [lo, hi] = useMemo(() => {
    const all = panels.flatMap(x => x.members.flatMap(m => sparks.data?.[m.row.name]?.v ?? []))
    if (!all.length) return [-1, 1]
    const a = Math.min(-0.5, ...all), b = Math.max(0.5, ...all)
    const pad = (b - a) * 0.06
    return [a - pad, b + pad]
  }, [panels, sparks.data])
  if (ov.isLoading) return <Loading h={520} />
  if (ov.error && !ov.data) return <ErrorNote error={ov.error} what="famílias" />
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
        <h1 className="t-title text-[26px]">Famílias</h1>
        <p className="max-w-[620px] text-[13.5px] text-ink-2">Cada curva é um teste, em % desde o início. Todos os painéis usam a mesma escala, para dar para comparar alturas. O melhor de cada família fica colorido.</p>
      </div>
      <FilterBar showSort={false} count={visible.length} total={entries.length} />
      {!FAMILIES.length || !panels.length ? <Note>Nenhum teste com esses filtros.</Note> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {panels.map(x => <Panel key={x.p.key} p={x.p} members={x.members} sparks={sparks.data} lo={lo} hi={hi} />)}
        </div>
      )}
    </div>
  )
}
