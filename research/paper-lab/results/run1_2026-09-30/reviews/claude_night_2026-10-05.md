# Diário da revisão noturna autónoma — 2026-10-05 (dia 6/30, paper only)

Terceira noite do investigador Claude. Fontes: `night_cli context` e `status`, diários de 10-03 e 10-04, `reviews/2026-10-05.md` (tuner das 00:30), `data/lab/status.json`, `data/lab/portfolios/*.json`, `logs/lab_decisions.jsonl` (só leitura; o ficheiro só guarda as decisões desde as 00:00 de hoje).

Mercado nas 24 h: lateral. SOL −0.2% (faixa 1.8%), memes mistas (BONK +3.0%, FARTCOIN +3.9%, MEW −2.1%, GOAT −3.0%). Depois de um dia baixista (10-03) e um altista (10-04), este é o terceiro regime distinto: o que se repetiu nos três dias já não é viés do sinal do dia.

## 1. Reflexão por família (GEPA em linguagem simples)

Método: só a diferença (% nos erros − % nos acertos) distingue chamadas; deep/quiet/calm/soft estão em ~100% de tudo. Separo o que se repetiu nos três dias do que se inverteu.

### von (SOL e memes)

- **Porque errou.** SOL: 608 chamadas confiantes (corte 0.360), 311 erros em 37 episódios, 117 acertos, **hit 20%** — o pior dos três dias (28% → 23% → 20%). Quase só compras em `flat calm green/red` com a fita `tight`. Marcadores de erro de hoje: night +0.22, green +0.12, early +0.12. Acertos: late, gray.
- **Nada se repetiu três dias seguidos.** green: +0.21 (10-03), +0.03 (10-04), +0.12 (10-05) — oscila. Hora do dia: night nos acertos ontem (89% vs 71%), night nos erros hoje (42% vs 21%). Inversão total em 24 h = ruído de episódio (a hora é a variável mais autocorrelacionada do estado). Conclusão: o von em SOL a 15 s não tem um marcador de erro estável; tem um hit baixo em tudo.
- **O controlo de ontem (`h1_exits_von_relaxed__fork1`) deu resultado claro — ver secção 2.** Resumo: uma cláusula só no buy preserva a distribuição (93% compras, igual ao texto base) e baixa a confiança só 0.024 (p50 0.292 vs 0.316). Mas o von **continua a comprar com a fita green** (green 42% nos erros do fork vs 23% nos acertos; estado de erro mais frequente `flat calm night green tight` ×34, igual ao base). O texto não é aplicado semanticamente; funciona como regulador de confiança. Junto com a lição de ontem (conteúdo no hold → sell), fecha o quadro: **no von, critérios de texto mexem na confiança e na mistura buy/sell, não na seleção de estados.** A alavanca que resta é o portão/exits.
- **Memes.** 153 confiantes, 51 erros em 39 episódios vs 45 acertos, hit 30%. Erros são vendas em `fading calm red wide` (red +0.09, sem lift forte); acertos early +0.22 (ontem era late/night nos acertos). Terceiro dia sem marcador estável. Portfólios a 2% de exposição. Nada a fazer.
- **Números.** `relaxed` −8.4 US$ de habilidade (99% exposto, beta). `relaxed__fork1` (teto 50% + exits) +7.7 US$ com 6 trades e timing p 0.03: a única coisa positiva no von em SOL, mas 6 trades. `v2` +1.7 (1/1 trades). H3 −42.4, H4 −26.6, híbridos −27.5: direção negativa unânime pelo terceiro dia, ainda sem 5 RT.
- **Decisão: zero ações no von.** Dois forks de critérios já responderam à pergunta de método; não há marcador para codificar; o único positivo (relaxed__fork1) já corre.

### poorjev (SOL e memes; H1, H3, H4, híbridos regime)

- **Continua só-compra:** SOL 5649/0/0, memes 1432/0/0. Em memes satura a 99% em horas: `*_poorjev_*` memes −34.8 US$ de habilidade, 140/0 trades, puro beta.
- **O padrão de dois dias passou a três, em três regimes de mercado.** Memes hoje: erros **green** 83% vs 57% (+0.26), **pumping** 48% vs 24% (+0.24), **tight** 46% vs 22% (+0.24), **jumpy** 72% vs 51% (+0.21); acertos **wide** 54% vs 78% (−0.24), **calm** (−0.20), **red** 7% vs 25% (−0.19). Quatro palavras elegíveis pelo próprio relatório (lift ≥ 0.2 com suporte). 10-03: acertos dumping/violent; 10-04: erros jumpy/pumping; 10-05: erros green/pumping/tight/jumpy. SOL hoje: erros lifting +0.18, tight +0.16, green +0.14; acertos red, wide, fading. **Mesmo mecanismo, duas classes de ativos, três dias com sinais de mercado diferentes: comprar a fita que já sobe falha a 15 min; comprar o recuo acerta.** É o único achado robusto do laboratório até agora.
- **Onde se monetiza.** H1 memes é a única família claramente positiva: +67.9 US$ de habilidade, FARTCOIN +55.5 (timing p 0.01), BONK +22.1 (p 0.06), WIF +17.2 (p 0.03), GOAT +7.7 (p 0.01). Mas: 579 compras e 25 vendas em 7 moedas e 4 dias — toda a habilidade vem de ~25 saídas por trailing/TP; o resto é beta a 95%.
- **Como o poorjev reage ao texto (fork WIF, ver secção 2):** nas *mesmas* decisões, o pai responde buy com conf 0.875–0.918 e o fork buy com conf 0.60–0.83. A ação não muda (203/203 buy); a confiança cai ~0.2 e fica mais dispersa. Se a dispersão for dependente do estado (menor em pumping/jumpy), o texto pode virar filtro através de um portão mais alto. Ainda não há dados de trades (ambos 100% investidos).
- **Decisão: codificar "não perseguir" pelo único parâmetro disponível**, a reentrada após saída (`exits.reentry_cooldown_min` 30 → 120), em duas moedas H1 (BONK e MEW) para separar efeito de moeda de efeito de mecanismo. Ver secção 3.

### Laya (SOL e memes)

- **SOL — `laya_relaxed__fork1` responde à hipótese de ontem: a Laya vende em SOL** (57 compras / 15 vendas em 10-04; 21 round trips fechados em 2 dias — a linhagem que acumula amostra mais depressa no lab). Habilidade −18.4 US$ vs pai, −10.1 US$ só em 10-04. **Mas a decomposição muda a leitura:** em 10-04, taxas 6.86 + custo vs mark 6.37 = 13.2 US$ com excesso ajustado −10.07 → a seleção bruta foi ≈ +3 US$. Em 2 dias: 125 trades × ~0.18 US$ ≈ 22 US$ de custo contra −18 de habilidade → bruto ≈ +4. **A perda é toda custo; a seleção é ≈ 0 ou ligeiramente positiva.** Hoje (00:00–01:30) o fork fez 11 trades em 356 ciclos, com 31 bloqueios por cooldown: está ao ritmo do teto 8/h.
- **Padrão repetido três dias:** erros em compras **lifting tight** (hoje lifting +0.25, 40% vs 15%; tight +0.16; 10-04 lifting/tight/green; 10-03 lifting tight). Acertos: wide, fading. Mesmo mecanismo do poorjev. hit 26% nas confiantes.
- **FARTCOIN — `FARTCOIN_laya_relaxed__fork1` continua a 0 trades, e agora sei porquê.** Nas 13 decisões de hoje: confiança 0.024–0.077 (mais alta do que ontem, 7/13 ≥ 0.05, 3/13 ≥ 0.07); mas em 10 de 13 ciclos o motivo é `skip_noul_high`, **incluindo os 3 ciclos em que a confiança passou o portão**. O veto de skip da Laya também está numa escala própria; ontem só calibrei a confiança. A Laya respondeu sell em 9 das 13 chamadas (único modelo pequeno que vende em memes).
- **Memes (chamadas).** 148 confiantes, 47 erros em 37 episódios vs 42 acertos, hit 29%. Erros wide +0.15, violent +0.10, loud +0.10; acertos calm −0.19, tight −0.15. Sem palavra elegível. Sinal fraco.
- **Decisões:** (a) fork de `laya_relaxed__fork1` com cooldown 3600 s (testa custo vs seleção); (b) fork de `FARTCOIN_laya_relaxed` que relaxa o veto de skip mantendo o portão de confiança do fork1. Ambas as linhagens estavam bloqueadas até 01:40/01:41 — ver secção 3 e 5.

### Regras, H2 e bot real (sem ação)

- `*_rule_donch_regime_full` continuam as piores (WIF −135.7, MEW −130.1, BONK −109.4 US$) com 1–3 trades; MEW e PNUT perderam mais −40 e −32 hoje. Não forkáveis pelo night_cli (grupo rule só via tuner). Ficam rotuladas.
- H2: FARTCOIN e WIF com forks do nightly ≈ iguais ao pai (+1.2, +0.6). H2 BONK −13.7 hoje. Nada a acrescentar.
- Bot real (paper): −0.12 US$ contra segurar, hit 80/135; auditoria do dia 366 erros vs 453 acertos, sem palavra com lift. Terceiro dia sem evidência multi-dia de uma frase. 0/1.

## 2. Forks anteriores (margens desde a criação)

| Fork | Quem | Mudança | Idade | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---:|---|---|
| relaxed__fork1 | nightly | exits + teto 50% | 2.1 d | +0.56 | +7.8 | 6/0 | em observação; o único positivo no von (timing p 0.03) mas 6 trades |
| poorjev_relaxed__fork1 | nightly | exits + margem 0 | 2.1 d | +0.43 | −5.2 | 40/0 | sem dados sobre saídas (1 RT); a margem de PnL é beta |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | 2.1 d | −2.64 | −21.8 | 162/42 | **refutada** (3.º dia atrás: −6.4 → −9.6 → −21.8; 10-04 sozinho +0.2 vs +6.3 do pai). Saídas apertadas em memes cortam cedo e geram recompras (95 trades/dia, 16.6 US$ de custos). Não apago; rótulo do tuner "atrás da original" |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | 2.1 d | +0.12 | +1.2 | 17/19 | sem dados (≈ pai) |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | 2.1 d | +0.07 | +0.6 | 11/12 | sem dados (≈ pai) |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip) | 2.0 d | −0.49 | +1.2 | 1/0 | **a caminho de refutar** pelo critério "< 5 trades em 7 dias": 0 trades e 0% exposição em 10-04; 82% das chamadas são sell com conf p50 0.186. O texto estrangula o von |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | 2.0 d | −1.45 | −18.4 | 125/0 | **método confirmado** (a Laya negoceia e vende: 21 RT); **habilidade líquida refutada** com ≥ 20 trades, mas a decomposição mostra que é custo (≈ 22 US$) e não seleção (≈ +4 bruto). Gera a hipótese (a) desta noite |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | 2.0 d | +0.00 | +0.0 | 0/0 | **sem dados por portão mal calibrado**: o bloqueio é o veto de skip, não a confiança. Gera a hipótese (b) |
| h1_exits_von_relaxed__fork1 | claude-night | critérios (1 cláusula no buy) | 1.0 d | −0.36 | −5.3 | 12/21 | **controlo de método concluído**: distribuição preservada (5160 buy / 395 sell, 93%), conf p50 0.292 (base 0.316, −0.024). Nem confirma (p50 < 0.30) nem refuta (p50 > 0.25, sells 7%). O que ensina: o von não aplica a cláusula (continua a comprar green); baixou a frequência de trades para metade via confiança, o que em dia de alta custou beta (exposição 41% vs 96%). Habilidade 10-04: −1.3 vs +0.8 do pai. Continua a correr para o teste de habilidade com ≥ 15 trades |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios "não perseguir" | 1.0 d | +0.04 | −5.2 | 0/0 | **sem dados de trades**: pai e fork clonaram o mesmo livro 100% investido (`insufficient_usdt` em todos os ciclos) e a saída não disparou (WIF +0.4%). **Mas já há dados sobre o modelo:** o poorjev *reage* ao texto — mesma decisão, conf 0.91 no pai vs 0.60–0.83 no fork, ação igual (buy). Hit das confiantes do fork 41% (22 chamadas) vs 35% da família: sentido certo, amostra ínfima. A primeira divergência de trades só aparece depois da primeira venda |

### O que os forks ensinaram esta noite

1. **Os três modelos pequenos reagem ao texto do mesmo modo: pela confiança, não pela ação nem pela seleção.** von: 1 cláusula → −0.024 de conf, ação igual, continua a comprar o estado proibido; hold com conteúdo → sell. poorjev: 3 cláusulas → −0.2 de conf, ação igual. Isto reorganiza o método GEPA no lab: um fork de critérios só vale se vier acoplado a um portão de confiança na escala nova (o que exige dois passos em noites diferentes, por causa do limite por linhagem) — ou se o pai tiver saídas mecânicas que monetizem a diferença de confiança.
2. **Custos são a primeira coisa a separar antes de julgar um modelo.** A Laya em SOL parecia refutada (−18 US$); bruto de custos é ≈ 0. O fork FARTCOIN H1 do nightly perdeu 16.6 US$ só em custos num dia.
3. **Clonar um livro 100% investido adia o teste.** O fork WIF só diverge depois de uma saída. Em forks futuros de pais saturados, a leitura começa na primeira venda — contar os dias a partir daí.

## 3. Decisões desta noite

### A. H1 BONK — reentrada 120 min — `h1_exits_BONK_poorjev_relaxed__fork1` (criado)

- Comando: `night_cli.py fork --parent h1_exits_BONK_poorjev_relaxed --diff '{"exits": {"reentry_cooldown_min": 120}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.35, margem ≥ 0.2, skip < 0.5, cooldown 120 s, ≤ 8/h, compra 25% USDT, TP 6% / SL 4% / trailing 3% (arma +3%), **reentrada 120 min** (pai: 30).
- Porquê este pai: melhor habilidade das 24 h (+18.8, p 0.03), 105/6 trades (mais vendas da família → resposta mais rápida), linhagem livre. Os timestamps do pai mostram o mecanismo: cada venda é seguida, 31 min depois, de uma sequência de recompras de 7 em 7 min até saturar.
- Hipótese: o padrão de 3 dias (comprar pumping/jumpy/green/tight falha; comprar red/dumping/calm/wide acerta) não tem parâmetro que o codifique directamente; o mais próximo é a reentrada após saída, porque 30 min depois de um trailing a fita costuma estar ainda agitada. A habilidade de H1 vem das saídas (~6 por moeda), não do tempo exposto, logo esperar 2 h não deve custar habilidade.
- Confirma se (3–7 dias): habilidade fork − pai > 0 US$ com ≥ 3 vendas no fork.
- Refuta se: habilidade fork − pai ≤ 0 com ≥ 3 vendas; ou PnL fork − pai < −1 pp com habilidade ≈ 0 (perda de beta sem ganho de seleção).
- Resultado: `created`. Caps 1/6, total 11/80.

### B. H1 MEW — reentrada 120 min — `h1_exits_MEW_poorjev_relaxed__fork1` (criado)

- Comando: `night_cli.py fork --parent h1_exits_MEW_poorjev_relaxed --diff '{"exits": {"reentry_cooldown_min": 120}}' --reason '…'` (dry-run OK antes).
- Efetivo: igual a A, em MEW.
- Porquê: réplica da mesma ideia numa segunda moeda (91 trades, 4 RT, +7.3 US$ nas 24 h, p 0.05), para separar efeito de moeda de efeito de mecanismo. Em memes o ruído por moeda é enorme (o +18.8 de BONK hoje é uma sequência de saídas).
- Confirma se: habilidade fork − pai > 0 com ≥ 3 vendas, **no mesmo sentido que BONK**. Refuta se: ≤ 0 com ≥ 3 vendas, ou sinais opostos entre BONK e MEW (efeito de moeda).
- Resultado: `created`. Caps 2/6, total 12/80.

### C. Laya SOL — cooldown 3600 s sobre `laya_relaxed__fork1` (ver resultado abaixo)

- Comando: `night_cli.py fork --parent laya_relaxed__fork1 --diff '{"gates": {"cooldown_seconds": 3600}}' --reason '…'`.
- Hipótese: a perda do fork1 é custo (125 trades ≈ 22 US$) e não seleção (bruto ≈ +4). Uma pausa de 1 h entre trades corta a frequência para ≤ 24/dia (hoje está ao ritmo de 8/h) e deixa o sinal, se existir, aparecer líquido. Uma ideia: frequência; o resto (conf 0.04, margem 0) herda do fork1.
- Confirma se: habilidade fork − `laya_relaxed` > 0 US$ com ≥ 20 trades em 3–7 dias (e acima da margem do fork1 no mesmo período). Refuta se: ≤ 0 com ≥ 20 trades → a Laya em SOL não tem seleção positiva mesmo sem churn; a linha Laya SOL fecha.
- Resultado: ver secção 5 (recusado por linhagem às 01:3x; nova tentativa no fim da noite, registada abaixo).

### D. Laya FARTCOIN — veto de skip — sobre `FARTCOIN_laya_relaxed` (ver resultado abaixo)

- Comando: `night_cli.py fork --parent FARTCOIN_laya_relaxed --diff '{"gates": {"min_confidence": 0.07, "min_prob_margin": 0.0, "max_skip_noul": 0.95}}' --reason '…'`.
- Hipótese: o fork1 está a 0 trades porque o veto de skip (`skip_noul_high`) bloqueia 10 de 13 ciclos, incluindo os 3 em que a confiança passou. Relaxar só o veto, mantendo conf 0.07 e margem 0 do fork1 (a diferença fork−fork1 isola o veto), torna a Laya FARTCOIN mensurável — é o único modelo pequeno que vende em memes.
- Confirma se: ≥ 20 trades com vendas > 0 em 3–7 dias e habilidade fork − pai > 0 US$. Refuta se: ≥ 20 trades e habilidade ≤ 0 (Laya sem habilidade em memes), ou 0 trades em 3 dias (há outro bloqueio).
- Resultado: ver secção 5.

### Ideias consideradas e não executadas

- **Critérios no von** (qualquer pai): dois forks já mostraram que o texto regula confiança, não seleção; não há marcador estável em 3 dias. Zero.
- **Critérios no poorjev noutra moeda H1**: o fork WIF ainda não divergiu (livro saturado); replicar antes de ver a primeira venda seria gastar uma chamada por ciclo sem informação nova.
- **Portão de confiança mais alto sobre o fork WIF** (transformar a queda de conf em filtro): linhagem bloqueada até 10-06 01:35; e primeiro preciso de ver se a conf do fork varia com o estado. Candidato para amanhã.
- **Critério de venda na Laya SOL contra "lifting tight"**: a lição do texto (regula confiança) é ainda mais perigosa na Laya, cuja confiança está a 0.028 contra um portão de 0.04 — qualquer deslocamento liga ou desliga tudo. Primeiro o custo (fork C).
- **Saídas mais largas em H1 FARTCOIN** (simétrico ao fork refutado): a habilidade do pai vem de 4 vendas; não há como calibrar níveis com isso.
- **H3 limite / H4 horas / híbridos**: terceiro dia negativo, mas < 5 RT; o tuner trata. Nada por mim.
- **Bot real**: 0/1, sem frase com evidência multi-dia.

## 4. O que verificar amanhã (2026-10-06)

1. **Forks A e B (reentrada 120 min):** houve alguma venda no pai ou no fork desde a criação? Só a partir daí a comparação conta. Verificar se o fork recomprou ≈ 2 h depois e o pai ≈ 30 min, e o que a fita estava a dizer em cada recompra (adjetivos nas decisões).
2. **Fork WIF poorjev (critérios):** primeira venda já? Se sim, o fork recompra com menos frequência do que o pai (conf abaixo de 0.35 em algum ciclo)? Comparar conf do fork por estado (pumping/jumpy vs red/dumping) nas decisões do dia: se for menor em pumping/jumpy, o texto é um filtro de estado disfarçado e um fork de portão (conf ≥ 0.7) na linhagem (desbloqueia 10-06 01:35) é o passo seguinte.
3. **Fork von (1 cláusula):** ≥ 15 trades? habilidade fork − pai? Se continuar atrás com ≥ 15 trades, refutar e não voltar a propor criteria-forks no von.
4. **Forks C e D (Laya):** se tiverem sido criados, confirmar que D negoceia (vendas > 0) e que C fez ≤ 24 trades/dia. Se não tiverem sido criados por bloqueio, são as duas primeiras ações de amanhã (comandos acima, linhagens livres a partir de 10-05 01:40/01:41).
5. **`relaxed_expcap50__fork1`:** 7.º dia a 10-10; se < 5 trades, refutada. `h1_exits_FARTCOIN_poorjev_relaxed__fork1`: já rotulada refutada por mim; ver se o tuner mantém "atrás da original".
6. **Lift do poorjev com 4 dias:** se green/pumping/tight/jumpy continuarem marcadores de erro, o padrão está estabelecido e vale a pena propor ao bot real (que usa o von, cuidado: o padrão é do poorjev; para o bot real seria preciso o mesmo lift na auditoria do próprio bot, que hoje não mostra nenhuma palavra).
7. Linhagens que desbloqueiam: BONK/MEW H1 a 10-07 ~01:4x; h1 WIF e h1 von a 10-06 01:35.

## 5. Recusas e limites

- **Recusas exit 2 (4):** `fork --parent laya_relaxed__fork1` e `fork --parent FARTCOIN_laya_relaxed` recusados duas vezes cada com `cap_1_fork_per_2.0d` (linhagens bloqueadas até 10-05 01:40/01:41; as tentativas foram antes dessa hora). Aceitei a recusa; não usei outro pai para contornar. Resultado da última tentativa (fim da noite): ver adenda abaixo.
- Limites: 2/6 forks criados esta noite (+ até 2 se a adenda confirmar); total 12/80; bot real 0/1. Nenhum fork de critérios esta noite (zero chamadas extra ao modelo).
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-05/`. Nenhuma credencial lida.

### Adenda — última tentativa dos forks C e D

- Terceira tentativa (dry-run) de C e D depois de escrever o diário: **recusadas de novo** com `cap_1_fork_per_2.0d (último: laya_relaxed__fork1)` e `cap_1_fork_per_2.0d (último: FARTCOIN_laya_relaxed__fork1)`. Total de recusas exit 2 esta noite: 6 (3 por linhagem para cada uma). O relógio do limite de linhagem não libertou dentro da janela desta sessão. Não contornei (não forquei outra moeda Laya nem outro pai SOL).
- **C e D ficam como as duas primeiras ações de amanhã**, com os comandos e as hipóteses exatamente como estão na secção 3; se a linhagem `laya_relaxed` ainda recusar o pai `laya_relaxed__fork1` (fork de fork), a alternativa equivalente é `--parent laya_relaxed --diff '{"gates": {"min_confidence": 0.04, "min_prob_margin": 0.0, "cooldown_seconds": 3600}}'` (fork1 + uma ideia), registando que a comparação relevante é contra o fork1 e não contra o pai.
- Balanço final: 2/6 forks criados (A e B, ambos de parâmetros, zero chamadas extra ao modelo); total 12/80; bot real 0/1.
