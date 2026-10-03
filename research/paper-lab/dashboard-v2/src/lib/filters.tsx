// Estado dos filtros (compartilhado entre Placar e Famílias); a ordenação fica lembrada neste navegador.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AssetFilter, FamilyFilter, SortKey } from './board'

interface FilterState {
  sort: SortKey; setSort: (k: SortKey) => void
  fam: FamilyFilter; setFam: (f: FamilyFilter) => void
  asset: AssetFilter; setAsset: (a: AssetFilter) => void
  q: string; setQ: (q: string) => void
  reset: () => void
  active: boolean
}
const Ctx = createContext<FilterState | null>(null)
const KEY = 'paperlab.sort'

export function FilterProvider({ children }: { children: ReactNode }) {
  const [sort, setSort] = useState<SortKey>(() => {
    try { const v = localStorage.getItem(KEY); return v === 'habilidade' || v === 'segurar' ? v : 'lucro' } catch { return 'lucro' }
  })
  const [fam, setFam] = useState<FamilyFilter>('all')
  const [asset, setAsset] = useState<AssetFilter>('all')
  const [q, setQ] = useState('')
  useEffect(() => { try { localStorage.setItem(KEY, sort) } catch { /* sem storage */ } }, [sort])
  const v = useMemo(() => ({
    sort, setSort, fam, setFam, asset, setAsset, q, setQ,
    reset: () => { setFam('all'); setAsset('all'); setQ('') },
    active: fam !== 'all' || asset !== 'all' || q !== '',
  }), [sort, fam, asset, q])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}
export function useFilters() {
  const c = useContext(Ctx)
  if (!c) throw new Error('FilterProvider ausente')
  return c
}
