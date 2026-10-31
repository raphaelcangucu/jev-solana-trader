# Diário da revisão noturna autónoma — 2026-10-07 (dia 8/30, paper only)

Quinta noite do investigador Claude. Fontes: `night_cli context` e `status` (01:30 BRT), diários de 10-05 (2.ª versão) e 10-06, `reviews/2026-10-07.md` (tuner das 00:30) e as linhas dos mesmos portfólios em `reviews/2026-10-04.md`, `2026-10-05.md`, `2026-10-06.md` (para a decomposição de custos em 3–4 dias), `data/lab/portfolios/*.json` dos forks e pais (timestamps de trades), `data/lab/registry.json` (parâmetros efetivos do H1 SOL), `logs/lab_decisions.jsonl` (só leitura; decisões desde as 00:00 de hoje), `bot/lab_bot.py` e `bot/gates.py` (só leitura, para confirmar se as saídas passam pelo cooldown).

Mercado nas 24 h: queda generalizada. SOL −1.6% (faixa 4.2%); memes −2.5% (GOAT) a −7.3% (BONK), com FARTCOIN −6.6%, PNUT −6.4%, WIF −6.1%, POPCAT −5.4%, MEW −4.9%. É o quinto regime distinto em cinco noites (baixa, alta, lateral, memes em baixa com SOL parado, queda forte geral). O que se repetiu nos cinco já não é viés de um dia; o que se inverteu hoje era condicional ao regime.

## 1. Reflexão por família (GEPA em linguagem simples)

Método igual ao das noites anteriores: só a diferença (% nos erros − % nos acertos) distingue chamadas, porque deep/quiet/calm/soft estão em ~100% de tudo. Lembrete de ontem: quando três modelos veem a mesma fita de SOL no mesmo dia, um marcador comum aos três não é evidência independente.

### von (SOL e memes)

- **Porque errou.** SOL: 611 confiantes (corte P90 0.366), 175 erros em 35 episódios, 292 acertos, **hit 48%** — o melhor dos cinco dias (28% → 23% → 20% → 33% → 48%). Erros: compras em `lifting calm mid gray tight` ×35, `lifting calm night gray tight` ×28, `lifting calm early green tight` ×21. Marcadores de erro: **tight +0.20**, gray +0.13, pumping +0.12; acertos: **wide −0.20**, flat −0.17, green −0.14. No v2 o mesmo: tight +0.19, gray +0.18, early +0.16; acertos green −0.26, wide −0.19.
- **Primeiro marcador com três dias seguidos no von: a fita `tight`.** 10-05 (erros "quase só compras … com a fita tight"), 10-06 (+0.10), 10-07 (+0.20); e `wide` nos acertos nos dois últimos. green continua a oscilar (−0.18 ontem, −0.14 hoje: dois dias nos acertos depois de três nos erros). Não é acionável: o spread não tem parâmetro, e a linha de critérios de texto no von ficou fechada ontem (dois forks de critérios: um estrangulou, outro baixou exposição sem mudar seleção). Fica registado como marcador a vigiar.
- **Memes.** 147 confiantes, 39 erros em 30 episódios, 60 acertos, hit 42%. Erros são vendas em `fading calm late red wide` (red +0.24, elegível); acertos night −0.41 (vendas de madrugada acertam). Portfólios a 2% de exposição; a palavra elegível não move dinheiro. Nada a fazer.
- **Números.** `relaxed` −9.2 US$ (99% exposto; −15.9 hoje, beta puro). **`relaxed__fork1` (saídas + teto 50%) continua a única linha positiva do von: +11.7 US$ acumulados (+12.5 vs pai), 28 trades, 5 RT, timing p 0.04, à frente em 100% dos dias.** Hoje −10.1 de PnL mas habilidade −2.7 com 6.7 US$ de custos (bruto ≈ +4). `v2` +0.7. H3 −48.4, H4 −28.7, híbridos SOL −31.5: quinto dia negativo, < 5 RT.
- **Descoberta sobre o `relaxed__fork1` que muda o que posso fazer com ele.** Fui ver os parâmetros efetivos do `h1_exits_von_relaxed` no registo: **tem exatamente as mesmas saídas do fork1** (TP 2.5% / SL 1.5% / trailing 1% arma 1% / reentrada 30 min), sem o teto. Logo o quadro 2×2 já está completo há cinco dias: nada (`relaxed`) −9.2; só teto (`relaxed_expcap50`) −3.4; só saídas (`h1_exits_von_relaxed`) família −21.3; saídas + teto (`relaxed__fork1`) +11.7. **A vantagem do fork1 não vem das saídas; vem do teto ou da interação.** E `gates.max_exposure_frac` não está na lista de parâmetros forkáveis pelo night_cli. Conclusão: não há fork útil sobre o fork1 esta noite; o que ele precisa é de dias (amanhã completa 5 d com ≥ 20 trades e pode ser lead fork pelo tuner).
- **Decisão no von: um fork de parâmetros no `h1_exits_von_relaxed`** (secção 3, A), motivado pela decomposição de custos (secção 1, "Custos"), não pelos adjetivos.

### poorjev (SOL e memes; H1, H3, H4, híbridos regime)

- **Continua só-compra:** SOL 5495/0/0, memes 1404/0/0.
- **O padrão de quatro dias inverteu-se no quinto.** Memes hoje: 187 confiantes (corte 0.944), 77 erros em 30 episódios, 71 acertos, hit 38%. Erros: `dumping jumpy mid red wide` ×23, `dumping calm mid red wide` ×10; marcadores calm +0.08, harsh +0.07, wide +0.06; acertos **pumping −0.11**. Em 10-03 a 10-06 era o contrário (erros tight/pumping/jumpy/lifting; acertos wide/red/dumping). Num dia em que todas as memes caíram 5–7%, comprar o recuo falhou e comprar a subida acertou. **Leitura: "não perseguir a fita" é uma regra de mercado lateral ou misto; em dia de tendência forte, o despejo continua.** Isto enfraquece a base do fork de critérios WIF (texto que prefere red/dumping): nas duas últimas noites, as confiantes do fork1 nos estados preferidos (`dumping calm … red wide`) acertaram 29% (ontem 11/6, hoje 12/6 em 12 episódios). SOL hoje: erros red +0.08, fading +0.07; acertos early −0.14. Nada elegível.
- **H1 memes: +49.8 US$ acumulados (de +67.9 → +29.8 → +49.8).** Hoje +20 no conjunto, mas a dispersão por moeda é enorme: FARTCOIN +20.5, POPCAT +25.6 (p 0.04), PNUT +13.7 (timing p 0.86: não é timing), BONK −17.0, WIF −13.1, GOAT −7.2, MEW −0.5. O que decide o dia de cada moeda é se o SL a 4% disparou antes ou depois do fundo. FARTCOIN H1 continua o melhor portfólio do lab: +74.8 (p 0.00), 8 RT. Não há como calibrar níveis com 6–8 vendas por moeda; mantenho o que disse ontem.
- **Forks BONK/MEW (reentrada 120 min)** — ver secção 2: BONK atingiu 3 vendas e está à frente, mas a margem vem de um caminho divergente; MEW tem 1 venda. Aguardo.
- **Fork WIF (portão 0.75)** — ver secção 2: o mecanismo confirmou-se (o portão filtra estados), habilidade pendente.
- **Decisão: um fork de parâmetros no `poorjev_relaxed__fork1`** (SOL com saídas; secção 3, B), réplica do mesmo teste de custo do von, para separar modelo de mecanismo.

### Laya (SOL e memes)

- **SOL.** 563 confiantes (corte 0.044), 205 erros em 36 episódios, 239 acertos, hit 43%. Erros: vendas em `fading calm gray wide` ×48/×36 e compras em `lifting calm mid gray tight` ×35; marcadores gray +0.17, fading +0.17; acertos green −0.22. `lifting` passou para os acertos (−0.13) depois de quatro dias nos erros — mais um marcador de dia.
- **`laya_relaxed__fork2` (cooldown 3600 s) — dia 1 a favor da hipótese.** Desde 01:35 de 10-06: 16 trades (12/4), **≤ 24/dia como previsto** (17 trades em 24 h, espaçados ≥ 1 h: 05:12, 06:34, 07:44, … 00:47), taxas 2.38 + custo vs mark 3.58 = 5.96 US$, excesso ajustado **+0.73** (bruto ≈ +6.7). No mesmo dia o fork1 fez 83 trades, custos 18.04, excesso ajustado **−18.06** (bruto ≈ 0: o pior dia de seleção do fork1). Margem fork2 − fork1 +18.9 US$; vs `laya_relaxed` (pai do pai, 0 trades) +0.7. Hoje, 72 ciclos bloqueados por cooldown e 1 trade. Critério de confirmação (≥ 20 trades e habilidade > 0 vs `laya_relaxed`): 17 trades, ainda não; direção certa.
- **`FARTCOIN_laya_relaxed__fork2` (veto < 0.95) — mecanismo confirmado, e o churn repete-se.** 8 trades em 1 dia (fork1: 4 em 4 dias). Mas os 4 round trips duraram 7, 14, 14 e 70 min; 0 ganhos; realizado −1.17 US$ dos quais −1.00 são taxas (preço −0.17). Hoje 12 decisões: 11 `low_confidence` (0.024–0.063), 1 venda a 0.090 executada. **A Laya em FARTCOIN comporta-se como a Laya em SOL antes do fork2: a perda é taxa, não preço.** Linhagem bloqueada até 10-08 01:35; o passo seguinte é o mesmo que funcionou em SOL (cooldown 3600 s sobre o fork2), não antes.
- **Memes (chamadas).** 150 confiantes, 54 erros em 32 episódios, 52 acertos, hit 35%. Erros: vendas em `fading calm late red wide` ×18 e `dumping violent night red wide` ×12; red +0.15. Nada elegível.

### Custos: o que se repete em quatro portfólios e quatro dias

Juntei, das revisões do tuner, excesso ajustado vs (taxas + custo vs mark) dos portfólios SOL com saídas ou com a Laya calibrada:

| Portfólio | Janela | Excesso aj. US$ | Custos US$ | Bruto ≈ | Trades |
|---|---|---:|---:|---:|---:|
| h1_exits_von_relaxed | 10-04 a 10-06 | −7.0 | 14.9 | +7.9 | 92 |
| poorjev_relaxed__fork1 | 10-03 a 10-06 | −3.5 | 10.9 | +7.4 | 111 |
| relaxed__fork1 | 10-03 a 10-06 | +4.1 | 10.2 | +14.3 | 28 |
| laya_relaxed__fork1 | 10-03 a 10-06 | −47.1 | 55.0 | +7.9 | 298 |
| laya_relaxed__fork2 | 10-06 (dia 1) | +0.7 | 6.0 | +6.7 | 16 |

Em todos, o bruto é positivo e parecido (+7 a +14 em 3–4 dias) e o líquido é o bruto menos ~0.15–0.35 US$ por trade; o "custo vs mark" disparou em 10-06 (faixa de SOL 4.2%): 9.6 no H1 von, 8.4 na Laya, 5.4 no fork1, 4.8 no poorjev. Isto é um achado do lab, não de um modelo: **a seleção a 15 s é ligeiramente positiva em bruto e a frequência decide o sinal do líquido.** A Laya fork2 foi o primeiro teste de "cortar frequência e manter seleção" e o dia 1 disse que sim. As ações A e B desta noite replicam esse teste no von e no poorjev.

Verifiquei no código (só leitura) o que importa para estes forks: `check_exits` em `bot/lab_bot.py` chama `market_trade` diretamente, sem passar por `apply_gates`; o cooldown em `bot/gates.py` só se aplica às ações do modelo. **Um cooldown de 1 h espaça as compras (a escada de recompra) e nunca atrasa um stop-loss ou take-profit.**

### Regras, H2 e bot real (sem ação)

- Regras memes: −1112.9 US$ acumulados; as `_full` são as piores (GOAT donch −119.4, MEW donch −99.8, GOAT regime −99.5, WIF donch −95.6), e hoje cada `_regime_full` fez 1 compra / 1 venda e perdeu −35 a −66 com timing p 1.00. O context diz agora que regras são forkáveis (`rule.*`, `exits.*`, `regime_filter.*`), mas com barras de 1 h e 2–3 RT em 5 dias nenhuma hipótese é falsificável em 3–7 dias. Domínio do tuner; ficam rotuladas.
- H2 memes −141.6 acumulados (8% exposto); H2 SOL −45.1 com 20 RT. Forks de cooldown 600 s do nightly: FARTCOIN +3.2, WIF −6.9 — sinais opostos, ruído. Não tenho diagnóstico dos votos do ensemble para propor `pct_threshold`.
- Bot real (paper): −1.06 US$ contra segurar, hit 81/154, 142C/12V; auditoria 407 erros vs 396 acertos, nenhuma palavra com lift. Quinto dia sem frase com evidência multi-dia. 0/1.

## 2. Forks anteriores (margens desde a criação; fonte: `night_cli context` 01:30)

| Fork | Quem | Mudança | Idade | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---:|---|---|
| relaxed__fork1 | nightly | exits + teto 50% | 4.1 d | +1.41 | +12.5 | 28/0 | **em observação, a confirmar-se**: à frente 100% dos dias, p 0.04, 5 RT; amanhã (5 d, ≥ 20 trades) pode ser lead fork. Novo: a célula "só saídas" existe (H1 von) e é negativa → a vantagem exige o teto |
| poorjev_relaxed__fork1 | nightly | exits + margem 0 | 4.1 d | −0.77 | −4.4 | 120/1 | 5 RT; decomposição: −3.5 de habilidade com 10.9 de custos → bruto +7.4 (3 de 4 dias > 0). Gera o fork B |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | 4.1 d | −3.56 | −46.7 | 343/122 | **refutada** (5.º dia; 10-06: +12.0 vs +20.5 do pai, 100 trades, 24 US$ de custos). Rotulada |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | 4.1 d | +0.32 | +3.2 | 39/45 | ≈ pai |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | 4.1 d | −0.82 | −6.9 | 38/47 | atrás; sinal oposto a FARTCOIN → ruído |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip) | 4.0 d | +0.49 | +2.0 | 1/0 | **a caminho de refutar**: 0 trades e 0–1% de exposição pelo 3.º dia seguido; o "+2.0" é estar em caixa num dia de queda. 7.º dia a 10-10 |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | 4.0 d | −5.01 | −48.5 | 305/0 | método confirmado (60 RT); habilidade líquida refutada; 10-06 foi o pior dia (bruto ≈ 0, custos 18). Vive como controlo do fork2 |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | 4.0 d | −0.18 | −1.7 | 4/0 | substituído na prática pelo fork2 (o bloqueio era o veto) |
| h1_exits_von_relaxed__fork1 | claude-night | critérios (1 cláusula) | 3.0 d | −0.07 | −11.2 | 45/101 | **refutada** (ontem). Hoje −2.5 vs −6.2 do pai só porque esteve 39% exposto vs 90% — exposição, não seleção. Mantém-se |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios "não perseguir" | 3.0 d | −0.02 | −0.4 | 59/59 | **clone do pai em trades**: SL às 23:00 de 10-06 e 16 recompras nos mesmos ciclos. Vive como pai do fork2 |
| h1_exits_BONK_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 2.0 d | +2.10 | +10.6 | 64/76 | **3 vendas atingidas, à frente — mas com ressalva de atribuição.** Vendas do fork: 10-05 14:18, 10-06 13:33, 10-06 22:58; do pai: 10-05 14:18, 10-06 18:41, 10-06 23:01. A saída das 13:33 (que o pai não teve, porque o seu preço de entrada era mais baixo) e a recompra 15:34–18:02 antes do SL do pai às 18:41 explicam o +4.0 vs −17.0 de 10-06. A espera de 2 h divergiu os livros e, a partir daí, as saídas; a margem não isola "esperar 2 h". Episódio das 23:00: pai recomprou 23:31–01:03 (16 compras, entrada média 3.509e-6), fork 01:03–01:31 (5 até agora, 3.491e-6: 0.5% mais barato — o primeiro episódio tinha sido 0.5% mais caro). Decisão só com MEW |
| h1_exits_MEW_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 2.0 d | +0.06 | −0.5 | 18/29 | **1 venda** (23:00 de 10-06, simultânea com o pai). Pai recomprou 23:36–01:09 (16, entrada média 0.0005039); fork 01:01–01:29 (5, 0.0005037): igual. Sem dados |
| laya_relaxed__fork2 | claude-night | cooldown 3600 s | 1.0 d | +1.84 | +18.9 | 17/87 | **dia 1 a favor**: 16 trades, custos 6.0, habilidade +0.7 (bruto +6.7) vs fork1 83 trades, custos 18.0, −18.1. Falta chegar a 20 trades |
| FARTCOIN_laya_relaxed__fork2 | claude-night | skip < 0.95 | 1.0 d | −0.23 | −1.1 | 8/0 | **mecanismo confirmado** (8 trades/dia vs 4 em 4 dias); **seleção sem dados** (4 RT de 7–70 min, 0 ganhos, perda = taxas). O churn da Laya repete-se em memes |
| h1_exits_WIF_poorjev_relaxed__fork2 | claude-night | conf ≥ 0.75 | 1.0 d | +0.71 | +2.4 | 28/34 | **mecanismo confirmado**: saturou em ~10 h (fork1: 2.5 h); depois do SL das 23:00 recomprou em 11 de 16 ciclos. Hoje 12 decisões: 8 compras a 0.75–0.83 em `dumping … red wide`; 4 bloqueadas a 0.66–0.70 em `whipping jumpy night red tight`, `flat calm night red wide`, `fading calm night red wide`, `flat calm night red tight`. O texto + portão é um filtro de estado. 1 venda; habilidade pendente (≥ 3 vendas) |

### O que os forks ensinaram esta noite

1. **A seleção bruta a 15 s é positiva em todos os portfólios SOL com saídas, e o líquido é a frequência.** Quatro portfólios, três modelos, 3–4 dias: bruto +7 a +14, líquido = bruto − custos. O único que é positivo líquido (`relaxed__fork1`) é o que menos negoceia (28 trades em 4 dias). O Laya fork2 confirmou no dia 1 que cortar a frequência não destrói a seleção (bruto por trade até subiu).
2. **Texto + portão na escala nova funciona como filtro de estado no poorjev.** O WIF fork2 compra em dumping/red/wide e bloqueia whipping/flat/tight. Mas o padrão que o texto codifica inverteu-se hoje em dia de tendência: se o fork2 ganhar, será por recomprar menos, não por escolher melhor o estado.
3. **Divergir o livro muda tudo a jusante.** A reentrada de 2 h em BONK criou um preço de entrada diferente, que criou uma saída diferente (13:33), que criou a margem. Com 3 vendas, a hipótese "esperar 2 h recompra mais barato" só tem dois episódios limpos (um contra, um a favor, ±0.5%). Precisa de MEW.
4. **O 2×2 do von já estava feito.** Antes de propor "a célula que falta", ler o registo: a célula existia e dizia que as saídas sem teto perdem.

## 3. Decisões desta noite

### A. H1 von SOL — cooldown 3600 s — `h1_exits_von_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent h1_exits_von_relaxed --diff '{"gates": {"cooldown_seconds": 3600}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.35, margem ≥ 0.2, skip < 0.5, **cooldown 3600 s** (pai: 120), ≤ 8/h, compra 25% USDT, saídas TP 2.5% / SL 1.5% / trailing 1% (arma +1%), reentrada 30 min.
- Hipótese: o H1 von SOL perde por custo e não por seleção (3 dias: habilidade −7.0 com 14.9 de custos → bruto +7.9; 92 trades; a escada de recompra depois de cada saída faz 8–10 compras por hora). As saídas não passam pelo cooldown (verificado no código), logo a pausa só espaça as compras. É a réplica, noutro modelo, do que o `laya_relaxed__fork2` mostrou no dia 1. Uma ideia: frequência.
- Confirma se (3–7 dias): habilidade fork2 − pai > 0 US$ com ≥ 15 trades, e custos por dia (taxas + custo vs mark) abaixo de metade dos do pai. Refuta se: ≤ 0 com ≥ 15 trades (a seleção do von não sobrevive à amostragem esparsa), ou < 8 trades em 3 dias.
- Resultado: `created`. Caps 1/6, total 16/80.

### B. poorjev SOL com saídas — cooldown 3600 s — `poorjev_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent poorjev_relaxed__fork1 --diff '{"gates": {"cooldown_seconds": 3600}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.35, margem ≥ 0.0, skip < 0.5, **cooldown 3600 s** (fork1: 120), ≤ 8/h, compra 25% USDT, saídas TP 2.5% / SL 1.5% / trailing 1% (arma +1%), reentrada 30 min.
- Hipótese: réplica de A no poorjev (que compra em todos os ciclos, logo a escada de recompra é a mais densa do lab), para separar efeito de modelo de efeito de mecanismo — o mesmo desenho de BONK/MEW. 4 dias: habilidade −3.5 com 10.9 de custos → bruto +7.4 (3 de 4 dias > 0), 111 trades.
- Confirma se: habilidade fork2 − fork1 > 0 US$ com ≥ 15 trades em 3–7 dias, **no mesmo sentido que A**. Refuta se: ≤ 0 com ≥ 15 trades, ou sinais opostos entre von e poorjev (efeito de modelo, não de frequência).
- Resultado: `created`. Caps 2/6, total 17/80.

### Ideias consideradas e não executadas

- **Fork sobre `relaxed__fork1`** (a melhor linha do von): a alavanca que o distingue é o teto de exposição, que o night_cli não deixa forkar; e a célula "saídas sem teto" já existe (H1 von, negativa). Precisa de dias, não de variantes.
- **Reentrada 120 min numa terceira moeda H1 (FARTCOIN)**: BONK tem 3 vendas a favor mas com atribuição confundida; MEW tem 1 venda. Replicar antes de MEW decidir é gastar um fork sem informação nova.
- **Cooldown 3600 s sobre `FARTCOIN_laya_relaxed__fork2`**: é o passo certo (o churn repete-se), mas a linhagem está bloqueada até 10-08 01:35. Fazer o mesmo noutra moeda Laya seria usar outro pai só para fugir ao bloqueio. Fica para amanhã (tentar depois das 01:36).
- **Critérios de texto** (qualquer modelo): von fechado ontem; no poorjev o padrão de 4 dias inverteu-se hoje (regime); na Laya a confiança a 0.028 contra portão 0.04 liga/desliga tudo com qualquer deslocamento. Zero forks de critérios, zero chamadas extra ao modelo.
- **Regras `_full` com saídas**: −1113 acumulados, mas 1 h por barra e 2–3 RT por portfólio — nenhuma condição de confirmação cabe em 3–7 dias.
- **H2 `pct_threshold`**: sem diagnóstico dos votos.
- **Saídas mais largas em H1 memes** depois de outro dia de −6%: 6–8 vendas por moeda não calibram níveis.
- **Bot real**: 0/1; quinto dia sem palavra com lift na auditoria do próprio bot.

## 4. O que verificar amanhã (2026-10-08)

1. **`h1_exits_von_relaxed__fork2` e `poorjev_relaxed__fork2`**: ≤ 24 trades/dia cada? custos por dia vs pai/fork1 (devem cair para ≈ 1/4); habilidade vs pai (A) e vs fork1 (B) na mesma janela; **os dois no mesmo sentido que o Laya fork2?** Se os três (Laya, von, poorjev) forem positivos líquidos com menos trades, o achado de custos está estabelecido entre modelos. Nota: os livros clonados nascem ~90% expostos; a diferença só aparece depois da primeira saída.
2. **`laya_relaxed__fork2`**: chega aos 20 trades? continua à frente de `laya_relaxed` e do fork1? Se sim, a hipótese "custo, não seleção" fica confirmada pelo meu critério.
3. **`FARTCOIN_laya_relaxed__fork2`**: duração dos round trips e perda = taxas de novo? Se sim, criar `--parent FARTCOIN_laya_relaxed__fork2 --diff '{"gates": {"cooldown_seconds": 3600}}'` (linhagem livre a 10-08 01:35; tentar depois das 01:36; se recusar, aceitar e registar).
4. **`h1_exits_WIF_poorjev_relaxed__fork2`**: 2.ª/3.ª venda? habilidade vs fork1; fração de ciclos bloqueados; estados das compras continuam dumping/red/wide? Linhagem livre a 10-08 01:35, sem plano de ação.
5. **BONK/MEW**: MEW precisa de ≥ 3 vendas. Em cada novo episódio, preço médio da recompra do fork (2 h) vs do pai (30 min); já há 1 contra e 1 a favor em BONK (±0.5%).
6. **`relaxed__fork1`**: o tuner marca lead fork (5 d, 28 trades, 100% dos dias)? **`relaxed_expcap50__fork1`**: 7.º dia a 10-10; se < 5 trades, refutada.
7. **Lift do poorjev em memes (6.º dia)**: o padrão tight/pumping nos erros volta num dia lateral, ou era só regime? Anotar o retorno do dia ao lado do lift. **`tight` no von SOL**: 4.º dia nos erros?
8. Linhagens que desbloqueiam: `FARTCOIN_laya_relaxed`, `h1_exits_WIF_poorjev_relaxed`, `laya_relaxed` a 10-08 01:35; `h1_exits_von_relaxed` e `poorjev_relaxed` a 10-09 ~01:4x.

## 5. Recusas e limites

- **Recusas exit 2: nenhuma.** Os dois dry-runs e os dois forks passaram à primeira; as linhagens `h1_exits_von_relaxed` e `poorjev_relaxed` estavam livres. Não tentei nenhuma linhagem bloqueada.
- Limites: **2/6 forks criados** (A e B, ambos de parâmetros, zero forks de critérios, zero chamadas extra ao modelo); total 17/80; bot real 0/1.
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-07/`. Código lido (`bot/lab_bot.py`, `bot/gates.py`), nunca editado. Nenhuma credencial lida.
