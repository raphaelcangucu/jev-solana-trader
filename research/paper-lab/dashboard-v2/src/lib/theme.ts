// Tema: 'light' | 'dark' | 'system'. O atributo data-theme no <html> sempre carrega o tema resolvido.
import { useEffect, useState } from 'react'

export type ThemePref = 'light' | 'dark' | 'system'
const KEY = 'paperlab.theme'

function read(): ThemePref {
  try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : 'system' } catch { return 'system' }
}
const mq = () => window.matchMedia('(prefers-color-scheme: dark)')
export function resolved(p: ThemePref): 'light' | 'dark' { return p === 'system' ? (mq().matches ? 'dark' : 'light') : p }
function apply(p: ThemePref) { document.documentElement.dataset.theme = resolved(p) }

export function useTheme() {
  const [pref, setPref] = useState<ThemePref>(read)
  const [, force] = useState(0)
  useEffect(() => {
    apply(pref)
    try { if (pref === 'system') localStorage.removeItem(KEY); else localStorage.setItem(KEY, pref) } catch { /* sem storage */ }
    const m = mq()
    const on = () => { if (pref === 'system') { apply('system'); force(x => x + 1) } }
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [pref])
  const mode = resolved(pref)
  return { pref, mode, toggle: () => setPref(mode === 'dark' ? 'light' : 'dark'), setPref }
}

/** Observa data-theme (para gráficos em canvas que precisam ler as cores). */
export function useThemeMode(): 'light' | 'dark' {
  const [m, setM] = useState<'light' | 'dark'>(() => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'))
  useEffect(() => {
    const o = new MutationObserver(() => setM(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'))
    o.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => o.disconnect()
  }, [])
  return m
}

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
