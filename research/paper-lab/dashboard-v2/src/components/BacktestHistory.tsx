// Histórico do retroativo: seletor de período (meses de 30 dias e 6 meses), comparação entre meses e o gráfico de 6 meses.
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type BtChart, type BtIndex, type BtIndexRun } from '@/lib/api'
import { dayMon } from '@/lib/backtest'
import { int, signedPct, signedUsd, smartUsd } from '@/lib/format'
import {
  asReturn, benchLines, consistency, describeName, familyLines, familyScopes, lastValue, maxDrawdown, memesRet, monthlyRuns,
  monthShort, orderRuns, runForMonth, runPill, strategyPool, whoName, type LineDef,
} from '@/lib/history'
import { parseMarkdown } from '@/lib/markdown'
import { btHref, openBacktest } from '@/lib/router'
import { useMedia } from '@/lib/useMedia'
import { cn } from '@/lib/utils'
import { Chip, Delta, ErrorNote, Loading, Mark, Note, SectionHead, Tip } from './ui'
import { Markdown } from './MarkdownView'
import { LineKey } from './charts/LineKey'

const LinesChart = lazy(() => import('./charts/LinesChart'))

// ---------------------------------------------------------------- seletor de período

export function RunPills({ idx, current, compare }: { idx: BtIndex; current: string | null; compare: boolean }) {
  const runs = orderRuns(idx)
  const months = monthlyRuns(idx, 3)
  if (!runs.length) return null
  const pill = (on: boolean) => cn('inline-flex min-h-9 shrink-0 flex-col justify-center rounded-lg border px-3 py-1 text-left leading-tight transition-colors',
    on ? 'border-ink bg-ink text-surface' : 'border-rule-strong bg-surface text-ink-2 hover:border-ink-3 hover:text-ink')
  return (
    <nav aria-label="Período da simulação" className="flex flex-wrap items-stretch gap-1.5">
      {runs.map(r => {
        const p = runPill(r)
        const on = !compare && current === r.run_id
        return (
          <a key={r.run_id} href={btHref(r.run_id)} aria-current={on ? 'page' : undefined} title={`${p.title} (${r.run_id})`} className={pill(on)}>
            <span className="t-semi text-[14px]">{p.label}</span>
            <span className={cn('hidden text-[11.5px] t-tab sm:block', on ? 'text-surface/75' : 'text-ink-3')}>{p.sub}</span>
          </a>
        )
      })}
      {months.length >= 2 && (
        <>
          <span aria-hidden className="mx-1 hidden w-px self-stretch bg-rule sm:block" />
          <a href="#/retroativo?view=comparar" aria-current={compare ? 'page' : undefined} className={pill(compare)}>
            <span className="t-semi text-[14px]">Comparar meses</span>
            <span className={cn('hidden text-[11.5px] sm:block', compare ? 'text-surface/75' : 'text-ink-3')}>{months.length} meses lado a lado</span>
          </a>
        </>
      )}
    </nav>
  )
}

// ---------------------------------------------------------------- comparar meses

function NameLink({ run, name, note, lookAhead }: { run: string; name: string | null | undefined; note?: React.ReactNode; lookAhead?: string[] | null }) {
  if (!name) return <span className="text-ink-3">nenhuma</span>
  const d = describeName(name)
  const ahead = lookAhead?.includes(name)
  return (
    <a href={btHref(run, name)} className="group block min-w-0 rounded-sm" title={name}>
      <span className="block leading-snug text-ink group-hover:underline">{d.title}</span>
      <span className="flex flex-wrap gap-x-2 text-[12px] text-ink-3 t-tab"><span>{d.asset}</span>{note ? <span className="text-ink-2">{note}</span> : null}{ahead && <span title="Fork criado depois do início do mês: usa parâmetros que só existiram mais tarde.">olhar no futuro</span>}</span>
    </a>
  )
}

function Verdicts({ r }: { r: BtIndexRun }) {
  return (
    <span className="flex flex-col gap-0.5 text-[13px] t-tab">
      <span className={cn((r.n_winners ?? 0) > 0 ? 'text-gain t-semi' : 'text-ink-3')}><span aria-hidden className="text-[9px]">▲ </span>{int(r.n_winners)} vencedora{r.n_winners === 1 ? '' : 's'}</span>
      <span className="text-ink-2">{int(r.n_inconclusive)} inconclusiva{r.n_inconclusive === 1 ? '' : 's'}</span>
      <span className={cn((r.n_losers ?? 0) > 0 ? 'text-loss' : 'text-ink-3')}><span aria-hidden className="text-[9px]">▼ </span>{int(r.n_losers)} perdedora{r.n_losers === 1 ? '' : 's'}</span>
    </span>
  )
}

const ordinal = (n: number) => `${n}º`

export function CompareMonths({ idx }: { idx: BtIndex }) {
  const months = useMemo(() => monthlyRuns(idx, 3), [idx])
  const rep = useMemo(() => consistency(months, 5), [months])
  const [all, setAll] = useState(false)
  if (months.length < 2) return <Note>Ainda não há meses suficientes para comparar. Assim que houver dois runs mensais de 30 dias, eles aparecem aqui lado a lado.</Note>
  const n = months.length
  const repeat = rep.filter(c => c.count >= 2)
  const shown = all ? rep : rep.slice(0, Math.max(8, repeat.length))
  const th = 'sticky left-0 z-[1] bg-surface py-2.5 pr-3 text-left align-top text-[12.5px] font-normal text-ink-3'
  const td = 'py-2.5 pr-4 align-top'
  const book = (r: BtIndexRun, b: string) => r.realbot?.find(x => x.book === b)
  const books = [...new Set(months.flatMap(r => (r.realbot ?? []).map(b => b.book)))].sort()
  const headRow = (
    <tr className="border-b border-rule-strong">
      <th scope="col" className={cn(th, 'w-[118px] sm:w-[150px]')}><span className="sr-only">Medida</span></th>
      {months.map(r => {
        const p = runPill(r)
        return (
          <th key={r.run_id} scope="col" className="min-w-[132px] py-2.5 pr-4 text-left align-bottom font-normal">
            <a href={btHref(r.run_id)} className="group inline-flex flex-col rounded-sm">
              <span className="t-title text-[19px] text-ink group-hover:underline">{p.label}</span>
              <span className="text-[12px] text-ink-3 t-tab">{p.sub}</span>
            </a>
          </th>
        )
      })}
    </tr>
  )
  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="cmp-title" className="sheet min-w-0 rounded-xl p-4 sm:p-6">
        <SectionHead id="cmp-title" title={`Os últimos ${n} meses lado a lado`}>
          Cada coluna é uma simulação de 30 dias com as mesmas estratégias. Toque num nome para abrir o teste naquele mês.
        </SectionHead>
        <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <table className="w-full min-w-[520px] border-collapse text-[14px]">
            <thead>{headRow}</thead>
            <tbody className="divide-y divide-rule">
              <tr>
                <th scope="row" className={th}>SOL</th>
                {months.map(r => <td key={r.run_id} className={td}><Delta v={r.assets?.SOL} className="t-num text-[16px]">{signedPct(r.assets?.SOL)}</Delta></td>)}
              </tr>
              <tr>
                <th scope="row" className={th}><Tip content="Média simples da variação das memecoins simuladas no mês."><span className="underline decoration-dotted underline-offset-2">Memecoins</span></Tip></th>
                {months.map(r => { const m = memesRet(r.assets); return <td key={r.run_id} className={td}><Delta v={m} className="t-num text-[16px]">{signedPct(m)}</Delta></td> })}
              </tr>
              <tr>
                <th scope="row" className={th}>Mais habilidade</th>
                {months.map(r => { const sk = r.top_skill?.find(t => t.name === r.winner?.by_skill); return <td key={r.run_id} className={td}><NameLink run={r.run_id} name={r.winner?.by_skill} lookAhead={r.look_ahead_forks} note={sk?.skill != null ? smartUsd(sk.skill, true) : undefined} /></td> })}
              </tr>
              <tr>
                <th scope="row" className={th}>Mais lucro</th>
                {months.map(r => { const pn = r.top_pnl?.find(t => t.name === r.winner?.by_pnl); return <td key={r.run_id} className={td}><NameLink run={r.run_id} name={r.winner?.by_pnl} lookAhead={r.look_ahead_forks} note={pn?.pnl_pct != null ? signedPct(pn.pnl_pct) : undefined} /></td> })}
              </tr>
              <tr>
                <th scope="row" className={th}>Melhor veredito</th>
                {months.map(r => <td key={r.run_id} className={td}><NameLink run={r.run_id} name={r.winner?.by_verdict} lookAhead={r.look_ahead_forks} /></td>)}
              </tr>
              <tr>
                <th scope="row" className={th}>Vereditos</th>
                {months.map(r => <td key={r.run_id} className={td}><Verdicts r={r} /></td>)}
              </tr>
              {books.map(b => (
                <tr key={b}>
                  <th scope="row" className={th}>Bot real, livro {b}</th>
                  {months.map(r => {
                    const x = book(r, b)
                    return (
                      <td key={r.run_id} className={td}>
                        {x ? <>
                          <Delta v={x.pnl_pct} className="t-num block text-[16px]">{signedPct(x.pnl_pct, 2)}</Delta>
                          <span className="block text-[12px] text-ink-3 t-tab">vs. segurar {signedUsd(x.vs_hold)}</span>
                        </> : <span className="text-ink-3">—</span>}
                      </td>
                    )
                  })}
                </tr>
              ))}
              <tr>
                <th scope="row" className={th}>Testes</th>
                {months.map(r => (
                  <td key={r.run_id} className={cn(td, 'text-[13px] text-ink-2 t-tab')}>
                    {int(r.n_portfolios)}
                    {(r.look_ahead_forks?.length ?? 0) > 0 && (
                      <Tip content={`Forks criados depois do início do mês: usam parâmetros que só existiram mais tarde. ${r.look_ahead_forks!.join(', ')}`}>
                        <span tabIndex={0} className="mt-0.5 block text-[12px] text-ink-3 underline decoration-dotted underline-offset-2">{r.look_ahead_forks!.length} com olhar no futuro</span>
                      </Tip>
                    )}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="cmp-rep" className="sheet min-w-0 rounded-xl p-4 sm:p-6">
        <SectionHead id="cmp-rep" title="Quem se repete no topo">
          Aparecer no top 5 (por habilidade ou por lucro) em mais de um mês é mais difícil de explicar por sorte.
          Com marca-texto: no topo em {n === 2 ? 'os 2 meses' : `2 ou mais dos ${n} meses`}.
        </SectionHead>
        {rep.length ? (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[520px] border-collapse text-[14px]">
              <thead>
                <tr className="border-b border-rule-strong">
                  <th scope="col" className={cn(th, 'w-[170px] align-bottom sm:w-[38%]')}>Estratégia</th>
                  {months.map(r => <th key={r.run_id} scope="col" className="py-2.5 pr-3 text-left align-bottom text-[12.5px] font-normal text-ink-3">{runPill(r).label}</th>)}
                  <th scope="col" className="py-2.5 text-right align-bottom text-[12.5px] font-normal text-ink-3">No top 5</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {shown.map(c => {
                  const d = describeName(c.name)
                  const hot = c.count >= 2
                  return (
                    <tr key={c.name}>
                      <th scope="row" className="sticky left-0 z-[1] bg-surface py-2.5 pr-3 text-left align-top font-normal">
                        <span className={cn('block leading-snug', hot ? 't-semi text-ink' : 'text-ink-2')} title={c.name}><Mark on={hot}>{d.title}</Mark></span>
                        <span className="mt-0.5 flex flex-wrap gap-1"><Chip>{d.asset}</Chip><Chip>{d.tag}</Chip></span>
                      </th>
                      {months.map(r => {
                        const h = c.hits.find(x => x.run_id === r.run_id)
                        return (
                          <td key={r.run_id} className="whitespace-nowrap py-2.5 pr-3 align-top text-[12.5px] t-tab">
                            {h ? (
                              <a href={btHref(r.run_id, c.name)} className="flex flex-col gap-0.5 rounded-sm text-ink hover:underline" aria-label={`${d.title} em ${runPill(r).label}`}>
                                {h.skillRank != null && <span>habilidade {ordinal(h.skillRank)}</span>}
                                {h.pnlRank != null && <span>lucro {ordinal(h.pnlRank)}</span>}
                              </a>
                            ) : <span className="text-ink-3">—</span>}
                          </td>
                        )
                      })}
                      <td className="py-2.5 text-right align-top">
                        <span className={cn('t-num text-[16px]', hot ? 'text-ink' : 'text-ink-3')}>{c.count}</span>
                        <span className="text-[12px] text-ink-3"> de {n}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : <Note>Os runs não trouxeram o top 5 de cada mês.</Note>}
        {rep.length > shown.length && (
          <button type="button" onClick={() => setAll(true)} className="mt-3 text-[13.5px] text-ink-2 underline underline-offset-2 hover:text-ink">
            Mostrar todas as {rep.length} que passaram pelo top 5
          </button>
        )}
      </section>
      {idx.has_history && <HistoryReport />}
    </div>
  )
}

function HistoryReport() {
  const [open, setOpen] = useState(false)
  const q = useQuery({ queryKey: ['bt-history'], queryFn: api.backtestHistory, enabled: open, staleTime: 10 * 60_000, retry: 1 })
  const blocks = useMemo(() => (q.data ? parseMarkdown(q.data) : []), [q.data])
  return (
    <details className="sheet group rounded-xl" onToggle={e => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="flex cursor-pointer list-none flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-4 sm:px-6 [&::-webkit-details-marker]:hidden">
        <h2 className="t-title text-[19px] sm:text-[21px]"><span aria-hidden className="mr-2 inline-block text-[13px] text-ink-3 transition-transform group-open:rotate-90">▶</span>Relatório da comparação</h2>
        <a href="/api/v2/backtest/history" target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="text-[13px] text-ink-2 underline underline-offset-2 hover:text-ink">abrir como texto</a>
      </summary>
      <div className="border-t border-rule px-4 pb-6 pt-5 sm:px-6">
        {q.isLoading ? <Loading h={140} label="Abrindo o relatório…" /> : q.error ? <ErrorNote error={q.error} what="relatório" /> : <Markdown blocks={blocks} />}
      </div>
    </details>
  )
}

// ---------------------------------------------------------------- 6 meses

type ChartView = 'estrategias' | 'familias'
const pctOf = (v: number | null | undefined) => signedPct(asReturn(v))
const fmtEq = (v: number) => int(v)

function Segmented<T extends string>({ value, onChange, options, label }: { value: T; onChange: (v: T) => void; options: { key: T; label: string }[]; label: string }) {
  return (
    <div role="group" aria-label={label} className="inline-flex max-w-full rounded-lg border border-rule-strong bg-surface p-[3px]">
      {options.map(o => (
        <button key={o.key} type="button" aria-pressed={value === o.key} onClick={() => onChange(o.key)}
          className={cn('h-8 shrink-0 rounded-md px-3 text-[13.5px] transition-colors', value === o.key ? 'bg-ink text-surface t-semi' : 'text-ink-2 hover:text-ink')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

function LegendToggle({ l, on, onToggle, why }: { l: LineDef; on: boolean; onToggle: () => void; why?: string }) {
  const v = lastValue(l.data)
  return (
    <button type="button" aria-pressed={on} onClick={onToggle} title={why ? `${l.label}: ${why}` : l.label}
      className={cn('inline-flex h-7 max-w-full items-center gap-1.5 rounded-md border px-2 text-[12.5px] transition-colors sm:h-8 sm:gap-2 sm:px-2.5 sm:text-[13px]',
        on ? 'border-rule-strong bg-surface text-ink' : 'border-dashed border-rule bg-transparent text-ink-3 hover:text-ink-2')}>
      <span className={cn(!on && 'opacity-40')}><LineKey color={l.color} style={l.style} /></span>
      <span className="min-w-0 truncate">{l.label}</span>
      <span className={cn('t-tab text-[12.5px]', on ? 'text-ink-2' : 'text-ink-3')}>{pctOf(v)}</span>
    </button>
  )
}

function LinesTable({ lines }: { lines: LineDef[] }) {
  const rows = [...lines].sort((a, b) => (lastValue(b.data) ?? -Infinity) - (lastValue(a.data) ?? -Infinity))
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] border-collapse text-[13px] t-tab">
        <thead><tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3">
          <th scope="col" className="py-1.5 pr-3 font-normal">Linha</th>
          <th scope="col" className="py-1.5 pr-3 text-right font-normal">Fim (1.000 = início)</th>
          <th scope="col" className="py-1.5 pr-3 text-right font-normal">Variação</th>
          <th scope="col" className="py-1.5 text-right font-normal">Maior queda</th>
        </tr></thead>
        <tbody>{rows.map(l => {
          const v = lastValue(l.data), dd = maxDrawdown(l.data)
          return (
            <tr key={l.id} className="border-b border-rule">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal"><span className="inline-flex items-center gap-2"><LineKey color={l.color} style={l.style} />{l.label}</span></th>
              <td className="py-1.5 pr-3 text-right">{v == null ? '—' : int(v)}</td>
              <td className="py-1.5 pr-3 text-right"><Delta v={asReturn(v)} arrowOn={false}>{pctOf(v)}</Delta></td>
              <td className="py-1.5 text-right text-ink-2">{dd == null ? '—' : signedPct(dd)}</td>
            </tr>
          )
        })}</tbody>
      </table>
    </div>
  )
}

function MonthStrip({ ch, idx, has }: { ch: BtChart; idx: BtIndex | null | undefined; has: (name: string) => boolean }) {
  const ms = ch.monthly ?? []
  if (!ms.length) return null
  const years = new Set(ms.map(m => m.month.slice(0, 4)))
  const Who = ({ name, label }: { name?: string | null; label: string }) => {
    if (!name) return null
    return (
      <p className="min-w-0 text-[12.5px] leading-snug">
        <span className="block text-ink-3">{label}</span>
        {has(name)
          ? <button type="button" onClick={() => openBacktest(name)} className="block max-w-full rounded-sm text-left text-ink hover:underline" title={name}>{whoName(name)}</button>
          : <span className="block text-ink" title={name}>{whoName(name)}</span>}
      </p>
    )
  }
  return (
    <div>
      <h3 className="t-semi mb-2 text-[15px]">Mês a mês: quem liderou</h3>
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {ms.map(m => {
          const run = runForMonth(idx, m.start_brt)
          return (
            <li key={m.month} className="flex min-w-0 flex-col gap-2 rounded-lg border border-rule bg-surface px-3 py-2.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="t-title text-[17px]">{monthShort(m.month, years.size > 1)}</span>
                {run
                  ? <a href={btHref(run)} className="text-[12px] text-ink-2 underline underline-offset-2 hover:text-ink" title={`Abrir o run de 30 dias: ${run}`}>ver o mês</a>
                  : <span className="text-[11.5px] text-ink-3 t-tab">{dayMon(m.start_brt)}</span>}
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[12.5px] t-tab">
                <span><span className="text-ink-3">SOL </span><Delta v={m.sol_ret} arrowOn={false}>{signedPct(m.sol_ret)}</Delta></span>
                <span><span className="text-ink-3">memes </span><Delta v={m.memes_ret} arrowOn={false}>{signedPct(m.memes_ret)}</Delta></span>
              </div>
              <Who name={m.top_by_pnl} label="mais lucro" />
              {m.top_by_skill && m.top_by_skill !== m.top_by_pnl ? <Who name={m.top_by_skill} label="mais habilidade" /> : m.top_by_skill ? <p className="text-[12px] text-ink-3">também a maior habilidade</p> : null}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

export function SixMonths({ runId, run, idx, has }: { runId: string; run: BtIndexRun | null; idx: BtIndex | null | undefined; has: (name: string) => boolean }) {
  const q = useQuery({ queryKey: ['bt-chart', runId], queryFn: () => api.backtestChart(runId), staleTime: 10 * 60_000, retry: 1 })
  const ch = q.data
  const [view, setView] = useState<ChartView>('estrategias')
  const [scope, setScope] = useState<'' | 'SOL' | 'Memecoins'>('')
  const [table, setTable] = useState(false)
  const pool = useMemo(() => (ch ? strategyPool(ch, run) : []), [ch, run])
  const bench = useMemo(() => (ch ? benchLines(ch) : []), [ch])
  const scopes = useMemo(() => (ch ? familyScopes(ch) : []), [ch])
  const fams = useMemo(() => (ch ? familyLines(ch, scope) : []), [ch, scope])
  const [on, setOn] = useState<Set<string>>(new Set())
  useEffect(() => { setOn(new Set([...pool.filter(p => p.defaultOn).map(p => p.id), ...bench.map(b => b.id)])) }, [pool, bench])
  useEffect(() => { if (scopes.length && !scopes.includes(scope)) setScope(scopes[0]) }, [scopes, scope])
  const [famOn, setFamOn] = useState<Set<string> | null>(null)
  useEffect(() => { setFamOn(null) }, [scope, runId])
  const wide = useMedia('(min-width: 640px)')

  if (q.isLoading) return <Loading h={520} label="Desenhando os 6 meses…" />
  if (q.error) return (q.error as { status?: number })?.status === 404
    ? <Note>Este run de 6 meses não gravou o gráfico (chart.json). O placar abaixo continua valendo.</Note>
    : <ErrorNote error={q.error} what="gráfico de 6 meses" />
  if (!ch || ch.t.length < 2) return <Note>O gráfico de 6 meses está vazio neste run.</Note>

  const famVisible = famOn ?? new Set(fams.map(f => f.id))
  const stratLines = view === 'estrategias' ? pool.filter(p => on.has(p.id)) : fams.filter(f => famVisible.has(f.id))
  const benchOn = bench.filter(b => on.has(b.id))
  const lines = [...stratLines, ...benchOn]
  const toggle = (id: string) => setOn(s => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const toggleFam = (id: string) => setFamOn(() => { const n = new Set(famVisible); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const t0 = ch.t[0], t1 = ch.t[ch.t.length - 1]
  const solEnd = asReturn(lastValue(ch.benchmarks?.sol_bh ?? []))
  const basket = ch.benchmarks?.memes_in_basket ?? []
  const strat = pool.filter(p => p.name)
  const above = strat.filter(p => (lastValue(p.data) ?? -Infinity) > (lastValue(ch.benchmarks?.sol_bh ?? []) ?? Infinity)).length

  return (
    <section aria-labelledby="six-title" id="seis-meses" data-shot="chart-6m" className="sheet min-w-0 rounded-xl p-4 sm:p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <h2 id="six-title" className="t-title text-[21px] sm:text-[24px]">Como cada algoritmo teria ido em 6 meses</h2>
          <p className="mt-1 max-w-[760px] text-[13.5px] text-ink-2">
            Patrimônio normalizado: tudo começa em 1.000 no dia {dayMon(t0)} e termina em {dayMon(t1)}.
            As linhas tracejadas são referências: só segurar SOL ({signedPct(solEnd)}), a cesta de memecoins
            {basket.length ? ` (média de ${basket.join(', ')})` : ''} e USDC rendendo 6% ao ano.
            {strat.length > 0 && ` ${above} das ${strat.length} estratégias em destaque terminaram acima de só segurar SOL.`}
          </p>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Segmented label="O que mostrar" value={view} onChange={setView}
          options={[{ key: 'estrategias', label: 'Estratégias' }, { key: 'familias', label: 'Por família' }]} />
        {view === 'familias' && scopes.length > 1 && (
          <Segmented label="Ativo das famílias" value={scope} onChange={setScope}
            options={scopes.map(s => ({ key: s, label: s || 'Todas' }))} />
        )}
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Linhas do gráfico (toque para mostrar ou esconder)">
        {view === 'estrategias'
          ? pool.map(p => <LegendToggle key={p.id} l={p} on={on.has(p.id)} onToggle={() => toggle(p.id)} why={p.why} />)
          : fams.map(f => <LegendToggle key={f.id} l={f} on={famVisible.has(f.id)} onToggle={() => toggleFam(f.id)} why="mediana da família" />)}
        <span aria-hidden className="mx-0.5 hidden w-px self-stretch bg-rule sm:block" />
        {bench.map(b => <LegendToggle key={b.id} l={b} on={on.has(b.id)} onToggle={() => toggle(b.id)} why="referência" />)}
      </div>

      {lines.length ? (
        <Suspense fallback={<Loading h={wide ? 440 : 320} />}>
          <LinesChart t={ch.t} lines={lines} height={wide ? 440 : 320} format={fmtEq} valueNote={v => pctOf(v)} baseline={1000}
            ariaLabel={`Patrimônio normalizado de ${lines.length} linhas de ${dayMon(t0)} a ${dayMon(t1)}; a tabela abaixo traz os valores finais.`} />
        </Suspense>
      ) : <Note>Nenhuma linha ligada. Toque numa estratégia acima para mostrar.</Note>}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px]">
        <button type="button" aria-expanded={table} onClick={() => setTable(v => !v)} className="text-ink-2 underline underline-offset-2 hover:text-ink">
          {table ? 'Esconder a tabela' : 'Ver os valores em tabela'}
        </button>
        {view === 'familias' && <span className="text-ink-3">Cada linha é a mediana das carteiras da família, dia a dia.</span>}
      </div>
      {table && <div className="mt-3"><LinesTable lines={view === 'estrategias' ? [...pool, ...bench] : [...fams, ...bench]} /></div>}

      <div className="mt-6 border-t border-rule pt-5">
        <MonthStrip ch={ch} idx={idx} has={has} />
      </div>
    </section>
  )
}
