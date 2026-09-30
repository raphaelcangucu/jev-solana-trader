import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Crown, Pause, Play } from 'lucide-react'
import { api, type LabHyp, type LabMember } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/input'
import { ConfirmAction, Empty, ErrorBlock, LoadingBlock, Pnl, SectionTitle, VerdictBadge, VerdictProgress } from '@/components/common'
import { useDrawer } from '@/components/drawer-context'
import { brtTime, num, pct, usd } from '@/lib/format'
import { cn } from '@/lib/utils'

const HYP_DESC: Record<string, string> = {
  H1: 'Saídas TP/SL/trailing sobre decisões existentes',
  H2: 'Ensemble (concordância entre modelos)',
  H3: 'Ordens limite (maker) em vez de mercado',
  H4: 'Filtro de horário (só horas favoráveis)',
}

function MemberCard({ m, original, onOpen }: { m: LabMember; original?: LabMember; onOpen: () => void }) {
  const behind = m.report_label || (!m.is_original && original && (m.pnl ?? 0) < (original.pnl ?? 0) ? 'atrás da original' : null)
  return (
    <button onClick={onOpen} className={cn('w-60 shrink-0 rounded-xl border bg-card p-3 text-left hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', m.is_lead && 'border-primary/60')}>
      <div className="flex items-center gap-1.5">
        <span className="truncate text-sm font-medium" title={m.name}>{m.name}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-1">
        {m.is_original ? <Badge variant="secondary">original · nunca alterado</Badge> : <Badge variant="outline">fork</Badge>}
        {m.is_lead && <Badge variant="default"><Crown className="size-3" />fork líder = base de tuning, não veredito</Badge>}
        {behind && <Badge variant="warn">{behind}</Badge>}
      </div>
      <div className="mt-2 flex items-baseline justify-between num"><span className="font-semibold">{usd(m.equity_usd)}</span><Pnl v={m.pnl} pctV={m.pnl_pct} /></div>
      <div className="mt-0.5 flex justify-between text-[11px] text-muted-foreground num"><span>vs B&H <Pnl v={m.vs_bh} /></span><span>{m.trades ?? 0} tr</span></div>
      <div className="mt-2 flex items-center gap-2"><VerdictBadge v={m.verdict} /><VerdictProgress p={m.progress_obj} text={m.progress} /></div>
      {m.params_diff && <pre className="mt-1 max-h-16 overflow-auto rounded bg-muted/50 p-1 text-[10px]">{JSON.stringify(m.params_diff)}</pre>}
    </button>
  )
}

export default function LabTab() {
  const poll = usePollInterval()
  const q = useQuery({ queryKey: ['lab'], queryFn: api.lab, refetchInterval: poll })
  const { open } = useDrawer()
  const [onlyForks, setOnlyForks] = useState(false)
  const byHyp = useMemo(() => {
    const g: Record<string, LabHyp[]> = {}
    for (const h of q.data?.hypotheses || []) (g[h.hyp || (h.parent ? 'fork' : '?')] ||= []).push(h)
    return g
  }, [q.data])
  if (q.isLoading) return <LoadingBlock h={600} />
  if (q.error) return <ErrorBlock error={q.error} />
  const L = q.data!
  const st = L.status || {}
  const ind = (L.rules_status?.indicators || {}).sol || {}
  const lineages = L.lineages.filter(l => !onlyForks || l.members.length > 1).sort((a, b) => b.members.length - a.members.length || a.lineage.localeCompare(b.lineage))
  const anyForks = L.lineages.some(l => l.members.length > 1)
  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Laboratório & regras</CardTitle>
            <CardDescription className="num">lab: ciclos {st.cycles ?? '—'} · erros {st.errors ?? '—'} · decisões-fonte {st.processed_source_decisions ?? '—'} · vereditos {brtTime(L.verdicts_ts_brt, true)} · próxima revisão {brtTime(L.nightly?.next_run_brt, true)} BRT</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <ConfirmAction title={L.lab_paused ? 'Retomar o Lab?' : 'Pausar o Lab?'} description={L.lab_paused ? 'Hipóteses H1–H4 e forks voltam a negociar (paper).' : 'Todas as hipóteses e forks param de abrir novos trades (paper). Nada é apagado.'}
              onConfirm={() => api.pauseBot('lab', !L.lab_paused)} variant={L.lab_paused ? 'secondary' : 'warn'}>{L.lab_paused ? <><Play />Retomar Lab</> : <><Pause />Pausar Lab</>}</ConfirmAction>
            <ConfirmAction title={L.rules_paused ? 'Retomar Rules?' : 'Pausar Rules?'} description={L.rules_paused ? 'Estratégias de regra voltam a negociar (paper).' : 'Estratégias de regra (grid, RSI, regime, Donchian) param de abrir novos trades (paper).'}
              onConfirm={() => api.pauseBot('rules', !L.rules_paused)} variant={L.rules_paused ? 'secondary' : 'warn'}>{L.rules_paused ? <><Play />Retomar Rules</> : <><Pause />Pausar Rules</>}</ConfirmAction>
          </div>
        </CardHeader>
        <CardContent><p className="text-xs text-muted-foreground">{L.verdict_rule}</p></CardContent>
      </Card>

      <section>
        <SectionTitle desc={`SOL 1h: fechamento ${num(ind.close_1h, 3)} · EMA12 ${num(ind.ema12, 3)} · EMA26 ${num(ind.ema26, 3)} · RSI ${num(ind.rsi, 1)} · regime ${ind.regime_bull ? 'alta' : ind.regime_bull === false ? 'baixa' : '—'} · rules ciclos ${L.rules_status?.cycles ?? '—'} erros ${L.rules_status?.errors ?? '—'}`}>
          Estratégias de regra e híbridos
        </SectionTitle>
        <Card>
          <CardContent className="max-h-[420px] overflow-auto pt-3">
            {L.rule_rows.length ? (
              <table className="w-full min-w-[720px] text-xs num">
                <thead className="sticky top-0 bg-card text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Portfólio</th><th>Ativo</th><th>Tipo</th><th className="text-right">Valor</th><th className="text-right">vs B&H</th><th className="text-right">Trades</th><th className="text-right">Exp.</th><th className="pl-3">Veredito</th></tr></thead>
                <tbody>
                  {L.rule_rows.sort((a, b) => (b.vs_bh_pct ?? -1e9) - (a.vs_bh_pct ?? -1e9)).map(r => (
                    <tr key={r.name} className="cursor-pointer border-t border-border/50 hover:bg-accent/40" onClick={() => open(r.name)} tabIndex={0} onKeyDown={e => e.key === 'Enter' && open(r.name)}>
                      <td className="py-1.5 font-medium">{r.name}{r.paused && <Badge variant="warn" className="ml-1">pausado</Badge>}</td><td>{r.asset}</td><td><Badge variant="outline">{r.kind === 'hybrid' ? 'híbrido' : 'regra'}</Badge></td>
                      <td className="text-right">{usd(r.equity)}</td><td className="text-right"><Pnl v={r.vs_bh} pctV={r.vs_bh_pct} /></td><td className="text-right">{r.trades ?? 0}</td><td className="text-right">{pct(r.exposure_pct, 0)}</td>
                      <td className="pl-3"><div className="flex items-center gap-2"><VerdictBadge v={r.verdict} /><VerdictProgress p={r.progress} text={r.progress_text} compact /></div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <Empty>Aguardando rules_bot.</Empty>}
          </CardContent>
        </Card>
      </section>

      <section>
        <SectionTitle desc="Liga/desliga por portfólio ou por hipótese inteira (pausa paper; nada é apagado).">Hipóteses H1–H4</SectionTitle>
        <div className="grid gap-3 lg:grid-cols-2">
          {['H1', 'H2', 'H3', 'H4'].map(h => {
            const list = (byHyp[h] || []).sort((a, b) => a.name.localeCompare(b.name))
            const allPaused = list.length > 0 && list.every(x => x.paused)
            return (
              <Card key={h}>
                <CardHeader>
                  <div><CardTitle>{h} · {HYP_DESC[h]}</CardTitle><CardDescription>{list.length} portfólios · {list.filter(x => x.paused).length} pausados</CardDescription></div>
                  {list.length > 0 && (
                    <ConfirmAction title={allPaused ? `Ligar todas de ${h}?` : `Desligar todas de ${h}?`} description={`${list.length} portfólios de ${h} serão ${allPaused ? 'retomados' : 'pausados'} (paper).`}
                      onConfirm={() => Promise.all(list.map(x => api.setParams(x.name, { paused: !allPaused })))} variant={allPaused ? 'secondary' : 'warn'} size="xs">{allPaused ? `Ligar ${h}` : `Desligar ${h}`}</ConfirmAction>
                  )}
                </CardHeader>
                <CardContent>
                  {list.length ? (
                    <ul className="divide-y divide-border/50">
                      {list.map(x => (
                        <li key={x.name} className="flex items-center gap-2 py-1.5 text-xs">
                          <button className="min-w-0 flex-1 text-left" onClick={() => open(x.name)}>
                            <div className="truncate font-medium" title={x.label || x.name}>{x.name}</div>
                            <div className="flex gap-2 text-[11px] text-muted-foreground num"><span>{usd(x.equity_usd)}</span><Pnl v={x.pnl} /><span>vs B&H <Pnl v={x.vs_bh} /></span><span>{x.trades ?? 0} tr</span>{x.open_order && <Badge variant="outline">ordem limite aberta</Badge>}</div>
                          </button>
                          <VerdictBadge v={x.verdict} />
                          <ConfirmAction title={x.paused ? `Ligar ${x.name}?` : `Desligar ${x.name}?`} description={x.paused ? 'Volta a negociar (paper).' : 'Para de abrir novos trades (paper).'} onConfirm={() => api.setParams(x.name, { paused: !x.paused })} variant="ghost" size="xs" ariaLabel={`${x.paused ? 'Ligar' : 'Desligar'} ${x.name}`}>
                            <Switch checked={!x.paused} tabIndex={-1} aria-hidden className="pointer-events-none" />
                          </ConfirmAction>
                        </li>
                      ))}
                    </ul>
                  ) : <Empty>Nenhum portfólio.</Empty>}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section>
        <SectionTitle desc="Original → forks lado a lado. Forks que ficam atrás só recebem o rótulo; nada é desativado."
          right={<div className="flex items-center gap-2"><Switch id="onlyforks" checked={onlyForks} onCheckedChange={setOnlyForks} /><Label htmlFor="onlyforks">só linhagens com forks</Label></div>}>
          Linhagens
        </SectionTitle>
        {!anyForks && <p className="mb-2 text-xs text-muted-foreground">Nenhum fork ainda — tuning só com dados suficientes (limite: 1 fork por linhagem a cada {L.caps?.per_lineage_days ?? 7} dias, {L.caps?.total ?? 40} no total).</p>}
        {lineages.length === 0 ? <Empty>Nenhuma linhagem com forks.</Empty> : (
          <div className="flex flex-col gap-2">
            {lineages.filter(l => l.members.length > 1).map(l => {
              const orig = l.members.find(x => x.is_original) || l.members[0]
              return (
                <div key={l.lineage} className="rounded-xl border bg-muted/20 p-2">
                  <div className="mb-1.5 px-1 text-[11px] text-muted-foreground">linhagem <b className="text-foreground">{l.lineage}</b>{l.lead && <> · líder: {l.lead}</>}</div>
                  <div className="flex items-stretch gap-2 overflow-x-auto pb-1">
                    {l.members.map((m, i) => (
                      <div key={m.name} className="flex items-center gap-2">
                        {i > 0 && <ArrowRight className="size-4 shrink-0 text-muted-foreground" aria-label="fork de" />}
                        <MemberCard m={m} original={orig} onOpen={() => open(m.name)} />
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
            {lineages.some(l => l.members.length === 1) && (
              <div>
                <div className="mb-1.5 text-[11px] text-muted-foreground">Originais ainda sem forks ({lineages.filter(l => l.members.length === 1).length})</div>
                <div className="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-2 [&>button]:w-full">
                  {lineages.filter(l => l.members.length === 1).map(l => <MemberCard key={l.lineage} m={l.members[0]} onOpen={() => open(l.members[0].name)} />)}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      <section>
        <SectionTitle desc="Atualizado pelo job noturno a cada 30 min.">Vereditos dos originais</SectionTitle>
        <Card>
          <CardContent className="max-h-[360px] overflow-auto pt-3">
            {L.original_verdicts.length ? (
              <table className="w-full min-w-[560px] text-xs">
                <thead className="sticky top-0 bg-card text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Portfólio</th><th>Veredito</th><th>Progresso</th><th>Motivo</th></tr></thead>
                <tbody>{L.original_verdicts.sort((a, b) => a.name.localeCompare(b.name)).map(v => (
                  <tr key={v.name} className="border-t border-border/50"><td className="py-1.5 font-medium">{v.name}</td><td><VerdictBadge v={v.verdict} /></td><td className="text-muted-foreground num">{v.progress}</td><td className="text-muted-foreground">{v.reason}</td></tr>
                ))}</tbody>
              </table>
            ) : <Empty>Aguardando job noturno.</Empty>}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
