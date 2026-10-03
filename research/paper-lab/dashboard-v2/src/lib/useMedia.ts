import { useEffect, useState } from 'react'
export function useMedia(q: string) {
  const [m, setM] = useState(() => window.matchMedia(q).matches)
  useEffect(() => { const mm = window.matchMedia(q); const f = () => setM(mm.matches); mm.addEventListener('change', f); return () => mm.removeEventListener('change', f) }, [q])
  return m
}
export const useReducedMotion = () => useMedia('(prefers-reduced-motion: reduce)')
