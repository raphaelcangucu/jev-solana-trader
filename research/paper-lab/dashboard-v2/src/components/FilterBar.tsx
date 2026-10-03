// Uma linha de controles acima de tudo o que ela filtra: ordenação, família, ativo, busca.
import { Search, X } from 'lucide-react'
import { SORTS, type AssetFilter, type FamilyFilter } from '@/lib/board'
import { FAMILIES, MEMES } from '@/lib/describe'
import { useFilters } from '@/lib/filters'
import { cn } from '@/lib/utils'
import { Tip } from './ui'

function Pill({ on, onClick, children, color }: { on: boolean; onClick: () => void; children: React.ReactNode; color?: string }) {
  return (
    <button type="button" aria-pressed={on} onClick={onClick}
      className={cn('inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[13px] t-cond transition-colors',
        on ? 'border-ink bg-ink text-surface' : 'border-rule-strong bg-surface text-ink-2 hover:border-ink-3 hover:text-ink')}>
      {color && <i aria-hidden className="inline-block size-[7px] rounded-full" style={{ background: color, boxShadow: on ? '0 0 0 1.5px var(--surface)' : undefined }} />}
      {children}
    </button>
  )
}

const FAM_BASE: { key: FamilyFilter; label: string }[] = [
  { key: 'von', label: 'Modelos von' }, { key: 'laya', label: 'Laya' }, { key: 'poorjev', label: 'poorjev' },
  { key: 'rules', label: 'Regras' }, { key: 'hybrid', label: 'Híbridos' }, { key: 'lab', label: 'Hipóteses' }, { key: 'forks', label: 'Forks' },
]
const FAM_ORDER = FAM_BASE.map(f => ({ ...f, color: FAMILIES.find(x => x.key === f.key)?.color }))

export function FilterBar({ showSort = true, count, total }: { showSort?: boolean; count: number; total: number }) {
  const f = useFilters()
  const toggleFam = (k: FamilyFilter) => f.setFam(f.fam === k ? 'all' : k)
  const toggleAsset = (a: AssetFilter) => f.setAsset(f.asset === a ? 'all' : a)
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2.5">
        {showSort && (
          <div role="group" aria-label="Ordenar por" className="inline-flex rounded-lg border border-rule-strong bg-surface p-[3px]">
            {SORTS.map(s => (
              <Tip key={s.key} content={s.hint}>
                <button type="button" aria-pressed={f.sort === s.key} onClick={() => f.setSort(s.key)}
                  className={cn('h-8 rounded-md px-3 text-[13.5px] transition-colors', f.sort === s.key ? 'bg-ink text-surface t-semi' : 'text-ink-2 hover:text-ink')}>
                  {s.label}
                </button>
              </Tip>
            ))}
          </div>
        )}
        <label className="relative ml-auto flex w-full items-center sm:w-[260px]">
          <span className="sr-only">Buscar teste</span>
          <Search aria-hidden className="pointer-events-none absolute left-2.5 size-4 text-ink-3" />
          <input value={f.q} onChange={e => f.setQ(e.target.value)} placeholder="Buscar: poorjev, WIF, saídas…"
            className="h-9 w-full rounded-lg border border-rule-strong bg-surface pl-8 pr-8 text-[14px] placeholder:text-ink-3 focus:border-ink focus:outline-none focus-visible:outline-2" />
          {f.q && <button type="button" onClick={() => f.setQ('')} className="absolute right-1.5 grid size-6 place-items-center rounded text-ink-3 hover:text-ink" aria-label="Limpar busca"><X className="size-4" /></button>}
        </label>
      </div>
      <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0" role="group" aria-label="Filtrar por família">
        {FAM_ORDER.map(x => <Pill key={x.key} on={f.fam === x.key} onClick={() => toggleFam(x.key)} color={x.color}>{x.label}</Pill>)}
        <span aria-hidden className="mx-1 hidden w-px self-stretch bg-rule sm:block" />
        <Pill on={f.asset === 'SOL'} onClick={() => toggleAsset('SOL')}>SOL</Pill>
        <Pill on={f.asset === 'memes'} onClick={() => toggleAsset('memes')}>Memecoins</Pill>
        {MEMES.map(m => <Pill key={m} on={f.asset === m} onClick={() => toggleAsset(m)}>{m}</Pill>)}
      </div>
      <p className="text-[12.5px] text-ink-3 t-tab" aria-live="polite">
        {count === total ? `${total} testes` : `${count} de ${total} testes`}
        {f.active && <button type="button" onClick={f.reset} className="ml-2 text-ink-2 underline underline-offset-2 hover:text-ink">limpar filtros</button>}
      </p>
    </div>
  )
}
