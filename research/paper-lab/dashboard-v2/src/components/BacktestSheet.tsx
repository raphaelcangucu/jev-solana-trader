// Detalhe de um teste na simulação retroativa: curva × só segurar, semana a semana, veredito e link para o run ao vivo.
import { lazy, Suspense, useMemo } from 'react'
import * as D from '@radix-ui/react-dialog'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink, X } from 'lucide-react'
import { api } from '@/lib/api'
import { dayMon, weeksFromEquity, type BtEntry } from '@/lib/backtest'
import { familyOf } from '@/lib/describe'
import { int, pct, pval, signedPct, signedUsd, smartUsd, usd } from '@/lib/format'
import { closeBacktest, liveHref } from '@/lib/router'
import { VerdictChip } from './BacktestBoard'
import { Chip, Delta, ErrorNote, Loading, Note, Stat, Tip } from './ui'

const TimeChart = lazy(() => import('./charts/TimeChart'))

function Weeks({ e, eq }: { e: BtEntry; eq: ReturnType<typeof weeksFromEquity> }) {
  // Com a curva: carteira e só segurar medidos na mesma fonte. Sem ela: só o que o summary traz.
  const fromSummary = (e.p.weeks ?? []).slice(0, 4)
  const rows = eq.length ? eq : fromSummary.map((v, i) => ({ i: i + 1, from: 0, to: 0, pct: v, bhPct: null, beat: null }))
  if (!rows.length) return <Note>Sem quebra semanal neste run.</Note>
  return (
    <table className="w-full border-collapse text-[13.5px]">
      <thead>
        <tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3">
          <th scope="col" className="py-1.5 pr-3 font-normal">Semana</th>
          <th scope="col" className="py-1.5 pr-3 text-right font-normal">Este teste</th>
          <th scope="col" className="py-1.5 pr-3 text-right font-normal">Só segurar</th>
          <th scope="col" className="py-1.5 text-right font-normal">Bateu?</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(w => (
          <tr key={w.i} className="border-b border-rule t-tab">
            <th scope="row" className="py-1.5 pr-3 text-left font-normal">
              {w.i}ª <span className="text-ink-3">{w.from ? `${dayMon(w.from)} a ${dayMon(w.to)}` : ''}</span>
            </th>
            <td className="py-1.5 pr-3 text-right"><Delta v={w.pct}>{signedPct(w.pct, 2)}</Delta></td>
            <td className="py-1.5 pr-3 text-right text-ink-2">{signedPct(w.bhPct, 2)}</td>
            <td className="py-1.5 text-right">{w.beat == null ? '—' : w.beat ? <span className="text-gain">▲ sim</span> : <span className="text-loss">▼ não</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Body({ e, run }: { e: BtEntry; run: string }) {
  const eq = useQuery({ queryKey: ['bt-equity', run, e.p.name], queryFn: () => api.backtestEquity(run, e.p.name), staleTime: 10 * 60_000, retry: 1 })
  const series = useMemo(() => {
    const s = eq.data
    if (!s) return null
    const pts = s.t.map((t, i) => ({ t, e: s.equity[i], b: s.bh[i] }))
    return [
      { id: 'eq', label: 'este teste', color: 'var(--ink)', width: 2 as const, data: pts.filter(p => p.e != null).map(p => ({ t: p.t, v: p.e })) },
      { id: 'bh', label: 'só segurar', color: 'var(--ink-3)', width: 1 as const, data: pts.filter(p => p.b != null).map(p => ({ t: p.t, v: p.b as number })) },
    ]
  }, [eq.data])
  const weeks = useMemo(() => weeksFromEquity(eq.data), [eq.data])
  const p = e.p
  const live = p.live_name
  return (
    <div className="grid gap-7">
      <section aria-label="O que este teste faz">
        <h3 className="mb-1 text-[13px] text-ink-3">O que este teste faz</h3>
        <p className="text-[16px] leading-relaxed">{e.d.explain}</p>
        <p className="mt-2 text-[12.5px] text-ink-3">Simulado sobre o histórico, com os parâmetros de hoje. Nada aqui foi executado.</p>
      </section>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 border-y border-rule py-5 sm:grid-cols-4">
        <Stat label="Lucro em 30 dias" sub={signedUsd(e.pnlUsd)}><Delta v={e.pnlPct}>{signedPct(e.pnlPct, 2)}</Delta></Stat>
        <Stat label="Vs. segurar" sub={signedUsd(e.vsHoldUsd)}><Delta v={e.vsHoldPct}>{signedPct(e.vsHoldPct, 2)}</Delta></Stat>
        <Stat label={<Tip content="Lucro menos exposição média × retorno do ativo. O que sobra quando se tira o beta."><span className="underline decoration-dotted underline-offset-2">Habilidade (sem beta)</span></Tip>}
          sub={p.timing != null ? `timing ${signedUsd(p.timing)}, ${pval(e.timingP)}` : pval(e.timingP)}>
          <Delta v={e.skillUsd}>{smartUsd(e.skillUsd, true)}</Delta>
        </Stat>
        <Stat label="Exposição média" sub={`começou com ${usd(p.start_value, 0)}`}>{pct(p.exposure_pct, 0)}</Stat>
        <Stat label="Maior queda" sub="do pico ao vale">{e.maxDd == null ? '—' : `−${pct(Math.abs(e.maxDd), 1)}`}</Stat>
        <Stat label="Compras / vendas" sub={p.closed_rt != null ? `${int(p.closed_rt)} operações fechadas` : `${int(e.trades)} trades`}>
          {p.buys == null ? int(e.trades) : `${int(p.buys)} / ${int(p.sells)}`}
        </Stat>
        <Stat label="Semanas acima de segurar" sub="de 4">{e.weeksBeat == null ? '—' : int(e.weeksBeat)}</Stat>
        <div>
          <dt className="mb-1.5 text-[12.5px] text-ink-3">Veredito</dt>
          <dd><VerdictChip v={e.verdict} /></dd>
          {(p.p_bh != null || p.p_usdc != null) && <dd className="mt-1 text-[12px] text-ink-3 t-tab">vs. segurar {pval(p.p_bh)}; vs. USDC {pval(p.p_usdc)}</dd>}
        </div>
      </dl>
      {p.verdict_reason && (
        <p className="-mt-3 text-[14px] text-ink-2"><span className="text-ink-3">Por quê: </span>{p.verdict_reason}</p>
      )}
      <section aria-label="Patrimônio">
        <h3 className="t-title mb-2 text-[17px]">Patrimônio contra só segurar</h3>
        {eq.isLoading ? <Loading h={300} label="Desenhando a curva…" />
          : eq.error ? <ErrorNote error={eq.error} what="curva" />
            : !series || series[0].data.length < 2 ? <Note>Este run não gravou a curva deste teste.</Note>
              : (
                <Suspense fallback={<Loading h={300} />}>
                  <TimeChart series={series} format={v => usd(v, 2)} height={280} idleLabel="fim da janela" ariaLabel={`Patrimônio simulado de ${e.d.title} contra só segurar`} />
                </Suspense>
              )}
      </section>
      <section aria-label="Semana a semana">
        <h3 className="t-title mb-2 text-[17px]">Semana a semana</h3>
        <Weeks e={e} eq={weeks} />
      </section>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule pt-4 text-[13.5px]">
        {live ? (
          <a href={liveHref(live)} className="inline-flex items-center gap-1.5 text-ink underline underline-offset-2 hover:text-ink-2">
            Ver no run ao vivo <ExternalLink aria-hidden className="size-3.5" />
          </a>
        ) : <span className="text-ink-3">Este teste não está rodando ao vivo agora.</span>}
        <span className="text-[12px] text-ink-3">{p.name}</span>
      </div>
    </div>
  )
}

export default function BacktestSheet({ entry, name, run }: { entry: BtEntry | null; name: string | null; run: string }) {
  return (
    <D.Root open={!!name} onOpenChange={o => { if (!o) closeBacktest() }}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-50 bg-[rgba(10,18,32,0.38)]" />
        <D.Content aria-describedby={undefined} onOpenAutoFocus={ev => { ev.preventDefault(); (ev.currentTarget as HTMLElement | null)?.focus() }} tabIndex={-1}
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[780px] flex-col border-l border-rule-strong bg-paper shadow-2xl outline-none">
          <div className="flex items-start gap-3 border-b border-rule bg-surface px-5 pb-4 pt-5 sm:px-7">
            <div className="min-w-0 flex-1">
              <D.Title className="t-title text-[22px] sm:text-[26px]">{entry?.d.title ?? name}</D.Title>
              {entry && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <Chip className="border-rule-strong">retroativo</Chip>
                  <Chip>{entry.d.asset}</Chip>
                  <Chip color={familyOf(entry.d.family).color}>{entry.d.tag}</Chip>
                </div>
              )}
            </div>
            <D.Close className="grid size-9 place-items-center rounded-md text-ink-2 hover:bg-sunk hover:text-ink" aria-label="Fechar detalhe"><X className="size-5" /></D.Close>
          </div>
          <div className="flex-1 overflow-y-auto px-5 pb-10 pt-5 sm:px-7">
            {entry ? <Body e={entry} run={run} /> : <Note>Esse teste não está neste run da simulação.</Note>}
          </div>
        </D.Content>
      </D.Portal>
    </D.Root>
  )
}
