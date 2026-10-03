import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Pause, Play, Search, Settings2 } from 'lucide-react'
import { api } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ConfirmAction, ErrorBlock, LoadingBlock, SectionTitle } from '@/components/common'
import { ParamEditor } from '@/components/ParamEditor'
import { brtTime } from '@/lib/format'

const BOTS: { id: 'sol' | 'meme' | 'rules' | 'lab'; label: string; desc: string }[] = [
  { id: 'sol', label: 'Bot SOL', desc: 'Todos os portfólios SOL (von/laya/poorjev/híbrido).' },
  { id: 'meme', label: 'Bot Memes', desc: 'Todos os portfólios de memecoins.' },
  { id: 'rules', label: 'Rules', desc: 'Estratégias de regra (grid, RSI, regime, Donchian).' },
  { id: 'lab', label: 'Lab', desc: 'Hipóteses H1–H4 e forks.' },
]

export default function ControlsTab() {
  const poll = usePollInterval()
  const p = useQuery({ queryKey: ['params'], queryFn: api.params, refetchInterval: poll })
  const ch = useQuery({ queryKey: ['paramChanges'], queryFn: api.paramChanges, refetchInterval: poll })
  const lab = useQuery({ queryKey: ['lab'], queryFn: api.lab })
  const [edit, setEdit] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const names = useMemo(() => Object.keys(p.data?.portfolios || {}).filter(n => n.toLowerCase().includes(q.toLowerCase())), [p.data, q])
  if (p.isLoading) return <LoadingBlock h={500} />
  if (p.error) return <ErrorBlock error={p.error} />
  const P = p.data!
  const botPaused = (id: string) => id === 'lab' ? !!lab.data?.lab_paused : !!P.bots[`${id}_paused`]
  const fields = P.editable
  return (
    <div className="flex flex-col gap-5">
      <section>
        <SectionTitle desc="Pausar um bot interrompe novos trades paper; estado e histórico são preservados.">Bots</SectionTitle>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {BOTS.map(b => {
            const paused = botPaused(b.id)
            return (
              <Card key={b.id}>
                <CardHeader><div><CardTitle>{b.label}</CardTitle><CardDescription>{b.desc}</CardDescription></div>{paused ? <Badge variant="warn">pausado</Badge> : <Badge variant="up">ativo</Badge>}</CardHeader>
                <CardContent>
                  <ConfirmAction title={paused ? `Retomar ${b.label}?` : `Pausar ${b.label}?`} description={paused ? 'Volta a negociar (paper) no próximo ciclo.' : 'Para de abrir novos trades (paper) até ser retomado.'}
                    onConfirm={() => api.pauseBot(b.id, !paused)} variant={paused ? 'secondary' : 'warn'}>{paused ? <><Play />Retomar</> : <><Pause />Pausar</>}</ConfirmAction>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section>
        <SectionTitle desc={`Limites rígidos (servidor): confiança/margem/skip 0–1 · fração 0,05–1 · cooldown ≥15s · 1–60 trades/h. Fora da faixa de tuning do lab exige confirmação extra.`}
          right={<div className="relative w-full sm:w-64"><Search className="pointer-events-none absolute left-2 top-2.5 size-4 text-muted-foreground" /><Input aria-label="Filtrar portfólios" className="pl-8" placeholder="Filtrar…" value={q} onChange={e => setQ(e.target.value)} /></div>}>
          Parâmetros por portfólio
        </SectionTitle>
        <Card>
          <CardContent className="max-h-[560px] overflow-auto pt-3">
            <table className="w-full min-w-[920px] text-xs num">
              <thead className="sticky top-0 z-10 bg-card text-left text-[11px] uppercase text-muted-foreground">
                <tr><th className="py-1.5">Portfólio</th>{fields.map(f => <th key={f} className="text-right font-mono normal-case">{f}</th>)}<th className="pl-3">Estado</th><th /></tr>
              </thead>
              <tbody>
                {names.map(n => {
                  const x = P.portfolios[n]
                  return (
                    <tr key={n} className="border-t border-border/50">
                      <td className="py-1.5 font-medium">{n}{x.is_baseline_control && <Badge variant="outline" className="ml-1">baseline</Badge>}</td>
                      {fields.map(f => <td key={f} className="text-right">{x[f] ?? '—'}</td>)}
                      <td className="pl-3">{x.paused ? <Badge variant="warn">pausado</Badge> : <span className="text-muted-foreground">ativo</span>}</td>
                      <td className="text-right"><Button size="xs" variant="outline" onClick={() => setEdit(n)} aria-label={`Editar ${n}`}><Settings2 />Editar</Button></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </section>

      <section>
        <SectionTitle desc="logs/param_changes.jsonl (mais recentes primeiro)">Histórico de alterações</SectionTitle>
        <Card>
          <CardContent className="max-h-[360px] overflow-auto pt-3">
            <table className="w-full min-w-[640px] text-xs num">
              <thead className="sticky top-0 bg-card text-left text-[11px] uppercase text-muted-foreground"><tr><th className="py-1.5">Quando (BRT)</th><th>Portfólio</th><th>Campo</th><th>De</th><th>Para</th><th>Quem</th></tr></thead>
              <tbody>{(ch.data || []).map((r, i) => (
                <tr key={i} className="border-t border-border/50" title={r.reason || ''}><td className="py-1.5">{brtTime(r.ts_brt, true)}</td><td>{r.portfolio}</td><td className="font-mono">{r.field}</td><td className="text-muted-foreground">{JSON.stringify(r.old)}</td><td>{JSON.stringify(r.new)}</td><td className="text-muted-foreground">{r.who}</td></tr>
              ))}</tbody>
            </table>
            {!ch.data?.length && <p className="py-4 text-center text-xs text-muted-foreground">Nenhuma alteração registrada.</p>}
          </CardContent>
        </Card>
      </section>

      <Dialog open={!!edit} onOpenChange={o => !o && setEdit(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>Parâmetros · {edit}</DialogTitle><DialogDescription>Validação local contra os limites rígidos; o servidor valida de novo.</DialogDescription></DialogHeader>
          {edit && <ParamEditor portfolio={edit} />}
        </DialogContent>
      </Dialog>
    </div>
  )
}
