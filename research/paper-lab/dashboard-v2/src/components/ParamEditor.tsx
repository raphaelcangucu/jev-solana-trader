// Per-portfolio gate/sizing params with client-side validation against the server hard bounds
// (dashboard/defaults.py validate_patch) + a softer check against the lab tuning bounds (lab_registry.HARD).
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { AlertTriangle, Pause, Play, RotateCcw, Save } from 'lucide-react'
import { api, type Params } from '@/lib/api'
import { Input, Label } from './ui/input'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { ConfirmAction } from './common'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog'

export const FIELD_LABELS: Record<string, string> = {
  min_confidence: 'Confiança mínima', min_prob_margin: 'Margem mín. de prob.', max_skip_noul: 'Skip noul máx.',
  buy_fraction_usdt: 'Fração de compra (USDT)', cooldown_seconds: 'Cooldown (s)', max_trades_per_hour: 'Máx. trades/hora',
}

function check(field: string, raw: string, p: Params): { err?: string; warn?: string; value?: number } {
  if (raw.trim() === '') return { err: 'obrigatório' }
  const isInt = p.ints.includes(field)
  const v = Number(raw.replace(',', '.'))
  if (!Number.isFinite(v)) return { err: 'número inválido' }
  if (isInt && !Number.isInteger(v)) return { err: 'deve ser inteiro' }
  const [lo, hi] = p.bounds[field] || [null, null]
  if (lo != null && v < lo) return { err: `mín. ${lo}` }
  if (hi != null && v > hi) return { err: `máx. ${hi}` }
  const tb = p.tuning_bounds?.[field]
  if (tb && (v < tb[0] || v > tb[1])) return { value: v, warn: `fora da faixa de tuning do lab [${tb[0]}–${tb[1]}]` }
  return { value: v }
}

export function ParamEditor({ portfolio }: { portfolio: string }) {
  const qc = useQueryClient()
  const { data: p } = useQuery({ queryKey: ['params'], queryFn: api.params })
  const cur = p?.portfolios[portfolio]
  const [form, setForm] = useState<Record<string, string>>({})
  const [confirm, setConfirm] = useState(false)
  const [ack, setAck] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (cur && p) setForm(Object.fromEntries(p.editable.map(f => [f, cur[f] == null ? '' : String(cur[f])])))
  }, [cur, p])
  const checks = useMemo(() => (p ? Object.fromEntries(p.editable.map(f => [f, check(f, form[f] ?? '', p)])) : {}), [form, p])
  if (!p || !cur) return <p className="text-sm text-muted-foreground">Sem controles de parâmetros para este portfólio.</p>
  const diffs = p.editable.filter(f => checks[f]?.value != null && Number(cur[f]) !== checks[f].value)
  const hasErr = p.editable.some(f => checks[f]?.err)
  const warns = p.editable.filter(f => checks[f]?.warn)
  const save = async () => {
    setBusy(true)
    try {
      const body = Object.fromEntries(diffs.map(f => [f, checks[f].value]))
      const r = await api.setParams(portfolio, body)
      toast.success(`Parâmetros salvos · ${portfolio}`, { description: r.warning || `${r.changes.length} alteração(ões)` })
      setConfirm(false); setAck(false)
      qc.invalidateQueries()
    } catch (e: any) { toast.error('Falhou', { description: String(e?.message || e) }) } finally { setBusy(false) }
  }
  return (
    <div className="flex flex-col gap-3">
      {cur.is_baseline_control && (
        <div className="flex items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 p-2.5 text-xs text-warn">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" /> Baseline = controle fiel ao artigo. Edite com cuidado.
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {p.editable.map(f => {
          const c = checks[f] || {}
          const [lo, hi] = p.bounds[f] || []
          const id = `pe-${portfolio}-${f}`
          return (
            <div key={f} className="flex flex-col gap-1">
              <Label htmlFor={id}>{FIELD_LABELS[f] || f} <span className="font-mono text-[10px] opacity-60">{f}</span></Label>
              <Input id={id} inputMode="decimal" value={form[f] ?? ''} aria-invalid={!!c.err} aria-describedby={`${id}-h`}
                onChange={e => setForm(s => ({ ...s, [f]: e.target.value }))} />
              <span id={`${id}-h`} className={c.err ? 'text-[11px] text-down' : c.warn ? 'text-[11px] text-warn' : 'text-[11px] text-muted-foreground'}>
                {c.err || c.warn || `limites: ${lo ?? '−∞'} – ${hi ?? '∞'}`}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" disabled={hasErr || diffs.length === 0} onClick={() => setConfirm(true)}><Save />Salvar {diffs.length ? `(${diffs.length})` : ''}</Button>
        <ConfirmAction title={cur.paused ? `Retomar ${portfolio}?` : `Pausar ${portfolio}?`}
          description={cur.paused ? 'O portfólio volta a poder negociar (paper) no próximo ciclo.' : 'O portfólio para de abrir novos trades (paper) até ser retomado. Nada é apagado.'}
          onConfirm={() => api.setParams(portfolio, { paused: !cur.paused })} variant={cur.paused ? 'secondary' : 'warn'}>
          {cur.paused ? <><Play />Retomar</> : <><Pause />Pausar</>}
        </ConfirmAction>
        <ConfirmAction title={`Restaurar padrões de ${portfolio}?`} destructive confirmLabel="Restaurar"
          description="Substitui todos os parâmetros editáveis pelos padrões do config.json e remove a pausa. A mudança é registrada em param_changes.jsonl."
          onConfirm={() => api.restore(portfolio)} variant="ghost"><RotateCcw />Restaurar padrões</ConfirmAction>
        {cur.paused && <Badge variant="warn">pausado</Badge>}
      </div>
      <AlertDialog open={confirm} onOpenChange={o => { setConfirm(o); if (!o) setAck(false) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Salvar parâmetros de {portfolio}?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="flex flex-col gap-2">
                <ul className="rounded-md border bg-muted/40 p-2 font-mono text-xs">
                  {diffs.map(f => <li key={f}>{f}: <span className="text-muted-foreground">{String(cur[f])}</span> → <b className="text-foreground">{checks[f].value}</b></li>)}
                </ul>
                {cur.is_baseline_control && <p className="text-warn">Atenção: este é um portfólio baseline (controle do artigo).</p>}
                {warns.length > 0 && (
                  <label className="flex items-start gap-2 text-warn">
                    <input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} className="mt-0.5" />
                    <span>Entendo que {warns.map(f => FIELD_LABELS[f] || f).join(', ')} {warns.length > 1 ? 'estão' : 'está'} fora da faixa de tuning do lab.</span>
                  </label>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="text-[11px] text-muted-foreground">Simulação (paper) — nenhuma ordem real é enviada.</p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <Button onClick={save} disabled={busy || (warns.length > 0 && !ack)}>Salvar</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
