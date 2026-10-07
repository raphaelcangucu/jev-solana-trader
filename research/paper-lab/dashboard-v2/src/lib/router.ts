// Rotas por hash: #/placar, #/familias, #/retroativo, #/carteira, #/controle, #/saude, #/funding; detalhe com ?p=<portfólio>
// (run ao vivo) ou ?b=<portfólio> (simulação retroativa, só em #/retroativo). No retroativo, ?run=<run_id> escolhe o
// período (mês de 30 dias ou 6 meses) e ?view=comparar abre a comparação entre meses.
import { useEffect, useState } from 'react'

export const PAGES = [
  { id: 'placar', label: 'Placar' },
  { id: 'familias', label: 'Famílias' },
  { id: 'retroativo', label: 'Retroativo' },
  { id: 'carteira', label: 'Carteira real' },
  { id: 'controle', label: 'Controle' },
  { id: 'saude', label: 'Saúde' },
  { id: 'funding', label: 'Funding' },
] as const
export type PageId = (typeof PAGES)[number]['id']

export interface Route { page: PageId; p: string | null; b: string | null; run: string | null; view: string | null }

function parse(): Route {
  const h = window.location.hash.replace(/^#\/?/, '')
  const [path, q] = h.split('?')
  const page = (PAGES.find(x => x.id === path)?.id ?? 'placar') as PageId
  const sp = new URLSearchParams(q || '')
  const bt = page === 'retroativo'
  return { page, p: sp.get('p'), b: bt ? sp.get('b') : null, run: bt ? sp.get('run') : null, view: bt ? sp.get('view') : null }
}
function href(r: Route) {
  const q = new URLSearchParams()
  if (r.p) q.set('p', r.p)
  if (r.run) q.set('run', r.run)
  if (r.view) q.set('view', r.view)
  if (r.b) q.set('b', r.b)
  const s = q.toString()
  return `#/${r.page}${s ? `?${s}` : ''}`
}

export function useRoute() {
  const [r, setR] = useState<Route>(parse)
  useEffect(() => {
    const f = () => setR(parse())
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  return r
}
export function go(next: Partial<Route>) {
  const cur = parse()
  const r = { ...cur, ...next }
  if (next.page && next.page !== cur.page) {
    if (!('p' in next)) r.p = null
    if (!('b' in next)) r.b = null
    if (!('run' in next)) r.run = null
    if (!('view' in next)) r.view = null
  }
  window.location.hash = href(r)
}
export const pageHref = (page: PageId) => `#/${page}`
export const openPortfolio = (name: string) => go({ p: name })
export const closePortfolio = () => go({ p: null })
export const openBacktest = (name: string) => go({ b: name })
export const closeBacktest = () => go({ b: null })
/** Troca o período do retroativo (fecha o detalhe e sai da comparação). `null` = o run mais recente. */
export const openBtRun = (run: string | null) => go({ run, view: null, b: null })
export const openBtCompare = () => go({ view: 'comparar', b: null })
/** Link para um teste dentro de um run específico do retroativo. */
export const btHref = (run: string, name?: string | null) => {
  const q = new URLSearchParams({ run })
  if (name) q.set('b', name)
  return `#/retroativo?${q.toString()}`
}
/** Link para o mesmo teste no placar ao vivo. */
export const liveHref = (name: string) => `#/placar?p=${encodeURIComponent(name)}`
