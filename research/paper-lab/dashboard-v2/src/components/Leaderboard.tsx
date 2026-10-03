// O placar: uma linha por teste, nomes humanos, top 3 da ordenação ativa com marca-texto.
import { memo, useMemo } from 'react'
import type { Sparks } from '@/lib/api'
import { metric, type Entry, type SortKey } from '@/lib/board'
import { familyOf } from '@/lib/describe'
import { int, pct, pval, signedPct, smartUsd } from '@/lib/format'
import { openPortfolio } from '@/lib/router'
import { cn } from '@/lib/utils'
import { Diverging, Sparkline, VerdictProgress } from './marks'
import { Chip, Delta, Mark, Meter, Tip } from './ui'

// rank | nome | curva | lucro | vs segurar | habilidade | exposição | C/V | veredito
const GRID = 'grid grid-cols-[22px_minmax(0,1fr)_82px_78px] gap-x-2 sm:gap-x-3 md:grid-cols-[30px_minmax(0,1fr)_96px_92px_minmax(104px,128px)_100px] lg:grid-cols-[34px_minmax(210px,1.6fr)_108px_100px_minmax(124px,1fr)_112px_72px_58px_92px] lg:gap-x-4'

function Head({ sort, onSort }: { sort: SortKey; onSort: (k: SortKey) => void }) {
  const H = ({ k, children, className }: { k?: SortKey; children: React.ReactNode; className?: string }) => (
    <div role="columnheader" aria-sort={k && sort === k ? 'descending' : undefined} className={cn('flex items-end', className)}>
      {k ? (
        <button type="button" onClick={() => onSort(k)} className={cn('rounded-sm text-left hover:text-ink', sort === k && 'text-ink t-semi')}>
          {children}{sort === k && <span aria-hidden className="ml-1 text-[10px]">▼</span>}
        </button>
      ) : children}
    </div>
  )
  return (
    <div role="row" className={cn(GRID, 'sticky top-[104px] z-10 border-b border-rule-strong bg-surface px-3 pb-2 pt-3 text-[12.5px] leading-tight text-ink-3 sm:px-4 lg:top-[56px]')}>
      <H><span className="sr-only">Posição</span>#</H>
      <H>Teste</H>
      <H className="hidden md:flex">Curva</H>
      <H k="lucro" className="justify-end text-right">Lucro</H>
      <H k="segurar" className="hidden md:flex">Vs. segurar</H>
      <H k="habilidade" className="justify-end text-right sm:justify-start sm:text-left">Habilidade</H>
      <H className="hidden lg:flex">Exposição</H>
      <H className="hidden lg:flex">Compras / vendas</H>
      <H className="hidden lg:flex">Rumo ao veredito</H>
    </div>
  )
}

const LeaderRow = memo(function LeaderRow({ e, rank, top, spark, holdMax, sweep }: { e: Entry; rank: number; top: boolean; spark?: Sparks[string]; holdMax: number; sweep: boolean }) {
  const fam = familyOf(e.d.family)
  const paused = e.row.paused || e.row.params_brief?.paused
  return (
    <div role="row" onClick={() => openPortfolio(e.row.name)}
      className={cn(GRID, 'group cursor-pointer items-center border-b border-rule px-3 py-2.5 hover:bg-[color-mix(in_srgb,var(--sunk)_55%,transparent)] sm:px-4', top && 'py-3.5')}
      style={{ contentVisibility: 'auto', containIntrinsicSize: 'auto 64px' }}>
      <div role="cell" className={cn('t-num text-ink-3', top ? 'text-[19px] text-ink' : 'text-[14px]')}>{rank}</div>
      <div role="cell" className="min-w-0">
        <button type="button" onClick={ev => { ev.stopPropagation(); openPortfolio(e.row.name) }}
          className={cn('max-w-full rounded-sm text-left leading-tight lg:-ml-[0.35em] lg:truncate lg:pl-[0.35em] lg:pr-[0.4em]', top ? 't-title text-[17px] sm:text-[18px]' : 't-semi text-[15px]')}
          title={`${e.d.title} (${e.row.name})`}>
          <Mark on={top} sweep={sweep}>{e.d.title}</Mark>
        </button>
        <div className="mt-1 flex min-w-0 flex-wrap items-center gap-1">
          <Chip>{e.d.asset}</Chip>
          <Chip color={fam.color}>{e.d.tag}</Chip>
          {paused && <Chip className="border-ink-3 text-ink">pausado</Chip>}
        </div>
      </div>
      <div role="cell" className="hidden md:block"><Sparkline s={spark} label={e.d.title} w={92} /></div>
      <div role="cell" className="text-right">
        <Delta v={e.pnlPct} className={cn('t-num block leading-tight max-sm:[font-stretch:100%]', top ? 'text-[17px] sm:text-[21px]' : 'text-[16px] sm:text-[18px]')}>{signedPct(e.pnlPct, e.pnlPct != null && Math.abs(e.pnlPct) < 10 ? 2 : 1)}</Delta>
        <span className="block text-[12px] text-ink-3 t-tab">{smartUsd(e.pnlUsd, true)}</span>
      </div>
      <div role="cell" className="hidden items-center gap-2 md:flex">
        <Diverging v={e.vsHoldPct} max={holdMax} w={58} />
        <Delta v={e.vsHoldPct} arrowOn={false} className="t-tab text-[13px]">{signedPct(e.vsHoldPct)}</Delta>
      </div>
      <div role="cell" className="text-right sm:text-left">
        <Delta v={e.skillUsd} className="t-num block text-[14px] leading-tight max-sm:[font-stretch:100%] sm:text-[16px]">{e.skillUsd == null ? '—' : smartUsd(e.skillUsd, true)}</Delta>
        {e.timingP != null ? (
          <Tip content="p do placebo de timing: chance de um resultado assim só por sorte. Abaixo de 0,05 começa a ser interessante.">
            <span className={cn('block text-[12px] t-tab', e.timingP < 0.05 ? 'text-ink t-semi' : 'text-ink-3')}>{pval(e.timingP)}</span>
          </Tip>
        ) : <span className="block text-[12px] text-ink-3">sem timing</span>}
      </div>
      <div role="cell" className="hidden lg:block">
        <span className="mb-1 block text-[12.5px] text-ink-2 t-tab">{pct(e.exposure, 0)}</span>
        <Meter value={e.exposure} label={`Exposição média ${pct(e.exposure, 0)}`} />
      </div>
      <div role="cell" className="hidden text-[13px] text-ink-2 t-tab lg:block">{e.buys == null ? '—' : `${int(e.buys)} / ${int(e.sells)}`}</div>
      <div role="cell" className="hidden lg:block">
        <VerdictProgress days={e.days} minDays={e.minDays} rt={e.rt} minRt={e.minRt} verdict={e.row.verdict} />
      </div>
    </div>
  )
})

export function Leaderboard({ entries, sort, onSort, sparks, firstPaint }: { entries: Entry[]; sort: SortKey; onSort: (k: SortKey) => void; sparks?: Sparks; firstPaint: boolean }) {
  const holdMax = useMemo(() => Math.max(1, ...entries.map(e => Math.abs(e.vsHoldPct ?? 0))), [entries])
  const firstWithValue = entries.findIndex(e => metric(e, sort) != null)
  return (
    <div role="table" aria-label="Placar dos testes" aria-rowcount={entries.length + 1} className="sheet rounded-xl">
      <Head sort={sort} onSort={onSort} />
      <div role="rowgroup">
        {entries.map((e, i) => (
          <LeaderRow key={e.row.name} e={e} rank={i + 1} top={i < 3 && firstWithValue === 0 && (metric(e, sort) ?? 0) > 0} spark={sparks?.[e.row.name]} holdMax={holdMax} sweep={firstPaint && i < 3} />
        ))}
      </div>
    </div>
  )
}
