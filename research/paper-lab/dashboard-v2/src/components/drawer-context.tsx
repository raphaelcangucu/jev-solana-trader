import { createContext, useContext, useState, type ReactNode, lazy, Suspense } from 'react'
const PortfolioDrawer = lazy(() => import('./PortfolioDrawer'))
const Ctx = createContext<{ open: (name: string) => void }>({ open: () => {} })
export const useDrawer = () => useContext(Ctx)
export function DrawerProvider({ children }: { children: ReactNode }) {
  const [name, setName] = useState<string | null>(null)
  return (
    <Ctx.Provider value={{ open: setName }}>
      {children}
      {name && <Suspense fallback={null}><PortfolioDrawer name={name} onClose={() => setName(null)} /></Suspense>}
    </Ctx.Provider>
  )
}
