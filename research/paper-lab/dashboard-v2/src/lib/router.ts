// Rotas por hash: #/placar, #/familias, #/carteira, #/controle, #/saude, #/funding; detalhe com ?p=<portfólio>.
import { useEffect, useState } from 'react'

export const PAGES = [
  { id: 'placar', label: 'Placar' },
  { id: 'familias', label: 'Famílias' },
  { id: 'carteira', label: 'Carteira real' },
  { id: 'controle', label: 'Controle' },
  { id: 'saude', label: 'Saúde' },
  { id: 'funding', label: 'Funding' },
] as const
export type PageId = (typeof PAGES)[number]['id']

export interface Route { page: PageId; p: string | null }

function parse(): Route {
  const h = window.location.hash.replace(/^#\/?/, '')
  const [path, q] = h.split('?')
  const page = (PAGES.find(x => x.id === path)?.id ?? 'placar') as PageId
  const p = new URLSearchParams(q || '').get('p')
  return { page, p }
}
function href(r: Route) { return `#/${r.page}${r.p ? `?p=${encodeURIComponent(r.p)}` : ''}` }

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
  if (next.page && next.page !== cur.page && !('p' in next)) r.p = null
  window.location.hash = href(r)
}
export const pageHref = (page: PageId) => `#/${page}`
export const openPortfolio = (name: string) => go({ p: name })
export const closePortfolio = () => go({ p: null })
