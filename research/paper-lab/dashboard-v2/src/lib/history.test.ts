// node --test src/lib/history.test.ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type { BtChart, BtIndex, BtIndexRun } from './api.ts'
import {
  asReturn, benchLines, consistency, familyLines, familyScopes, lastValue, maxDrawdown, memesRet, monthlyRuns, monthShort, orderRuns,
  parseFamilyKey, placeEndLabels, runForMonth, runPill, SERIES, strategyPool, whoName,
} from './history.ts'

const FIX = fileURLToPath(new URL('../../../dashboard/fixtures/backtest/', import.meta.url))
const index = JSON.parse(readFileSync(FIX + 'index.json', 'utf8')) as BtIndex
const chart = JSON.parse(readFileSync(FIX + 'bt180_2026-10-06/chart.json', 'utf8')) as BtChart
const six = index.runs.find(r => r.kind === '180d')!

const R = (o: Partial<BtIndexRun> & { run_id: string }): BtIndexRun => ({ kind: '30d', ...o })

test('pills: monthly runs are named by the month they cover, the long window is "6 meses"', () => {
  assert.deepEqual(runPill(R({ run_id: 'bt30_2026-10-06', start_brt: '2026-09-06T09:00:00-03:00', end_brt: '2026-10-06T09:00:00-03:00' })),
    { run_id: 'bt30_2026-10-06', kind: '30d', label: 'Set', sub: '6 set → 6 out', title: 'Set: 6 set → 6 out' })
  assert.equal(runPill(R({ run_id: 'x', start_brt: '2026-07-06T09:00:00-03:00', end_brt: '2026-08-06T09:00:00-03:00' })).label, 'Jul')
  assert.equal(runPill(six).label, '6 meses')
  assert.equal(runPill(six).sub, '6 abr → 6 out')
  assert.equal(runPill(R({ run_id: 'sem-datas' })).label, 'sem-datas')
})

test('order: 30-day months newest first, then the 6-month window; missing dirs are hidden', () => {
  const ids = orderRuns(index).map(r => r.run_id)
  assert.deepEqual(ids, ['20261006-0300', 'bt30_2026-09-06', 'bt30_2026-08-06', 'bt180_2026-10-06'])
  const withGone = { runs: [...index.runs, R({ run_id: 'gone', end_brt: '2026-12-01', available: false })] }
  assert.ok(!orderRuns(withGone).some(r => r.run_id === 'gone'))
  assert.deepEqual(orderRuns(null), [])
})

test('monthly runs for the comparison are the last three, oldest on the left', () => {
  assert.deepEqual(monthlyRuns(index).map(r => r.run_id), ['bt30_2026-08-06', 'bt30_2026-09-06', '20261006-0300'])
  assert.deepEqual(monthlyRuns(index, 2).map(r => r.run_id), ['bt30_2026-09-06', '20261006-0300'])
})

test('memes basket is the mean of every asset but SOL', () => {
  assert.equal(memesRet({ SOL: 10, WIF: 4, BONK: -2, GOAT: null }), 1)
  assert.equal(memesRet({ SOL: 5 }), null)
  assert.equal(memesRet(null), null)
})

test('consistency counts months in the top 5 by skill or by pnl', () => {
  const runs = [
    R({ run_id: 'a', top_skill: [{ name: 'x', skill: 1, pnl_pct: 1 }, { name: 'y', skill: 1, pnl_pct: 1 }], top_pnl: [{ name: 'z', skill: 1, pnl_pct: 1 }, { name: 'x', skill: 1, pnl_pct: 1 }] }),
    R({ run_id: 'b', top_skill: [{ name: 'y', skill: 1, pnl_pct: 1 }], top_pnl: [{ name: 'x', skill: 1, pnl_pct: 1 }] }),
    R({ run_id: 'c', top_skill: [{ name: 'q', skill: 1, pnl_pct: 1 }, { name: 'r', skill: 1, pnl_pct: 1 }, { name: 's', skill: 1, pnl_pct: 1 }, { name: 't', skill: 1, pnl_pct: 1 }, { name: 'u', skill: 1, pnl_pct: 1 }, { name: 'x', skill: 1, pnl_pct: 1 }] }),
  ]
  const c = consistency(runs, 5)
  assert.deepEqual(c.map(x => [x.name, x.count]).slice(0, 2), [['x', 2], ['y', 2]]) // x: 6º em c não conta
  assert.deepEqual(c[0].hits, [{ run_id: 'a', skillRank: 1, pnlRank: 2 }, { run_id: 'b', skillRank: null, pnlRank: 1 }])
  const fx = consistency(monthlyRuns(index), 5)
  assert.equal(fx[0].count, 3)
  assert.ok(fx.every((x, i) => i === 0 || fx[i - 1].count >= x.count))
})

test('strategy pool: defaults are top 3 by skill, 2 more by pnl and bot A/B; fixed colors in palette order', () => {
  const pool = strategyPool(chart, six)
  assert.ok(pool.length <= 8)
  assert.deepEqual(pool.map(p => p.color), SERIES.slice(0, pool.length))
  const on = pool.filter(p => p.defaultOn).map(p => p.name ?? p.id)
  const skill3 = six.top_skill!.slice(0, 3).map(t => t.name)
  assert.deepEqual(on.slice(0, 3), skill3)
  const pnl2 = six.top_pnl!.map(t => t.name).filter(n => !skill3.includes(n)).slice(0, 2)
  assert.deepEqual(on.slice(3, 5), pnl2)
  assert.deepEqual(on.slice(5), ['bot:A', 'bot:B'])
  assert.equal(pool.find(p => p.id === 'bot:A')!.label, 'Bot real, livro A')
  // a cor segue a entidade: ligar/desligar não muda nada no conjunto
  assert.deepEqual(strategyPool(chart, six).map(p => [p.id, p.color]), pool.map(p => [p.id, p.color]))
  // sem índice: ordem das chaves do chart.json
  const bare = strategyPool(chart, null)
  assert.equal(bare[0].name, Object.keys(chart.top)[0])
})

test('benchmarks are neutral ink and never solid', () => {
  const b = benchLines(chart)
  assert.deepEqual(b.map(x => x.id), ['bench:sol_bh', 'bench:memes_bh', 'bench:usdc'])
  assert.ok(b.every(x => x.style !== 'solid' && x.color.startsWith('var(--ink')))
})

test('family keys: scope prefix and aliases, page colors kept', () => {
  assert.deepEqual([parseFamilyKey('SOL · poorjev').scope, parseFamilyKey('SOL · poorjev').fam?.key], ['SOL', 'poorjev'])
  assert.equal(parseFamilyKey('Meme · hipóteses (lab)').fam?.key, 'lab')
  assert.equal(parseFamilyKey('Meme · regras').scope, 'Memecoins')
  assert.equal(parseFamilyKey('SOL · híbridos').fam?.key, 'hybrid')
  assert.equal(parseFamilyKey('jev').fam?.key, 'jev')
  assert.equal(parseFamilyKey('poorjev').scope, '')
  const ch = { ...chart, families: { 'SOL · von': [1000, 1010], 'SOL · poorjev': [1000, 990], 'Meme · von': [1000, 1001], 'SOL · algo novo': [1000, 1000] } }
  assert.deepEqual(familyScopes(ch), ['SOL', 'Memecoins'])
  const sol = familyLines(ch, 'SOL')
  assert.deepEqual(sol.map(l => l.color), ['var(--fam-von)', 'var(--fam-poorjev)', 'var(--fam-laya)'])
  assert.equal(sol[2].label, 'algo novo')
  assert.equal(familyLines(ch, 'Memecoins').length, 1)
  assert.deepEqual(familyScopes(chart), ['SOL', 'Memecoins'])
  assert.ok(familyLines(chart, 'SOL').length >= 4)
  assert.ok(familyLines(chart, 'Memecoins').every(l => l.color.startsWith('var(--fam-') || l.color.startsWith('var(--series-')))
})

test('reading helpers', () => {
  assert.ok(Math.abs(asReturn(1084)! - 8.4) < 1e-9)
  assert.equal(lastValue([1000, 1010, null]), 1010)
  assert.equal(lastValue([null]), null)
  assert.ok(Math.abs((maxDrawdown([1000, 1200, 900, 1300])! + 25)) < 1e-9)
  assert.equal(monthShort('2026-04'), 'abr')
  assert.equal(monthShort('2026-12', true), 'dez/26')
  assert.equal(runForMonth(index, '2026-08-06T09:00:00-03:00'), 'bt30_2026-09-06')
  assert.equal(runForMonth(index, '2026-04-06T09:00:00-03:00'), null)
  assert.equal(whoName('h2_ensemble_FARTCOIN'), 'Ensemble dos 3 modelos em FARTCOIN')
})

test('end labels keep by priority and never overlap; the rest falls back to legend', () => {
  const kept = placeEndLabels([
    { id: 'a', y: 100, priority: 0 }, { id: 'b', y: 108, priority: 1 }, { id: 'c', y: 130, priority: 2 },
    { id: 'd', y: null, priority: 3 }, { id: 'e', y: 500, priority: 4 },
  ], 17, 0, 400)
  assert.deepEqual([...kept.keys()], ['a', 'c'])
  assert.equal(kept.get('a'), 100) // nunca empurra o rótulo para longe da linha
})
