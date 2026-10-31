# Diário da revisão noturna autónoma — 2026-10-03 (dia 4/30, paper only)

Primeira noite do investigador Claude: não havia diários anteriores (`reviews/claude_night_*.md` vazio). Fontes: `night_cli context` e `status`, `reviews/2026-10-03.md` (tuner das 00:30), `reports/summary_latest.md`, `params.json` (só leitura).

Mercado nas 24 h: SOL -2.5%, memes quase todas em queda (BONK -5.8%, WIF -6.7%, FARTCOIN -3.9%), só MEW +2.8%. Dia baixista: qualquer família só-compra parece pior do que é, e a auditoria de "erros confiantes" em compras herda esse viés.

## 1. Reflexão por família (GEPA em linguagem simples)

Nota transversal: a auditoria do tuner (secção 6 da revisão) escolhe palavras pela frequência bruta e propôs "be wary when the tape reads calm, deep, quiet". Essas palavras aparecem em 100% dos erros **e** 100% dos acertos — são o estado de base, não um sinal. Aqui uso só a diferença (% nos erros − % nos acertos), que é o que de facto separa as chamadas.

### von (SOL: `relaxed`, `relaxed_expcap50`, `v2`, híbridos, H1/H3/H4)

- **Porque errou.** 572 chamadas confiantes (P90, corte 0.383), 250 erros em 42 episódios, 158 acertos, hit 28%. Praticamente só compras. Erros têm a fita **green** (60% vs 39% nos acertos) e **pumping** (12% vs 6%); acertos têm **gray** (59% vs 32%) e são mais tarde no dia (late 48% vs 38%). Leitura: o von compra depois de o movimento já ter acontecido; quando a fita ainda está gray e só "lifting", a compra funciona mais vezes. O v2 (critérios do tuner, "prefer deep quiet pumping") tem o mesmo padrão e hit pior (24%): pedir "pumping" é pedir o marcador de erro.
- **Números.** `relaxed`: 60 compras/2 vendas, exposição 97%, habilidade -9.5 US$ — é beta de SOL com deriva só-compra. `relaxed_expcap50` (teto 50%): -3.1 US$. `v2`: +1.2 US$ com 1/1 trades, isto é, quase não negoceia (o texto v2 baixou a confiança do von: p50 0.263 vs 0.334). Híbridos SOL -25.9, H3 limite -40.6 (adverse selection das ordens limite: só preenche quando o preço atravessa o limite para baixo), H4 horas -27.9. Tudo com 1–3 dias e < 5 round trips: inconclusivo, mas a direção é unânime (negativa) em SOL.
- **Memes (`meme_*_relaxed`).** 1438 chamadas, 76% vendas; 52 erros vs 68 acertos (hit 46%, 39 episódios), ligeiramente positivo. Erros são vendas numa fita **calm red fading late/night** (late 50% vs 32%, calm 69% vs 53%) que depois ressalta; acertos são vendas com fita **jumpy/gray/tight**. Portfólios quase não negoceiam (21/11 trades em 7 moedas, exposição 2%); `meme_FARTCOIN_relaxed` +8.2 US$ de habilidade com 2/1 trades é ruído. Sem fork hoje: pouca potência.

### poorjev (SOL e memes, baseline/relaxed, híbridos regime, fonte dos H1 memes)

- **É um modelo só-compra.** 5692 chamadas em SOL: 5692 buy, 0 sell, 0 hold. Memes: 1436 buy, 0 sell. Confiança 0.93–0.97 em memes, por isso qualquer portão passa e o portfólio satura a 98% de exposição em horas: `*_poorjev_baseline/relaxed` memes = -25.8 US$ de habilidade, 140/0 trades, puro beta. Em SOL a conf é 0.52–0.62 e a margem 0.2 bloqueia ("low_prob_margin"): 1 trade.
- **Onde há sinal.** Nas chamadas confiantes em memes, os acertos são compras em fita **red violent dumping** (dumping 63% nos acertos vs 41% nos erros; violent 58% vs 36%) e os erros são compras em fita **jumpy/whipping/green/harsh/tight**. Ou seja: comprar o despejo violento revertia a 15 min; comprar a fita nervosa não. Isto só se monetiza com saídas mecânicas, porque o poorjev nunca vende — e é exactamente o que H1 mostra: `h1_exits_*_poorjev_relaxed` memes +38.3 US$ de habilidade (FARTCOIN +47.4 com p 0.00; WIF +22.8 p 0.06), contra -25.8 nos mesmos modelos sem saídas.
- **Decisão: nenhum fork poorjev.** Um fork de critérios é inútil num modelo que responde buy a tudo com conf 0.95 (custaria uma chamada por ciclo para nada); a alavanca é exits, e a linhagem H1 FARTCOIN já tem o fork do nightly com saídas mais apertadas (e está bloqueada até 10-05). Amanhã: ver se o fork1 (tp 1.5%, trail 0.7%) perde para o pai (hoje -6.4 US$ com 9/0 trades: as saídas apertadas cortam cedo).

### Laya (SOL e memes, baseline/relaxed)

- **Zero trades em 4 dias, em 16 portfólios.** Não é prudência: é escala. A confiança da Laya tem p50 0.028 e máximo 0.096 em SOL (memes: p50 0.046, máx 0.176). O portão baseline (0.6) e o relaxed (0.35 + margem 0.2) foram calibrados ao von e nunca deixam passar nada. A família Laya não produziu uma única evidência sobre negociar — só sobre chamadas.
- **Chamadas.** SOL: hit 31%, 250 erros vs 208 acertos (46 episódios), erros em compras **lifting tight** e vendas **fading wide**; sinal fraco ou negativo num dia baixista. Memes: 65 acertos vs 58 erros (hit 45%), **vende** (553 de 1437 chamadas), erros em vendas durante **dumping jumpy loud** e **whipping harsh** late.
- **Decisão: dois forks de portão** na escala da Laya (abaixo). A hipótese principal é de método (tornar a família mensurável); a secundária é que em memes, por vender, a Laya pode ter habilidade onde o poorjev só tem beta.

### Regras e H2 (sem modelo, sem acção possível)

- `*_rule_donch_regime_full` são as piores do laboratório (WIF -105.5, FARTCOIN -87.8, BONK -83.1 US$ de habilidade, com 1/1 trades cada): um único rompimento comprado no topo e vendido no fim do regime. Não são pais aceitáveis (grupo `rule` não é forkável) — ficam só rotuladas pelo tuner.
- H2 ensemble: positivo em FARTCOIN (+8.8) e BONK (+3.8), negativo em POPCAT/WIF; o nightly já forcou cooldown 600 s em FARTCOIN e WIF. Nada a acrescentar.

## 2. Forks anteriores (todos do nightly, criados há ~0.1 d)

| Fork | Pai | Mudança | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---|---|
| relaxed__fork1 | relaxed | exits SOL 2.5/1.5/1.0/1.0, reentrada 30 min (iguais aos níveis do pai) + max_exposure 0.5 | +0.00 | +0.2 | 0/0 | sem dados |
| poorjev_relaxed__fork1 | poorjev_relaxed | mesmos exits | +0.00 | +0.1 | 0/0 | sem dados (poorjev SOL bloqueado pela margem; o fork herda o bloqueio) |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | h1 FARTCOIN poorjev | tp 1.5%, trail 0.7% | +0.01 | -6.4 | 9/0 | **tendência a refutar**: saídas apertadas cortam o melhor portfólio do lab cedo; 1 dia, não conclusivo |
| h2_ensemble_FARTCOIN__fork1 | h2 FARTCOIN | cooldown 600 s | +0.00 | +0.0 | 0/0 | sem dados |
| h2_ensemble_WIF__fork1 | h2 WIF | cooldown 600 s | +0.00 | +0.0 | 0/0 | sem dados |

O que aprendi: o tuner forcou `relaxed__fork1` e `poorjev_relaxed__fork1` com valores de exits **iguais aos do pai** (a diferença real é só `max_exposure_frac` 0.5 no primeiro, e nenhuma no segundo, em que exits está desligado). Esses dois forks medem pouco ou nada. Não os toco (regra), mas não vale repetir a ideia.

## 3. Decisões desta noite (3 de 6)

### A. Critérios von SOL — `relaxed_expcap50__fork1` (criado)

- Comando: `night_cli.py criteria-fork --parent relaxed_expcap50 --criteria-file run/claude_night/2026-10-03/von_sol_gray_lift.json`
- Texto: buy «the move is strong and depth is not thin; prefer a gray tape that is lifting on a calm book; be wary of buying when the tape is already green or pumping with a tight spread»; hold «anything else; hold when the tape is green and lifting with a tight spread, or when the signals are mixed»; sell inalterado; skip acrescenta «skip when the book is thin or a bot_war meets a violent tape». Instrução: «do not chase a tape that is already green».
- Porquê este pai: linhagem `relaxed` bloqueada até 10-05; `relaxed_expcap50` tem o mesmo portão von relaxed com teto de exposição 50%, o que reduz o beta na comparação fork−pai. `v2` quase não negoceia.
- Hipótese: o von persegue a fita green/pumping; preferir gray lifting reduz compras tardias.
- Confirma se (3–7 dias): habilidade fork − pai > 0 US$ com ≥ 15 trades e hit das chamadas confiantes do fork > pai.
- Refuta se: habilidade fork − pai ≤ 0 com ≥ 15 trades; ou < 5 trades em 7 dias (o texto estrangula a confiança, como aconteceu ao v2).
- Resultado: `created`, sha 695f62ca…, ficheiro `data/lab/criteria/relaxed_expcap50__fork1.json`.

### B. Portão Laya SOL — `laya_relaxed__fork1` (criado)

- Comando: `night_cli.py fork --parent laya_relaxed --diff '{"gates": {"min_confidence": 0.04, "min_prob_margin": 0.0}}'`
- Efetivo: conf ≥ 0.04, margem ≥ 0.0, skip < 0.5, cooldown 120 s, ≤ 8/h, compra 25% USDT.
- Hipótese (uma ideia: portão calibrado à escala do modelo, no P90 da Laya): a Laya passa a negociar e fica mensurável. Espero habilidade ≤ 0 em SOL (hit 31% nas chamadas confiantes).
- Confirma se: ≥ 20 trades e habilidade fork − pai > 0 US$. Refuta se: ≥ 20 trades e habilidade ≤ 0 (Laya sem habilidade em SOL), ou 0 trades em 3 dias (portão ainda mal calibrado: ver `gate_reasons`, pode ser o skip).
- Resultado: `created`.

### C. Portão Laya FARTCOIN — `FARTCOIN_laya_relaxed__fork1` (criado)

- Comando: `night_cli.py fork --parent FARTCOIN_laya_relaxed --diff '{"gates": {"min_confidence": 0.07, "min_prob_margin": 0.0}}'`
- Efetivo: conf ≥ 0.07, margem ≥ 0.0, skip < 0.5, cooldown 120 s, ≤ 8/h, compra 25% USDT.
- Hipótese: a Laya é o único modelo pequeno que vende em memes e as suas chamadas confiantes foram ligeiramente positivas; com portão na própria escala pode mostrar habilidade onde o poorjev só mostra beta. FARTCOIN pela maior faixa e melhor sinal nas outras famílias.
- Confirma se: ≥ 20 trades, vendas > 0 e habilidade fork − pai > 0 US$. Refuta se: ≥ 20 trades e habilidade ≤ 0, ou 0 trades em 3 dias.
- Resultado: `created`.

### Ideias consideradas e não executadas (zero acções é válido)

- **Critérios von memes** (vender menos em calm red fade late/night): padrão plausível, mas 1 dia, hit já 46% e os portfólios von memes quase não negoceiam; um fork numa só moeda cobriria 1/7 das chamadas. Rever com 2–3 dias de auditoria.
- **Critérios poorjev**: modelo responde buy a tudo com conf 0.95; texto não deve mudar nada e custaria uma chamada por ciclo. A alavanca (exits) já está em H1 e no fork do nightly.
- **H3 limite** (`exec.offset_bps`): -40 US$ num dia por adverse selection; evidência de 1 dia e 22 trades, espero mais um dia.
- **Bot real**: evidência de um único dia; a regra exige consistência em mais de um dia. 0/1.
- **Regras Donchian full**: não forkáveis (grupo `rule`).

## 4. O que verificar amanhã

1. `laya_relaxed__fork1` e `FARTCOIN_laya_relaxed__fork1`: há trades? Se 0, ler `gate_reasons` em `status.json` (se for `high_skip`, o portão a mexer é `max_skip_noul`, não a confiança). Se há trades, olhar C/V — a Laya vende mesmo em SOL?
2. `relaxed_expcap50__fork1`: quantas trades vs pai; distribuição da confiança do von com o texto novo (p50 e máx) — se cair abaixo de 0.35 como no v2, o texto estrangula; o próprio audit por família deve mostrar o fork como grupo "von · critérios relaxed_expcap50__fork1".
3. `h1_exits_FARTCOIN_poorjev_relaxed__fork1`: continua atrás do pai? Se sim com ≥ 20 trades, a hipótese "saídas mais apertadas" está refutada para FARTCOIN; registar, não apagar.
4. Repetir a análise de lift (erros% − acertos%) para von memes e poorjev memes com 2 dias; se "green/pumping" continuar o marcador de erro do von em SOL em dia de alta de SOL, o padrão não é só o viés baixista do dia.
5. Linhagens `relaxed`, `poorjev_relaxed`, H1 FARTCOIN, H2 FARTCOIN/WIF desbloqueiam a 10-05 00:10.

## 5. Recusas e limites

- Nenhuma recusa (exit 2) em comandos de fork; os dois primeiros dry-runs falharam só por `--reason` curto (sonda com 13 caracteres), corrigido.
- Limites: 3/6 forks esta noite; total 8/80; bot real 0/1. Linhagens bloqueadas até 10-05: relaxed, poorjev_relaxed, h1_exits_FARTCOIN_poorjev_relaxed, h2_ensemble_FARTCOIN, h2_ensemble_WIF — respeitadas (o pai `relaxed_expcap50` foi escolhido por mérito próprio, teto de exposição, não para contornar o bloqueio de `relaxed`).
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-03/`.
