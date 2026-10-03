import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { LiveProvider } from '@/lib/live'
import { DrawerProvider } from '@/components/drawer-context'
import App from './App'
import './index.css'

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 4_000, gcTime: 5 * 60_000, refetchOnWindowFocus: true, retry: 2, placeholderData: (prev: unknown) => prev } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <TooltipProvider>
        <LiveProvider>
          <DrawerProvider>
            <App />
          </DrawerProvider>
        </LiveProvider>
        <Toaster theme="dark" position="top-right" richColors closeButton />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
