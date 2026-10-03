// Model backends as "bot cards" (pattern: Hummingbot dashboard bot orchestration cards).
import { useQuery } from '@tanstack/react-query'
import { Cpu, KeyRound } from 'lucide-react'
import { api, type ModelDist } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { ConfirmAction, ErrorBlock, LoadingBlock, StatusDot } from '@/components/common'
import { Histogram } from '@/components/charts/Histogram'
import { num } from '@/lib/format'

function Dist({ d, title, color }: { d: ModelDist; title: string; color: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-muted-foreground num"><span>{title}</span><span>n={d.n} · p50 {num(d.latency_p50, 0)}ms · p95 {num(d.latency_p95, 0)}ms{d.errors ? ` · ${d.errors} falhas` : ''}</span></div>
      <Histogram bins={d.conf_hist} height={70} color={color} label={`Confiança ${title}`} thresholds={[{ at: 0.35, label: 'relaxed .35', color: '#34d399' }, { at: 0.6, label: 'baseline .6' }]} />
      <div className="mt-1 flex flex-wrap gap-1">{Object.entries(d.chosen).map(([k, v]) => <Badge key={k} variant="outline">{k}: {v}</Badge>)}</div>
    </div>
  )
}

export default function ModelsTab() {
  const poll = usePollInterval()
  const q = useQuery({ queryKey: ['models'], queryFn: api.models, refetchInterval: poll })
  if (q.isLoading) return <LoadingBlock h={500} />
  if (q.error) return <ErrorBlock error={q.error} />
  const M = q.data!
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-muted-foreground num">Ciclo SOL {num(M.cycle_wall_ms, 0)} ms · ciclo meme {num(M.meme_cycle_wall_ms, 0)} ms · distribuições das últimas ~6000 decisões por modelo</p>
      <div className="grid gap-3 lg:grid-cols-2">
        {Object.values(M.models).map(m => {
          const running = m.process.running
          const lvl = !m.enabled ? 'off' : m.id === 'jev' ? (m.status === 'ativo' ? 'ok' : 'warn') : running ? 'ok' : 'bad'
          return (
            <Card key={m.id}>
              <CardHeader>
                <div>
                  <CardTitle className="flex items-center gap-2"><StatusDot level={lvl as any} /><Cpu className="size-4 text-muted-foreground" aria-hidden />{m.id} <span className="font-normal text-muted-foreground">{m.label}</span></CardTitle>
                  <CardDescription className="num">{m.kind}{m.port ? ` · porta ${m.port}` : ''} · pid {m.process.pid ?? '—'} · status {m.status}</CardDescription>
                </div>
                <div className="flex flex-col items-end gap-1.5 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">SOL</span>
                    <ConfirmAction title={`${m.enabled ? 'Desabilitar' : 'Habilitar'} ${m.id} (SOL)?`} description={m.enabled ? `Os portfólios SOL de ${m.id} param de receber decisões novas.` : `Habilita ${m.id} em models.json.${m.id === 'jev' ? ' Jev hospedado exige JEV_API_KEY no ambiente do supervisor; sem a chave fica “aguardando chave”.' : ''}`}
                      onConfirm={() => api.modelEnable(m.id, { enabled: !m.enabled })} variant="ghost" size="xs" ariaLabel={`${m.enabled ? 'Desabilitar' : 'Habilitar'} ${m.id} SOL`}>
                      <Switch checked={m.enabled} tabIndex={-1} aria-hidden className="pointer-events-none" />
                    </ConfirmAction>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Memes</span>
                    <ConfirmAction title={`${m.memes_enabled ? 'Desligar' : 'Ligar'} ${m.id} nas memecoins?`} disabled={m.id === 'von' && m.memes_enabled}
                      description={m.id === 'von' ? 'von é o padrão das memecoins e permanece ligado.' : `Portfólios meme de ${m.id} ${m.memes_enabled ? 'deixam de' : 'passam a'} receber decisões novas.`}
                      onConfirm={() => api.modelEnable(m.id, { memes_enabled: !m.memes_enabled })} variant="ghost" size="xs" ariaLabel={`${m.memes_enabled ? 'Desligar' : 'Ligar'} ${m.id} memes`}>
                      <Switch checked={m.memes_enabled} tabIndex={-1} aria-hidden className="pointer-events-none" />
                    </ConfirmAction>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="grid grid-cols-3 gap-2 text-center num">
                  <div className="rounded-lg bg-muted/40 p-2"><div className="text-[10px] uppercase text-muted-foreground">latência SOL</div><div className="text-sm font-semibold">{num(m.latency_ms, 0)} ms</div></div>
                  <div className="rounded-lg bg-muted/40 p-2"><div className="text-[10px] uppercase text-muted-foreground">latência meme</div><div className="text-sm font-semibold">{num(m.meme_latency_ms, 0)} ms</div></div>
                  <div className="rounded-lg bg-muted/40 p-2"><div className="text-[10px] uppercase text-muted-foreground">portfólios SOL</div><div className="text-sm font-semibold">{m.sol_portfolios.length}</div></div>
                </div>
                {m.id === 'jev' && <p className="flex items-center gap-1.5 text-xs text-warn"><KeyRound className="size-3.5" />Chave: {M.jev?.key_present ? 'presente' : 'ausente'} (env {M.jev?.api_key_env || 'JEV_API_KEY'}; nunca gravada em disco) · live_trading=false</p>}
                <Dist d={m.sol} title="SOL" color="#60a5fa" />
                <Dist d={m.meme} title="Memes" color="#f472b6" />
                <div className="flex flex-wrap gap-1">{m.sol_portfolios.map(p => <Badge key={p} variant="secondary">{p}</Badge>)}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
