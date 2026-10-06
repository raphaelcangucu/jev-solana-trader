// Retroativo: a simulação dos últimos 30 dias com todas as estratégias do lab. "Quem teria ganho no mês passado?"
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type BtBook, type BtSummary } from '@/lib/api'
import { asPct, BT_SORTS, familyInfo, familySorted, markWinners, sortBt, stamp, toBtEntry, windowLabel, type BtEntry, type BtSortKey } from '@/lib/backtest'
import { matches, type AssetFilter, type FamilyFilter } from '@/lib/board'
import { FAMILIES, familyOf, MEMES } from '@/lib/describe'
import { int, num, pct, price, pval, signedPct, signedUsd, smartUsd, usd } from '@/lib/format'
import { parseMarkdown, type Block, type Inline } from '@/lib/markdown'
import { openBacktest, useRoute } from '@/lib/router'
import { cn } from '@/lib/utils'
import { BacktestBoard, VerdictChip } from '@/components/BacktestBoard'
import { Pill } from '@/components/FilterBar'
import { Diverging } from '@/components/marks'
import { Chip, Delta, ErrorNote, Loading, Mark, Note, SectionHead, Stat, Tip } from '@/components/ui'

const BacktestSheet = lazy(() => import('@/components/BacktestSheet'))
const SORT_KEY = 'paperlab.bt.sort'

// ---------------------------------------------------------------- abertura

function Opening({ s, byName, runs, run, onRun }: { s: BtSummary; byName: Map<string, BtEntry>; runs: { run_id: string; generated_brt?: string | null }[]; run: string; onRun: (r: string | null) => void }) {
  const w = s.winner || {}
  const targets = [w.by_pnl, w.by_skill, w.by_verdict].filter((x): x is string => !!x)
    .map(raw => ({ raw, label: byName.get(raw)?.who ?? raw }))
  const segs = markWinners(w.text ?? '', targets)
  const assets = Object.entries(s.assets ?? {}).sort(([a], [b]) => (a === 'SOL' ? -1 : b === 'SOL' ? 1 : MEMES.indexOf(a) - MEMES.indexOf(b)))
  const step = s.window?.step_s
  return (
    <section aria-labelledby="bt-title" className="sheet relative overflow-hidden rounded-xl px-4 pb-5 pt-4 sm:px-7 sm:pt-6">
      <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-3">
        <div>
          <p className="text-[13.5px] text-ink-3">Se o lab tivesse rodado nos últimos {s.window?.days ?? 30} dias</p>
          <h1 id="bt-title" className="t-display mt-1 text-[34px] sm:text-[42px]">{windowLabel(s.window)}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 sm:justify-end sm:pt-6">
          <Chip className="border-rule-strong">simulação retroativa</Chip>
          <Chip>{s.portfolios.length} testes</Chip>
          {step ? <Chip>passo de {step >= 60 ? `${num(step / 60, 0)} min` : `${step} s`}</Chip> : null}
          <Chip>gerada {stamp(s.generated_brt)}</Chip>
          {runs.length > 1 && (
            <label className="ml-1 inline-flex items-center gap-1.5 text-[12.5px] text-ink-3">
              <span className="sr-only">Escolher simulação</span>
              <select value={run} onChange={e => onRun(e.target.value)} className="h-7 rounded-md border border-rule-strong bg-surface px-1.5 text-[12.5px] text-ink">
                {runs.map(r => <option key={r.run_id} value={r.run_id}>{r.generated_brt ? stamp(r.generated_brt) : r.run_id}</option>)}
              </select>
            </label>
          )}
        </div>
      </div>

      {assets.length > 0 && (
        <div className="mt-4">
          <p className="mb-1.5 text-[12.5px] text-ink-3">O mercado no período</p>
          <ul className="flex flex-wrap gap-1.5" aria-label="Variação de cada ativo na janela">
            {assets.map(([sym, a]) => (
              <li key={sym}>
                <Tip content={`${sym}: de ${price(a.start_px)} para ${price(a.end_px)}. Dados ${a.source ?? 'sem fonte'}${a.coverage != null ? `, cobertura ${pct(asPct(a.coverage), 1)}` : ''}.`}>
                  <span tabIndex={0} className="inline-flex h-7 items-center gap-2 rounded-md border border-rule bg-surface px-2.5 text-[13px]">
                    <span className="t-cond text-ink-2">{sym}</span>
                    <Delta v={a.ret_pct} className="t-num text-[13.5px]">{signedPct(a.ret_pct)}</Delta>
                  </span>
                </Tip>
              </li>
            ))}
          </ul>
        </div>
      )}

      {segs.length > 0 && (
        <p className="mt-5 max-w-[920px] border-t border-rule pt-4 text-[17px] leading-relaxed sm:text-[19px]">
          {segs.map((g, i) => g.mark ? <Mark key={i} sweep><span className="t-semi">{g.text}</span></Mark> : <span key={i}>{g.text}</span>)}
        </p>
      )}
      <p className="mt-3 max-w-[920px] text-[13.5px] text-ink-2">
        <span className="t-semi text-ink">Como ler:</span> <b className="t-semi">lucro</b> é quanto a carteira rendeu;{' '}
        <b className="t-semi">habilidade</b> é o lucro sem a parte que o mercado deu de graça (beta);{' '}
        <b className="t-semi">veredito</b> só diz vencedora quando a habilidade é difícil de explicar por sorte, pelo mesmo critério do run ao vivo.
      </p>
    </section>
  )
}

// ---------------------------------------------------------------- pódio

function PodiumCard({ label, e, children, sub }: { label: string; e: BtEntry | null; children?: React.ReactNode; sub?: React.ReactNode }) {
  if (!e) return null
  return (
    <button type="button" onClick={() => openBacktest(e.p.name)}
      className="sheet group flex min-w-0 flex-col items-start gap-2 rounded-xl px-4 py-4 text-left transition-colors hover:border-rule-strong sm:px-5">
      <span className="text-[13px] text-ink-3">{label}</span>
      <span className="t-title max-w-full text-[19px] leading-snug"><Mark sweep>{e.d.title}</Mark></span>
      <span className="flex flex-wrap gap-1">
        <Chip>{e.d.asset}</Chip>
        <Chip color={familyOf(e.d.family).color}>{e.d.tag}</Chip>
      </span>
      <span className="mt-1 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">{children}</span>
      {sub && <span className="text-[12.5px] text-ink-3 t-tab">{sub}</span>}
    </button>
  )
}

function Podium({ s, byName }: { s: BtSummary; byName: Map<string, BtEntry> }) {
  const w = s.winner || {}
  const sk = w.by_skill ? byName.get(w.by_skill) ?? null : null
  const pn = w.by_pnl ? byName.get(w.by_pnl) ?? null : null
  const vd = w.by_verdict ? byName.get(w.by_verdict) ?? null : null
  const winners = s.portfolios.filter(p => toBtEntry(p).verdict === 'vencedora').length
  return (
    <section aria-labelledby="bt-podium" className="flex flex-col gap-3">
      <h2 id="bt-podium" className="sr-only">Vencedores</h2>
      <div className="grid gap-3 md:grid-cols-3">
        <PodiumCard label="Mais habilidade, sem beta" e={sk} sub={sk ? `lucro ${signedPct(sk.pnlPct)}; vs. segurar ${signedPct(sk.vsHoldPct)}` : undefined}>
          {sk && <><Delta v={sk.skillUsd} className="t-display text-[28px]">{smartUsd(sk.skillUsd, true)}</Delta><span className="text-[13px] text-ink-3 t-tab">{pval(sk.timingP)}</span></>}
        </PodiumCard>
        <PodiumCard label="Mais lucro" e={pn} sub={pn ? `habilidade ${smartUsd(pn.skillUsd, true)}; vs. segurar ${signedPct(pn.vsHoldPct)}` : undefined}>
          {pn && <><Delta v={pn.pnlPct} className="t-display text-[28px]">{signedPct(pn.pnlPct)}</Delta><span className="text-[13px] text-ink-3 t-tab">{smartUsd(pn.pnlUsd, true)}</span></>}
        </PodiumCard>
        {vd ? (
          <PodiumCard label={`Melhor veredito${winners > 1 ? ` (de ${winners} vencedoras)` : ''}`} e={vd} sub={vd.p.verdict_reason ?? undefined}>
            <VerdictChip v={vd.verdict} className="h-[26px] px-2 text-[14px]" />
            <Delta v={vd.skillUsd} className="t-num text-[18px]">{smartUsd(vd.skillUsd, true)}</Delta>
          </PodiumCard>
        ) : (
          <div className="flex flex-col justify-center rounded-xl border border-dashed border-rule-strong px-5 py-4">
            <span className="text-[13px] text-ink-3">Melhor veredito</span>
            <p className="mt-1 text-[15px] text-ink-2">Nenhum teste passou o critério de vencedora nestes {s.window?.days ?? 30} dias.</p>
          </div>
        )}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- placar com filtros

const FAM_BASE: { key: FamilyFilter; label: string }[] = [
  { key: 'von', label: 'Modelos von' }, { key: 'laya', label: 'Laya' }, { key: 'poorjev', label: 'poorjev' },
  { key: 'rules', label: 'Regras' }, { key: 'hybrid', label: 'Híbridos' }, { key: 'lab', label: 'Hipóteses' }, { key: 'forks', label: 'Forks' },
]

function Board({ entries, run }: { entries: BtEntry[]; run: string }) {
  const [sort, setSortS] = useState<BtSortKey>(() => {
    try { const v = localStorage.getItem(SORT_KEY); return v === 'lucro' || v === 'segurar' || v === 'veredito' ? v : 'habilidade' } catch { return 'habilidade' }
  })
  const setSort = (k: BtSortKey) => { setSortS(k); try { localStorage.setItem(SORT_KEY, k) } catch { /* sem storage */ } }
  const [fam, setFam] = useState<FamilyFilter>('all')
  const [asset, setAsset] = useState<AssetFilter>('all')
  const sparks = useQuery({ queryKey: ['bt-sparks', run], queryFn: () => api.backtestSparks(run, 60), staleTime: 10 * 60_000, retry: 1 })
  const firstPaint = useRef(true)
  useEffect(() => { const t = setTimeout(() => { firstPaint.current = false }, 1500); return () => clearTimeout(t) }, [])
  const famsHere = useMemo(() => FAM_BASE.filter(f => entries.some(e => matches(e, f.key, 'all', ''))), [entries])
  const memes = useMemo(() => MEMES.filter(m => entries.some(e => e.d.asset === m)), [entries])
  const visible = useMemo(() => sortBt(entries.filter(e => matches(e, fam, asset, '')), sort), [entries, fam, asset, sort])
  const active = fam !== 'all' || asset !== 'all'
  return (
    <section aria-labelledby="bt-board" className="flex flex-col gap-3">
      <SectionHead id="bt-board" title="Placar dos 30 dias">Toque num teste para ver a curva contra só segurar e cada semana.</SectionHead>
      <div className="flex flex-col gap-2.5">
        <div role="group" aria-label="Ordenar por" className="inline-flex max-w-full self-start overflow-x-auto rounded-lg border border-rule-strong bg-surface p-[3px]">
          {BT_SORTS.map(s => (
            <Tip key={s.key} content={s.hint}>
              <button type="button" aria-pressed={sort === s.key} onClick={() => setSort(s.key)}
                className={cn('h-8 shrink-0 rounded-md px-3 text-[13.5px] transition-colors', sort === s.key ? 'bg-ink text-surface t-semi' : 'text-ink-2 hover:text-ink')}>
                {s.label}
              </button>
            </Tip>
          ))}
        </div>
        <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0" role="group" aria-label="Filtrar por família e ativo">
          {famsHere.map(f => (
            <Pill key={f.key} on={fam === f.key} onClick={() => setFam(fam === f.key ? 'all' : f.key)} color={FAMILIES.find(x => x.key === f.key)?.color}>{f.label}</Pill>
          ))}
          <span aria-hidden className="mx-1 hidden w-px self-stretch bg-rule sm:block" />
          <Pill on={asset === 'SOL'} onClick={() => setAsset(asset === 'SOL' ? 'all' : 'SOL')}>SOL</Pill>
          {memes.length > 0 && <Pill on={asset === 'memes'} onClick={() => setAsset(asset === 'memes' ? 'all' : 'memes')}>Memecoins</Pill>}
          {memes.map(m => <Pill key={m} on={asset === m} onClick={() => setAsset(asset === m ? 'all' : m)}>{m}</Pill>)}
        </div>
        <p className="text-[12.5px] text-ink-3 t-tab" aria-live="polite">
          {visible.length === entries.length ? `${entries.length} testes` : `${visible.length} de ${entries.length} testes`}
          {active && <button type="button" onClick={() => { setFam('all'); setAsset('all') }} className="ml-2 text-ink-2 underline underline-offset-2 hover:text-ink">limpar filtros</button>}
        </p>
      </div>
      {visible.length
        ? <BacktestBoard entries={visible} sort={sort} onSort={setSort} sparks={sparks.data} firstPaint={firstPaint.current} />
        : <Note>Nenhum teste com esses filtros. <button type="button" className="underline" onClick={() => { setFam('all'); setAsset('all') }}>Limpar filtros</button></Note>}
    </section>
  )
}

// ---------------------------------------------------------------- famílias

function Families({ s, byName }: { s: BtSummary; byName: Map<string, BtEntry> }) {
  const fs = familySorted(s.families ?? [])
  const max = Math.max(1, ...fs.map(f => Math.abs(f.median_pnl_pct ?? 0)))
  const NameBtn = ({ n, prefix }: { n?: string | null; prefix: string }) => {
    if (!n) return null
    const e = byName.get(n)
    return (
      <button type="button" onClick={() => openBacktest(n)} className="max-w-full truncate rounded-sm text-left text-[12.5px] text-ink-2 hover:text-ink hover:underline">
        <span className="text-ink-3">{prefix} </span>{e?.who ?? n}{e?.pnlPct != null && <span className="t-tab text-ink-3"> ({signedPct(e.pnlPct)})</span>}
      </button>
    )
  }
  return (
    <section aria-labelledby="bt-fam" className="sheet min-w-0 rounded-xl p-4 sm:p-6">
      <SectionHead id="bt-fam" title="Por família">Lucro mediano de cada família e quantos testes dela bateram só segurar.</SectionHead>
      {fs.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {fs.map(f => {
            const info = familyInfo(f.family)
            const beat = f.beat_bh
            return (
              <li key={f.family} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 py-3 sm:grid-cols-[minmax(0,1fr)_150px_110px]">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 t-semi text-[15px]">
                    <i aria-hidden className="inline-block size-[9px] shrink-0 rounded-full" style={{ background: info.color }} />{info.label}
                    <span className="text-[12.5px] font-normal text-ink-3 t-tab">{int(f.n)} {f.n === 1 ? 'teste' : 'testes'}</span>
                  </p>
                  <div className="mt-0.5 flex min-w-0 flex-col">
                    <NameBtn n={f.best} prefix="melhor:" />
                    {f.worst && f.worst !== f.best && <NameBtn n={f.worst} prefix="pior:" />}
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 sm:justify-start">
                  <span className="hidden sm:inline"><Diverging v={f.median_pnl_pct} max={max} w={64} /></span>
                  <span className="text-right">
                    <Delta v={f.median_pnl_pct} className="t-num block text-[16px]">{signedPct(f.median_pnl_pct)}</Delta>
                    <span className="block text-[11.5px] text-ink-3">mediana</span>
                  </span>
                </div>
                <div className="col-span-2 text-[12.5px] text-ink-2 t-tab sm:col-span-1">
                  {beat == null ? '—' : <>{int(beat)} de {int(f.n)} <span className="text-ink-3">bateram segurar</span></>}
                </div>
              </li>
            )
          })}
        </ul>
      ) : <Note>Este run não trouxe o resumo por família.</Note>}
    </section>
  )
}

// ---------------------------------------------------------------- bot real A × B

function exitsText(x: BtBook['exits']): string {
  if (x == null) return '—'
  if (typeof x === 'number') return int(x)
  const total = Object.values(x).reduce((a, b) => a + (Number(b) || 0), 0)
  return int(total)
}

function RealBot({ books }: { books: BtBook[] }) {
  return (
    <section aria-labelledby="bt-real" className="sheet min-w-0 rounded-xl p-4 sm:p-6">
      <SectionHead id="bt-real" title="Bot real, A × B">O mesmo bot e o mesmo von nos 30 dias: A como roda hoje, B com saídas mecânicas e no máximo metade em SOL.</SectionHead>
      {books.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {books.map(b => (
            <div key={b.book} className="min-w-0 rounded-lg border border-rule px-4 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <h3 className="t-title text-[18px]">Livro {b.book}</h3>
                {b.profile && <Chip>{b.profile}</Chip>}
              </div>
              <p className="mt-2 flex flex-wrap items-baseline gap-x-3">
                <Delta v={b.pnl} className="t-display text-[26px]">{signedUsd(b.pnl)}</Delta>
                <Delta v={b.pnl_pct} arrowOn={false} className="t-num text-[15px]">{signedPct(b.pnl_pct, 2)}</Delta>
              </p>
              <p className="text-[12.5px] text-ink-3 t-tab">de {usd(b.start_value)} para {usd(b.end_value)}</p>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
                <Stat label="Vs. segurar"><Delta v={b.vs_hold}>{signedUsd(b.vs_hold)}</Delta></Stat>
                <Stat label="Acerto 15 min">{b.hit_15m == null ? '—' : pct(asPct(b.hit_15m), 0)}</Stat>
                <Stat label="Maior queda">{b.max_dd_pct == null ? '—' : `−${pct(Math.abs(b.max_dd_pct), 1)}`}</Stat>
                <Stat label="Trades / saídas">{int(b.trades)} / {exitsText(b.exits)}</Stat>
              </dl>
            </div>
          ))}
        </div>
      ) : <Note>Este run não simulou o bot real.</Note>}
    </section>
  )
}

// ---------------------------------------------------------------- método e limitações

function Inl({ xs }: { xs: Inline[] }) {
  return <>{xs.map((x, i) => x.t === 'b' ? <b key={i} className="t-semi">{x.v}</b> : x.t === 'i' ? <em key={i}>{x.v}</em>
    : x.t === 'code' ? <code key={i} className="rounded bg-sunk px-1 text-[0.92em]">{x.v}</code> : <span key={i}>{x.v}</span>)}</>
}

function Markdown({ blocks }: { blocks: Block[] }) {
  return (
    <div className="grid gap-3 text-[14px] leading-relaxed">
      {blocks.map((b, i) => {
        if (b.k === 'h') {
          const cls = b.level === 1 ? 't-title text-[21px]' : b.level === 2 ? 't-title mt-2 text-[18px]' : 't-semi mt-1 text-[15px]'
          return <p key={i} role="heading" aria-level={b.level + 2} className={cls}><Inl xs={b.text} /></p>
        }
        if (b.k === 'p') return <p key={i} className="text-ink-2"><Inl xs={b.text} /></p>
        if (b.k === 'ul') return <ul key={i} className="ml-5 list-disc text-ink-2">{b.items.map((it, j) => <li key={j}><Inl xs={it} /></li>)}</ul>
        if (b.k === 'ol') return <ol key={i} className="ml-5 list-decimal text-ink-2">{b.items.map((it, j) => <li key={j}><Inl xs={it} /></li>)}</ol>
        if (b.k === 'code') return <pre key={i} className="overflow-x-auto rounded-md bg-sunk px-3 py-2 text-[12.5px]"><code>{b.text}</code></pre>
        if (b.k === 'hr') return <hr key={i} className="border-rule" />
        return (
          <div key={i} className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px] t-tab">
              <thead><tr className="border-b border-rule-strong text-left text-ink-3">{b.head.map((h, j) => <th key={j} scope="col" className="py-1 pr-3 font-normal"><Inl xs={h} /></th>)}</tr></thead>
              <tbody>{b.rows.map((r, j) => <tr key={j} className="border-b border-rule">{r.map((c, k) => <td key={k} className="py-1 pr-3"><Inl xs={c} /></td>)}</tr>)}</tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}

function Report({ run }: { run: string }) {
  const q = useQuery({ queryKey: ['bt-report', run], queryFn: () => api.backtestReport(run), staleTime: 10 * 60_000, retry: 1 })
  const blocks = useMemo(() => (q.data ? parseMarkdown(q.data) : []), [q.data])
  if (q.isLoading) return <Loading h={160} label="Abrindo o relatório…" />
  if (q.error) return <ErrorNote error={q.error} what="relatório" />
  return <div className="rounded-lg border border-rule bg-surface px-4 py-4 sm:px-5"><Markdown blocks={blocks} /></div>
}

function Method({ s, run, hasReport }: { s: BtSummary; run: string; hasReport: boolean }) {
  const [showReport, setShowReport] = useState(false)
  const models = Object.entries(s.models ?? {})
  const assets = Object.entries(s.assets ?? {})
  return (
    <details className="sheet group rounded-xl">
      <summary className="flex cursor-pointer list-none flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-4 sm:px-6 [&::-webkit-details-marker]:hidden">
        <h2 className="t-title text-[19px] sm:text-[21px]"><span aria-hidden className="mr-2 inline-block text-[13px] text-ink-3 transition-transform group-open:rotate-90">▶</span>Método e limitações</h2>
        <span className="text-[13px] text-ink-3">{(s.assumptions ?? []).length} premissas, cobertura dos modelos e dos dados</span>
      </summary>
      <div className="grid gap-6 border-t border-rule px-4 pb-6 pt-5 sm:px-6">
        {(s.assumptions ?? []).length > 0 && (
          <div>
            <h3 className="t-semi mb-2 text-[15px]">Premissas</h3>
            <ul className="ml-5 list-disc space-y-1 text-[14px] text-ink-2">{s.assumptions!.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </div>
        )}
        <div className="grid gap-6 lg:grid-cols-2">
          {models.length > 0 && (
            <div className="min-w-0">
              <h3 className="t-semi mb-2 text-[15px]">Modelos</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[13px] t-tab">
                  <thead><tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3">
                    <th scope="col" className="py-1.5 pr-3 font-normal">Modelo</th><th scope="col" className="py-1.5 pr-3 text-right font-normal">Chamadas</th>
                    <th scope="col" className="py-1.5 pr-3 text-right font-normal">Do cache</th><th scope="col" className="py-1.5 pr-3 text-right font-normal">Cobertura</th>
                    <th scope="col" className="py-1.5 text-right font-normal">Confiança p50 / p90</th>
                  </tr></thead>
                  <tbody>{models.map(([m, v]) => (
                    <tr key={m} className="border-b border-rule">
                      <th scope="row" className="py-1.5 pr-3 text-left font-normal">{m}</th>
                      <td className="py-1.5 pr-3 text-right">{int(v.calls)}</td>
                      <td className="py-1.5 pr-3 text-right">{v.calls ? pct(((v.cache_hits ?? 0) / v.calls) * 100, 0) : int(v.cache_hits)}</td>
                      <td className="py-1.5 pr-3 text-right">{pct(asPct(v.coverage), 1)}</td>
                      <td className="py-1.5 text-right">{num(v.conf_p50, 2)} / {num(v.conf_p90, 2)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
          )}
          {assets.length > 0 && (
            <div className="min-w-0">
              <h3 className="t-semi mb-2 text-[15px]">Dados de preço</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[13px] t-tab">
                  <thead><tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3">
                    <th scope="col" className="py-1.5 pr-3 font-normal">Ativo</th><th scope="col" className="py-1.5 pr-3 font-normal">Fonte</th>
                    <th scope="col" className="py-1.5 pr-3 text-right font-normal">Cobertura</th><th scope="col" className="py-1.5 text-right font-normal">Preço</th>
                  </tr></thead>
                  <tbody>{assets.map(([a, v]) => (
                    <tr key={a} className="border-b border-rule">
                      <th scope="row" className="py-1.5 pr-3 text-left font-normal">{a}</th>
                      <td className="py-1.5 pr-3 text-ink-2">{v.source ?? '—'}</td>
                      <td className="py-1.5 pr-3 text-right">{pct(asPct(v.coverage), 1)}</td>
                      <td className="whitespace-nowrap py-1.5 text-right">{price(v.start_px)} → {price(v.end_px)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
          )}
        </div>
        {hasReport ? (
          <div className="grid gap-3">
            <div className="flex flex-wrap items-center gap-3 text-[13.5px]">
              <button type="button" aria-expanded={showReport} onClick={() => setShowReport(v => !v)}
                className="inline-flex h-8 items-center rounded-md border border-rule-strong bg-surface px-3 text-ink hover:border-ink-3">
                {showReport ? 'Esconder o relatório completo' : 'Ler o relatório completo'}
              </button>
              <a href={`/api/v2/backtest/${encodeURIComponent(run)}/report`} target="_blank" rel="noreferrer" className="text-ink-2 underline underline-offset-2 hover:text-ink">abrir como texto</a>
            </div>
            {showReport && <Report run={run} />}
          </div>
        ) : <p className="text-[13px] text-ink-3">Este run não gravou report.md.</p>}
      </div>
    </details>
  )
}

// ---------------------------------------------------------------- página

export default function Retroativo() {
  const route = useRoute()
  const [run, setRun] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['backtest', run], queryFn: () => api.backtest(run), staleTime: 5 * 60_000, refetchInterval: 10 * 60_000 })
  const d = q.data
  useEffect(() => { if (run && d && !d.available && d.latest) setRun(null) }, [run, d])
  const s = d?.available ? d.summary : undefined
  const entries = useMemo(() => (s?.portfolios ?? []).map(toBtEntry), [s])
  const byName = useMemo(() => new Map(entries.map(e => [e.p.name, e])), [entries])
  if (q.isLoading) return <Loading h={520} label="Abrindo a simulação…" />
  if (q.error && !d) return <ErrorNote error={q.error} what="simulação retroativa" />
  if (!d?.available || !s || !d.run_id) {
    return (
      <section aria-labelledby="bt-empty" className="sheet rounded-xl px-4 py-6 sm:px-7">
        <h1 id="bt-empty" className="t-display text-[30px] sm:text-[36px]">Retroativo</h1>
        <p className="mt-2 max-w-[640px] text-[14px] text-ink-2">Aqui aparece quem teria ganho se todas as estratégias do lab tivessem rodado nos últimos 30 dias.</p>
        <Note className="mt-5">
          Ainda não há simulação retroativa. Rode <code className="rounded bg-sunk px-1">scripts/backtest_30d.py</code> e esta página mostra o resultado quando ela terminar.
        </Note>
      </section>
    )
  }
  const runId = d.run_id
  const sheetEntry = route.b ? byName.get(route.b) ?? null : null
  return (
    <div className="flex flex-col gap-6">
      <Opening s={s} byName={byName} runs={d.runs} run={runId} onRun={r => setRun(r === d.latest ? null : r)} />
      <Podium s={s} byName={byName} />
      <Board entries={entries} run={runId} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Families s={s} byName={byName} />
        <RealBot books={s.realbot ?? []} />
      </div>
      <Method s={s} run={runId} hasReport={!!d.has_report} />
      {route.b && <Suspense fallback={null}><BacktestSheet entry={sheetEntry} name={route.b} run={runId} /></Suspense>}
    </div>
  )
}
