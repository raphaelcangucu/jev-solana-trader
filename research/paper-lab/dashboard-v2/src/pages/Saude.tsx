// Saúde: processos, batimentos, reinícios, qualidade dos fills e disco. Página secundária, leitura rápida.
import { useHealth } from '@/lib/queries'
import { ago, int, isoTime, num, pct } from '@/lib/format'
import { procName } from '@/components/TopBar'
import { Dot, ErrorNote, Loading, SectionHead, Stat } from '@/components/ui'
import { cn } from '@/lib/utils'

export default function Saude() {
  const h = useHealth()
  if (h.isLoading) return <Loading h={400} />
  if (h.error || !h.data) return <ErrorNote error={h.error} what="saúde" />
  const H = h.data
  const X = H.extras ?? {}
  const restarts = Object.entries(X.restarts_24h ?? {})
  const fills = X.fills_24h
  const verdict = H.level === 'ok' ? 'Tudo rodando.' : H.down.length ? `Parado: ${H.down.map(procName).join(', ')}.` : H.stale.length ? `Sem sinal recente: ${H.stale.map(procName).join(', ')}.` : `${H.errors} erro(s) nos ciclos.`
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
        <h1 className="t-title flex items-center gap-3 text-[26px]"><Dot level={H.level} className="size-3" />Saúde</h1>
        <p className="text-[13.5px] text-ink-2">{verdict} Atualizado {isoTime(H.ts_brt)}.</p>
      </div>

      <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="s-proc">
        <SectionHead id="s-proc" title="Processos" />
        <ul className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule sm:grid-cols-3 lg:grid-cols-6">
          {H.processes.map(p => {
            const level = p.running ? 'ok' : p.expected === false ? 'off' : 'bad'
            return (
              <li key={p.name} className={cn('flex min-w-0 items-center gap-2.5 bg-surface px-3 py-2.5', level === 'bad' && 'bg-[var(--loss-wash)]')}>
                <Dot level={level} />
                <div className="min-w-0">
                  <div className="truncate text-[14px] t-semi">{procName(p.name)}</div>
                  <div className="text-[12px] text-ink-3 t-tab">{p.running ? `pid ${p.pid}` : p.expected === false ? 'desligado de propósito' : 'parado'}</div>
                </div>
              </li>
            )
          })}
        </ul>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="s-beats">
          <SectionHead id="s-beats" title="Batimentos">Cada bot grava um sinal a cada ciclo. Mais de 3 minutos sem sinal é um alerta.</SectionHead>
          <table className="w-full text-[13.5px] t-tab">
            <thead><tr className="border-b border-rule-strong text-left text-[12.5px] text-ink-3"><th className="py-1.5 font-normal">Bot</th><th className="font-normal">Último sinal</th><th className="text-right font-normal">Ciclos</th><th className="text-right font-normal">Erros</th></tr></thead>
            <tbody>
              {H.heartbeats.map(b => {
                const stale = b.name !== 'nightly' && (b.age_s == null || b.age_s > 180)
                return (
                  <tr key={b.name} className="border-b border-rule">
                    <td className="py-2"><span className="inline-flex items-center gap-2"><Dot level={stale ? 'warn' : 'ok'} />{procName(b.name)}</span></td>
                    <td className={stale ? 'text-loss' : ''}>{b.age_s == null ? 'nunca' : `há ${ago(b.age_s)}`}</td>
                    <td className="text-right">{b.cycles == null ? '—' : int(b.cycles)}</td>
                    <td className={cn('text-right', (b.errors ?? 0) > 0 && 'text-loss t-semi')}>{b.errors == null ? '—' : int(b.errors)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="mt-3 text-[12.5px] text-ink-3">Rotina noturna: próxima às {isoTime(H.nightly?.next_run_brt, true)}.{H.last_review ? ` Última revisão: ${H.last_review.name}.` : ''}</p>
        </section>

        <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="s-misc">
          <SectionHead id="s-misc" title="Últimas 24 horas" />
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5">
            <Stat label="Fills a mercado" sub={fills?.mark_fallbacks != null ? `${int(fills.mark_fallbacks)} usaram o preço de referência` : undefined}>{fills?.market_fills == null ? '—' : int(fills.market_fills)}</Stat>
            <Stat label="Sem cotação real" sub="fill caiu no preço de referência">{fills?.fallback_rate == null ? '—' : pct(fills.fallback_rate * 100, 1)}</Stat>
            <Stat label="Reinícios" sub={restarts.length ? restarts.map(([k, v]) => `${procName(k)} ${v}×`).join(', ') : 'nenhum'}>{int(restarts.reduce((a, [, v]) => a + v, 0))}</Stat>
            <Stat label="Disco livre" sub={X.disk?.used_frac != null ? `${pct(X.disk.used_frac * 100, 0)} usado` : undefined}>{X.disk ? `${num(X.disk.free_gb, 0)} GB` : '—'}</Stat>
          </dl>
          {fills?.reasons && Object.keys(fills.reasons).length > 0 && (
            <div className="mt-5">
              <h3 className="mb-1 text-[12.5px] text-ink-3">Por que faltou cotação</h3>
              <ul className="divide-y divide-rule border-y border-rule text-[13px]">
                {Object.entries(fills.reasons).map(([r, n]) => <li key={r} className="flex justify-between gap-3 py-1"><span className="truncate text-ink-2">{r}</span><span className="t-tab">{n}</span></li>)}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
