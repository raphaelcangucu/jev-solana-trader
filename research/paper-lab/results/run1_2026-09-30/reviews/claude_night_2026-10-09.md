# Diário da revisão noturna autónoma — 2026-10-09 (dia 10/30, paper only)

Sétima noite do investigador Claude. Fontes: `night_cli context` e `status` (01:30 BRT), diários de 10-07 e 10-08, `reviews/2026-10-09.md` (tuner das 00:30; estatísticas do dia 10-08, elegibilidade e rótulos), `data/lab/portfolios/*.json` dos forks e pais (só timestamps de trades, preço médio de entrada e `reentry_block_until`). Nenhum código lido ou editado; nenhuma credencial lida.

Mercado nas 24 h: terceiro dia seguido de queda e o mais largo da semana. SOL −4.3% (faixa 9.6%); memes de −5.5% (WIF) a +1.8% (FARTCOIN, a única verde), com BONK −3.2%, GOAT −3.2%, POPCAT −2.8%, MEW −2.6%, PNUT −0.4%. Houve uma queda sincronizada por volta das 12:15–12:25 BRT que disparou o stop-loss de quase todos os H1 memes ao mesmo minuto.

Nota de contexto: o tuner das 00:30 criou **12 forks** esta noite (31 no total antes dos meus; eram 19 ontem): confiança 0.42 em quatro von (híbridos, H3, H4), percentil 0.96 no H2 SOL, SL 3.2–3.6% em GOAT/PNUT/POPCAT (GOAT também com reentrada 36 min), confiança 0.385 em quatro von memes. Essas linhagens ficam bloqueadas para mim até 10-11. Também bloqueou por cap de 7 dias os candidatos para `h1_exits_von_relaxed`, `relaxed_expcap50`, BONK, FARTCOIN, MEW e WIF.

## 1. Reflexão por família (GEPA em linguagem simples)

Método igual: só a diferença (% nos erros − % nos acertos) distingue chamadas, porque deep/quiet/calm/soft/held estão em ~100% de tudo em SOL. Lembrete: três modelos a ver a mesma fita de SOL no mesmo dia são um episódio visto por três cabeças.

### von (SOL e memes)

- **Porque errou.** SOL: 612 confiantes (corte P90 0.384), 219 erros em 48 episódios, 252 acertos, **hit 41%** (série 28 → 23 → 20 → 33 → 48 → 31 → 41). Erros: compras em `lifting calm early gray tight` ×40, `lifting calm night green tight` ×33, `lifting calm mid green tight` ×32. Marcador elegível: **early +0.22** (37% vs 14%), green +0.10; acertos late −0.15, night −0.11. No v2 igual (early +0.20; acertos night −0.35, late −0.33). Segundo dia seguido com `early` nos erros — mas a hora é a variável mais autocorrelacionada do estado: 40 compras erradas em `early` são uma manhã. Sétimo dia sem marcador de texto estável no von; `green` continua a trocar de lado (hoje +0.10, ontem +0.07, antes −0.14/−0.18). Linha de critérios de texto no von: fechada desde 10-06, mantém-se.
- **Memes.** 166 confiantes, 59 erros em 40 episódios, 76 acertos, hit 46%. Erros são vendas em `fading calm night/late red wide`; elegíveis **late +0.34, calm +0.26, fading +0.21**; acertos violent −0.21, loud −0.21. Ou seja: o von vende bem no caos e mal na calma noturna. Os portfólios von memes estão a 0.6–3% de exposição e o tuner acabou de forkar quatro deles (conf 0.385). Nada a fazer; a palavra elegível não move dinheiro.
- **Números.** `relaxed` −8.3 US$ de habilidade (99% exposto; beta). **`relaxed__fork1` continua lead fork**: 6.0 d, 70 trades, +21.8 US$ de habilidade vs pai (+5.24 pp), à frente em 100% de 5 dias; hoje +0.85 com 36 trades e 42% de exposição num dia de −4.3%. Única linha von positiva em sete regimes; a alavanca (teto 50%) não é forkável. `v2` −4.9 (hoje −9.1 com 1 venda: um episódio). H3 −73.2, H4 −22.9, híbridos SOL −52.5: sétimo dia negativo; os híbridos venderam 1 vez hoje a −35 cada (timing p 0.93–0.94).
- **`h1_exits_von_relaxed__fork2` (cooldown 3600 s, dia 2) — segundo dia contra.** Dia 10-08: 26 trades (20/6), 5 de 6 RT ganhos, taxas 3.15 e custo vs mark **−4.99** (fills favoráveis), excesso ajustado **−6.24** vs **−0.80** do pai (97 trades, 6/6 RT); exposição 40% vs 80%. Acumulado −4.5 US$ vs pai com 41 trades (≥ 15: a cláusula de amostra está cumprida). PnL do fork melhor (−2.77% vs −4.34%) porque esteve metade do tempo em caixa num dia de queda — isso é beta, e a habilidade desconta-o. Ver leitura conjunta com o poorjev abaixo.
- **`h1_exits_von_relaxed__fork1` (1 cláusula, refutado em 10-06)**: hoje +10.7 vs −0.8 do pai, 45 trades vs 97, exposição 50% vs 80%, timing +21.3 (p 0.18). Acumulado ainda −9.2 US$ de habilidade; marcador `early` igual ao do pai (+0.16 vs +0.22) → o texto continua a não mudar a seleção. Um dia bom não reabre a hipótese; fica anotado.
- **Decisão no von: zero ações.**

### poorjev (SOL e memes; H1, H3, H4, híbridos regime)

- **Continua só-compra:** SOL 5630/0/0, memes 1429/0/0.
- **Memes, 7.º dia — o marcador voltou a trocar de lado com o regime.** 143 confiantes (corte 0.955), 73 erros em 20 episódios, 56 acertos, hit 39%. Erros: compras em `dumping violent mid red wide` ×30, `pumping violent mid red tight` ×12. Elegíveis **violent +0.26, red +0.24**; acertos jumpy −0.26, green −0.23. Leitura dos sete dias: em dias laterais (10-03 a 10-06) a compra confiante falha quando persegue `pumping/tight`; em dias de queda (10-07, hoje) falha quando compra o despejo `dumping/red`; em dia de queda suave (10-08) é neutro. **A compra confiante do poorjev falha na direção em que o dia tende**: é um modelo sem informação a 15 min e os seus erros são o regime do dia. Nenhum texto codifica isso sem olhar o retorno do dia. SOL: 571 confiantes (corte 0.537), 216 erros em 31 episódios, hit 43%; gray +0.15; acertos red −0.14. Nada elegível.
- **H1 memes: +134.7 US$ de habilidade acumulada (ontem +27.5).** O dia 10-08 deu ≈ +83 na família: GOAT +26.9 (p 0.03), PNUT +18.7 (p 0.03), POPCAT +17.4 (p 0.04), WIF +15.8, FARTCOIN +8.7, BONK −0.9, MEW −3.3. Mecanismo visível nos timestamps: SL sincronizado às 12:1x–12:2x na queda geral, recompra 30 min depois mais barato. É o mesmo mecanismo que, nos dias 10-07 (BONK −17, WIF −13), devolveu dinheiro quando o preço ressaltou depois do SL. **A habilidade de H1 é um punhado de saídas e o sinal depende de a queda continuar depois do stop.** Com 6–11 vendas por moeda em 7 dias ninguém calibra níveis; o tuner forkou SL mais apertado (3.2–3.6%) em três moedas — vou acompanhar como teste externo.
- **Reentrada 120 min (BONK/MEW) — o terceiro episódio é limpo e a favor nas duas moedas.** Timestamps de 10-08:
  - MEW: pai vendeu 12:23:37, bloqueio até 12:53, recomprou 12:54–15:14 (19 compras, entrada média 0.0004588); fork vendeu **12:21:04** (2.5 min antes, mesmo episódio), bloqueio até 14:21, recomprou 14:25–16:48 (19 compras, entrada média **0.0004528: 1.3% mais barato**). Dia: fork +22.7 de excesso vs −3.3 do pai; PnL +0.02% vs −4.31% com MEW −2.6%.
  - BONK: pai vendeu 09:50 (SL só dele, por entrada diferente) e 12:22:21; recomprou 12:56–15:16 (entrada 3.213e-6); fork vendeu **12:12:53**, bloqueio até 14:12, recomprou 14:13–16:36 (entrada **3.167e-6: 1.4% mais barato**). Dia: fork +45.2 (p 0.06) vs −0.9.
  - Acumulado: BONK fork +60.4 US$ de habilidade vs pai (4.0 d, 100 trades, 100% de 3 dias); MEW fork +22.3 (74 trades, 67% de 3 dias, **3 vendas** — o mínimo que eu pedia). Episódios de recompra por moeda: BONK +0.5% mais caro / −0.5% / **−1.4%**; MEW igual / (simultâneo, pior em excesso) / **−1.3%**.
  - **Ressalva honesta:** os dois episódios a favor caem em dias de queda (10-07, 10-08), em que esperar 2 h compra mais barato porque o ativo continua a cair depois do stop. O que ainda não vi é um episódio depois de take-profit/trailing num dia de subida, onde esperar deve custar. Por isso a réplica desta noite é em **FARTCOIN (a única meme que subiu hoje, e a que mais saídas tem: 11 RT) e em WIF (a que mais caiu)**: se as duas ganharem, é mecanismo; se só WIF, é regime de queda.
- **Fork WIF de critérios (fork1) e portão 0.75 (fork2): 4.º dia a 29%.** 21 confiantes (corte 0.823), 13 erros em 13 episódios, 6 acertos; erros são compras em `dumping violent mid red wide`; red +0.17, violent +0.12. Série de hit nas confiantes dos estados que o texto manda preferir: 29%, 29%, 29%, 29%. Nos trades, os três livros WIF fizeram **exatamente 40 (38/2)** em 10-08 — o fork2 (conf ≥ 0.75) deixou de filtrar: depois do SL das 12:2x recomprou em todos os ciclos, como o pai. Excesso 14.4 vs 15.5 vs 15.8. Clones. A linhagem continua sem decisão possível pelo texto; a decisão desta noite usa o **pai original** como base (ver 3.B).
- **`poorjev_relaxed__fork2` (cooldown 3600 s, dia 2) — segundo dia contra, no mesmo sentido do von.** 10-08: 27 trades (22/5), 4/5 RT, taxas 3.34 + custo vs mark 1.85 = 5.2, excesso **−15.0** vs **+3.3** do fork1 (108 trades, 6/6 RT); exposição 42% vs 82%. Acumulado **−15.9 US$** vs fork1 com 43 trades. **Leitura conjunta von + poorjev, 2 dias, ambos negativos com > 15 trades:** num dia com 5–6 saídas, a recarga de 1 compra/hora nunca chega à exposição cheia; o fork vende nos mesmos stops (as saídas não passam pelo cooldown) mas participa menos nos ressaltos entre stops. O que eu chamei ontem "recarga lenta" é, na prática, **"estar sempre a meio da exposição num dia de serra"** — e a habilidade penaliza isso dos dois lados. A cláusula de refutação (≤ 0 com ≥ 15 trades) está cumprida nos dois ao fim de 2 dias; como escrevi 3–7 dias, **rotulo amanhã se o dia 3 não inverter**. O que aprendi fica abaixo (lições).
- **Decisões no poorjev: duas réplicas da reentrada 120 min (FARTCOIN e WIF).** Secção 3.

### Laya (SOL e memes)

- **SOL — o marcador `lifting` falhou pela segunda vez em sete dias.** 612 confiantes (corte 0.044), 218 erros em 50 episódios, 253 acertos, hit 41%. Erros: vendas em `fading calm mid gray wide` ×47, compras em `lifting calm mid gray tight` ×35 e `lifting calm night green tight` ×33 — mas `lifting` também está nos acertos na mesma proporção (não aparece na lista de lifts; green +0.06 é o maior). Histórico de `lifting` nos erros da Laya SOL: sim, sim, sim (+0.25), sim (+0.09), **não** (−0.13), sim (+0.24), **≈ 0**. Cinco de sete. Continua a ser o marcador mais estável do lab, mas hoje não teria justificado um texto.
- **`laya_relaxed__fork3` (critérios "não perseguir lifting tight", criado ontem) — refutado no mecanismo no dia 1.** Chamadas do fork: **buy 8 / sell 307 / hold 5204** (94% hold; o pai com texto base: buy 4462 / sell 1082 / hold 85). Conf p50 0.014 (base 0.023). Trades: **1** (uma venda às 05:01 de 10-08; desde então 100% em USDT) contra 21 do fork2 no mesmo dia. O meu critério de refutação era "trades do fork3 < metade dos do fork2": 1 vs 21, e o mecanismo (hold em 94% dos ciclos) não vai mudar com mais dias. Excesso do dia +4.1 e habilidade +7.4 vs fork2 são "estar em caixa num dia de −4.3%". **Refutada.** Lição (nova, diferente da do von): no von o texto deslocou a *confiança*; na Laya o texto deslocou a *ação* — a cláusula de hold («hold when the tape is lifting with a tight spread, or when the signals are mixed») foi lida à letra e "signals are mixed" é quase sempre verdade. O desenho limpo que sobra para a Laya é **só uma cautela no buy, com hold = «anything else» intacto**. A linhagem `laya_relaxed` está bloqueada até 10-10 01:38 e o marcador falhou hoje: não há ação, e só proponho esse texto se `lifting` voltar aos erros amanhã.
- **`laya_relaxed__fork2` (cooldown 3600 s) — dia 3 contra.** 10-08: 21 trades (14/7), 4/7 RT, taxas 2.48 + custo vs mark 2.92 = 5.4, excesso **−7.22** (bruto ≈ −1.8: o primeiro dia com seleção bruta negativa). No mesmo dia o fork1 fez 128 trades, 26/32 RT ganhos, custos 24.6, excesso −13.9 (bruto ≈ +10.7). Acumulado vs `laya_relaxed` (0 trades): +0.7, +2.7, −7.2 → **≈ −3.8 US$ com 57 trades**; vs fork1 +34.5. O meu critério ("habilidade vs `laya_relaxed` > 0 com ≥ 20 trades em 3–7 dias") está em sinal errado no dia 3. Não refuto ainda (janela até 10-13), mas a leitura muda: **o cooldown cortou o custo (5 vs 25 por dia) e manteve a seleção em 2 de 3 dias; no dia de serra larga, 1 trade por hora perdeu a seleção que o fork1 (a cada 2 min) teve.** Isto é coerente com o que vi no von/poorjev fork2: a amostragem esparsa é cega aos ressaltos de um dia de faixa 9.6%.
- **`FARTCOIN_laya_relaxed__fork3` (cooldown 3600 s, criado ontem) — mecanismo confirmado, seleção a 1 h má no dia 1.** 9 trades (5/4) espaçados ≥ 1 h (11:41, 12:52, 14:09, 15:12, 17:50, 19:21, 21:13, 22:23, 23:54), 1 de 4 RT ganhos, taxas 1.10 + custo vs mark 2.88 = 4.0, **excesso −17.0** num dia em que FARTCOIN subiu 1.8% (bruto ≈ −13: já não é custo, é seleção). O fork2 no mesmo dia: 22 trades, 1/5 RT, excesso −26.5. Margem +9.7 mas ambos muito negativos. Com 9 trades falta 1 para o critério (≥ 10). Se amanhã repetir, a Laya não tem seleção em FARTCOIN a nenhuma frequência e a linha Laya memes fecha.
- **Memes (chamadas).** 145 confiantes, 67 erros em 37 episódios, 50 acertos, hit 35%. Erros são vendas em `dumping jumpy mid red wide` ×9 e `fading calm late red wide` ×8; late +0.13; acertos fading −0.12. Nada elegível.
- **Decisão na Laya: zero ações** (linhagens bloqueadas; marcador falhou; dois forks em dia contra).

### Regras, H2 e bot real (sem ação)

- Regras memes: −960.0 US$ acumulados; `_full` continuam as piores (GOAT donch −110.5, WIF donch −86.3, MEW donch −82.7), 2–3 RT, timing p > 0.8; 0 trades hoje em todas as 28. Regras SOL: `grid_sol_2pct` +11.0 de excesso hoje com 6 compras (p 0.05) — um dia. Domínio do tuner.
- H2 memes −228.5 acumulados (10% exposto); H2 SOL −46.1 (99.6% exposto, 0 trades hoje; o tuner forkou percentil 0.96). `h2_ensemble_FARTCOIN__fork1` (cooldown 600 s) é lead fork: +14.2 vs pai, hoje +13.5 com 17 trades; `h2_ensemble_WIF__fork1` −7.1: sinais opostos, ruído. Sem diagnóstico dos votos, não proponho `pct_threshold`.
- Bot real (paper): −4.30 US$ contra segurar (−8.28%), hit 91/171, 148C/23V; auditoria do dia 416 erros vs 339 acertos, **nenhuma palavra com lift** (– / –). Sétimo dia sem frase com evidência multi-dia no próprio bot. 0/1.

### Lições desta noite

1. **Amostragem esparsa é cega a dias de serra.** Três forks de cooldown 3600 s (Laya SOL dia 3, von e poorjev dia 2) perderam a seleção no mesmo dia de faixa 9.6% com 5–7 saídas. O cooldown funciona quando a perda é taxa em dias estreitos; num dia largo, 1 trade/hora não apanha os ressaltos e vende nos mesmos stops. **Frequência não é um parâmetro de custo; é um parâmetro de regime.**
2. **O texto na Laya desloca a ação, não a confiança.** Uma cláusula de hold com "signals are mixed" fez 94% hold. Para a Laya, nunca tocar no hold; só cautela no buy.
3. **A reentrada de 2 h ganha quando o ativo continua a cair depois do stop.** Dois episódios limpos a favor (−1.3%, −1.4%), ambos em dias de queda. Falta o episódio depois de TP num dia de subida; a réplica em FARTCOIN (verde hoje) e WIF (a que mais caiu) foi desenhada para isso.
4. **Quando um fork fica sincronizado com o pai, não há teste.** WIF fork1/fork2 fizeram exatamente os 40 trades do pai em 10-08; o portão 0.75 só filtrava enquanto o livro estava a encher. Só o pai original serve de base para uma mudança mecânica (secção 3.B).

## 2. Forks anteriores (margens desde a criação; fonte: `night_cli context` 01:30 e `reviews/2026-10-09.md`)

| Fork | Quem | Mudança | Idade | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---:|---|---|
| relaxed__fork1 | nightly | exits + teto 50% | 6.0 d | +5.24 | +21.8 | 70/— | **lead fork (tuner)**, 100% de 5 dias; hoje +0.85 com 36 trades |
| poorjev_relaxed__fork1 | nightly | exits + margem 0 | 6.1 d | −3.50 | +5.9 | 253/4 | atrás em PnL, à frente em habilidade (hoje +3.3 com 108 trades); controlo do fork2 |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | 6.1 d | −8.17 | −95.3 | 477/177 | **refutada** (7.º dia; hoje −47.1 com 83 trades, 0/8 RT, 26 US$ de custos) |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | 6.1 d | +1.38 | +14.2 | 71/83 | lead fork (tuner); hoje +13.5 |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | 6.1 d | −0.87 | −7.1 | 55/69 | atrás; sinal oposto a FARTCOIN → ruído |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip) | 6.0 d | +3.76 | +1.4 | 1/19 | **refutada na prática**: 1 trade em 6 dias, 0% exposto pelo 5.º dia; o "+" é caixa em dias de queda. Rótulo formal a 10-10 (7.º dia, < 5 trades) |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | 6.0 d | −8.64 | −63.0 | 513/0 | método confirmado (113 RT); habilidade líquida refutada; hoje −13.9 com 24.6 de custos (bruto +10.7, 26/32 RT) |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | 6.0 d | −0.18 | −1.8 | 4/0 | 0 trades; substituído pelo fork2/fork3 |
| h1_exits_von_relaxed__fork1 | claude-night | critérios (1 cláusula) | 5.0 d | +2.71 | −9.2 | 110/223 | **refutada** (10-06); hoje +10.7 vs −0.8 com metade dos trades e da exposição — um dia; marcador `early` igual ao pai |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios "não perseguir" | 5.0 d | −0.04 | −0.8 | 102/102 | clone do pai (40/40 trades hoje); confiantes nos estados preferidos a 29% pelo 4.º dia → **texto não codificou regra de 15 min** |
| h1_exits_BONK_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 4.0 d | +6.49 | +60.4 | 100/116 | **3.º episódio limpo a favor** (recompra 1.4% mais barata); 100% de 3 dias; ressalva: dois episódios a favor em dias de queda |
| h1_exits_MEW_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 4.0 d | +2.57 | +22.3 | 74/74 | **3 vendas atingidas**; 3.º episódio a favor (recompra 1.3% mais barata, +22.7 vs −3.3 no dia); mesma ressalva |
| laya_relaxed__fork2 | claude-night | cooldown 3600 s | 3.0 d | +3.40 | +34.5 | 57/295 | vs fork1 à frente; **vs `laya_relaxed` ≈ −3.8 com 57 trades (dia 3 contra: −7.2, bruto −1.8)**; janela até 10-13 |
| FARTCOIN_laya_relaxed__fork2 | claude-night | skip < 0.95 | 3.0 d | −2.82 | −26.1 | 37/0 | mecanismo confirmado; hoje −26.5 com 22 trades, 1/5 RT → a Laya em FARTCOIN perde por seleção, não só por taxa |
| h1_exits_WIF_poorjev_relaxed__fork2 | claude-night | conf ≥ 0.75 | 3.0 d | +0.78 | +2.4 | 77/77 | deixou de filtrar (40 trades = pai); sem teste possível |
| h1_exits_von_relaxed__fork2 | claude-night | cooldown 3600 s | 2.0 d | +1.50 | −4.5 | 41/120 | **a caminho de refutar**: 2 dias negativos (−2.8, −6.2 vs −0.2, −0.8), 41 trades; dia 3 decide |
| poorjev_relaxed__fork2 | claude-night | cooldown 3600 s | 2.0 d | +0.22 | −15.9 | 43/129 | **a caminho de refutar**: −15.0 vs +3.3 hoje; mesmo sentido do von → efeito de mecanismo; dia 3 decide |
| FARTCOIN_laya_relaxed__fork3 | claude-night | cooldown 3600 s | 1.0 d | +0.92 | +9.7 | 9/23 | mecanismo confirmado (9 trades ≥ 1 h); seleção −17.0 no dia 1 (bruto −13); 9/10 trades para o critério |
| laya_relaxed__fork3 | claude-night | critérios (buy+hold) | 1.0 d | +1.40 | +7.4 | 1/20 | **refutada no mecanismo**: hold em 94% das chamadas, 1 trade vs 21 do pai (critério "trades < metade" cumprido) |
| 12 forks do tuner (00:31) | nightly | conf 0.42 / 0.385, SL 3.2–3.6%, pct 0.96 | 0.0 d | 0 | 0 | 0 | nascidos esta noite; sem dados |

## 3. Decisões desta noite

Linhagens livres com hipótese madura: `h1_exits_FARTCOIN_poorjev_relaxed` (último fork 10-03) e `h1_exits_WIF_poorjev_relaxed` (livre desde 10-08). Ambos os dry-runs passaram à primeira; `--reason` escrito com folga (< 700 caracteres).

### A. H1 FARTCOIN — reentrada 120 min — `h1_exits_FARTCOIN_poorjev_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent h1_exits_FARTCOIN_poorjev_relaxed --diff '{"exits": {"reentry_cooldown_min": 120}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.35, margem ≥ 0.2, skip < 0.5, cooldown 120 s, ≤ 8/h, compra 25% USDT, saídas TP 6% / SL 4% / trailing 3% (arma +3%), **reentrada 120 min** (pai: 30).
- Hipótese: réplica em 3.ª moeda da reentrada de 2 h de BONK/MEW (+60 e +22 US$ em 4 dias; em 10-08 recompra 1.3–1.4% mais barata depois de vender ao mesmo minuto que o pai). FARTCOIN é a única meme que subiu hoje e a que tem mais saídas (11 RT): testa o mecanismo num regime diferente e acumula episódios depressa. Uma ideia: esperar 2 h depois de uma saída.
- Confirma se (3–7 dias): habilidade fork − pai > 0 US$ com ≥ 3 vendas, no mesmo sentido que BONK/MEW. Refuta se: ≤ 0 com ≥ 3 vendas (o ganho de BONK/MEW era regime de queda).
- Resultado: **`created`**. Caps 1/6, total 32/80.

### B. H1 WIF — reentrada 120 min — `h1_exits_WIF_poorjev_relaxed__fork3` (criado)

- Comando: `night_cli.py fork --parent h1_exits_WIF_poorjev_relaxed --diff '{"exits": {"reentry_cooldown_min": 120}}' --reason '…'` (dry-run OK antes).
- Efetivo: igual a A (reentrada 120 min; pai 30).
- Hipótese: par de A na moeda que mais caiu (−5.5%). Se só WIF ganhar, o efeito é regime de queda; se FARTCOIN e WIF ganharem, é mecanismo. O pai original é a base limpa porque fork1 (texto) e fork2 (portão 0.75) ficaram clones do pai em trades. Uma ideia, a mesma de A, noutro regime.
- Confirma se (3–7 dias): habilidade fork − pai > 0 US$ com ≥ 3 vendas. Refuta se: ≤ 0 com ≥ 3 vendas, ou sinal oposto ao de FARTCOIN sem explicação de regime.
- Resultado: **`created`**. Caps 2/6, total 33/80.

### Ideias consideradas e não executadas

- **Texto na Laya SOL só com cautela no buy (hold intacto)**, para corrigir o estrangulamento do fork3: linhagem `laya_relaxed` bloqueada até 10-10 01:38 e o marcador `lifting` falhou hoje (5/7). Fica como plano condicional.
- **Qualquer coisa sobre os três forks de cooldown 3600 s** (Laya dia 3, von e poorjev dia 2, todos negativos no dia): a lição é de regime, não de parâmetro; deixo correr até o critério fechar.
- **Texto no poorjev memes (violent/red elegíveis)**: o marcador troca de lado com a direção do dia (7 dias); um texto que evita `dumping red` perde nos dias laterais onde isso acertava. Não.
- **Texto no von (early elegível, von memes late/calm/fading)**: hora = episódio; portfólios memes a 2%; linha fechada.
- **Fork sobre `relaxed__fork1`**: a alavanca é o teto (não forkável); precisa de dias.
- **Reentrada 120 min em GOAT/PNUT/POPCAT**: bloqueadas pelo tuner até 10-11 (o tuner pôs 36 min em GOAT: um meio-teste externo).
- **H2 `pct_threshold`, regras 1 h, saídas de H1**: pelas razões das noites anteriores (sem diagnóstico; 2–3 RT; níveis incalibráveis com 6–11 vendas).
- **Bot real**: 0/1; sétimo dia sem palavra com lift na auditoria do próprio bot.

## 4. O que verificar amanhã (2026-10-10)

1. **A e B (reentrada 120 min em FARTCOIN e WIF)**: nasceram clones (livros ~95% expostos); a diferença só aparece na primeira saída. Em cada saída anotar: hora, tipo (SL ou TP/trailing), direção do dia, e preço médio da recompra do fork (2 h) vs do pai (30 min). Guardar a tabela de episódios por moeda (já tenho BONK: +0.5/−0.5/−1.4; MEW: 0/−/−1.3).
2. **Os três forks de cooldown 3600 s**: `h1_exits_von_relaxed__fork2` e `poorjev_relaxed__fork2` no dia 3 — se continuarem ≤ 0 vs pai com ≥ 15 trades, **rotular refutados** e escrever a lição de regime; `laya_relaxed__fork2` vs `laya_relaxed` (hoje ≈ −3.8): a janela vai até 10-13. Anotar a faixa do dia ao lado de cada um (hipótese derivada: cooldown ganha em dias de faixa < 5%, perde em dias > 8%).
3. **`FARTCOIN_laya_relaxed__fork3`**: chega aos 10 trades; se habilidade vs fork2 continuar negativa em bruto, fechar a linha Laya memes (rótulo).
4. **`relaxed_expcap50__fork1`**: 7.º dia; se < 5 trades, rótulo refutada (previsto).
5. **`laya_relaxed__fork3`**: confirmar que continua em hold (esperado); já rotulado refutado.
6. **Marcadores**: `lifting` na Laya SOL (8.º dia; está 5/7); `early` no von (3.º dia?); poorjev memes com o retorno do dia ao lado (hipótese: o marcador segue a direção do dia).
7. **Forks do tuner** (12, nascidos 00:31): dia 1; só anotar se algum SL 3.2–3.6% disparou onde o pai (4%) não.
8. **Bot real**: hit e palavras com lift; nada a fazer até haver evidência multi-dia.
9. Linhagens: `h1_exits_FARTCOIN_poorjev_relaxed` e `h1_exits_WIF_poorjev_relaxed` bloqueadas até 10-11 ~01:4x; `laya_relaxed` e `FARTCOIN_laya_relaxed` livres a 10-10 01:38; `h1_exits_von_relaxed` e `poorjev_relaxed` livres desde 10-09 01:37; GOAT/PNUT/POPCAT/híbridos/H2 SOL/meme von bloqueadas pelo tuner até 10-11 00:31.

## 5. Recusas e limites

- **Recusas exit 2: nenhuma.** Dois dry-runs e dois forks passaram à primeira; nenhuma linhagem bloqueada foi tentada. (Uma chamada `ls` via Bash foi negada pelo harness — correto, o Bash é só para o `night_cli`; li os livros com Read.)
- Limites: **2/6 forks criados** (A e B, ambos de parâmetros, mesma ideia em duas moedas de regime oposto; zero forks de critérios, zero chamadas extra ao modelo); total 33/80; bot real 0/1.
- Linhagens agora bloqueadas por mim: `h1_exits_FARTCOIN_poorjev_relaxed` e `h1_exits_WIF_poorjev_relaxed` até 10-11 ~01:4x.
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-09/`. Nenhum código lido ou editado. Nenhuma credencial lida.
