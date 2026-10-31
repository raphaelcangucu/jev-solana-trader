# Diário da revisão noturna autónoma — 2026-10-08 (dia 9/30, paper only)

Sexta noite do investigador Claude. Fontes: `night_cli context` e `status` (01:30 BRT), diários de 10-06 e 10-07, `reviews/2026-10-08.md` (tuner das 00:30; estatísticas do dia 10-07 e rótulos dos forks), `data/lab/portfolios/*.json` dos forks criados ontem e anteontem (só timestamps de trades; os ficheiros não guardam lado nem tamanho). Nenhum código lido esta noite; nenhuma credencial.

Mercado nas 24 h: queda geral mais suave do que ontem. SOL −2.4% (faixa 4.3%); memes de −0.6% (BONK) a −5.7% (GOAT), com WIF −2.8%, POPCAT −3.4%, MEW −3.4%, PNUT −1.9%, FARTCOIN −1.0%. Sexto dia; segundo dia seguido de queda.

## 1. Reflexão por família (GEPA em linguagem simples)

Método igual ao das noites anteriores: só a diferença (% nos erros − % nos acertos) distingue chamadas, porque deep/quiet/calm/soft estão em ~100% de tudo. Lembrete: os três modelos veem a mesma fita de SOL no mesmo dia; um marcador comum aos três é o mesmo episódio visto por três cabeças, não três evidências.

### von (SOL e memes)

- **Porque errou.** SOL: 596 confiantes (corte P90 0.361), 268 erros em 43 episódios, 176 acertos, **hit 31%** (48% ontem; a série é 28 → 23 → 20 → 33 → 48 → 31: sobe e desce com o regime). Erros: compras em `lifting calm early gray tight` ×50, `lifting calm mid gray tight` ×35, `lifting calm night gray tight` ×26. Marcadores: **early +0.21**, green +0.07, pumping +0.05; acertos **late −0.22**. No v2 o mesmo (early +0.25, late −0.21), no fork de 1 cláusula também (early +0.29, late −0.29).
- **A série de três dias da fita `tight` quebrou.** Hoje wide 16% nos erros / 15% nos acertos → lift de `tight` ≈ 0. O que apareceu foi a hora (early nos erros, late nos acertos), que é a variável mais autocorrelacionada do estado: as 50 compras erradas em `early` são uma manhã. Sexto dia sem marcador estável no von. Linha de critérios de texto no von continua fechada (10-06).
- **Memes.** 171 confiantes, 60 erros em 41 episódios, 69 acertos, hit 40%. Erros são vendas em `fading calm … red wide`; late +0.15; acertos early −0.23. Portfólios a 2% de exposição; nada elegível, nada a fazer.
- **Números.** `relaxed` −9.1 US$ de habilidade (99% exposto; beta). **`relaxed__fork1` foi rotulado pelo tuner como lead fork** (5.0 d, 34 trades, +14.0 US$, à frente em 100% de 4 dias): era o que eu tinha dito para verificar. Acumulado +9.9 de habilidade, timing +14.5 (p 0.07), 37 trades, 7 vendas; hoje 6 trades e −1.0 de excesso ajustado (dia neutro). `v2` +0.1. H3 −54.2, H4 −28.8, híbridos SOL −33.3: sexto dia negativo.
- **O que o `h1_exits_von_relaxed__fork2` (cooldown 3600 s, criado ontem) ensinou no dia 1 — o mecanismo era outro.** Timestamps do fork: nasceu 01:38 ~99% exposto; saída (venda) às 09:46; depois **13 compras espaçadas de 1 h** (10:51, 12:06, 13:06, 14:11, 15:26, 17:02, 18:47, 20:16, 21:19, 22:19, 23:20, 00:21, 01:21) e nova saída às 01:21:30. O pai fez a mesma saída e recarregou em ~1 h (33 compras a 25% do USDT restante). Resultado do dia: fork2 14 trades, **taxas 0.96 + custo vs mark 1.64 = 2.60 US$**; pai 34 trades, **1.06 + 1.39 = 2.45 US$**. Custos iguais com menos de metade dos trades, porque a escada de 25% do USDT restante compra quase todo o USDT seja em 13 ou em 33 passos: o notional é o mesmo. **Num livro guiado por saídas, o cooldown não corta custo; atrasa a recarga** (exposição média 79% vs 96%). Habilidade do dia −2.8 vs −0.2 do pai (a recarga lenta apanhou preços piores naquele episódio; um episódio). A cláusula "custos por dia abaixo de metade dos do pai" já falha no dia 1 e não vai deixar de falhar: o fork fica a correr como teste de "recarga lenta", e o critério que importa passa a ser só habilidade com ≥ 15 trades. Lição: o churn de um livro com saídas é (n.º de saídas) × (notional da recarga); só o teto de exposição (não forkável) ou menos saídas (SL/TP mais largos) o reduzem. É por isso que, no 2×2 do von, a única célula positiva é a do teto.
- **Decisão no von: zero ações.** O positivo (lead fork) precisa de dias; a linhagem `h1_exits_von_relaxed` está bloqueada até 10-09; não há marcador de texto.

### poorjev (SOL e memes; H1, H3, H4, híbridos regime)

- **Continua só-compra:** SOL 5663/0/0, memes 1434/0/0.
- **Memes, 6.º dia.** 158 confiantes (corte 0.945), 51 erros em **15 episódios**, 63 acertos, hit 40%. O estado de erro mais frequente voltou a ser `pumping jumpy mid green tight` ×10 (o padrão de 10-03 a 10-06), mas os lifts são pequenos: green +0.08, lifting +0.07; acertos jumpy −0.07. Nada elegível. Leitura acumulada em seis dias: "perseguir pumping/tight falha" é verdade em dias laterais ou mistos (10-03 a 10-06), inverte em dia de queda forte (10-07) e fica neutro em dia de queda suave (10-08). É um marcador de regime, não do modelo. SOL: 567 confiantes, 254 erros em 36 episódios, hit 29%; gray +0.14, fading +0.13; acertos red −0.23, late −0.15. Nada elegível.
- **H1 memes: +27.5 US$ acumulados (67.9 → 29.8 → 49.8 → 27.5).** Hoje −3.0% de PnL na família; MEW pai −9.6 de excesso (SL perto do fundo), BONK −1.0, FARTCOIN −0.8, WIF +0.1. FARTCOIN H1 continua o melhor do lab: +74.2 (p 0.00), 8 RT. Como ontem: a habilidade de H1 é um punhado de saídas e cada dia de queda devolve uma parte.
- **O fork de critérios WIF (prefere red/dumping) está a ser refutado ao nível das chamadas, pelo terceiro dia seguido.** Hoje (fork1 e fork2 recebem a mesma chamada): 21 confiantes (corte 0.814), 10 erros em 10 episódios, 6 acertos, **hit 29%**; erros são compras em `dumping calm night red wide` ×4 e `dumping calm early red wide` ×3; **red +0.30**, early +0.33; acertos green −0.33. 10-06: 29% (11/6). 10-07: 29% (12/6). 10-08: 29% (10/6). As confiantes nos estados que o texto manda preferir acertam 29% em três dias e três regimes. Como as saídas do H1 são a 6%/4% e não a 15 min, isto não decide o PnL do fork2 — mas diz que o texto não codificou uma regra de 15 min. Os livros WIF (fork1, fork2, pai) estão a 98–99% expostos e sem vendas desde 10-06: nenhuma divergência possível até à próxima saída.
- **`poorjev_relaxed__fork2` (cooldown 3600 s, criado ontem)**: 15 trades (14/1) no dia, taxas 0.97 + custo vs mark 0.32 = 1.29 vs fork1 34 trades, 1.05 + 0.83 = 1.88. Taxas iguais, custo vs mark menor (0.3 vs 0.8, um dia). Habilidade −2.1 vs −0.2. Mesmo mecanismo do von: recarga lenta, não menos notional. Ambos no mesmo sentido (ligeiramente atrás no dia 1).
- **Decisão: zero ações no poorjev.** Linhagem `poorjev_relaxed` bloqueada até 10-09; BONK/MEW sem dados novos; WIF saturado.

### Laya (SOL e memes)

- **SOL — o marcador mais estável do lab.** 576 confiantes (corte 0.042), 198 erros em 47 episódios, 223 acertos, hit 40%. Erros: compras em `lifting calm mid gray tight` ×35, vendas em `fading calm mid gray wide` ×27, compras em `fading calm night gray wide` ×26. **lifting +0.24 (51% vs 26%), tight +0.22 (48% vs 26%), green +0.19 (29% vs 10%)**; acertos fading −0.38, wide −0.22, gray −0.19. Histórico de `lifting` nos erros da Laya SOL: 10-03 sim, 10-04 sim, 10-05 sim (+0.25), 10-06 sim (+0.09), 10-07 **não** (−0.13), 10-08 sim (+0.24): **5 de 6 dias**, em regimes de baixa, alta, lateral e queda. No von, `green` trocou de lado todos os dias; na Laya, `lifting` só falhou um dia. É a primeira vez que tenho um marcador de texto com suporte multi-dia num modelo.
- **`laya_relaxed__fork2` (cooldown 3600 s) — dia 2 a favor.** Dia 10-07: 19 trades (15/4), 2 de 4 RT ganhos, taxas 2.28 + custo vs mark 2.48 = 4.75 US$, **excesso ajustado +2.73**, timing +4.44 (p 0.18), exposição 38%. O fork1 no mesmo dia: 78 trades, 9/21 RT, custos 16.4, excesso −5.59 (bruto ≈ +10.8; o fork2 bruto ≈ +7.5 com 1/4 dos trades). Acumulado desde 10-06: 36 trades, ≈ **+3.5 US$ vs `laya_relaxed`** (0 trades), +30.9 vs fork1. O meu critério era "habilidade vs `laya_relaxed` > 0 com ≥ 20 trades em 3–7 dias": no dia 2, 36 trades e sinal positivo. Ainda não é confirmação (3 dias amanhã), mas é a primeira linha Laya positiva líquida e dois dias no mesmo sentido.
- **Porque é que a Laya com cooldown é o pai certo para um teste de texto.** O que refutou os dois forks de critérios do von foi que o texto deslocou a confiança (menos trades, menos exposição) sem mudar a seleção. Na Laya, a confiança (p50 0.028) contra o portão (0.04) tem o mesmo risco — foi a razão de ontem para não propor texto. Mas o fork2 é limitado pelo cooldown, não pelo portão: ontem contei 72 ciclos bloqueados por cooldown em 1.5 h, ou seja, o portão deixa passar dezenas de ciclos por hora e o cooldown escolhe 1. Se o texto baixar a confiança e passar a deixar passar só metade dos ciclos, continua a haver 1 trade por hora. **O texto só pode mudar qual ciclo da hora passa — ou seja, o estado — e não quantos trades há.** É a única configuração do lab onde "texto muda seleção" e "texto muda frequência" se separam. Daí a ação B.
- **FARTCOIN — `FARTCOIN_laya_relaxed__fork2` (veto < 0.95) repetiu o churn no dia 2.** Timestamps de 10-07: venda 00:38 (fechou a compra das 23:27 de 10-06: 71 min), compra 15:36 / venda 15:43 (7 min), compra 22:29 / venda 22:36 / compra 22:43 / venda 22:50 (7 min cada). Dia: 7 trades, 0 de 3 RT ganhos, taxas 0.95 + **custo vs mark 3.84** (FARTCOIN via jupiter_quote custa ~0.2% por lado), excesso −3.39. Acumulado: 14 trades, 7 RT, 0 ganhos, realizado −3.32 com 1.83 de taxas. A Laya em FARTCOIN vira buy→sell em 7 min, e cada round trip custa ~0.8%; nenhuma chamada a 15 min cobre isso. O plano de ontem (cooldown 3600 s sobre o fork2, o mesmo que funcionou em SOL) aplica-se: ação A. Nota honesta: em SOL o cooldown cortou 100 trades/dia para 19; em FARTCOIN são 7/dia, logo o cooldown não corta frequência, **obriga a segurar ≥ 1 h**. É um mecanismo um pouco diferente, e escrevi-o assim na hipótese.
- **Memes (chamadas).** 144 confiantes, 52 erros em 34 episódios, 42 acertos, hit 31%. Erros são vendas em `fading calm late red wide` ×8 e `dumping jumpy early red wide` ×6; calm +0.24 (elegível, mas é a palavra que está em tudo em SOL e aqui separa calm/jumpy); acertos night −0.22, jumpy −0.22. Sem portfólio Laya memes com trades além do FARTCOIN fork2; nada a fazer.

### Regras, H2 e bot real (sem ação)

- Regras memes: −1006.9 US$ acumulados; as `_full` continuam as piores (GOAT donch −111.2, WIF donch −92.9, MEW donch −88.6, GOAT regime −74.9), todas com 2–3 RT e timing p > 0.8. Barras de 1 h: nenhuma hipótese cabe em 3–7 dias. Domínio do tuner.
- H2 memes −178.1 acumulados (8% exposto); H2 SOL −45.2. Forks de cooldown 600 s do nightly: FARTCOIN +4.9 (lead fork pelo tuner), WIF −6.4: sinais opostos, ruído. Hoje `h2_ensemble_FARTCOIN` −9.3 de excesso com 16 trades e 7.2 de custos — o mesmo problema de churn, mas sem diagnóstico dos votos não proponho `pct_threshold`.
- Bot real (paper): −2.21 US$ contra segurar (−4.25%), hit 81/154, 142C/12V; auditoria 488 erros vs 340 acertos, **nenhuma palavra com lift** (– / –). Sexto dia sem frase com evidência multi-dia no próprio bot. 0/1.

### O achado de custos, corrigido depois do dia 1 dos forks A e B de ontem

Ontem escrevi "a seleção a 15 s é ligeiramente positiva em bruto e a frequência decide o sinal do líquido" e repliquei o cooldown de 1 h no von e no poorjev. O dia 1 corrige a parte do mecanismo: **frequência de trades só decide o custo quando é o modelo que vende** (Laya: o cooldown cortou 100 → 19 trades/dia e os custos 16 → 5). Quando quem vende é a saída (H1 von, poorjev fork1), o custo é (n.º de saídas) × (notional da recarga), e o cooldown só atrasa a recarga sem reduzir o notional (taxas 0.96 vs 1.06 no von, 0.97 vs 1.05 no poorjev). Os forks A e B de ontem testam, afinal, "recarga lenta depois de uma saída", que é um teste de timing/beta, não de custo. Ficam a correr (podem ser positivos por outra razão), mas a hipótese registada tinha o mecanismo errado e deixo isto escrito para não repetir o erro: **antes de forkar um parâmetro, perguntar quem gera os trades que custam.**

## 2. Forks anteriores (margens desde a criação; fonte: `night_cli context` 01:30 e `reviews/2026-10-08.md`)

| Fork | Quem | Mudança | Idade | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---:|---|---|
| relaxed__fork1 | nightly | exits + teto 50% | 5.1 d | +2.15 | +10.5 | 37/0 | **lead fork (tuner, 5 d, 100% dos dias)**. Hoje neutro (−1.0, 6 trades). 7 vendas; ainda pequeno, mas é a única linha von positiva em seis regimes |
| poorjev_relaxed__fork1 | nightly | exits + margem 0 | 5.1 d | −2.69 | −8.9 | 146/1 | atrás; hoje −0.2 com 34 trades (dia de 1 saída). Vive como pai do fork2 |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | 5.1 d | −2.91 | −41.0 | 398/126 | **refutada** (6.º dia). Hoje +4.6 vs −0.8 do pai (54 trades, 3 vendas, 10.5 de custos): um dia bom não muda −41 |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | 5.1 d | +0.51 | +4.9 | 52/60 | lead fork pelo tuner; ≈ pai |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | 5.1 d | −0.81 | −6.4 | 42/51 | atrás; sinal oposto a FARTCOIN → ruído |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip) | 5.0 d | +1.69 | −0.1 | 1/4 | **a caminho de refutar**: 0 trades e 0% de exposição pelo 4.º dia seguido; 82% das chamadas são sell (erros hoje: vendas em `fading … wide`, late +0.23). 7.º dia a 10-10 → refutada se < 5 trades |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | 5.0 d | −6.76 | −56.3 | 380/0 | método confirmado (81 RT); habilidade líquida refutada; hoje −5.6 com 16.4 de custos (bruto ≈ +10.8). Vive como controlo do fork2 |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | 5.0 d | −0.18 | −1.7 | 4/0 | 0 trades hoje; substituído na prática pelo fork2 |
| h1_exits_von_relaxed__fork1 | claude-night | critérios (1 cláusula) | 4.0 d | −0.17 | −22.8 | 62/127 | **refutada** (10-06). Hoje −3.7 vs −0.2 do pai, 66% vs 96% exposto; marcador `early` igual ao pai (texto não muda seleção) |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios "não perseguir" | 4.0 d | −0.03 | −3.1 | 63/63 | clone do pai em trades; **as chamadas confiantes nos estados preferidos (dumping red) acertam 29% há 3 dias** → o texto não codificou regra de 15 min. Vive como pai do fork2 |
| h1_exits_BONK_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 3.0 d | +2.08 | +13.7 | 80/79 | 3 vendas, à frente, atribuição confundida (ontem). Hoje 0 vendas nos dois (20 vs 14 compras). Sem dados novos |
| h1_exits_MEW_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 3.0 d | −0.14 | −1.5 | 54/54 | **2 vendas** (23:00 de 10-06 e 1 hoje, simultânea com o pai; excesso −11.7 vs −9.6). Preciso de ≥ 3; ainda sem dados |
| laya_relaxed__fork2 | claude-night | cooldown 3600 s | 2.0 d | +2.94 | +30.9 | 37/162 | **dia 2 a favor**: +2.7 de excesso, 19 trades, custos 4.75, 2/4 RT. ≈ +3.5 vs `laya_relaxed` com 36 trades (critério ≥ 20 atingido, sinal certo; faltam dias) |
| FARTCOIN_laya_relaxed__fork2 | claude-night | skip < 0.95 | 2.0 d | −0.54 | −4.3 | 14/0 | **mecanismo confirmado** (14 trades em 2 d vs 4 em 5 d); **churn confirmado** (7 RT de 7–71 min, 0 ganhos, perda = taxas + slippage). Gera a ação A |
| h1_exits_WIF_poorjev_relaxed__fork2 | claude-night | conf ≥ 0.75 | 2.0 d | +0.64 | +3.1 | 38/38 | saturado (98% exposto, 1 venda, 0 hoje); +0.8 vs +0.1 no dia é ruído de exposição. Sem dados até à próxima saída |
| h1_exits_von_relaxed__fork2 | claude-night | cooldown 3600 s | 1.0 d | +0.09 | −3.1 | 17/24 | **mecanismo diferente do previsto**: custos iguais ao pai (2.60 vs 2.45), recarga em 13 h em vez de 1 h. Cláusula de custos já falhou; resta habilidade com ≥ 15 trades (hoje −2.8 vs −0.2, 1 episódio) |
| poorjev_relaxed__fork2 | claude-night | cooldown 3600 s | 1.0 d | +0.07 | −2.8 | 17/22 | idem: taxas iguais (0.97 vs 1.05), −2.1 vs −0.2 no dia 1; mesmo sentido que o von (não é efeito de modelo) |

### O que os forks ensinaram esta noite

1. **Perguntar quem gera os trades que custam antes de forkar.** O cooldown funcionou na Laya porque a Laya vende; no H1 von e no poorjev fork1 quem vende é a saída, e a recarga compra o mesmo notional em 13 passos ou em 33. Os forks A/B de ontem viraram testes de "recarga lenta".
2. **A Laya com cooldown é a primeira linha onde um teste de texto fica limpo.** O número de trades é fixado pelo cooldown; o texto só decide o estado em que o trade cai. É o desenho que faltava para o método GEPA deste lab.
3. **Um marcador que aguenta 5 de 6 dias vale mais do que um lift grande num dia.** `lifting` na Laya SOL (5/6) contra `green` no von (troca de lado todos os dias) e `tight`/`pumping` no poorjev memes (4 dias, depois inverteu e ficou neutro).
4. **Um texto que prefere estados que acertam 29% três dias seguidos não é uma regra de 15 min.** O fork WIF só pode ganhar por recomprar menos (portão), não por escolher o estado.

## 3. Decisões desta noite

Ambas as linhagens que eu queria usar (`FARTCOIN_laya_relaxed`, `laya_relaxed`) estavam com desbloqueio marcado para 10-08 01:35; o contexto foi gerado às 01:30. Fiz os dry-runs primeiro (os dois recusados por `--reason` > 800 caracteres, erro meu; encurtei) e depois ambos recusaram por `cap_1_fork_per_2.0d`. Repeti uma vez no fim da noite; o resultado está em cada ação.

### A. Laya FARTCOIN — cooldown 3600 s sobre `FARTCOIN_laya_relaxed__fork2`

- Comando: `night_cli.py fork --parent FARTCOIN_laya_relaxed__fork2 --diff '{"gates": {"cooldown_seconds": 3600}}' --reason '…'`.
- Efetivo se criado: conf ≥ 0.07, margem ≥ 0.0, skip < 0.95, **cooldown 3600 s** (fork2: 120), ≤ 8/h, compra 25% USDT, sem saídas.
- Hipótese: o fork2 perde por custo de round trips de minutos, não por seleção (2 dias: 14 trades, 7 RT de 7–71 min, 0 ganhos, realizado −3.3 com 1.8 de taxas e 3.8 de custo vs mark no dia; cada RT custa ~0.8%). Em SOL o cooldown de 1 h deixou a Laya positiva líquida 2 dias seguidos. Replica o mecanismo em FARTCOIN para separar ativo de mecanismo. Uma ideia: pausa de 1 h (em FARTCOIN obriga a segurar ≥ 1 h, mais do que cortar frequência).
- Confirma se (3–7 dias): habilidade fork3 − fork2 > 0 US$ com ≥ 10 trades. Refuta se: ≤ 0 com ≥ 10 trades (a Laya não tem seleção em FARTCOIN a 1 h; fecha a linha Laya memes) ou < 6 trades em 4 dias.
- Resultado: **`created` à segunda tentativa** → `FARTCOIN_laya_relaxed__fork3`. Efetivo: conf ≥ 0.07, margem ≥ 0.0, skip < 0.95, cooldown 3600 s, ≤ 8/h, compra 25% USDT. Caps 1/6, total 18/80. (Primeira tentativa: dry-run recusado por `--reason` 844 caracteres; segunda: recusado por `cap_1_fork_per_2.0d` antes das 01:35.)

### B. Laya SOL — critérios "não perseguir lifting tight" sobre `laya_relaxed__fork2`

- Ficheiro: `run/claude_night/2026-10-08/laya_sol_nochase.json` (sem dígitos). Muda só buy/instructions/hold; sell e skip iguais ao baseline:
  - instr.: «buy on strength only when the book can absorb it; do not chase a tape that is already lifting with a tight spread»
  - buy: «the move is strong and depth is not thin; be wary of buying when the tape is already lifting or green with a tight spread on a calm book»
  - sell: «the move is fading or fees are climbing»
  - hold: «anything else; hold when the tape is lifting with a tight spread, or when the signals are mixed»
  - skip: «conditions are too hostile to trade at all»
- Comando: `night_cli.py criteria-fork --parent laya_relaxed__fork2 --criteria-file …/laya_sol_nochase.json --reason '…'`.
- Hipótese: as compras confiantes da Laya em SOL falham quando perseguem uma fita já `lifting` com spread `tight` (lifting nos erros em 5 de 6 dias; hoje lifting +0.24, tight +0.22, green +0.19; erro mais frequente `buy lifting calm mid gray tight` ×35), ao contrário do von, onde `green` trocava de lado cada dia. O pai é o primeiro Laya positivo líquido e, como o cooldown fixa ~1 trade/h, o texto só muda qual ciclo da hora passa, não quantos: controla o confundidor que refutou os textos do von. Uma ideia: não perseguir. Custo: uma chamada extra à Laya por ciclo.
- Confirma se (3–7 dias): habilidade fork3 − fork2 > 0 US$ com ≥ 20 trades **e** trades do fork3 ≥ metade dos do fork2 (prova de que o texto não estrangulou). Refuta se: ≤ 0 com ≥ 20 trades, ou trades < metade do pai (o texto só baixou a confiança, como no von; fecha a linha de texto na Laya).
- Resultado: **`created` à segunda tentativa** → `laya_relaxed__fork3`, critérios `cbac4690b6…` em `data/lab/criteria/laya_relaxed__fork3.json` (pai usava `criteria_baseline.json`). Caps 2/6, total 19/80. (Dry-runs recusados por `--reason` com 1001, 825 e 814 caracteres — três cortes até caber; depois `cap_1_fork_per_2.0d` antes das 01:35.)

### Ideias consideradas e não executadas

- **Qualquer fork sobre `h1_exits_von_relaxed__fork2` / `poorjev_relaxed__fork2`** para corrigir o mecanismo: linhagens bloqueadas até 10-09; e a alavanca certa (teto de exposição) não é forkável. O que reduz saídas (SL/TP mais largos) é outra hipótese, com 1–2 saídas/dia não se mede em 3–7 dias.
- **Fork sobre `relaxed__fork1`** (lead fork): precisa de dias; o tuner agora usa-o como base.
- **Reentrada 120 min numa terceira moeda**: MEW tem 2 vendas, BONK 3 com atribuição confundida. Esperar.
- **Contra-texto no WIF** (o texto atual prefere estados que acertam 29%): seria um fork de critérios com chamada extra, com os livros saturados e sem relação demonstrada entre acerto a 15 min e PnL de saídas a 6%/4%. Não.
- **Texto no von, texto no poorjev**: von fechado (10-06); poorjev memes sem lift hoje e marcador dependente de regime.
- **H2 `pct_threshold`**, **regras 1 h**, **saídas de H1 memes**: pelas mesmas razões das noites anteriores (sem diagnóstico; 2–3 RT; 6–8 vendas por moeda).
- **Bot real**: 0/1; sexto dia sem palavra com lift na auditoria do próprio bot.

## 4. O que verificar amanhã (2026-10-09)

1. **A e B foram criados** (`FARTCOIN_laya_relaxed__fork3`, `laya_relaxed__fork3`). Os livros clonados nascem iguais ao pai; a diferença só aparece a partir do primeiro ciclo em que o cooldown ou o texto decide diferente. Dia 1 serve para confirmar o mecanismo, não a habilidade.
2. **`laya_relaxed__fork2`**: dia 3. Continua positivo vs `laya_relaxed` com ≥ 20 trades? Se sim, é a primeira hipótese do Claude confirmada pelo critério que escrevi; anotar os custos por dia (≈ 5) e o bruto.
3. **`h1_exits_von_relaxed__fork2` e `poorjev_relaxed__fork2`**: medir só habilidade vs pai com ≥ 15 trades (a cláusula de custos está morta). Contar saídas por dia e a duração da recarga; se um dia tiver 3+ saídas, o fork recarrega tão devagar que fica a meio da exposição o dia todo — ver se isso ajuda ou prejudica na habilidade.
4. **Se B for criado**: trades do fork3 vs fork2 no mesmo dia (tem de ser ≥ metade), e em que estados caem as compras do fork3 (esperado: menos `lifting … tight`). Juntar `lab_decisions` por `source_decision_id` se precisar.
5. **Se A for criado**: n.º de trades (esperado 2–6/dia), duração dos RT (≥ 1 h), e se a perda deixa de ser só taxas.
6. **WIF fork1/fork2**: a 4.ª leitura das confiantes em `dumping red` continua a 29%? Primeira venda do fork2 desde 10-06?
7. **MEW**: 3.ª venda? Preço médio da recompra fork (2 h) vs pai (30 min).
8. **`relaxed_expcap50__fork1`**: 7.º dia a 10-10; se < 5 trades, refutada.
9. **Marcadores**: `lifting` na Laya SOL (7.º dia); `early/late` no von (hora = episódio, não regra); `pumping/tight` no poorjev memes com o retorno do dia ao lado.
10. Linhagens: `h1_exits_von_relaxed` e `poorjev_relaxed` livres a 10-09 ~01:37; `FARTCOIN_laya_relaxed` e `laya_relaxed` bloqueadas até 10-10 ~01:4x (A e B criados hoje); `h1_exits_WIF_poorjev_relaxed` livre desde 10-08 01:35, sem plano.

## 5. Recusas e limites

- **Recusas exit 2 (6, nenhuma por limite do lab a sério):**
  - 4 por `--reason` acima de 800 caracteres (A: 844; B: 1001, 825, 814). Erro meu, igual ao de 10-06; corrigido encurtando. Nota para as próximas noites: escrever o `--reason` com folga, ≤ 700.
  - 2 por `cap_1_fork_per_2.0d` (A sobre `FARTCOIN_laya_relaxed__fork2`, B sobre `laya_relaxed__fork2`), porque os dry-runs correram entre 01:30 e 01:35 e as linhagens só desbloqueavam às 01:35. Aceitei, escrevi o diário, e repeti uma vez cada: ambos `created`. Não usei outro pai para fugir ao bloqueio.
- Limites: **2/6 forks criados** (A de parâmetros; B de critérios, a primeira chamada extra ao modelo desta semana, e a primeira na Laya); total 19/80; bot real 0/1.
- Linhagens agora bloqueadas: `FARTCOIN_laya_relaxed` e `laya_relaxed` até 10-10 ~01:4x; `h1_exits_von_relaxed` e `poorjev_relaxed` até 10-09 ~01:37.
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-08/`. Nenhum código lido ou editado esta noite. Nenhuma credencial lida.
