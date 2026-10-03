import { Moon, Sun } from 'lucide-react'
import { Chip, Dot, Tip } from './ui'
import { useLive } from '@/lib/live'
import { useHealth } from '@/lib/queries'
import { PAGES, pageHref, type PageId } from '@/lib/router'
import { ago, price } from '@/lib/format'
import { cn } from '@/lib/utils'

const PROC_NAME: Record<string, string> = {
  supervisor: 'supervisor', von: 'modelo von', laya: 'modelo Laya', poorjev: 'modelo poorjev', sol: 'bot de SOL', meme: 'bot de memecoins',
  rules: 'bot de regras', lab: 'bot do laboratório', nightly: 'rotina noturna', dashboard: 'painel', tunnel: 'túnel de acesso remoto', funding: 'funding',
  sol_bot: 'bot de SOL', meme_bot: 'bot de memecoins', rules_bot: 'bot de regras', lab_bot: 'bot do laboratório',
}
export const procName = (n: string) => PROC_NAME[n] ?? n

function HealthDot() {
  const { data, isError } = useHealth()
  const live = useLive()
  const level = isError ? 'bad' : data?.level ?? 'off'
  const lines: string[] = []
  if (isError) lines.push('Não consegui ler a saúde dos processos.')
  else if (data) {
    if (data.down.length) lines.push(`Parado: ${data.down.map(procName).join(', ')}.`)
    if (data.stale.length) lines.push(`Sem sinal há mais de 3 min: ${data.stale.map(procName).join(', ')}.`)
    if (data.errors) lines.push(`${data.errors} erro(s) nos ciclos recentes.`)
    if (!lines.length) lines.push('Todos os processos estão rodando.')
  }
  lines.push(live.connected ? 'Atualização ao vivo ligada.' : 'Ao vivo indisponível: atualizando a cada 15 s.')
  const short = level === 'ok' ? 'tudo ok' : level === 'bad' ? (data?.down.length ? `${data.down.length} parado` : 'falha') : level === 'warn' ? 'atenção' : '…'
  return (
    <Tip content={<div className="grid gap-1">{lines.map(l => <span key={l}>{l}</span>)}<a href={pageHref('saude')} className="mt-1 underline">Abrir Saúde</a></div>} side="bottom">
      <a href={pageHref('saude')} className="inline-flex h-8 items-center gap-2 rounded-md px-2 text-[13px] text-ink-2 hover:bg-sunk" aria-label={`Saúde: ${lines.join(' ')}`}>
        <Dot level={level} /><span className="hidden t-cond text-[13px] sm:inline">{short}</span>
      </a>
    </Tip>
  )
}

export function TopBar({ page, theme, onTheme }: { page: PageId; theme: 'light' | 'dark'; onTheme: () => void }) {
  const live = useLive()
  const h = useHealth()
  const px = live.price ?? h.data?.price_usd
  const age = live.lastEvent ? (Date.now() - live.lastEvent) / 1000 : null
  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-[color-mix(in_srgb,var(--paper)_88%,transparent)] backdrop-blur-md">
      <div className="mx-auto flex max-w-[1360px] flex-wrap items-center gap-x-3 gap-y-0 sm:gap-x-5 px-4 sm:px-6">
        <a href={pageHref('placar')} className="flex h-14 items-center gap-2 rounded-sm sm:gap-2.5">
          <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden className="shrink-0">
            <rect x="1" y="1" width="20" height="20" rx="3" fill="none" stroke="var(--ink)" strokeWidth="1.5" />
            <path d="M5 15 L9 10 L12 12.5 L17 6" fill="none" stroke="var(--ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            <rect x="4" y="14.2" width="14" height="3.4" rx="1" fill="var(--hl)" opacity=".9" />
          </svg>
          <span className="t-display text-[19px]">Paper lab</span>
          <Tip content="Tudo aqui é simulado: nenhuma ordem real é enviada e nenhuma chave é lida." side="bottom">
            <span><Chip className="border-rule-strong">simulação</Chip></span>
          </Tip>
        </a>
        <nav aria-label="Seções" className="order-3 -mx-4 flex w-[calc(100%+32px)] gap-1 overflow-x-auto px-4 pb-2 lg:order-none lg:mx-0 lg:w-auto lg:overflow-visible lg:px-0 lg:pb-0">
          {PAGES.map(p => (
            <a key={p.id} href={pageHref(p.id)} aria-current={page === p.id ? 'page' : undefined}
              className={cn('relative flex h-9 shrink-0 items-center rounded-md px-2.5 text-[14px] text-ink-2 hover:bg-sunk hover:text-ink lg:h-14 lg:rounded-none lg:px-2.5 lg:hover:bg-transparent',
                page === p.id && 'text-ink t-semi after:absolute after:inset-x-2.5 after:bottom-0 after:h-[2px] after:rounded-full after:bg-ink lg:after:bottom-[-1px]')}>
              {p.label}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex h-14 items-center gap-0.5 sm:gap-2">
          <Tip content={`Preço de SOL (${live.priceSource ?? h.data?.price_source ?? 'fonte desconhecida'})${age != null ? `, atualizado há ${ago(age)}` : ''}.`} side="bottom">
            <span className="flex items-baseline gap-1.5 px-1 text-[13px] text-ink-3" aria-live="polite" aria-label={`SOL ${price(px)} dólares`}>
              <span className="hidden min-[400px]:inline">SOL</span> <b className="t-num text-[16px] text-ink"><span className="hidden sm:inline">US$ </span>{price(px)}</b>
            </span>
          </Tip>
          <HealthDot />
          <button type="button" onClick={onTheme} className="grid size-8 place-items-center rounded-md text-ink-2 hover:bg-sunk hover:text-ink" aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}>
            {theme === 'dark' ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />}
          </button>
        </div>
      </div>
    </header>
  )
}
