// Parâmetros efetivos com selo de origem + editor com validação, confirmação e erros inline.
import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError } from '@/lib/api'
import { layerName } from '@/lib/describe'
import { PARAM_DEFS, SHOWN_GROUPS, flatten, fmtParam, getPath, parseInput, serverErrorText, toInput } from '@/lib/params'
import { cn } from '@/lib/utils'
import { Button, Confirm, Tip } from './ui'

const LAYER_TONE: Record<string, string> = {
  'padrão': 'border-rule-strong text-ink-3', perfil: 'border-rule-strong text-ink-2', tipo: 'border-rule-strong text-ink-2',
  modelo: 'border-rule-strong text-ink-2', ativo: 'border-rule-strong text-ink-2', 'portfólio': 'border-ink-2 text-ink',
  fork: 'border-ink-2 text-ink', 'ajuste manual': 'border-ink bg-ink text-surface',
}
export function LayerBadge({ prov }: { prov?: string }) {
  if (!prov) return null
  const n = layerName(prov)
  return (
    <Tip content={`Vem da camada "${prov}" de params.json${prov === 'overlay' ? ' (ajuste feito pelo painel, em tempo real)' : ''}.`}>
      <span className={cn('inline-flex h-[19px] items-center rounded-full border px-2 text-[11px] leading-none t-cond', LAYER_TONE[n] ?? 'border-rule-strong text-ink-2')}>{n}</span>
    </Tip>
  )
}

export function ParamsTable({ effective, provenance }: { effective: Record<string, unknown>; provenance: Record<string, string> }) {
  const groups = useMemo(() => SHOWN_GROUPS.map(g => {
    const v = effective[g.key]
    if (v == null) return { ...g, rows: [] as [string, unknown][] }
    if (g.key === 'exits' && !(v as { enabled?: boolean }).enabled) return { ...g, rows: [['exits.enabled', false]] as [string, unknown][] }
    if (g.key === 'regime_filter' && !(v as { enabled?: boolean }).enabled) return { ...g, rows: [['regime_filter.enabled', false]] as [string, unknown][] }
    if (g.key === 'exec' && (v as { mode?: string }).mode !== 'limit') {
      return { ...g, rows: flatten(v as Record<string, unknown>, 'exec').filter(([p]) => !['exec.offset_bps', 'exec.ttl_min', 'exec.fee_bps'].includes(p)) }
    }
    return { ...g, rows: Array.isArray(v) ? [[g.key, v]] as [string, unknown][] : flatten(v as Record<string, unknown>, g.key) }
  }).filter(g => g.rows.length), [effective])
  return (
    <div className="grid gap-4">
      {groups.map(g => (
        <div key={g.key}>
          <h4 className="mb-1 text-[13px] text-ink-3">{g.label}</h4>
          <dl className="divide-y divide-rule border-y border-rule">
            {g.rows.map(([p, v]) => (
              <div key={p} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 py-1.5">
                <dt className="min-w-0 truncate text-[13.5px] text-ink-2" title={p}>{PARAM_DEFS[p]?.label ?? p}</dt>
                <dd className="t-tab text-right text-[14px] t-semi">{fmtParam(p, v)}</dd>
                <dd className="w-[92px] text-right"><LayerBadge prov={provenance[p] ?? provenance[p.split('.')[0]]} /></dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  )
}

/** Editor de um conjunto de campos. `save` recebe só o que mudou, em {caminho: valor}. */
export function FieldEditor({ fields, current, provenance, limits, save, title, confirmTitle, note, queryKeys, shadowed }: {
  fields: string[]; current: Record<string, unknown>; provenance?: Record<string, string>
  limits?: Record<string, { min?: number; max?: number }>; save: (changes: Record<string, unknown>) => Promise<unknown>
  title?: string; confirmTitle: string; note?: React.ReactNode; queryKeys: string[]
  /** camada mais forte que define este campo (mudar aqui não teria efeito) */
  shadowed?: (path: string) => string | null
}) {
  const qc = useQueryClient()
  const init = useMemo(() => Object.fromEntries(fields.map(f => [f, toInput(f, getPath(current, f))])), [fields, current])
  const [draft, setDraft] = useState<Record<string, string>>(init)
  const [confirm, setConfirm] = useState(false)
  const [serverErr, setServerErr] = useState<string | null>(null)
  const parsed = useMemo(() => Object.fromEntries(fields.map(f => [f, PARAM_DEFS[f]?.kind === 'bool' ? { ok: true as const, v: draft[f] === 'true' } : parseInput(f, draft[f] ?? '', limits?.[f])])), [fields, draft, limits])
  const changes = useMemo(() => {
    const out: Record<string, unknown> = {}
    for (const f of fields) {
      const p = parsed[f]
      if (p.ok && JSON.stringify(p.v) !== JSON.stringify(getPath(current, f) ?? null)) out[f] = p.v
    }
    return out
  }, [fields, parsed, current])
  const invalid = fields.some(f => !parsed[f].ok)
  const dirty = Object.keys(changes).length > 0
  const m = useMutation({
    mutationFn: () => save(changes),
    onSuccess: () => { setConfirm(false); setServerErr(null); toast.success('Parâmetros salvos'); queryKeys.forEach(k => qc.invalidateQueries({ queryKey: [k] })) },
    onError: (e: unknown) => { setConfirm(false); setServerErr(e instanceof ApiError ? serverErrorText(e.message) : String(e)) },
  })
  return (
    <div>
      {title && <h4 className="mb-2 t-semi text-[14px]">{title}</h4>}
      <div className="grid gap-x-5 gap-y-3 sm:grid-cols-2">
        {fields.map(f => {
          const def = PARAM_DEFS[f]
          const p = parsed[f]
          const id = `fld-${f.replace(/\W/g, '-')}-${title ?? ''}`.replace(/\s/g, '')
          const lim = limits?.[f]
          const shadow = shadowed?.(f) ?? null
          const limTxt = !lim ? '' : lim.min != null && lim.max != null ? `; limite ${fmtParam(f, lim.min)} a ${fmtParam(f, lim.max)}` : lim.min != null ? `; mínimo ${fmtParam(f, lim.min)}` : lim.max != null ? `; máximo ${fmtParam(f, lim.max)}` : ''
          return (
            <div key={f} className="min-w-0">
              <label htmlFor={id} className="flex items-center justify-between gap-2 text-[13px] text-ink-2">
                <span className="truncate">{def?.label ?? f}</span>
                {provenance && <LayerBadge prov={provenance[f]} />}
              </label>
              {def?.kind === 'bool' ? (
                <select id={id} value={draft[f]} disabled={!!shadow} onChange={e => setDraft(d => ({ ...d, [f]: e.target.value }))}
                  className="mt-1 h-9 w-full rounded-md border border-rule-strong bg-surface px-2 text-[14px]">
                  <option value="true">sim</option><option value="false">não</option>
                </select>
              ) : (
                <div className="relative mt-1">
                  <input id={id} disabled={!!shadow} inputMode={def?.kind === 'hours' ? 'text' : 'decimal'} value={draft[f] ?? ''} aria-invalid={!p.ok}
                    aria-describedby={!p.ok ? `${id}-err` : undefined}
                    onChange={e => setDraft(d => ({ ...d, [f]: e.target.value }))}
                    className={cn('h-9 w-full rounded-md border bg-surface px-2.5 pr-12 text-[14px] t-tab focus:outline-none focus-visible:outline-2',
                      p.ok ? 'border-rule-strong focus:border-ink' : 'border-loss', shadow && 'opacity-60')} />
                  <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[12px] text-ink-3">{def?.kind === 'pct' ? '%' : def?.unit ?? ''}</span>
                </div>
              )}
              {shadow ? <p className="mt-1 text-[12px] text-ink-3">Definido na camada {layerName(shadow)} ({shadow}), que vale por cima do tipo. Mude lá.</p>
                : !p.ok ? <p id={`${id}-err`} className="mt-1 text-[12px] text-loss">{p.err}</p>
                : <p className="mt-1 text-[12px] text-ink-3 t-tab">agora {fmtParam(f, getPath(current, f))}{limTxt}</p>}
            </div>
          )
        })}
      </div>
      {serverErr && <p role="alert" className="mt-3 whitespace-pre-line rounded-md border border-loss/50 px-3 py-2 text-[13px] text-loss">O servidor recusou: {serverErr}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button variant="ink" size="sm" disabled={!dirty || invalid || m.isPending} onClick={() => setConfirm(true)}>Salvar</Button>
        {dirty && <Button variant="ghost" size="sm" onClick={() => { setDraft(init); setServerErr(null) }}>Desfazer</Button>}
        {note && <span className="text-[12.5px] text-ink-3">{note}</span>}
      </div>
      <Confirm open={confirm} onOpenChange={setConfirm} title={confirmTitle} confirmLabel="Salvar parâmetros" busy={m.isPending} onConfirm={() => m.mutate()}>
        <ul className="mt-1 grid gap-1">
          {Object.entries(changes).map(([f, v]) => (
            <li key={f} className="t-tab"><span className="text-ink">{PARAM_DEFS[f]?.label ?? f}</span>: {fmtParam(f, getPath(current, f))} para <b className="text-ink">{fmtParam(f, v)}</b></li>
          ))}
        </ul>
        <p className="mt-2">O servidor valida de novo antes de gravar e a mudança fica registrada no histórico.</p>
      </Confirm>
    </div>
  )
}
