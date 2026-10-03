// Controle: pausas dos bots, modelos ligados, parâmetros por tipo de teste (com origem e limites) e histórico.
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, ApiError } from '@/lib/api'
import { usePollInterval } from '@/lib/live'
import { isoTime, tsTime } from '@/lib/format'
import { PARAM_DEFS, READ_ONLY_TYPES, TYPE_FIELDS, TYPE_NAMES, fmtParam, getPath } from '@/lib/params'
import { useEntries } from '@/lib/queries'
import { FieldEditor } from '@/components/ParamsView'
import { Confirm, ErrorNote, Loading, Note, SectionHead, Switch } from '@/components/ui'

const BOTS: { id: 'sol' | 'meme' | 'rules' | 'lab'; label: string; what: string }[] = [
  { id: 'sol', label: 'Bot de SOL', what: 'modelos e híbrido em SOL' },
  { id: 'meme', label: 'Bot de memecoins', what: 'modelos nas 7 memecoins' },
  { id: 'rules', label: 'Bot de regras', what: 'grade, RSI, regime e Donchian' },
  { id: 'lab', label: 'Bot do laboratório', what: 'hipóteses H1 a H4 e forks' },
]

function nest(changes: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [p, v] of Object.entries(changes)) {
    const i = p.indexOf('.')
    if (i < 0) { out[p] = v; continue }
    const g = p.slice(0, i)
    const grp = (out[g] as Record<string, unknown> | undefined) ?? {}
    grp[p.slice(i + 1)] = v
    out[g] = grp
  }
  return out
}

function Toggles() {
  const qc = useQueryClient()
  const params = useQuery({ queryKey: ['params'], queryFn: api.params })
  const [ask, setAsk] = useState<null | { kind: 'bot'; id: 'sol' | 'meme' | 'rules' | 'lab'; label: string; to: boolean } | { kind: 'model'; id: string; field: 'enabled' | 'memes_enabled'; label: string; to: boolean }>(null)
  const [err, setErr] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: async () => {
      if (!ask) return
      if (ask.kind === 'bot') await api.pauseBot(ask.id, ask.to)
      else await api.modelEnable(ask.id, { [ask.field]: ask.to })
    },
    onSuccess: () => { setAsk(null); setErr(null); toast.success('Alteração salva'); ['params', 'lab', 'models', 'health'].forEach(k => qc.invalidateQueries({ queryKey: [k] })) },
    onError: e => { setAsk(null); setErr(e instanceof ApiError ? e.message : String(e)) },
  })
  if (params.isLoading) return <Loading h={200} />
  if (params.error || !params.data) return <ErrorNote error={params.error} what="controles" />
  const P = params.data
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="c-bots">
        <SectionHead id="c-bots" title="Bots">Pausar um bot para todos os testes dele no próximo ciclo. As carteiras ficam como estão.</SectionHead>
        <ul className="divide-y divide-rule border-y border-rule">
          {BOTS.map(b => {
            const paused = !!P.bots?.[`${b.id}_paused`]
            return (
              <li key={b.id} className="flex items-center justify-between gap-4 py-3">
                <div><div className="t-semi text-[15px]">{b.label}</div><div className="text-[13px] text-ink-3">{b.what}</div></div>
                <label className="flex items-center gap-2 text-[13.5px] text-ink-2">
                  {paused ? 'pausado' : 'rodando'}
                  <Switch checked={!paused} onCheckedChange={v => setAsk({ kind: 'bot', id: b.id, label: b.label, to: !v })} aria-label={`${b.label}: ${paused ? 'retomar' : 'pausar'}`} />
                </label>
              </li>
            )
          })}
        </ul>
      </section>
      <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="c-models">
        <SectionHead id="c-models" title="Modelos">Ligar ou desligar um modelo para os testes que dependem dele.</SectionHead>
        <ul className="divide-y divide-rule border-y border-rule">
          {Object.entries(P.models || {}).map(([id, md]) => (
            <li key={id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4 py-3">
              <div className="min-w-0"><div className="t-semi text-[15px]">{md.label || id}</div><div className="truncate text-[13px] text-ink-3">{md.kind ?? ''}</div></div>
              <label className="flex items-center gap-2 text-[13px] text-ink-2">SOL
                <Switch checked={md.enabled} onCheckedChange={v => setAsk({ kind: 'model', id, field: 'enabled', label: `${md.label || id} em SOL`, to: v })} aria-label={`${md.label || id}: ligado em SOL`} />
              </label>
              <label className="flex items-center gap-2 text-[13px] text-ink-2">memes
                <Switch checked={md.memes_enabled} onCheckedChange={v => setAsk({ kind: 'model', id, field: 'memes_enabled', label: `${md.label || id} nas memecoins`, to: v })} aria-label={`${md.label || id}: ligado nas memecoins`} />
              </label>
            </li>
          ))}
        </ul>
        {err && <p role="alert" className="mt-3 text-[13px] text-loss">O servidor recusou: {err}</p>}
      </section>
      <Confirm open={!!ask} onOpenChange={o => { if (!o) setAsk(null) }} busy={m.isPending} onConfirm={() => m.mutate()}
        title={!ask ? '' : ask.kind === 'bot' ? `${ask.to ? 'Pausar' : 'Retomar'} ${ask.label.toLowerCase()}?` : `${ask.to ? 'Ligar' : 'Desligar'} ${ask.label}?`}
        confirmLabel={!ask ? 'Confirmar' : ask.kind === 'bot' ? (ask.to ? 'Pausar' : 'Retomar') : (ask.to ? 'Ligar' : 'Desligar')} danger={ask?.to === true && ask.kind === 'bot'}>
        Vale a partir do próximo ciclo e fica registrado no histórico de mudanças.
      </Confirm>
    </div>
  )
}

function TypeParams() {
  const types = useQuery({ queryKey: ['paramsTypes'], queryFn: api.paramsTypes })
  const { entries } = useEntries()
  if (types.isLoading) return <Loading h={300} />
  if (types.error || !types.data) return <ErrorNote error={types.error} what="parâmetros por tipo" />
  const T = types.data
  const count = (t: string) => entries.filter(e => e.row.test_type === t).length
  const ORDER = ['model_gated', 'hybrid', 'rule_grid', 'rule_rsi', 'rule_regime', 'rule_donchian', 'lab_h1_exits', 'lab_h2_ensemble', 'lab_h3_limit', 'lab_h4_hours']
  const ids = Object.keys(T.types).filter(t => !READ_ONLY_TYPES.has(t)).sort((a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99))
  return (
    <section aria-labelledby="c-types">
      <SectionHead id="c-types" title="Parâmetros por tipo de teste">
        Valem para todos os testes do tipo, salvo quando um perfil, ativo, portfólio ou ajuste manual diz outra coisa. O servidor valida todos os testes antes de gravar em params.json.
      </SectionHead>
      {T.doc_errors?.length ? <p role="alert" className="mb-3 text-[13px] text-loss">params.json com erro: {T.doc_errors.join('; ')}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {ids.map(t => {
          const v = T.types[t]
          const fields = (TYPE_FIELDS[t] ?? []).filter(f => getPath(v.effective, f) !== undefined || f === 'hours')
          const note = (v.layer as { note?: string } | undefined)?.note
          const n = count(t)
          return (
            <article key={t} className="sheet rounded-xl p-4 sm:p-5">
              <header className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="t-title text-[17px]">{TYPE_NAMES[t] ?? t}</h3>
                <span className="text-[12.5px] text-ink-3 t-tab">{n ? `${n} ${n === 1 ? 'teste' : 'testes'}` : 'sem testes no placar'}</span>
              </header>
              {note && <p className="mt-1 text-[13px] text-ink-2">{note}</p>}
              {v.errors.length > 0 && <p role="alert" className="mt-2 text-[12.5px] text-loss">{v.errors.join('; ')}</p>}
              <div className="mt-4">
                {fields.length ? (
                  <FieldEditor key={JSON.stringify(fields.map(f => getPath(v.effective, f)))} fields={fields} current={v.effective} provenance={v.provenance}
                    limits={Object.fromEntries(fields.map(f => [f, { min: PARAM_DEFS[f]?.min, max: f === 'gates.buy_fraction_usdt' ? (getPath(v.effective, 'limits.buy_fraction_usdt_max') as number | undefined) ?? PARAM_DEFS[f]?.max : f === 'gates.max_trades_per_hour' ? (getPath(v.effective, 'limits.max_trades_per_hour_max') as number | undefined) ?? 8 : PARAM_DEFS[f]?.max }]))}
                    shadowed={f => { const pv = v.provenance[f] ?? ''; return /^(models|assets|portfolios)\./.test(pv) ? pv : null }}
                    confirmTitle={`Salvar ${TYPE_NAMES[t] ?? t}?`} queryKeys={['paramsTypes', 'effective', 'overview']}
                    save={ch => api.setLayer('types', t, { set: nest(ch) })} />
                ) : <p className="text-[13px] text-ink-3">Nada específico para ajustar aqui: os portões vêm do perfil ({fmtParam('gates.min_confidence', getPath(v.effective, 'gates.min_confidence'))} de confiança).</p>}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

function History() {
  const poll = usePollInterval(30_000)
  const q = useQuery({ queryKey: ['paramChanges'], queryFn: api.paramChanges, refetchInterval: poll })
  const rows = (q.data ?? []).slice(0, 14)
  return (
    <section className="sheet rounded-xl p-4 sm:p-6" aria-labelledby="c-hist">
      <SectionHead id="c-hist" title="Histórico de mudanças">As últimas alterações de parâmetros, pausas e forks, de quem quer que tenham vindo.</SectionHead>
      {q.isLoading ? <Loading h={120} /> : rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule text-[13.5px]">
          {rows.map((r, i) => (
            <li key={i} className="grid grid-cols-[96px_minmax(0,1fr)] gap-3 py-1.5 sm:grid-cols-[96px_minmax(0,1fr)_auto]">
              <span className="text-ink-3 t-tab">{r.ts_brt ? isoTime(r.ts_brt, true) : tsTime(r.ts, true)}</span>
              <span className="min-w-0 truncate">
                <b className="t-semi">{r.layer ?? r.portfolio ?? '—'}</b> {r.type === 'fork_created' ? 'fork criado' : `${PARAM_DEFS[r.field]?.label ?? PARAM_DEFS[`gates.${r.field}`]?.label ?? r.field ?? ''}: ${JSON.stringify(r.old)} para ${JSON.stringify(r.new)}`}
              </span>
              <span className="hidden text-ink-3 sm:block">{r.who ?? ''}</span>
            </li>
          ))}
        </ul>
      ) : <Note>Nenhuma mudança registrada ainda.</Note>}
    </section>
  )
}

export default function Controle() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
        <h1 className="t-title text-[26px]">Controle</h1>
        <p className="max-w-[620px] text-[13.5px] text-ink-2">Toda gravação pede confirmação, é validada pelo servidor e fica no histórico. Para ajustar um teste só, abra-o no Placar.</p>
      </div>
      <Toggles />
      <TypeParams />
      <History />
    </div>
  )
}
