// O bot real em papel: o livro que espelha a carteira (~US$ 52), contra simplesmente segurar o livro inicial.
// Com um livro B (logs/paper_b: o mesmo bot com saídas TP/SL/trailing e exposição ≤ 50%), A e B lado a lado no topo.
import { lazy, Suspense, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type RealBot } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { frac, isoTime, num, pct, price, signedPct, signedUsd, usd } from '@/lib/format'
import { Delta, ErrorNote, Loading, Note, SectionHead, Stat } from '@/components/ui'

const TimeChart = lazy(() => import('@/components/charts/TimeChart'))

const REASON: Record<string, string> = {
  low_confidence: 'confiança baixa', high_skip: 'incerteza alta', insufficient_usdt: 'sem USDT para comprar', insufficient_sol: 'sem SOL para vender',
  cooldown: 'pausa entre trades', max_trades_per_hour: 'limite de trades por hora', low_margin: 'margem baixa', market_closed: 'mercado indisponível',
  low_prob_margin: 'margem baixa', skip: 'incerteza alta', fail_closed: 'sem resposta do modelo', reentry_cooldown: 'pausa depois de uma saída',
  max_exposure: 'teto de exposição',
}
const EXIT: Record<string, string> = { tp: 'take profit', sl: 'stop loss', trail: 'trailing stop' }

// Campos do placar por livro (A/B) que o tipo RealBot de lib/api ainda não descreve.
type Exits = { total: number; by_reason: Record<string, number>; avg_cost: number | null; ret_from_avg: number | null; exposure: number | null; last_exit_t: string | null }
type Book = RealBot & { book?: string; params_profile?: string | null; log_dir?: string; exits?: Exits }
type Board = Book & { books?: Book[] }

function BookCard({ B }: { B: Book }) {
  const hold = B.pnl_vs_hold, hr = B.hit_rate, tr = B.trades, ex = B.exits, comp = B.composition
  const exits = ex && ex.total ? Object.entries(ex.by_reason).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${EXIT[k] ?? k}`).join(', ') : 'nenhuma'
  return (
    <div className="min-w-0 rounded-lg border border-rule px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h3 className="t-title text-[19px]">Livro {B.book ?? 'A'}</h3>
        <span className="text-[12.5px] text-ink-3 t-tab">{B.params_profile ?? '—'}; desde {isoTime(B.start_t, true)}</span>
      </div>
      <p className="mt-2 flex flex-wrap items-baseline gap-x-3">
        <Delta v={hold?.usd} className="t-display text-[30px]">{signedUsd(hold?.usd)}</Delta>
        <Delta v={hold?.pct} arrowOn={false} className="t-num text-[16px]">{signedPct(hold?.pct, 2)}</Delta>
      </p>
      <p className="text-[12.5px] text-ink-3 t-tab">contra segurar o livro inicial; vale {usd(hold?.paper_value_usd)}</p>
      {comp && <div className="mt-3"><Composition sol={comp.sol_usd} usdt={comp.usdt_usd} /></div>}
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <Stat label={`Acerto ${hr?.horizon_min ?? 15} min`} sub={`${hr?.hits ?? 0} de ${hr?.resolved ?? 0}`}>{hr?.rate == null ? '—' : pct(hr.rate * 100, 0)}</Stat>
        <Stat label="Compras / vendas" sub={`maior queda ${pct(B.drawdown?.pct, 1)}`}>{tr?.buy ?? 0} / {tr?.sell ?? 0}</Stat>
        <Stat label="Saídas" sub={exits}>{num(ex?.total ?? 0, 0)}</Stat>
        <Stat label="Custo médio" sub={ex?.ret_from_avg == null ? 'sem posição' : `${signedPct(ex.ret_from_avg * 100, 2)} até agora`}>{ex?.avg_cost == null ? '—' : `US$ ${price(ex.avg_cost)}`}</Stat>
      </dl>
    </div>
  )
}
const ACTION: Record<string, string> = { buy: 'compra', sell: 'venda', hold: 'espera' }

function Composition({ sol, usdt }: { sol: number; usdt: number }) {
  const tot = sol + usdt
  const f = tot > 0 ? sol / tot : 0
  return (
    <div>
      <div className="flex h-[8px] w-full gap-[2px] overflow-hidden rounded-full" role="img" aria-label={`Composição: ${frac(f)} em SOL e ${frac(1 - f)} em USDT`}>
        {f > 0 && <span className="h-full rounded-l-full bg-ink" style={{ width: `${f * 100}%`, borderTopRightRadius: f >= 1 ? 999 : 0, borderBottomRightRadius: f >= 1 ? 999 : 0 }} />}
        {f < 1 && <span className="h-full flex-1 rounded-r-full bg-rule-strong" style={{ borderTopLeftRadius: f <= 0 ? 999 : 0, borderBottomLeftRadius: f <= 0 ? 999 : 0 }} />}
      </div>
      <div className="mt-2 flex justify-between text-[13px] t-tab">
        <span><i aria-hidden className="mr-1.5 inline-block size-2 rounded-sm bg-ink" />SOL {frac(f)} <span className="text-ink-3">({usd(sol)})</span></span>
        <span><i aria-hidden className="mr-1.5 inline-block size-2 rounded-sm bg-rule-strong" />USDT {frac(1 - f)} <span className="text-ink-3">({usd(usdt)})</span></span>
      </div>
    </div>
  )
}

export default function CarteiraReal() {
  const poll = usePollInterval(30_000)
  const q = useQuery({ queryKey: ['realbot'], queryFn: api.realbot, refetchInterval: poll || 60_000 })
  const R = q.data as Board | undefined
  const series = useMemo(() => {
    const rows = R?.series?.rows ?? []
    return [
      { id: 'paper', label: 'livro de papel', color: 'var(--ink)', width: 2 as const, data: rows.map(r => ({ t: r[0], v: r[1] })) },
      { id: 'hold', label: 'só segurar o livro inicial', color: 'var(--ink-3)', width: 1 as const, data: rows.map(r => ({ t: r[0], v: r[2] })) },
    ]
  }, [R])
  if (q.isLoading) return <Loading h={480} />
  if (q.error && !R) return <ErrorNote error={q.error} what="dados do bot real" />
  if (!R?.available) return <Note>O placar do bot real não está disponível nesta máquina: {R?.reason ?? 'sem logs'}. Ele aparece quando logs/decisions.jsonl do bot existir.</Note>
  const hold = R.pnl_vs_hold!, hr = R.hit_rate!, dd = R.drawdown!, tr = R.trades!
  const comp = R.composition
  return (
    <div className="flex flex-col gap-6">
      <section className="sheet rounded-xl px-4 py-5 sm:px-7 sm:py-6" aria-labelledby="rb-title">
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-2">
          <div>
            <h1 id="rb-title" className="t-title text-[26px]">Carteira real, em papel{(R.books?.length ?? 0) > 1 ? ' (livro A)' : ''}</h1>
            <p className="mt-1 max-w-[620px] text-[13.5px] text-ink-2">O bot de verdade decidindo com o von, mas executando só num livro de papel que começou igual à carteira. Nada é enviado à rede.</p>
          </div>
          <p className="text-[12.5px] text-ink-3 t-tab">desde {isoTime(R.start_t, true)}; última decisão {isoTime(R.last_t)}</p>
        </div>
        <div className="mt-5 grid gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <div>
            <p className="text-[13.5px] text-ink-3">Contra segurar o livro inicial</p>
            <p className="mt-1 flex flex-wrap items-baseline gap-x-3">
              <Delta v={hold.usd} className="t-display text-[40px] sm:text-[46px]">{signedUsd(hold.usd)}</Delta>
              <Delta v={hold.pct} arrowOn={false} className="t-num text-[20px]">{signedPct(hold.pct, 2)}</Delta>
            </p>
            <p className="mt-1 text-[13.5px] text-ink-2 t-tab">Livro de papel {usd(hold.paper_value_usd)}; parado valeria {usd(hold.base_value_usd)}. SOL a US$ {price(R.last_px)}.</p>
          </div>
          {comp && (
            <div>
              <p className="mb-2 text-[13.5px] text-ink-3">Composição agora</p>
              <Composition sol={comp.sol_usd} usdt={comp.usdt_usd} />
              {comp.sol_frac != null && comp.sol_frac > 0.9 && <p className="mt-3 text-[13.5px] text-ink-2">Está quase todo em SOL: daqui para a frente o resultado acompanha o preço de SOL (é beta, não escolha).</p>}
              <p className="mt-2 text-[12.5px] text-ink-3 t-tab">{num(R.paper_book?.sol, 6)} SOL + {num(R.paper_book?.usdt, 2)} USDT; começou com {num(R.start_book?.sol, 6)} SOL + {num(R.start_book?.usdt, 2)} USDT.</p>
            </div>
          )}
        </div>
        <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-5 border-t border-rule pt-5 sm:grid-cols-4">
          <Stat label={`Acerto em ${hr.horizon_min} min`} sub={`${hr.hits} de ${hr.resolved} trades${hr.unresolved ? `, ${hr.unresolved} por resolver` : ''}`}>{hr.rate == null ? '—' : pct(hr.rate * 100, 0)}</Stat>
          <Stat label="Maior queda" sub={dd.trough_t ? `fundo às ${isoTime(dd.trough_t, true)}` : undefined}>{pct(dd.pct, 1)}</Stat>
          <Stat label="Compras / vendas" sub={`${tr.total} trades de papel`}>{tr.buy} / {tr.sell}</Stat>
          <Stat label="Decisões" sub="uma a cada ~17 s">{num(R.n_decisions, 0)}</Stat>
        </dl>
      </section>

      {(R.books?.length ?? 0) > 1 && (
        <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="rb-ab">
          <SectionHead id="rb-ab" title="A × B">O mesmo bot e o mesmo von; o B junta saídas mecânicas (take profit, stop loss, trailing) e não passa de metade do livro em SOL. Cada livro conta desde o seu início, sempre contra segurar o mesmo livro inicial.</SectionHead>
          <div className="grid gap-4 md:grid-cols-2">
            {R.books!.map(b => <BookCard key={b.book ?? b.log_dir} B={b} />)}
          </div>
        </section>
      )}

      <section className="sheet rounded-xl p-4 sm:p-6" aria-label="Valor do livro contra segurar">
        <SectionHead title="Valor no tempo">A linha fina é o mesmo livro inicial parado; a distância entre as duas é o que as decisões renderam.</SectionHead>
        {series[0].data.length > 1 ? (
          <Suspense fallback={<Loading h={300} />}>
            <TimeChart series={series} format={v => usd(v, 2)} height={300} ariaLabel="Valor do livro de papel contra segurar o livro inicial" />
          </Suspense>
        ) : <Note>Sem decisões com preço ainda.</Note>}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="rb-dec">
          <SectionHead id="rb-dec" title="Últimas decisões" />
          <ul className="divide-y divide-rule border-y border-rule text-[13.5px]">
            {(R.recent_decisions ?? []).slice(0, 14).map((d, i) => (
              <li key={i} className="grid grid-cols-[54px_74px_minmax(0,1fr)_auto] items-baseline gap-3 py-1.5 t-tab">
                <span className="text-ink-3">{isoTime(d.t)}</span>
                <span className={d.action === 'buy' ? 'text-gain' : d.action === 'sell' ? 'text-loss' : 'text-ink-2'}>{d.action === 'buy' ? '▲ ' : d.action === 'sell' ? '▼ ' : ''}{ACTION[d.action] ?? d.action}</span>
                <span className="truncate text-ink-2">{d.model_action && d.model_action !== d.action ? `queria ${ACTION[d.model_action] ?? d.model_action}; ${REASON[d.reason ?? ''] ?? d.reason ?? ''}` : d.paper_fill ? 'executada no papel' : (REASON[d.reason ?? ''] ?? d.reason ?? '')}</span>
                <span className="text-ink-3">conf. {num(d.conf, 2)}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="rb-tr">
          <SectionHead id="rb-tr" title="Últimos trades de papel" />
          {(R.recent_trades ?? []).length ? (
            <ul className="divide-y divide-rule border-y border-rule text-[13.5px]">
              {R.recent_trades!.slice(0, 14).map((t, i) => (
                <li key={i} className="grid grid-cols-[86px_74px_minmax(0,1fr)_auto] items-baseline gap-3 py-1.5 t-tab">
                  <span className="text-ink-3">{isoTime(t.t, true)}</span>
                  <span className={t.side === 'buy' ? 'text-gain' : 'text-loss'}>{t.side === 'buy' ? '▲ compra' : '▼ venda'}</span>
                  <span className="text-ink-2">a US$ {price(t.fill_px ?? t.px)}</span>
                  <span className="text-ink-3">{t.side === 'buy' ? usd(t.in_ui) : `${num(t.in_ui, 5)} SOL`}</span>
                </li>
              ))}
            </ul>
          ) : <Note>Sem trades ainda: o primeiro aparece quando o bot passar os portões.</Note>}
        </section>
      </div>
    </div>
  )
}
