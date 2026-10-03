// node --test src/lib/describe.test.ts  (Node ≥ 22.18 remove os tipos sozinho)
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { describePortfolio, diffText, layerName } from './describe.ts'

const cases: [Parameters<typeof describePortfolio>[0], string, string, string, string][] = [
  // entrada, título, ativo, chip, família
  [{ name: 'h1_exits_FARTCOIN_poorjev_relaxed', asset: 'FARTCOIN', hyp: 'H1', profile: 'relaxed' }, 'poorjev relaxado + saídas', 'FARTCOIN', 'hipótese H1', 'lab'],
  [{ name: 'meme_WIF_relaxed' }, 'von relaxado', 'WIF', 'modelo', 'von'],
  [{ name: 'WIF_relaxed', asset: 'WIF', profile: 'relaxed' }, 'von relaxado', 'WIF', 'modelo', 'von'],
  [{ name: 'WIF_poorjev_baseline', asset: 'WIF' }, 'poorjev artigo', 'WIF', 'modelo', 'poorjev'],
  [{ name: 'BONK_rule_donch_regime_full', asset: 'BONK' }, 'Donchian + regime, 100%', 'BONK', 'regra', 'rules'],
  [{ name: 'BONK_rule_regime', asset: 'BONK' }, 'Regime de SOL', 'BONK', 'regra', 'rules'],
  [{ name: 'hybrid_von_relaxed_cap2', profile: 'relaxed' }, 'von relaxado + regime', 'SOL', 'híbrido', 'hybrid'],
  [{ name: 'MEW_hybrid_poorjev_regime', asset: 'MEW' }, 'poorjev relaxado + regime', 'MEW', 'híbrido', 'hybrid'],
  [{ name: 'h2_ensemble_sol', hyp: 'H2', asset: 'SOL' }, 'Ensemble dos 3 modelos', 'SOL', 'hipótese H2', 'lab'],
  [{ name: 'h2_ensemble_GOAT', hyp: 'H2', asset: 'GOAT' }, 'Ensemble dos 3 modelos', 'GOAT', 'hipótese H2', 'lab'],
  [{ name: 'h3_limit_hybrid_von_cap2', hyp: 'H3' }, 'híbrido von + ordem limite', 'SOL', 'hipótese H3', 'lab'],
  [{ name: 'h4_hours_poorjev_relaxed', hyp: 'H4', profile: 'relaxed' }, 'poorjev relaxado + janela de horário', 'SOL', 'hipótese H4', 'lab'],
  [{ name: 'h1_exits_hybrid_von_cap2', hyp: 'H1', profile: 'relaxed' }, 'híbrido von + saídas', 'SOL', 'hipótese H1', 'lab'],
  [{ name: 'relaxed_expcap50', hyp: 'EXP' }, 'von relaxado, exposição ≤ 50%', 'SOL', 'teste de exposição', 'lab'],
  [{ name: 'grid_sol_2pct' }, 'Grade de 2%', 'SOL', 'regra', 'rules'],
  [{ name: 'rsi_sol_1h' }, 'RSI de 1 hora', 'SOL', 'regra', 'rules'],
  [{ name: 'laya_baseline' }, 'Laya artigo', 'SOL', 'modelo', 'laya'],
  [{ name: 'baseline' }, 'von artigo', 'SOL', 'modelo', 'von'],
  [{ name: 'v2' }, 'von critérios v2', 'SOL', 'modelo', 'von'],
  [{ name: 'relaxed__fork2', parent: 'relaxed', params_diff: { gates: { min_confidence: 0.3 } } }, 'von relaxado, ajuste 2', 'SOL', 'fork', 'von'],
  [{ name: 'meme_WIF_relaxed__fork1', asset: 'WIF' }, 'von relaxado, ajuste 1', 'WIF', 'fork', 'von'],
  [{ name: 'h1_exits_MEW_poorjev_relaxed__fork1', asset: 'MEW', hyp: 'H1' }, 'poorjev relaxado + saídas, ajuste 1', 'MEW', 'fork', 'lab'],
]

for (const [inp, title, asset, tag, family] of cases) {
  test(`describe ${inp.name}`, () => {
    const d = describePortfolio(inp)
    assert.equal(d.title, title)
    assert.equal(d.asset, asset)
    assert.equal(d.tag, tag)
    assert.equal(d.family, family)
    assert.ok(d.explain.length > 20 && d.explain.endsWith('.'), d.explain)
  })
}

test('H1 explanation uses effective numbers when present', () => {
  const d = describePortfolio({ name: 'h1_exits_FARTCOIN_poorjev_relaxed', hyp: 'H1', profile: 'relaxed', asset: 'FARTCOIN',
    params_brief: { min_confidence: 0.35, margin_gate: true, min_prob_margin: 0.2, exits: { tp: 0.06, sl: 0.04, trail: 0.03 } } })
  assert.match(d.explain, /poorjev tem confiança ≥ 0,35/)
  assert.match(d.explain, /take-profit, stop-loss ou trailing \(6% \/ 4% \/ 3%\)/)
})

test('fork explanation lists the diff', () => {
  assert.equal(diffText({ gates: { min_confidence: 0.3, max_trades_per_hour: 6 } }), 'confiança mínima 0,3, trades por hora 6')
  const d = describePortfolio({ name: 'relaxed__fork2', params_diff: { gates: { min_confidence: 0.3 } } })
  assert.match(d.explain, /ajuste noturno com confiança mínima 0,3/)
})

test('layer names', () => {
  assert.deepEqual(['defaults', 'profiles.relaxed', 'types.lab_h1_exits', 'models.von', 'assets.meme.symbols.WIF', 'portfolios.x', 'fork:x__fork1', 'overlay'].map(layerName),
    ['padrão', 'perfil', 'tipo', 'modelo', 'ativo', 'portfólio', 'fork', 'ajuste manual'])
})
