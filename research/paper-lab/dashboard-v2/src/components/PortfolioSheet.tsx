// Detalhe de um teste (folha lateral): curva × só segurar com trades, o que o teste faz, números, parâmetros e ajuste.
import { lazy, Suspense, useMemo, useState } from 'react'
import * as D from '@radix-ui/react-dialog'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { toast } from 'sonner'
import { api, ApiError } from '@/lib/api'
import { toEntry } from '@/lib/board'
import { familyOf } from '@/lib/describe'
import { int, isoTime, pct, price, pval, signedPct, signedUsd, smartUsd, usd } from '@/lib/format'
import { OVERLAY_FIELDS } from '@/lib/params'
import { useOverview } from '@/lib/queries'
import { closePortfolio } from '@/lib/router'
import { VerdictProgress } from './marks'
import { FieldEditor, ParamsTable } from './ParamsView'
import { Chip, Confirm, Delta, ErrorNote, Loading, Note, Stat, Switch, Tip } from './ui'

const TimeChart = lazy(() => import('./charts/TimeChart'))

function EquityBlock({ name }: { name: string }) {
  const eq = useQuery({ queryKey: ['equity', name], queryFn: () => api.equity([name], 900), staleTime: 15_000 })
  const det = useQuery({ queryKey: ['portfolio', name], queryFn: () => api.portfolio(name), staleTime: 15_000 })
  const series = useMemo(() => {
    const s = eq.data?.[name]
    if (!s) return null
    const pts = s.t.map((t, i) => ({ t, e: s.equity[i], b: s.bh[i] })).filter(p => p.e != null)
    return [
      { id: 'eq', label: 'este teste', color: 'var(--ink)', width: 2 as const, data: pts.map(p => ({ t: p.t, v: p.e as number })) },
      { id: 'bh', label: 'só segurar', color: 'var(--ink-3)', width: 1 as const, data: pts.filter(p => p.b != null).map(p => ({ t: p.t, v: p.b as number })) },
    ]
  }, [eq.data, name])
  const markers = useMemo(() => (det.data?.trades ?? []).filter(t => t.ts && (t.side === 'buy' || t.side === 'sell')).map(t => ({ t: t.ts as number, side: t.side as 'buy' | 'sell' })), [det.data])
  if (eq.isLoading) return <Loading h={320} label="Desenhando a curva…" />
  if (eq.error) return <ErrorNote error={eq.error} what="curva" />
  if (!series || series[0].data.length < 2) return <Note>Sem curva ainda: o teste grava o primeiro ponto no próximo ciclo.</Note>
  return (
    <Suspense fallback={<Loading h={320} />}>
      <TimeChart series={series} markers={markers} format={v => usd(v, 2)} height={280} ariaLabel={`Patrimônio de ${name} contra só segurar`} />
    </Suspense>
  )
}

function Controls({ name, control, paused }: { name: string; control: string; paused: boolean }) {
  const qc = useQueryClient()
  const eff = useQuery({ queryKey: ['effective', name], queryFn: () => api.effective(name) })
  const params = useQuery({ queryKey: ['params'], queryFn: api.params, staleTime: 60_000 })
  const [askPause, setAskPause] = useState(false)
  const [askRestore, setAskRestore] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const done = (msg: string) => { setErr(null); toast.success(msg); ['overview', 'effective', 'params', 'portfolio'].forEach(k => qc.invalidateQueries({ queryKey: [k] })) }
  const fail = (e: unknown) => setErr(e instanceof ApiError ? e.message : String(e))
  const pause = useMutation({ mutationFn: (p: boolean) => api.setParams(control, { paused: p }), onSuccess: (_d, p) => { setAskPause(false); done(p ? 'Teste pausado' : 'Teste retomado') }, onError: e => { setAskPause(false); fail(e) } })
  const restore = useMutation({ mutationFn: () => api.restore(control), onSuccess: () => { setAskRestore(false); done('Ajuste manual removido') }, onError: e => { setAskRestore(false); fail(e) } })
  if (eff.isLoading) return <Loading h={200} />
  if (eff.error || !eff.data) return <ErrorNote error={eff.error} what="parâmetros" />
  const E = eff.data
  const g = (E.effective.gates || {}) as Record<string, unknown>
  const lim = (E.effective.limits || {}) as Record<string, number>
  const b = params.data?.bounds || {}
  const limits = Object.fromEntries(OVERLAY_FIELDS.map(f => {
    const [lo, hi] = b[f] ?? [null, null]
    const cap = f === 'buy_fraction_usdt' ? lim.buy_fraction_usdt_max : f === 'max_trades_per_hour' ? lim.max_trades_per_hour_max : undefined
    return [`gates.${f}`, { min: lo ?? undefined, max: cap ?? hi ?? undefined }]
  }))
  const hasOverlay = Object.values(E.provenance).includes('overlay')
  return (
    <div className="grid gap-6">
      <div>
        <h3 className="t-title text-[17px]">Parâmetros em uso</h3>
        {E.errors.length > 0 && <p role="alert" className="mt-2 text-[13px] text-loss">Parâmetros inválidos, o teste está nos últimos válidos: {E.errors.join('; ')}</p>}
        <div className="mt-3"><ParamsTable effective={E.effective} provenance={E.provenance} /></div>
      </div>
      <div className="rounded-lg border border-rule-strong p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="t-title text-[17px]">Ajuste manual</h3>
            <p className="text-[12.5px] text-ink-3">Vale na hora para este teste, por cima de params.json. Fica registrado e pode ser desfeito.</p>
          </div>
          <label className="flex items-center gap-2 text-[13.5px]">
            {paused ? 'pausado' : 'rodando'}
            <Switch checked={!paused} onCheckedChange={() => setAskPause(true)} aria-label={paused ? 'Retomar este teste' : 'Pausar este teste'} />
          </label>
        </div>
        <FieldEditor key={JSON.stringify(g)} fields={OVERLAY_FIELDS.map(f => `gates.${f}`)} current={E.effective} provenance={E.provenance} limits={limits}
          confirmTitle="Salvar o ajuste manual?" queryKeys={['effective', 'overview', 'params']}
          save={ch => api.setParams(control, Object.fromEntries(Object.entries(ch).map(([k, v]) => [k.replace('gates.', ''), v])))}
          note={hasOverlay ? <button type="button" className="underline underline-offset-2 hover:text-ink" onClick={() => setAskRestore(true)}>Remover ajuste manual</button> : undefined} />
        {err && <p role="alert" className="mt-3 text-[13px] text-loss">O servidor recusou: {err}</p>}
      </div>
      <Confirm open={askPause} onOpenChange={setAskPause} title={paused ? 'Retomar este teste?' : 'Pausar este teste?'} confirmLabel={paused ? 'Retomar' : 'Pausar'} busy={pause.isPending} onConfirm={() => pause.mutate(!paused)}>
        {paused ? 'Ele volta a decidir no próximo ciclo.' : 'Ele para de comprar e vender no próximo ciclo; a carteira fica como está e a curva continua sendo gravada.'}
      </Confirm>
      <Confirm open={askRestore} onOpenChange={setAskRestore} title="Remover o ajuste manual?" confirmLabel="Remover" busy={restore.isPending} onConfirm={() => restore.mutate()}>
        O teste volta aos valores de params.json (tipo, perfil e portfólio) e sai da pausa.
      </Confirm>
    </div>
  )
}

function ReadOnlyParams({ name }: { name: string }) {
  const eff = useQuery({ queryKey: ['effective', name], queryFn: () => api.effective(name) })
  if (eff.isLoading) return <Loading h={160} />
  if (eff.error || !eff.data) return <ErrorNote error={eff.error} what="parâmetros" />
  return (
    <div>
      <h3 className="t-title text-[17px]">Parâmetros em uso</h3>
      <div className="mt-3"><ParamsTable effective={eff.data.effective} provenance={eff.data.provenance} /></div>
      <p className="mt-3 text-[12.5px] text-ink-3">Este teste não tem ajuste manual próprio: mude pelo tipo de teste em Controle.</p>
    </div>
  )
}

function Trades({ name }: { name: string }) {
  const det = useQuery({ queryKey: ['portfolio', name], queryFn: () => api.portfolio(name), staleTime: 15_000 })
  const tr = det.data?.trades ?? []
  if (det.isLoading) return null
  return (
    <div>
      <h3 className="t-title mb-2 text-[17px]">Últimos trades</h3>
      {tr.length ? (
        <ul className="divide-y divide-rule border-y border-rule text-[13.5px]">
          {tr.slice(0, 12).map((t, i) => (
            <li key={i} className="grid grid-cols-[92px_74px_1fr_auto] items-baseline gap-3 py-1.5 t-tab">
              <span className="text-ink-3">{isoTime(t.ts_brt, true)}</span>
              <span className={t.side === 'buy' ? 'text-gain' : 'text-loss'}>{t.side === 'buy' ? '▲ compra' : '▼ venda'}</span>
              <span className="text-ink-2">a {price(t.fill_price ?? t.mark)}{t.fill_mode === 'limit_sim' ? ' (limite)' : ''}</span>
              <span>{smartUsd(t.usdt)}</span>
            </li>
          ))}
        </ul>
      ) : <Note>Sem trades ainda: o primeiro aparece quando este teste passar os portões.</Note>}
    </div>
  )
}

export default function PortfolioSheet({ name }: { name: string | null }) {
  const ov = useOverview()
  const row = ov.data?.rows.find(r => r.name === name)
  const e = useMemo(() => (row ? toEntry(row) : null), [row])
  const sk = row?.skill
  return (
    <D.Root open={!!name} onOpenChange={o => { if (!o) closePortfolio() }}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-50 bg-[rgba(10,18,32,0.38)]" />
        <D.Content aria-describedby={undefined} onOpenAutoFocus={ev => { ev.preventDefault(); (ev.currentTarget as HTMLElement | null)?.focus() }} tabIndex={-1} className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[780px] flex-col border-l border-rule-strong bg-paper shadow-2xl outline-none">
          <div className="flex items-start gap-3 border-b border-rule bg-surface px-5 pb-4 pt-5 sm:px-7">
            <div className="min-w-0 flex-1">
              <D.Title className="t-title text-[22px] sm:text-[26px]">{e?.d.title ?? name}</D.Title>
              {e && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <Chip>{e.d.asset}</Chip>
                  <Chip color={familyOf(e.d.family).color}>{e.d.tag}</Chip>
                  <span className="text-[12px] text-ink-3">{row!.name}</span>
                </div>
              )}
            </div>
            <D.Close className="grid size-9 place-items-center rounded-md text-ink-2 hover:bg-sunk hover:text-ink" aria-label="Fechar detalhe"><X className="size-5" /></D.Close>
          </div>
          <div className="flex-1 overflow-y-auto px-5 pb-10 pt-5 sm:px-7">
            {!row || !e ? (ov.isLoading ? <Loading h={300} /> : <Note>Não achei esse teste no placar. Ele pode ter sido renomeado.</Note>) : (
              <div className="grid gap-7">
                <section aria-label="O que este teste faz">
                  <h3 className="mb-1 text-[13px] text-ink-3">O que este teste faz</h3>
                  <p className="text-[16px] leading-relaxed">{e.d.explain}</p>
                </section>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-5 border-y border-rule py-5 sm:grid-cols-4">
                  <Stat label="Lucro" sub={signedUsd(e.pnlUsd)}><Delta v={e.pnlPct}>{signedPct(e.pnlPct, 2)}</Delta></Stat>
                  <Stat label="Vs. segurar" sub={signedUsd(e.vsHoldUsd)}><Delta v={e.vsHoldPct}>{signedPct(e.vsHoldPct, 2)}</Delta></Stat>
                  <Stat label={<Tip content="Lucro menos exposição média × retorno do ativo. O que sobra quando se tira o beta."><span className="underline decoration-dotted underline-offset-2">Habilidade (sem beta)</span></Tip>}
                    sub={sk?.timing_usd != null ? `timing ${signedUsd(sk.timing_usd)}, ${pval(sk.timing_p)}` : 'sem timing'}>
                    <Delta v={e.skillUsd}>{smartUsd(e.skillUsd, true)}</Delta>
                  </Stat>
                  <Stat label="Exposição média" sub={`agora ${pct(row.exposure_pct, 0)}`}>{pct(e.exposure, 0)}</Stat>
                  <Stat label="Maior queda" sub="do pico ao vale">{pct(row.max_dd_pct, 1)}</Stat>
                  <Stat label="Compras / vendas" sub={sk?.sells ? `${int(sk.rt_wins)} de ${int(sk.sells)} vendas com lucro` : 'nenhuma venda ainda'}>{e.buys == null ? '—' : `${int(e.buys)} / ${int(e.sells)}`}</Stat>
                  <Stat label="Custos" sub={`taxas ${smartUsd(sk?.fees)}`}>{smartUsd(sk?.cost_vs_mark)}</Stat>
                  <div><dt className="mb-1.5 text-[12.5px] text-ink-3">Rumo ao veredito</dt><dd><VerdictProgress days={e.days} minDays={e.minDays} rt={e.rt} minRt={e.minRt} verdict={row.verdict} /></dd></div>
                </dl>
                <section aria-label="Patrimônio">
                  <h3 className="t-title mb-2 text-[17px]">Patrimônio contra só segurar</h3>
                  <EquityBlock name={row.name} />
                </section>
                {row.control ? <Controls name={row.catalog ?? row.name} control={row.control} paused={!!row.paused} /> : <ReadOnlyParams name={row.catalog ?? row.name} />}
                <Trades name={row.name} />
                <p className="text-[12px] text-ink-3">Começou {isoTime(row.started_brt, true)}. {row.verdict_reason ? `Veredito: ${row.verdict} (${row.verdict_reason}).` : ''}</p>
              </div>
            )}
          </div>
        </D.Content>
      </D.Portal>
    </D.Root>
  )
}

