import { useEffect, useState } from 'react'
export function useMedia(q: string) {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.matchMedia(q).matches)
  useEffect(() => { const mq = window.matchMedia(q); const f = () => setM(mq.matches); mq.addEventListener('change', f); f(); return () => mq.removeEventListener('change', f) }, [q])
  return m
}
