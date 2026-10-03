import { lazy, Suspense, useEffect } from 'react'
import { Toaster } from 'sonner'
import { TopBar } from '@/components/TopBar'
import { Loading } from '@/components/ui'
import { PAGES, useRoute } from '@/lib/router'
import { useTheme } from '@/lib/theme'
import Placar from '@/pages/Placar'

const Familias = lazy(() => import('@/pages/Familias'))
const CarteiraReal = lazy(() => import('@/pages/CarteiraReal'))
const Controle = lazy(() => import('@/pages/Controle'))
const Saude = lazy(() => import('@/pages/Saude'))
const Funding = lazy(() => import('@/pages/Funding'))
const PortfolioSheet = lazy(() => import('@/components/PortfolioSheet'))

export default function App() {
  const route = useRoute()
  const theme = useTheme()
  useEffect(() => {
    const label = PAGES.find(p => p.id === route.page)?.label
    document.title = route.page === 'placar' ? 'Paper lab' : `${label}, Paper lab`
  }, [route.page])
  useEffect(() => { window.scrollTo({ top: 0 }) }, [route.page])
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" onClick={e => { e.preventDefault(); document.getElementById('main')?.focus() }}
        className="sr-only z-50 rounded bg-ink px-3 py-1 text-surface focus:not-sr-only focus:fixed focus:left-2 focus:top-2">Pular para o conteúdo</a>
      <TopBar page={route.page} theme={theme.mode} onTheme={theme.toggle} />
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1360px] flex-1 px-4 pb-16 pt-5 outline-none sm:px-6 sm:pt-7">
        <Suspense fallback={<Loading h={480} />}>
          {route.page === 'placar' && <Placar />}
          {route.page === 'familias' && <Familias />}
          {route.page === 'carteira' && <CarteiraReal />}
          {route.page === 'controle' && <Controle />}
          {route.page === 'saude' && <Saude />}
          {route.page === 'funding' && <Funding />}
        </Suspense>
      </main>
      <footer className="mx-auto w-full max-w-[1360px] px-4 pb-8 text-[12px] text-ink-3 sm:px-6">
        Simulação local: nenhuma ordem real, nenhuma chave lida. Números em US$, horário de Brasília.
      </footer>
      {route.p && <Suspense fallback={null}><PortfolioSheet name={route.p} /></Suspense>}
      <Toaster theme={theme.mode} position="bottom-right" closeButton toastOptions={{ className: 'pop', style: { fontFamily: 'inherit' } }} />
    </div>
  )
}
