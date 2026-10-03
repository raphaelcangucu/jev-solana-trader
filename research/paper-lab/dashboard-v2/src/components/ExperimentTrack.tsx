// Faixa de abertura: o experimento como uma régua de 30 dias + quem está na frente, em uma frase.
import type { Experiment } from '@/lib/api'
import type { Entry } from '@/lib/board'
import { familyOf } from '@/lib/describe'
import { dayMonth, pval, signedPct, smartUsd } from '@/lib/format'
import { openPortfolio } from '@/lib/router'
import { Chip, Delta, Mark, Tip } from './ui'

function Track({ exp }: { exp: Experiment }) {
  const total = exp.days_total
  const el = Math.max(0, Math.min(total, exp.elapsed_days ?? 0))
  const pos = (d: number) => `${(d / total) * 100}%`
  return (
    <div className="relative pb-9 pt-1" aria-hidden>
      <div className="relative h-[10px]">
        <div className="absolute inset-x-0 top-[4px] h-[2px] rounded-full bg-rule-strong" />
        <div className="absolute left-0 top-[3px] h-[4px] rounded-full bg-ink" style={{ width: pos(el) }} />
        {Array.from({ length: total + 1 }, (_, i) => (
          <span key={i} className="absolute top-0 w-px bg-rule-strong" style={{ left: pos(i), height: i % 5 === 0 ? 10 : 6, top: i % 5 === 0 ? 0 : 2 }} />
        ))}
        <span className="absolute top-[-3px] size-4 -translate-x-1/2 rounded-full border-[3px] border-surface bg-ink shadow-[0_0_0_1px_var(--ink)]" style={{ left: pos(el) }} />
        <span className="absolute top-[-6px] h-[22px] w-[2px] -translate-x-1/2 bg-ink" style={{ left: pos(exp.first_verdict_day) }} />
        <span className="absolute right-0 top-[-6px] h-[22px] w-[2px] bg-ink" />
      </div>
      <span className="absolute top-[18px] -translate-x-1/2 whitespace-nowrap text-[12px] text-ink t-semi" style={{ left: `clamp(24px, ${pos(el)}, calc(100% - 140px))` }}>hoje</span>
      <span className="absolute top-[18px] -translate-x-[calc(100%-4px)] whitespace-nowrap text-[12px] text-ink-2 sm:-translate-x-1/2" style={{ left: pos(exp.first_verdict_day) }}>
        <span className="hidden sm:inline">dia {exp.first_verdict_day}: primeiros </span>vereditos
      </span>
      <span className="absolute right-0 top-[18px] whitespace-nowrap text-[12px] text-ink-2"><span className="hidden sm:inline">dia {total}: </span>fim</span>
    </div>
  )
}

function Who({ e, children }: { e: Entry; children?: React.ReactNode }) {
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <button type="button" onClick={() => openPortfolio(e.row.name)} className="rounded-sm text-left hover:underline hover:decoration-1 hover:underline-offset-4">
        <Mark sweep><span className="t-title">{e.d.title}</span></Mark>
      </button>
      <span className="inline-flex translate-y-[-2px] gap-1">
        <Chip>{e.d.asset}</Chip>
        <Chip color={familyOf(e.d.family).color}>{e.d.tag}</Chip>
      </span>
      {children}
    </span>
  )
}

export function ExperimentTrack({ exp, byPnl, bySkill, counts }: { exp?: Experiment; byPnl: Entry | null; bySkill: Entry | null; counts: { tests: number; trades: number; verdicts: number } }) {
  const day = exp?.day
  return (
    <section aria-labelledby="track-title" className="sheet relative overflow-hidden rounded-xl px-4 pb-5 pt-4 sm:px-7 sm:pt-6">
      <div className="grid gap-x-10 gap-y-3 lg:grid-cols-[auto_1fr] lg:items-start">
        <div>
          <h1 id="track-title" className="t-display text-[34px] sm:text-[42px]">
            {day ? <>Dia {day} <span className="text-ink-3">de {exp!.days_total}</span></> : 'Experimento'}
          </h1>
          <p className="mt-1 text-[13px] text-ink-3 t-tab">
            {exp?.start_ts ? `${dayMonth(exp.start_ts)} a ${dayMonth(exp.end_ts)}, ${counts.tests} testes em paralelo` : 'aguardando o primeiro ciclo'}
          </p>
        </div>
        {exp?.start_ts ? <div className="lg:pt-5"><Track exp={exp} /></div> : null}
      </div>

      <div className="mt-2 grid gap-x-10 gap-y-4 border-t border-rule pt-4 text-[17px] sm:text-[19px] lg:grid-cols-2">
        <p className="leading-snug">
          <span className="mb-1 block text-[13.5px] text-ink-3">Na frente agora</span>
          {byPnl ? (
            <Who e={byPnl}>
              <Delta v={byPnl.pnlPct} className="t-display text-[22px] sm:text-[26px]">{signedPct(byPnl.pnlPct)}</Delta>
            </Who>
          ) : <span className="text-ink-3">ninguém ainda: o placar aparece depois do primeiro ciclo</span>}
        </p>
        <p className="leading-snug">
          <span className="mb-1 block text-[13.5px] text-ink-3">Mais habilidade, sem beta</span>
          {bySkill ? (
            <Who e={bySkill}>
              <Tip content="Lucro menos o que a exposição média ao ativo teria rendido sozinha. O p vem do placebo de timing: abaixo de 0,05 é difícil de explicar por sorte.">
                <span className="inline-flex items-baseline gap-2">
                  <Delta v={bySkill.skillUsd} className="t-display text-[22px] sm:text-[26px]">{smartUsd(bySkill.skillUsd, true)}</Delta>
                  {bySkill.timingP != null && <span className="text-[13px] text-ink-3 t-tab">{pval(bySkill.timingP)}</span>}
                </span>
              </Tip>
            </Who>
          ) : <span className="text-ink-3">calculando…</span>}
        </p>
      </div>
      <p className="mt-4 max-w-[860px] text-[13.5px] text-ink-2">
        Lucro sozinho é quase todo <b className="t-semi">beta</b>: quanto do dinheiro estava no ativo vezes quanto o ativo andou.
        A <b className="t-semi">habilidade</b> desconta isso. Vereditos só a partir do dia {exp?.first_verdict_day ?? 21} e com {exp?.min_closed_rt ?? 30} operações fechadas
        {counts.verdicts ? `; ${counts.verdicts} já ${counts.verdicts > 1 ? 'têm' : 'tem'} veredito.` : '; nenhum teste chegou lá ainda.'}
      </p>
    </section>
  )
}
