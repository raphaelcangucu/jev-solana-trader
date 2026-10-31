# Diário da revisão noturna autónoma — 2026-10-04 (dia 5/30, paper only)

Segunda noite do investigador Claude. Fontes: `night_cli context` e `status`, diário de 2026-10-03, `reviews/2026-10-04.md` (tuner das 00:30), `reports/summary_latest.md`, `data/lab/status.json`, `data/lab/portfolios/*.json`, `logs/lab_decisions.jsonl` (só leitura).

Mercado nas 24 h: dia de alta moderada. SOL +1.5% (faixa 1.8%), memes todas positivas (BONK +5.6%, GOAT +4.0%, WIF +2.2%, MEW +2.1%). Ontem foi baixista; hoje foi altista. Isto dá o primeiro teste de "o padrão sobrevive à mudança de sinal do dia?" para as hipóteses de ontem.

## 1. Reflexão por família (GEPA em linguagem simples)

Nota de método: continuo a usar só a diferença (% nos erros − % nos acertos). Palavras como deep/quiet/calm/soft aparecem em ~100% de tudo e não distinguem nada. Hoje separo também o que se repetiu nos dois dias (sinal candidato) do que se inverteu (ruído do dia).

### von (SOL: `relaxed`, `relaxed_expcap50`, `v2`, H1/H3/H4, híbridos)

- **Porque errou.** 277 chamadas confiantes (corte 0.356), 173 erros em 30 episódios, 63 acertos, hit 23%. Quase só compras. Erros: compras em `flat calm night green/red` com a fita **wide** (35% vs 24%) e **early** (13% vs 2%). Acertos: **late** (97% vs 75%), **night** (89% vs 71%), tight.
- **O marcador de ontem não se repetiu.** Ontem green tinha lift +0.21 (60% erros vs 39% acertos). Hoje green 59%/56% (+0.03). No v2 ainda aparece (+0.15) mas em 24 episódios. Conclusão honesta: "o von persegue a fita green" era, em boa parte, o viés de um dia baixista (comprar com fita verde num dia que desce é erro por construção). Sinal fraco; a hipótese do fork de ontem fica em dúvida pela própria evidência que a motivou.
- **O que se repetiu nos dois dias:** os acertos do von concentram-se mais tarde no dia (ontem late 48% vs 38%; hoje late 97% vs 75%). Mas hora-do-dia é a variável mais autocorrelacionada que há (blocos inteiros do dia caem num só episódio) e dois dias de intradiário de SOL não chegam. Não ajo sobre isto.
- **Números.** `relaxed`: 60C/2V, exposição 98%, PnL +0.98% mas habilidade −8.3 US$: beta de SOL. `relaxed_expcap50__fork1` (o meu fork de critérios): ver secção 2 — é a lição mais importante da noite. `v2`: +2.2 US$ com 1/1 trades (não negoceia). H3 limite −38.9, H4 horas −25.4, híbridos −25.4: a direção continua unanimemente negativa em SOL, ainda com < 5 round trips cada.
- **Memes (`meme_*_relaxed`).** 1437 chamadas, 49% vendas; 67 erros em 46 episódios vs 55 acertos, hit 27% (ontem 46%). Os erros são vendas em `fading calm red wide` que depois ressaltam. Ontem os erros eram late/night; hoje os acertos são late/night (80% vs 52%). O padrão horário inverteu-se: ruído. Red/fading sem lift (72% vs 67%). Sem sinal estável; sem ação.

### poorjev (SOL e memes; fonte dos H1, H3, H4 e híbridos regime)

- **Continua só-compra:** SOL 5648 buy/0/0; memes 1432 buy/0/0. Conf 0.52–0.54 em SOL (bloqueado pela margem 0.2, 1 trade), 0.90–0.97 em memes (satura a 99% em horas: `*_poorjev_*` memes −33.8 US$ de habilidade com 140/0 trades).
- **Primeiro padrão consistente em dois dias e duas classes de ativos.** Ontem (memes): acertos em `red violent dumping` (dumping 63% vs 41%), erros em `jumpy/whipping/green`. Hoje (memes): erros **jumpy** 95% vs 71% (+0.25), **pumping** 66% vs 43% (+0.23), tight +0.18; acertos **calm** 28% vs 2%, **wide**, **dumping** 26% vs 11%. Hoje (SOL): erros **green** 26% vs 6% (+0.20), **lifting** 18% vs 3%; acertos **flat** 82% vs 62%, **red** 19% vs 2%. Leitura: a 15 min, comprar o despejo funciona e comprar a fita que já sobe não. É reversão à média de curto prazo, e não depende do sinal do dia (ontem baixista, hoje altista). Duas palavras elegíveis pelo próprio relatório (lift ≥ 0.2 com suporte): jumpy, pumping.
- **Onde se monetiza.** Só com vendas. H1 memes (`h1_exits_*_poorjev_relaxed`) é a única família claramente positiva: +45.2 US$ de habilidade, FARTCOIN +50.4 (timing p 0.00), WIF +17.4 (p 0.05), GOAT +4.4 (p 0.04). Atenção à amostra: 487 compras mas só 19 vendas em 7 moedas e 3 dias — toda a habilidade vem de ~19 saídas por trailing/TP. É beta com saídas bem colocadas, ainda não é prova de seleção.
- **Decisão (ação B):** antes de gastar critérios no poorjev é preciso saber se o texto o move de todo. Ver secção 3.

### Laya (SOL e memes)

- **SOL — o fork de ontem pôs a Laya a negociar, mas só compra.** `laya_relaxed__fork1`: 50 compras, 0 vendas, 99% exposto em SOL, habilidade −5.1 US$ (−3.3 US$ são taxas de 50 compras). A Laya em SOL responde buy em 97% das chamadas (5495 buy / 130 sell / 30 hold): com portão na própria escala, vira um poorjev lento. Chamadas confiantes: hit 34%, 71 erros em 24 episódios.
- **Padrão repetido nos dois dias:** erros em compras **lifting tight green** (lift +0.22, +0.22, +0.15; ontem também "lifting tight"); acertos em **fading wide early** (fading 60% vs 30%). Mesmo mecanismo do poorjev: comprar o recuo acerta, comprar a subida falha. O relatório marca tight e lifting como elegíveis para frases.
- **Memes.** 162 confiantes, 45 erros em 34 episódios vs 53 acertos, hit 33%; erros são vendas em `fading calm red` (red +0.10), sem lift forte. `FARTCOIN_laya_relaxed__fork1` (conf ≥ 0.07): **0 trades em 23 h**. Motivo lido em `logs/lab_decisions.jsonl`: todas as 13 decisões de hoje com `low_confidence` (conf 0.030–0.041). O P90 de 0.066 que usei era o das 7 moedas juntas; em FARTCOIN a Laya raramente passa 0.05. Portão mal calibrado, não é veto de skip.
- **Decisão: nenhuma esta noite.** As duas linhagens Laya que quero tocar (`laya_relaxed`, `FARTCOIN_laya_relaxed`) estão bloqueadas até 10-05 01:40/01:41. Não uso outra moeda só para fugir ao bloqueio (seria a mesma hipótese com outro pai). Fica para amanhã: (i) Laya SOL com saídas ou com critério contra "lifting tight"; (ii) Laya FARTCOIN com conf ≈ 0.045.

### Regras, H2 e bot real (sem ação)

- `*_rule_donch_regime_full` continuam as piores (WIF −117.6, BONK −112.5, FARTCOIN −92.1 US$) com 1/1 trades: um rompimento comprado no topo. Não forkáveis. `*_rule_regime_full` perderam −30 US$ cada hoje com 1 compra no fecho de barra. Ficam só rotuladas pelo tuner.
- H2: BONK +7.7 (p 0.17, 30/12 trades) é o único positivo; FARTCOIN e WIF já têm forks do nightly. Nada a acrescentar.
- Bot real (paper): −0.02 US$ contra segurar, hit 80/135 (59%), auditoria do dia 347 erros vs 440 acertos sem palavra com lift. Sem evidência multi-dia de nada: 0/1.

## 2. Forks anteriores (idade ~1 dia; margens desde a criação)

| Fork | Quem | Mudança | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---|---|
| relaxed__fork1 | nightly | exits SOL iguais ao pai + teto 50% | +0.00 | −0.0 | 0/0 | sem dados (0 trades; o pai `relaxed` também não negociou hoje: conf do von 0.345 < 0.35) |
| poorjev_relaxed__fork1 | nightly | exits SOL + margem 0 | +0.88 | −1.5 | 19/0 | sem dados sobre saídas: 19 compras, 0 vendas (SOL moveu 1.8%, TP 2.5%/SL 1.5% nunca disparou). A margem de PnL é beta (o fork expôs-se, o pai não). |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | −1.00 | −9.6 | 55/18 | **refutada provisoriamente** (1 dia, 55 trades ≥ 20): saídas apertadas cortam cedo e geram 52 recompras; custo vs mark 6.6 US$ num dia. Continua a rodar; se ficar atrás 3 dias seguidos, rotular "atrás da original". |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | +0.05 | +0.5 | 7/8 | sem dados (quase igual ao pai) |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | −0.00 | −0.0 | 4/4 | sem dados (igual ao pai) |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip reescritos) | −0.56 | +0.9 | 1/0 | **tendência a refutar pelo critério "< 5 trades"**, e com uma lição inesperada (abaixo) |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | +0.06 | −3.2 | 50/0 | **método confirmado** (a Laya negoceia e é mensurável); **habilidade a refutar** como eu esperava: 50 compras, 0 vendas, −5.1 US$ em 1 dia. Precisa dos 3–7 dias, mas a direção é clara. |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | +0.00 | +0.0 | 0/0 | **sem dados por portão mal calibrado** (conf da Laya em FARTCOIN ≤ 0.041 em todas as decisões de hoje) |

### A lição do fork de critérios do von (`relaxed_expcap50__fork1`)

- Com o texto novo (buy com preferência por gray lifting e cautela com green/pumping; hold com "hold when the tape is green and lifting"; skip com thin/bot_war), o von **passou a responder sell em 82% das chamadas** (1019 buy / 4508 sell / 0 hold) e a confiança caiu para p50 0.186, máx 0.383 (texto base: p50 0.323, máx 0.402). Resultado: 1 trade em 23 h (uma venda), e as 681 chamadas confiantes do fork foram em 72% vendas em `flat calm gray tight held` que falharam (hit 28%) num dia em que SOL subiu.
- Interpretação: o von não tem saída "hold" útil (0 hold em todas as famílias). Quando o texto do hold ganha conteúdo, o von despeja esse conteúdo em **sell**. E quanto mais comprido o texto, menor a confiança (o v2 já mostrava isto: p50 0.251). Ou seja: no von, editar critérios muda a distribuição de ações e de confiança muito mais do que muda a seleção de estados. Qualquer fork de critérios futuro tem de controlar isto: uma cláusula de cada vez, só em buy ou só em sell, nunca no hold.
- A habilidade +0.9 US$ (timing p 0.04) com 1 trade é ruído e não conta.

## 3. Decisões desta noite (2 de 6)

### A. Critérios von SOL com uma só cláusula — `h1_exits_von_relaxed__fork1` (criado)

- Comando: `night_cli.py criteria-fork --parent h1_exits_von_relaxed --criteria-file run/claude_night/2026-10-04/von_sol_one_clause_green.json --reason '…'` (dry-run OK antes).
- Texto: igual ao baseline em tudo, exceto buy «the move is strong and depth is not thin; **do not buy when the tape is already green**». Hold «anything else», sell e skip intactos.
- Porquê este pai: von relaxed com saídas (99 trades, 4 RT), linhagem livre; `relaxed` e `relaxed_expcap50` bloqueadas até 10-05, `v2` não negoceia. A comparação fork−pai isola o efeito da cláusula.
- Hipótese (método): uma única cláusula só no buy preserva a distribuição do von (p50 > 0.30, maioria compras) e, se "green" tiver algum valor, corta compras tardias. É também o teste de controlo para a lição acima: se mesmo esta edição mínima virar o von para sell, então **qualquer** edição perturba o von e os forks de critérios no von têm de ser repensados (p. ex., só via portão).
- Confirma se (3–7 dias): ≥ 15 trades, compras > 50% das ordens, conf p50 do fork > 0.30, habilidade fork − pai > 0 US$.
- Refuta se: conf p50 < 0.25 ou vendas > 70% das chamadas (perturbação pelo texto); ou habilidade fork − pai ≤ 0 com ≥ 15 trades (a cláusula green não ajuda, coerente com o lift de hoje ≈ 0).
- Resultado: `created`, sha ca6fdf13…, `data/lab/criteria/h1_exits_von_relaxed__fork1.json`. Caps: 1/6.

### B. Critérios poorjev memes "não perseguir" — `h1_exits_WIF_poorjev_relaxed__fork1` (criado)

- Comando: `night_cli.py criteria-fork --parent h1_exits_WIF_poorjev_relaxed --criteria-file run/claude_night/2026-10-04/poorjev_wif_no_chase.json --reason '…'` (dry-run OK antes).
- Texto: instr. «…; do not chase a tape that is already pumping»; buy «…; prefer a red or dumping tape on a deep calm book; do not buy when the tape is pumping or jumpy with a tight spread»; hold «anything else; hold when the tape is pumping and jumpy»; sell e skip intactos.
- Porquê este pai: segundo melhor do lab (+17.4 US$, timing p 0.05, 100/4 trades), saídas ligadas (sem saídas o poorjev nunca vende e o texto não teria como se monetizar), linhagem livre (FARTCOIN H1 bloqueada até 10-05 00:10). WIF tem o maior volume de trades da família H1, logo dá resposta mais depressa.
- Hipótese: o padrão de dois dias (erros do poorjev = comprar pumping/jumpy/green; acertos = comprar red/dumping/flat) pode ser codificado em texto — **se** o poorjev reagir ao texto, o que é desconhecido (responde buy a tudo com conf 0.90–0.97). Este fork mede primeiro a sensibilidade ao texto e só depois a habilidade.
- Confirma se (3–7 dias): compras do fork < 70% das do pai (o texto tem efeito) e habilidade fork − pai > 0 US$ com ≥ 20 trades.
- Refuta se: trades do fork = pai ± 10% com as mesmas ações (o poorjev ignora o texto → não vale a pena mais forks de critérios no poorjev; a alavanca fica só em exits/portões); ou habilidade fork − pai ≤ 0 com ≥ 20 trades.
- Resultado: `created`, sha e2715f69…, `data/lab/criteria/h1_exits_WIF_poorjev_relaxed__fork1.json`. Caps: 2/6, total 10/80.

### Ideias consideradas e não executadas

- **Laya SOL com saídas / critério anti-"lifting tight"** e **Laya FARTCOIN conf ≈ 0.045**: linhagens bloqueadas até 10-05 01:40. Amanhã, com mais um dia de dados.
- **Critérios von memes**: o padrão horário inverteu-se entre ontem e hoje; red/fading sem lift; portfólios com 2% de exposição. Sem base.
- **H1 FARTCOIN saídas mais largas** (simétrico ao fork apertado do nightly): a habilidade do pai vem de ~3 vendas; não há como calibrar níveis com isso. Linhagem bloqueada, de resto.
- **H3 limite** (`exec.offset_bps`): −38.9 US$ acumulado em 2 linhagens; ainda só 1 RT fechado. Mais um dia.
- **Bot real**: sem evidência multi-dia; 0/1.
- **Zero ações** seria defensável para o von; optei por um fork de controlo porque a lição do hold→sell afeta todo o método GEPA no lab e precisa de ser testada, não só anotada.

## 4. O que verificar amanhã (2026-10-05)

1. `h1_exits_von_relaxed__fork1`: distribuição buy/sell e conf p50 do grupo "von · critérios h1_exits_von_relaxed__fork1" no audit por família. Se p50 < 0.25 ou sell > 70%: qualquer edição perturba o von — registar e parar de propor criteria-forks ao von até haver um portão por fork na escala nova.
2. `h1_exits_WIF_poorjev_relaxed__fork1`: n.º de compras vs pai e se apareceu algum `hold`/`sell` nas chamadas do poorjev. Se as ações forem idênticas ao pai, declarar "poorjev ignora o texto" e nunca mais gastar forks de critérios nele.
3. `laya_relaxed__fork1`: ainda 0 vendas? Se sim e a linhagem desbloquear (01:40), fork com `exits.enabled` não é possível por diff (só exits.* níveis); alternativa é criteria-fork que peça venda em "lifting tight green" — uma cláusula só no sell, aprendendo com a lição do von.
4. `FARTCOIN_laya_relaxed__fork1`: se continuar a 0 trades e a linhagem desbloquear, novo fork com conf ≈ 0.045 (P90 da Laya em FARTCOIN, não das 7 moedas). Confirmar primeiro o P90 por moeda nos logs.
5. `h1_exits_FARTCOIN_poorjev_relaxed__fork1`: terceiro dia atrás do pai? Se sim, rotular refutada (sem apagar).
6. Repetir o lift do poorjev (memes e SOL) com 3 dias: se jumpy/pumping/green continuarem marcadores de erro, o padrão "comprar o recuo" fica robusto a três dias com sinais de mercado diferentes.
7. Linhagens que desbloqueiam a 10-05 00:10: relaxed, poorjev_relaxed, h1 FARTCOIN, h2 FARTCOIN/WIF; a 01:40: laya_relaxed, relaxed_expcap50, FARTCOIN_laya_relaxed.

## 5. Recusas e limites

- Recusas exit 2: três, todas por `--reason` acima de 800 caracteres (811, 908 e 802); encurtei o texto sem perder hipótese/confirma/refuta. Nenhuma recusa por limite da noite, linhagem ou critérios inválidos.
- Limites: 2/6 forks esta noite; total 10/80; bot real 0/1. Linhagens bloqueadas respeitadas (não usei pais alternativos para contornar `laya_relaxed`, `FARTCOIN_laya_relaxed`, `relaxed`, `relaxed_expcap50` ou H1 FARTCOIN; os pais escolhidos, `h1_exits_von_relaxed` e `h1_exits_WIF_poorjev_relaxed`, foram-no por mérito: têm trades, saídas ligadas e isolam a variável).
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-04/`. Nenhuma credencial lida.
