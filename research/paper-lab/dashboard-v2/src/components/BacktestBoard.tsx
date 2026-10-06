// Placar retroativo: mesma folha e mesmas marcas do placar ao vivo, com as colunas que fazem sentido para 30 dias fechados.
import { memo, useMemo } from 'react'
import type { BtVerdict, Sparks } from '@/lib/api'
import { btMetric, isHighlight, type BtEntry, type BtSortKey } from '@/lib/backtest'
import { familyOf } from '@/lib/describe'
import { int, pct, pval, signedPct, smartUsd } from '@/lib/format'
import { openBacktest } from '@/lib/router'
import { cn } from '@/lib/utils'
import { Diverging, Sparkline } from './marks'
import { Chip, Delta, Mark, Tip } from './ui'

// # | teste | curva | lucro | vs segurar | habilidade | maior queda | trades | semanas | veredito
const GRID = 'grid grid-cols-[22px_minmax(0,1fr)_78px_80px] gap-x-2 sm:gap-x-3 md:grid-cols-[30px_minmax(0,1fr)_96px_88px_minmax(104px,128px)_100px] lg:grid-cols-[34px_minmax(200px,1.6fr)_100px_92px_minmax(118px,1fr)_104px_64px_52px_66px_104px] lg:gap-x-4'

export function VerdictChip({ v, className }: { v: BtVerdict; className?: string }) {
  if (v === 'vencedora') return <Chip className={cn('border-gain/50 text-gain t-semi', className)}><span aria-hidden className="text-[9px]">▲</span>vencedora</Chip>
  if (v === 'perdedora') return <Chip className={cn('border-loss/50 text-loss t-semi', className)}><span aria-hidden className="text-[9px]">▼</span>perdedora</Chip>
  return <Chip className={cn('border-dashed text-ink-3', className)}>inconclusiva</Chip>
}

/** Quantas das 4 semanas bateram só segurar (contagem, não posição). */
export function WeekPips({ n, of = 4 }: { n: number | null; of?: number }) {
  if (n == null) return <span className="text-[12px] text-ink-3">—</span>
  return (
    <span className="inline-flex items-center gap-[3px]" role="img" aria-label={`Bateu só segurar em ${n} de ${of} semanas`}>
      {Array.from({ length: of }, (_, i) => (
        <i key={i} aria-hidden className={cn('inline-block size-[9px] rounded-[2px] border', i < n ? 'border-ink bg-ink' : 'border-rule-strong bg-transparent')} />
      ))}
      <span className="ml-1 text-[12px] text-ink-3 t-tab">{n}/{of}</span>
    </span>
  )
}

function Head({ sort, onSort }: { sort: BtSortKey; onSort: (k: BtSortKey) => void }) {
  const H = ({ k, children, className, hint }: { k?: BtSortKey; children: React.ReactNode; className?: string; hint?: string }) => {
    const label = k ? (
      <button type="button" onClick={() => onSort(k)} className={cn('rounded-sm text-left hover:text-ink', sort === k && 'text-ink t-semi')}>
        {children}{sort === k && <span aria-hidden className="ml-1 text-[10px]">▼</span>}
      </button>
    ) : <span>{children}</span>
    return (
      <div role="columnheader" aria-sort={k && sort === k ? 'descending' : undefined} className={cn('flex items-end', className)}>
        {hint ? <Tip content={hint}>{label}</Tip> : label}
      </div>
    )
  }
  return (
    <div role="row" className={cn(GRID, 'sticky top-[104px] z-10 border-b border-rule-strong bg-surface px-3 pb-2 pt-3 text-[12.5px] leading-tight text-ink-3 sm:px-4 lg:top-[56px]')}>
      <H><span className="sr-only">Posição</span>#</H>
      <H>Teste</H>
      <H className="hidden md:flex">Curva</H>
      <H k="lucro" className="justify-end text-right">Lucro</H>
      <H k="segurar" className="hidden md:flex">Vs. segurar</H>
      <H k="habilidade" className="justify-end text-right sm:justify-start sm:text-left">Habilidade</H>
      <H className="hidden lg:flex" hint="Maior queda do pico ao vale nos 30 dias.">Queda</H>
      <H className="hidden lg:flex">Trades</H>
      <H className="hidden lg:flex" hint="Em quantas das 4 semanas a carteira rendeu mais do que só segurar o livro inicial.">Semanas</H>
      <H k="veredito" className="hidden lg:flex">Veredito</H>
    </div>
  )
}

const Row = memo(function Row({ e, rank, top, spark, holdMax, sweep }: { e: BtEntry; rank: number; top: boolean; spark?: Sparks[string]; holdMax: number; sweep: boolean }) {
  const fam = familyOf(e.d.family)
  const open = () => openBacktest(e.p.name)
  return (
    <div role="row" onClick={open}
      className={cn(GRID, 'group cursor-pointer items-center border-b border-rule px-3 py-2.5 hover:bg-[color-mix(in_srgb,var(--sunk)_55%,transparent)] sm:px-4', top && 'py-3.5')}
      style={{ contentVisibility: 'auto', containIntrinsicSize: 'auto 64px' }}>
      <div role="cell" className={cn('t-num text-ink-3', top ? 'text-[19px] text-ink' : 'text-[14px]')}>{rank}</div>
      <div role="cell" className="min-w-0">
        <button type="button" onClick={ev => { ev.stopPropagation(); open() }}
          className={cn('max-w-full rounded-sm text-left leading-tight lg:-ml-[0.35em] lg:truncate lg:pl-[0.35em] lg:pr-[0.4em]', top ? 't-title text-[17px] sm:text-[18px]' : 't-semi text-[15px]')}
          title={`${e.d.title} (${e.p.name})`}>
          <Mark on={top} sweep={sweep}>{e.d.title}</Mark>
        </button>
        <div className="mt-1 flex min-w-0 flex-wrap items-center gap-1">
          <Chip>{e.d.asset}</Chip>
          <Chip color={fam.color}>{e.d.tag}</Chip>
          {e.verdict !== 'inconclusiva' && <VerdictChip v={e.verdict} className="lg:hidden" />}
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
        {e.timingP != null
          ? <span className={cn('block text-[12px] t-tab', e.timingP < 0.05 ? 'text-ink t-semi' : 'text-ink-3')}>{pval(e.timingP)}</span>
          : <span className="block text-[12px] text-ink-3">sem p</span>}
      </div>
      <div role="cell" className="hidden text-[13px] text-ink-2 t-tab lg:block">{e.maxDd == null ? "—" : `−${pct(Math.abs(e.maxDd), 1)}`}</div>
      <div role="cell" className="hidden text-[13px] text-ink-2 t-tab lg:block">{int(e.trades)}</div>
      <div role="cell" className="hidden lg:block"><WeekPips n={e.weeksBeat} /></div>
      <div role="cell" className="hidden lg:block"><VerdictChip v={e.verdict} /></div>
    </div>
  )
})

export function BacktestBoard({ entries, sort, onSort, sparks, firstPaint }: { entries: BtEntry[]; sort: BtSortKey; onSort: (k: BtSortKey) => void; sparks?: Sparks; firstPaint: boolean }) {
  const holdMax = useMemo(() => Math.max(1, ...entries.map(e => Math.abs(e.vsHoldPct ?? 0))), [entries])
  const firstOk = entries.length > 0 && btMetric(entries[0], sort) != null && isHighlight(entries[0], sort)
  return (
    <div role="table" aria-label="Placar da simulação retroativa" aria-rowcount={entries.length + 1} className="sheet rounded-xl">
      <Head sort={sort} onSort={onSort} />
      <div role="rowgroup">
        {entries.map((e, i) => (
          <Row key={e.p.name} e={e} rank={i + 1} top={i < 3 && firstOk && isHighlight(e, sort)} spark={sparks?.[e.p.name]} holdMax={holdMax} sweep={firstPaint && i < 3} />
        ))}
      </div>
    </div>
  )
}
