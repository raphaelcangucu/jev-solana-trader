// Atualização ao vivo: SSE (/api/v2/stream) → invalida as queries do TanStack afetadas.
// Sem stream, as queries fazem polling a cada 15 s (refetchInterval lê `useLive().connected`).
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const TOPIC_KEYS: Record<string, string[]> = {
  sol: ['overview', 'sparks', 'equity', 'portfolio'],
  meme: ['overview', 'sparks', 'equity', 'portfolio'],
  lab: ['overview', 'sparks', 'equity', 'portfolio', 'lab'],
  params: ['params', 'paramChanges', 'paramsTypes', 'effective', 'lab', 'models', 'overview'],
  funding: ['funding'],
  health: ['health'],
  realbot: ['realbot'],
}

interface LiveState { connected: boolean; lastEvent: number | null; price: number | null; priceSource: string | null }
const Ctx = createContext<LiveState>({ connected: false, lastEvent: null, price: null, priceSource: null })
export const useLive = () => useContext(Ctx)
export const POLL_MS = 15_000

export function LiveProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [st, setSt] = useState<LiveState>({ connected: false, lastEvent: null, price: null, priceSource: null })
  const retry = useRef(0)
  useEffect(() => {
    let es: EventSource | null = null
    let timer: number | undefined
    let closed = false
    const open = () => {
      if (closed) return
      es = new EventSource('/api/v2/stream', { withCredentials: true })
      es.addEventListener('hello', () => { retry.current = 0; setSt(s => ({ ...s, connected: true, lastEvent: Date.now() })) })
      es.addEventListener('update', ev => {
        try {
          const d = JSON.parse((ev as MessageEvent).data)
          const keys = new Set<string>(['health'])
          for (const t of d.topics || []) for (const k of TOPIC_KEYS[t] || []) keys.add(k)
          keys.forEach(k => qc.invalidateQueries({ queryKey: [k] }))
          setSt(s => ({ ...s, connected: true, lastEvent: Date.now(), price: d.price_usd ?? s.price, priceSource: d.price_source ?? s.priceSource }))
        } catch { /* evento malformado: ignora */ }
      })
      es.onerror = () => {
        setSt(s => ({ ...s, connected: false }))
        es?.close()
        const wait = Math.min(60_000, 2000 * 2 ** retry.current++)
        timer = window.setTimeout(open, wait)
      }
    }
    open()
    return () => { closed = true; es?.close(); if (timer) clearTimeout(timer) }
  }, [qc])
  return <Ctx.Provider value={st}>{children}</Ctx.Provider>
}

/** refetchInterval: só faz polling quando o SSE caiu. */
export function usePollInterval(ms = POLL_MS) {
  const { connected } = useLive()
  return connected ? false : ms
}
