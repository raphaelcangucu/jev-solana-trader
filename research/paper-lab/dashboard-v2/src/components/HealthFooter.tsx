// Sticky health/status footer: processes, heartbeats, last nightly review.
import { useState } from 'react'
import { ChevronUp, FileText } from 'lucide-react'
import type { Health } from '@/lib/api'
import { StatusDot } from './common'
import { ago, brtTime } from '@/lib/format'
import { cn } from '@/lib/utils'

export function HealthFooter({ health }: { health?: Health }) {
  const [open, setOpen] = useState(false)
  const h = health
  const lvl = h?.level ?? 'warn'
  return (
    <footer className="sticky bottom-0 z-30 border-t bg-background/95 backdrop-blur" aria-label="Saúde do sistema">
      <div className="mx-auto max-w-[1600px] px-3 sm:px-5">
        <button className="flex w-full items-center gap-2 py-2 text-left text-xs" aria-expanded={open} onClick={() => setOpen(o => !o)}>
          <StatusDot level={lvl} label={`saúde ${lvl}`} />
          <span className="font-medium">{lvl === 'ok' ? 'Tudo operando' : lvl === 'warn' ? 'Atenção' : 'Problema'}</span>
          <span className="hidden text-muted-foreground sm:inline num">
            · {h?.processes.filter(p => p.running).length ?? '—'}/{h?.processes.length ?? '—'} processos · erros {h?.errors ?? '—'}
            {h?.stale.length ? ` · sem heartbeat: ${h.stale.join(', ')}` : ''}{h?.down.length ? ` · parados: ${h.down.join(', ')}` : ''}
          </span>
          {h?.last_review && (
            <a href={`/api/file?path=${encodeURIComponent(h.last_review.path)}`} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="ml-auto inline-flex items-center gap-1 text-primary hover:underline">
              <FileText className="size-3.5" />revisão noturna {h.last_review.name.replace('.md', '')}
            </a>
          )}
          <ChevronUp className={cn('size-4 transition-transform', h?.last_review ? '' : 'ml-auto', open ? '' : 'rotate-180')} aria-hidden />
        </button>
        {open && h && (
          <div className="grid gap-3 pb-3 text-xs md:grid-cols-3">
            <div>
              <div className="mb-1 font-medium text-muted-foreground">Processos</div>
              <div className="flex flex-wrap gap-1">
                {h.processes.map(p => (
                  <span key={p.name} className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 num">
                    <StatusDot level={p.running ? 'ok' : p.expected === false ? 'off' : 'bad'} />{p.name}<span className="text-muted-foreground">{p.pid ?? '—'}</span>
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 font-medium text-muted-foreground">Heartbeats</div>
              <ul className="grid grid-cols-2 gap-x-3 num">
                {h.heartbeats.map(b => (
                  <li key={b.name} className="flex justify-between gap-2"><span>{b.name}</span><span className={(b.age_s ?? 999) > 180 && b.name !== 'nightly' ? 'text-warn' : 'text-muted-foreground'}>{ago(b.age_s)}{b.errors ? ` · ${b.errors} err` : ''}</span></li>
                ))}
              </ul>
            </div>
            <div>
              <div className="mb-1 font-medium text-muted-foreground">Revisões e relatórios</div>
              <p className="text-muted-foreground">Próxima revisão noturna: {brtTime(h.nightly.next_run_brt, true)} BRT · rotação {brtTime(h.nightly.next_rotation_brt, true)}</p>
              <div className="mt-1 flex flex-wrap gap-x-2">
                {[...h.reviews, ...h.criteria, ...h.reports.slice(-4)].map(p => <a key={p} className="text-primary hover:underline" target="_blank" rel="noreferrer" href={`/api/file?path=${encodeURIComponent(p)}`}>{p.split('/').pop()}</a>)}
              </div>
              <p className="mt-1 text-muted-foreground">Atualizado {brtTime(h.ts_brt)} BRT · <a className="hover:underline" href="/legacy">painel antigo</a></p>
            </div>
          </div>
        )}
      </div>
    </footer>
  )
}
