import { useEffect, useMemo, useRef } from 'react'
import { ExperimentTrack } from '@/components/ExperimentTrack'
import { FilterBar } from '@/components/FilterBar'
import { Leaderboard } from '@/components/Leaderboard'
import { ErrorNote, Loading, Note } from '@/components/ui'
import { leaders, matches, sortEntries } from '@/lib/board'
import { useFilters } from '@/lib/filters'
import { useEntries, useSparks } from '@/lib/queries'

export default function Placar() {
  const { ov, entries } = useEntries()
  const sparks = useSparks()
  const f = useFilters()
  const firstPaint = useRef(true)
  useEffect(() => { if (entries.length) { const t = setTimeout(() => { firstPaint.current = false }, 1500); return () => clearTimeout(t) } }, [entries.length])
  const visible = useMemo(() => sortEntries(entries.filter(e => matches(e, f.fam, f.asset, f.q)), f.sort), [entries, f.fam, f.asset, f.q, f.sort])
  const lead = useMemo(() => leaders(entries), [entries])
  if (ov.isLoading) return <Loading h={520} label="Abrindo o caderno…" />
  if (ov.error && !ov.data) return <ErrorNote error={ov.error} what="placar" />
  const d = ov.data!
  const verdicts = entries.filter(e => e.row.verdict === 'vencedora' || e.row.verdict === 'perdedora').length
  return (
    <div className="flex flex-col gap-6">
      <ExperimentTrack exp={d.experiment} byPnl={lead.byPnl} bySkill={lead.bySkill} counts={{ tests: entries.length, trades: d.trades_today, verdicts }} />
      <section aria-labelledby="placar-title" className="flex flex-col gap-3">
        <h2 id="placar-title" className="t-title text-[23px]">Placar</h2>
        <FilterBar count={visible.length} total={entries.length} />
        {visible.length ? (
          <div className={ov.isFetching && !ov.isLoading ? 'opacity-[.92] transition-opacity' : ''}>
            <Leaderboard entries={visible} sort={f.sort} onSort={f.setSort} sparks={sparks.data} firstPaint={firstPaint.current} />
          </div>
        ) : (
          <Note>Nenhum teste com esses filtros. <button type="button" className="underline" onClick={f.reset}>Limpar filtros</button></Note>
        )}
        {d.skill_status?.error && <p className="text-[12.5px] text-ink-3">A habilidade não pôde ser calculada agora ({d.skill_status.error}); o lucro continua certo.</p>}
      </section>
    </div>
  )
}
