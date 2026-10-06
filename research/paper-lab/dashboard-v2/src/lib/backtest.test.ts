// node --test src/lib/backtest.test.ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type { BtPortfolio, BtSummary } from './api.ts'
import { asPct, dayMon, familyInfo, isHighlight, markWinners, normVerdict, sortBt, stamp, toBtEntry, weeksFromEquity, windowLabel } from './backtest.ts'
import { matches } from './board.ts'
import { inline, parseMarkdown } from './markdown.ts'

const FIX = fileURLToPath(new URL('../../../dashboard/fixtures/backtest/20261006-0300/', import.meta.url))
const summary = JSON.parse(readFileSync(FIX + 'summary.json', 'utf8')) as BtSummary

const P = (o: Partial<BtPortfolio> & { name: string }): BtPortfolio => ({
  start_value: 1000, end_value: 1000, pnl: 0, pnl_pct: 0, vs_bh: 0, skill: 0, timing_p: null, max_dd_pct: 0, trades: 0, verdict: 'inconclusiva', ...o,
})

test('entries get human names and derived numbers', () => {
  const e = toBtEntry(P({ name: 'h1_exits_FARTCOIN_poorjev_relaxed', asset: 'FARTCOIN', hyp: 'H1', profile: 'relaxed', end_value: 1100, vs_bh: 100, skill: 25 }))
  assert.equal(e.d.title, 'poorjev relaxado + saídas')
  assert.equal(e.who, 'poorjev relaxado + saídas em FARTCOIN')
  assert.ok(Math.abs((e.vsHoldPct ?? 0) - 10) < 1e-9) // 1100 contra 1000 de só segurar
  assert.equal(e.skillPct, 2.5)
  assert.equal(toBtEntry(P({ name: 'relaxed' })).who, 'von relaxado')
  assert.equal(toBtEntry(P({ name: 'meme_WIF_relaxed', asset: 'WIF' })).who, 'von relaxado em WIF')
})

test('verdicts normalize to three values', () => {
  assert.equal(normVerdict('inconclusivo'), 'inconclusiva')
  assert.equal(normVerdict('Vencedora'), 'vencedora')
  assert.equal(normVerdict('perdedora'), 'perdedora')
  assert.equal(normVerdict(undefined), 'inconclusiva')
})

test('sorting: skill, profit, vs hold and verdict groups', () => {
  const es = [
    toBtEntry(P({ name: 'a', skill: 5, pnl_pct: 9, vs_bh: -10, verdict: 'inconclusiva' })),
    toBtEntry(P({ name: 'baseline', skill: 30, pnl_pct: -2, vs_bh: 40, verdict: 'vencedora' })),
    toBtEntry(P({ name: 'relaxed', skill: -20, pnl_pct: 1, vs_bh: 5, verdict: 'perdedora' })),
    toBtEntry(P({ name: 'v2', skill: null, pnl_pct: null, vs_bh: null, end_value: null, verdict: 'vencedora' })),
  ]
  assert.deepEqual(sortBt(es, 'habilidade').map(e => e.p.name), ['baseline', 'a', 'relaxed', 'v2'])
  assert.deepEqual(sortBt(es, 'lucro').map(e => e.p.name), ['a', 'relaxed', 'baseline', 'v2'])
  assert.deepEqual(sortBt(es, 'segurar').map(e => e.p.name), ['baseline', 'relaxed', 'a', 'v2'])
  assert.deepEqual(sortBt(es, 'veredito').map(e => e.p.name), ['baseline', 'v2', 'a', 'relaxed'])
  assert.equal(isHighlight(es[1], 'veredito'), true)
  assert.equal(isHighlight(es[0], 'veredito'), false)
  assert.equal(isHighlight(es[2], 'habilidade'), false)
})

test('family and asset filters reuse the live board rules', () => {
  const fork = toBtEntry(P({ name: 'poorjev_relaxed__fork1', parent: 'poorjev_relaxed' }))
  const wif = toBtEntry(P({ name: 'WIF_rule_donch_regime_full', asset: 'WIF' }))
  assert.equal(matches(fork, 'forks', 'all', ''), true)
  assert.equal(matches(fork, 'poorjev', 'all', ''), true)
  assert.equal(matches(wif, 'rules', 'memes', ''), true)
  assert.equal(matches(wif, 'rules', 'SOL', ''), false)
  assert.equal(matches(wif, 'all', 'all', 'donchian'), true)
})

test('winner sentence: raw ids become marked human names', () => {
  const segs = markWinners('Quem mais lucrou foi h1_exits_FARTCOIN_poorjev_relaxed (+24%); habilidade: relaxed. Não relaxed__fork1.', [
    { raw: 'h1_exits_FARTCOIN_poorjev_relaxed', label: 'poorjev relaxado + saídas em FARTCOIN' },
    { raw: 'relaxed', label: 'von relaxado' },
  ])
  assert.deepEqual(segs.filter(s => s.mark).map(s => s.text), ['poorjev relaxado + saídas em FARTCOIN', 'von relaxado'])
  assert.equal(segs.map(s => s.text).join(''), 'Quem mais lucrou foi poorjev relaxado + saídas em FARTCOIN (+24%); habilidade: von relaxado. Não relaxed__fork1.')
  // texto que já vem com o nome humano: só marca
  const s2 = markWinners('O melhor foi von relaxado.', [{ raw: 'relaxed', label: 'von relaxado' }])
  assert.deepEqual(s2, [{ text: 'O melhor foi ' }, { text: 'von relaxado', mark: true }, { text: '.' }])
  assert.deepEqual(markWinners('sem nomes', []), [{ text: 'sem nomes' }])
})

test('dates are read on the Brasília clock', () => {
  assert.equal(windowLabel({ start_brt: '2026-09-06T00:00:00-03:00', end_brt: '2026-10-06T00:00:00-03:00' }), '6 set → 6 out')
  assert.equal(dayMon('2026-10-06T02:00:00Z'), '5 out') // 23:00 de 5 out em Brasília
  assert.equal(stamp('2026-10-06T03:12:44-03:00'), '6 out, 03:12')
  assert.equal(dayMon(null), '—')
})

test('weeks split the curve in four equal stretches', () => {
  const t = Array.from({ length: 9 }, (_, i) => i * 100)
  const w = weeksFromEquity({ t, equity: [100, 101, 102, 103, 104, 103, 102, 101, 110], bh: [100, 100, 100, 100, 100, 100, 100, 100, 100] })
  assert.equal(w.length, 4)
  assert.deepEqual(w.map(x => x.beat), [true, true, false, true])
  assert.ok(Math.abs((w[0].pct ?? 0) - 2) < 1e-9 && w[0].bhPct === 0)
  assert.deepEqual(weeksFromEquity(null), [])
})

test('family keys map to the documented palette, unknown keys stay readable', () => {
  assert.equal(familyInfo('rules').label, 'Regras')
  assert.equal(familyInfo('rule').label, 'Regras')
  assert.equal(familyInfo('poorjev').color, 'var(--fam-poorjev)')
  assert.equal(familyInfo('jev').label, 'Jev')
  assert.equal(familyInfo('forks').label, 'Forks')
  assert.deepEqual(familyInfo('novidade'), { label: 'novidade', color: 'var(--ink-3)' })
  assert.equal(asPct(0.98), 98)
  assert.equal(asPct(97.5), 97.5)
})

test('fixture: every portfolio gets a human title and a verdict', () => {
  const es = summary.portfolios.map(toBtEntry)
  assert.equal(es.length, 30)
  for (const e of es) {
    assert.ok(e.d.title && !e.d.title.includes('_'), e.p.name + ' → ' + e.d.title)
    assert.ok(['vencedora', 'perdedora', 'inconclusiva'].includes(e.verdict))
  }
  assert.ok(summary.portfolios.some(p => p.name === summary.winner.by_pnl))
})

test('markdown: headings, lists, tables, code and inline marks', () => {
  const b = parseMarkdown('# Título\n\nUm **forte** e `código` e *leve*.\nmesmo parágrafo\n\n- a\n- b\n\n1. um\n2. dois\n\n| A | B |\n|---|---:|\n| 1 | **2** |\n\n```\nx = 1\n```\n---\n')
  assert.deepEqual(b.map(x => x.k), ['h', 'p', 'ul', 'ol', 'table', 'code', 'hr'])
  assert.deepEqual(inline('a **b** `c` *d*').map(x => x.t), ['text', 'b', 'text', 'code', 'text', 'i'])
  const p = b[1] as { k: 'p'; text: { v: string }[] }
  assert.equal(p.text.map(x => x.v).join(''), 'Um forte e código e leve. mesmo parágrafo')
  const t = b[4] as { k: 'table'; rows: unknown[][] }
  assert.equal(t.rows.length, 1)
  assert.equal(parseMarkdown('<script>alert(1)</script>')[0].k, 'p') // vira texto, nunca HTML
})
