# Diário da revisão noturna autónoma — 2026-10-06 (dia 7/30, paper only)

Quarta noite do investigador Claude. Fontes: `night_cli context` e `status` (01:30 BRT), diários de 10-05 (duas versões), `reviews/2026-10-06.md` (tuner das 00:30), `data/lab/portfolios/*.json` dos forks e pais, `logs/lab_decisions.jsonl` (só leitura; só guarda as decisões desde as 00:00 de hoje, ~1,5 h).

Mercado nas 24 h: SOL lateral (−0.2%, faixa 2.6%); memes em baixa (FARTCOIN −5.7%, BONK −4.5%, GOAT −2.7%, WIF −1.4%, PNUT −1.3%, POPCAT −0.5%, MEW +0.5%). É o quarto regime distinto em quatro noites (baixa, alta, lateral, memes em baixa com SOL parado). O que se repetiu nos quatro já não é viés de um dia.

## 1. Reflexão por família (GEPA em linguagem simples)

Método igual ao das noites anteriores: só a diferença (% nos erros − % nos acertos) distingue chamadas, porque deep/quiet/calm/soft estão em ~100% de tudo. Separo o que se repetiu dos quatro dias do que se inverteu. Nota nova desta noite: quando os três modelos veem a mesma fita de SOL no mesmo dia, um marcador que aparece nos três **não** é evidência independente — é o mesmo episódio visto por três cabeças.

### von (SOL e memes)

- **Porque errou.** SOL: 569 confiantes (corte P90 0.366), 287 erros em 41 episódios, 190 acertos, hit 33%. Erros: `lifting calm night green tight` ×43, `lifting calm mid gray tight` ×43, `flat calm night green wide` ×36. Marcadores de erro: gray +0.16, lifting +0.15, early +0.12, tight +0.10. Acertos: late −0.27, green −0.18, night −0.16.
- **Quarto dia sem marcador estável.** green: +0.21 (10-03), +0.03 (10-04), +0.12 (10-05), **−0.18 (10-06, agora nos acertos)**. night: nos acertos em 10-04, nos erros em 10-05, nos acertos em 10-06. A hora e a cor da fita invertem de dia para dia; são as variáveis mais autocorrelacionadas do estado e viram ruído de episódio. O que aparece hoje (lifting + tight nos erros, wide/fading nos acertos) é o mesmo em v2 (lifting +0.23, elegível), no fork com 1 cláusula (lifting +0.26, tight +0.21), na Laya SOL (lifting +0.09) e no poorjev memes (lifting +0.15, tight +0.22): num dia de SOL lateral com faixa de 2.6%, "lifting" reverte em 15 min. É um episódio de regime, não uma regra do modelo.
- **O fork com 1 cláusula (`h1_exits_von_relaxed__fork1`) atingiu o critério que eu próprio fixei ontem (≥ 15 trades) e está atrás: refutado.** 27 trades, habilidade −14.4 US$ vs pai; em 10-05 sozinho −13.7 vs −1.6 do pai, com exposição 52% vs 95% num dia em que SOL fez −0.2% (a diferença não é beta). A cláusula "do not buy when the tape is already green" mirava um marcador que hoje inverteu (green nos acertos), e a auditoria do fork mostra os mesmos erros do texto base (lifting/tight). Fecha a linha: **não volto a propor forks de critérios no von.** Dois forks de critérios (um que estrangulou, um que não selecionou) responderam à pergunta de método.
- **Memes.** 143 confiantes, 44 erros em 32 episódios, 54 acertos, hit 38%. Erros são vendas em `fading calm red wide`; gray +0.16, nada elegível. Portfólios a 2% de exposição. Nada a fazer.
- **Números.** `relaxed` −8.7 US$ (99% exposto, beta puro). **`relaxed__fork1` (exits + teto 50%) é a única linha positiva do von: +10.4 US$ de habilidade, 13/3 trades, timing p 0.02, à frente do pai em 100% dos dias** — 3 RT, ainda pequeno, mas consistente em quatro regimes. `v2` +1.3. H3 −44.0, H4 −27.7, híbridos SOL −29.0: quarto dia negativo, ainda < 5 RT.
- **Decisão: zero ações no von.** O positivo já corre e precisa de dias, não de forks.

### poorjev (SOL e memes; H1, H3, H4, híbridos regime)

- **Continua só-compra:** SOL 5595/0/0, memes 1424/0/0.
- **O padrão de três dias passou a quatro.** Memes hoje: erros **tight** 48% vs 26% (+0.22, elegível), gray +0.15, lifting +0.15, jumpy +0.13, pumping +0.10; acertos **wide** 52% vs 74% (−0.22), loud −0.15, red −0.13. Estado de erro mais frequente: `pumping jumpy mid green tight` ×15. Em quatro dias e quatro regimes: 10-03 acertos dumping/violent; 10-04 erros jumpy/pumping; 10-05 erros green/pumping/tight/jumpy; 10-06 erros tight/lifting/jumpy/pumping, acertos wide/red. **Comprar a fita que já sobe com spread apertado falha a 15 min; comprar o recuo com spread largo acerta.** SOL hoje: erros gray +0.18, early +0.12; acertos red −0.14, fading −0.11 (o lado dos acertos coincide, o dos erros é novo).
- **Mas a habilidade de H1 em memes é frágil num dia de baixa.** H1 memes caiu de +67.9 para +29.8 US$ acumulados em 24 h (BONK fork −26.2, WIF −16.8, PNUT −9.0, GOAT −5.4). O mecanismo: 95% exposto, stop-loss a 4% dispara perto do fundo, 30 min depois recompra. FARTCOIN H1 continua +67.1 (p 0.01), toda de ~6 vendas. **A habilidade de H1 é um punhado de saídas; um dia de −5% com SL a 4% devolve metade.**
- **Fork WIF (critérios "não perseguir"): a primeira venda chegou e respondeu à pergunta de ontem.** Hoje às ~01:0x pai e fork levaram stop-loss no mesmo ciclo (entrada 0.2548 → 0.2446, −4%) e recompraram nos mesmos três ciclos 30 min depois. Nas 13 decisões de hoje: fork conf 0.62–0.74, pai 0.88–0.93; ação igual (buy em 100%). **O texto desloca a confiança ~0.2 para baixo e não muda uma única decisão de trade com o portão a 0.35.** Mas a auditoria do fork (24 h) mostra que o deslocamento **não é uniforme por estado**: o decil superior do fork (conf ≥ 0.81) cai em `dumping calm late red wide` ×7 — exatamente os estados que o texto manda preferir — enquanto o decil superior do poorjev sem texto cai em `pumping jumpy green tight`. O texto reordena os estados por confiança. Isso só vira seleção com um portão na escala nova; é a ação E desta noite. Cautela registada: essas confiantes do fork em dumping acertaram só 29% hoje (11 erros/6 acertos, 11 episódios) num dia em que WIF caiu 1.4% — comprar o recuo num dia de baixa também falha.
- **Decisão:** fork de portão (conf ≥ 0.75) sobre o fork de critérios WIF (secção 3, E). Não replico reentrada a uma terceira moeda (BONK/MEW já correm e o primeiro episódio de BONK foi contra; ver secção 2).

### Laya (SOL e memes)

- **SOL — a decomposição repete-se pelo terceiro dia.** `laya_relaxed__fork1` em 10-05: 101 trades (84/17), 17 RT fechados (5 ganhos), taxas 9.13 + custo vs mark 9.05 = 18.2 US$; excesso ajustado −14.4 → **seleção bruta ≈ +3.8 US$**. 10-04 tinha dado bruto ≈ +3; acumulado 3 dias: −31 de habilidade com ≈ 40 de custos → bruto ≈ +9. A Laya em SOL não perde por escolher mal; perde por negociar 100 vezes por dia a 0.18 US$ cada. Hoje (00:00–01:30) o fork fez 3 trades em 349 ciclos com 9 bloqueios por cooldown (mais calmo do que ontem). Marcadores: lifting +0.09 (era +0.25 ontem; quarto dia nos erros mas a enfraquecer), flat +0.07; acertos fading −0.13. hit 28%.
- **FARTCOIN — o fork1 fez o primeiro par de trades** (compra 12:53, venda 13:13 de 10-05, −0.16 realizado + 0.25 de taxas) e voltou a ficar parado. Nas 13 decisões de hoje: `skip_noul_high` em 8, **5 delas com conf 0.081–0.101 acima do portão 0.07** (bloqueadas só pelo veto); `low_confidence` em 7 (compras a 0.024–0.054). A Laya respondeu sell em 7/13 sem posição (não faz nada). Ressalva nova: as compras da Laya saem com confiança mais baixa do que as vendas; com o veto relaxado, os trades dependem de compras chegarem a 0.07. A cláusula "refuta se < 5 trades em 3 dias" cobre isto.
- **Memes (chamadas).** 146 confiantes, 61 erros em 41 episódios, 40 acertos, hit 27%. Erros são vendas em `fading calm` (gray +0.13, jumpy +0.11); acertos red −0.20. Nada elegível. Continua a ser o único modelo pequeno que vende em memes (553/1419).
- **Decisões:** C (cooldown 3600 s sobre `laya_relaxed__fork1`) e D (veto de skip relaxado sobre `FARTCOIN_laya_relaxed`), as duas pendentes de ontem por bloqueio de linhagem; ambas criadas esta noite (secção 3).

### Regras, H2 e bot real (sem ação)

- Regras memes: −892 US$ acumulados, as `*_rule_donch_regime_full` continuam as piores (MEW −122.5, WIF −109.0, PNUT −74.8, BONK −67.8) com 2–3 RT. Em 10-05 as `_full` ganharam +21 a +25 cada uma por terem vendido antes da queda (0/1 trade, exposição 38%). Barras de 1 h, 2–4 trades em 4 dias: não há base para afinar nada. Ficam rotuladas.
- H2 memes: −113.8 acumulados, 8% exposto. `h2_ensemble_WIF` +19.5 em 10-05 (p 0.01, 23 trades). Os forks do nightly com cooldown 600 s: WIF atrás (−9.0; em 10-05 +12.5 vs +19.5), FARTCOIN à frente (+3.8). Sinais opostos nas duas moedas → o efeito do cooldown é ruído por agora. Nada a acrescentar.
- Bot real (paper): −0.24 US$ contra segurar, hit 80/135, 135C/0V; auditoria 412 erros vs 453 acertos, nenhuma palavra com lift. Quarto dia sem frase com evidência multi-dia. 0/1.

## 2. Forks anteriores (margens desde a criação; fonte: `night_cli context` 01:30)

| Fork | Quem | Mudança | Idade | PnL f−p (pp) | Habilidade f−p (US$) | Trades f/p | Estado da hipótese |
|---|---|---|---:|---:|---:|---|---|
| relaxed__fork1 | nightly | exits + teto 50% | 3.1 d | +0.78 | +11.0 | 16/0 | **em observação, a confirmar-se**: única linha positiva do von, timing p 0.02, à frente 100% dos dias; 3 RT, pequeno |
| poorjev_relaxed__fork1 | nightly | exits + margem 0 | 3.1 d | +0.10 | −6.6 | 77/0 | sem dados sobre saídas (3 RT); margem de PnL é beta |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | TP 1.5%, trail 0.7% | 3.1 d | −4.05 | −44.4 | 241/72 | **refutada** (4.º dia: −6.4 → −9.6 → −21.8 → −44.4; em 10-05 −17.1 vs +2.5 do pai, 82 trades, 13.2 US$ só de custo vs mark). Fica rotulada |
| h2_ensemble_FARTCOIN__fork1 | nightly | cooldown 600 s | 3.1 d | +0.39 | +3.8 | 28/33 | sem dados (≈ pai) |
| h2_ensemble_WIF__fork1 | nightly | cooldown 600 s | 3.1 d | −0.90 | −9.0 | 27/35 | atrás; sinal oposto ao de FARTCOIN → ruído |
| relaxed_expcap50__fork1 | claude-night | critérios (buy+hold+skip) | 3.0 d | −0.35 | +2.1 | 1/0 | **a caminho de refutar** (0 trades e 0% exposição em 10-04 e 10-05; 82% das chamadas são sell). 7.º dia a 10-10 |
| laya_relaxed__fork1 | claude-night | conf ≥ 0.04, margem 0 | 3.0 d | −2.61 | −29.8 | 218/0 | **método confirmado** (38 RT, a linhagem mais rápida do lab); **habilidade líquida refutada**, mas 3 dias seguidos mostram custo ≈ 18–22/dia e seleção bruta ≈ +3–4/dia → gera o fork C |
| FARTCOIN_laya_relaxed__fork1 | claude-night | conf ≥ 0.07, margem 0 | 3.0 d | −0.14 | −1.4 | 2/0 | **sem dados por veto mal calibrado** (5 de 13 ciclos hoje passaram a confiança e caíram no veto) → gera o fork D |
| h1_exits_von_relaxed__fork1 | claude-night | critérios (1 cláusula no buy) | 2.0 d | −1.20 | −14.4 | 27/58 | **refutada** pelo critério de ontem (≥ 15 trades e atrás). O texto baixou a confiança e a exposição (52% vs 95%) sem mudar a seleção; o marcador que mirava (green) inverteu. Não volto a propor critérios no von |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios "não perseguir" | 2.0 d | +0.05 | +0.3 | 25/25 | **sem divergência de trades**: primeira venda (SL) e recompras no mesmo ciclo que o pai; conf 0.62–0.74 vs 0.88–0.93. **Mas o texto reordena estados por confiança** (decil superior em dumping/red/wide) → gera o fork E |
| h1_exits_BONK_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 1.0 d | −0.48 | −8.0 | 38/38 | **sem dados (1 venda; preciso de ≥ 3)**. Primeiro episódio **contra**: venda simultânea às 14:18; o pai recomprou 14:49–17:16, o fork 16:20–18:47 a um preço médio 0.5% mais alto (3.847e-6 vs 3.828e-6). BONK fez um ressalto nas 2 h de espera e caiu depois |
| h1_exits_MEW_poorjev_relaxed__fork1 | claude-night | reentrada 120 min | 1.0 d | +0.01 | +0.1 | 12/12 | **sem dados**: nenhuma venda desde a criação; o clone é idêntico ao pai (mesmo USDT ao cêntimo) |

### O que os forks ensinaram esta noite

1. **No von, o texto está esgotado como alavanca.** Dois forks de critérios: um estrangulou (0 trades), o outro baixou a exposição sem mudar a seleção e perdeu 14 US$ ao pai em dois dias. A única linha positiva do von é mecânica (saídas + teto de exposição). Daqui para a frente, no von só portões/saídas.
2. **No poorjev, o texto é um reordenador de confiança por estado, não um filtro.** Com o portão a 0.35 não muda nada (recompras idênticas). A pergunta aberta é se o decil superior do fork (dumping/red) tem seleção melhor do que o decil superior do pai (pumping/jumpy) — responde-se com um portão, não com mais texto.
3. **Esperar depois de uma saída é uma moeda ao ar num único dia.** O primeiro episódio de BONK foi contra (recomprou mais alto depois de um ressalto). Só com ≥ 3 vendas por moeda e as duas moedas no mesmo sentido é que a hipótese se decide.
4. **A habilidade de H1 em memes é um punhado de saídas e um dia de −5% devolve metade.** Não é um motivo para mexer nas saídas (não há como calibrar níveis com 6 vendas), mas é um motivo para não ler +67 US$ como sinal.

## 3. Decisões desta noite

### C. Laya SOL — cooldown 3600 s — `laya_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent laya_relaxed__fork1 --diff '{"gates": {"cooldown_seconds": 3600}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.04, margem ≥ 0.0, skip < 0.5, **cooldown 3600 s** (fork1: 120), ≤ 8/h, compra 25% USDT.
- Hipótese: o fork1 perde por custo e não por seleção (3 dias: ≈ 40 US$ de taxas + custo vs mark contra −31 de habilidade; bruto ≈ +9). Uma pausa de 1 h corta a frequência para ≤ 24/dia e deixa a seleção, se existir, aparecer líquida. Uma ideia: frequência.
- Confirma se (3–7 dias): habilidade fork2 − `laya_relaxed` > 0 US$ com ≥ 20 trades, e acima da margem do fork1 no mesmo período. Refuta se: ≤ 0 com ≥ 20 trades → a Laya em SOL não tem seleção positiva mesmo sem churn; a linha Laya SOL fecha.
- Resultado: `created`. Caps 1/6, total 13/80.

### D. Laya FARTCOIN — veto de skip relaxado — `FARTCOIN_laya_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent FARTCOIN_laya_relaxed --diff '{"gates": {"min_confidence": 0.07, "min_prob_margin": 0.0, "max_skip_noul": 0.95}}' --reason '…'` (dry-run OK antes).
- Efetivo: conf ≥ 0.07, margem ≥ 0.0, **skip < 0.95** (fork1: 0.5), cooldown 120 s, ≤ 8/h, compra 25% USDT.
- Hipótese: o fork1 fez 2 trades em 3 dias porque o veto de skip bloqueia a maioria dos ciclos, incluindo os que passam a confiança (hoje 5 de 13). O skip da Laya está na escala própria do modelo, como a confiança. A diferença fork2 − fork1 isola o veto. Torna mensurável o único modelo pequeno que vende em memes.
- Confirma se: ≥ 20 trades com vendas > 0 em 3–7 dias e habilidade fork2 − pai > 0 US$. Refuta se: ≥ 20 trades e habilidade ≤ 0 (Laya sem habilidade em memes), ou < 5 trades em 3 dias (há outro bloqueio: provavelmente as compras não chegam a 0.07).
- Resultado: `created`. Caps 2/6, total 14/80.

### E. WIF poorjev — portão 0.75 sobre o fork de critérios — `h1_exits_WIF_poorjev_relaxed__fork2` (criado)

- Comando: `night_cli.py fork --parent h1_exits_WIF_poorjev_relaxed__fork1 --diff '{"gates": {"min_confidence": 0.75}}' --reason '…'`. Primeira tentativa recusada por `--reason` com 833 caracteres (limite 800); repetida com o texto encurtado.
- Efetivo: **conf ≥ 0.75** (fork1: 0.35), margem ≥ 0.2, skip < 0.5, cooldown 120 s, ≤ 8/h, compra 25% USDT, saídas TP 6% / SL 4% / trailing 3% (arma +3%), reentrada 30 min, critérios próprios (e2715f698b, herdados do fork1).
- Hipótese: o texto do fork1 não muda a ação (buy em 100%) mas reordena a confiança por estado: o decil superior (≥ 0.81) cai em dumping/red/wide, os estados que o texto prefere; no poorjev sem texto cai em pumping/jumpy/green/tight. Com o portão a 0.75 (≈ P70–P75 do fork; p50 0.689), o fork2 só compra quando o texto "concorda" com a fita e recompra menos vezes depois de saídas (as recompras de hoje saíram a 0.65–0.74 e teriam sido bloqueadas). Uma ideia: portão; tudo o resto herda do fork1. É o segundo passo do método anunciado ontem (texto numa noite, portão na escala nova noutra).
- Confirma se (5–7 dias, contando da primeira venda — o livro clonado nasce saturado): habilidade fork2 − fork1 > 0 US$ com ≥ 3 vendas no fork2. Refuta se: ≤ 0 com ≥ 3 vendas, ou < 5 compras em 3 dias depois da primeira venda (portão alto demais). Cautela: hoje as confiantes do fork1 em dumping acertaram 29% (dia de baixa do WIF).
- Resultado: `created`. Caps 3/6, total 15/80.

### Ideias consideradas e não executadas

- **Critérios no von** (qualquer pai): linha fechada esta noite (fork refutado com ≥ 15 trades). Zero.
- **Reentrada 120 min numa terceira moeda H1**: BONK e MEW já correm; o primeiro episódio de BONK foi contra. Replicar antes de ter 3 vendas é gastar um fork sem informação nova.
- **Fork de `relaxed__fork1`** (a melhor linha do von): o que ele precisa é de dias, não de variantes; e a hipótese de reentrada já está a ser testada em H1.
- **Saídas mais largas em H1 memes** depois do dia de −5%: 6 vendas por moeda não calibram níveis; o fork oposto do nightly (saídas curtas) está refutado, o que não prova que largas sejam melhores.
- **Critério de venda na Laya SOL contra "lifting tight"**: o lift caiu de +0.25 para +0.09; e na Laya qualquer deslocamento de confiança (0.028 vs portão 0.04) liga ou desliga tudo. Primeiro o custo (fork C).
- **Baixar a confiança da Laya FARTCOIN para 0.05 junto com o veto**: seria duas ideias num fork; e a 0.05 (≈ P60) o fork negociaria 40% dos ciclos — o churn que acabou de refutar a Laya SOL. Fica para 10-08 se D ficar a 0 trades.
- **H2 cooldown**: domínio do nightly; sinais opostos entre WIF e FARTCOIN.
- **Regras 1 h**: 2–4 trades em 4 dias.
- **Bot real**: 0/1; quarto dia sem palavra com lift na auditoria do próprio bot.

## 4. O que verificar amanhã (2026-10-07)

1. **`laya_relaxed__fork2`**: ≤ 24 trades no dia? taxas + custo vs mark em relação ao fork1 (deve cair para ≈ 1/4); habilidade fork2 vs `laya_relaxed` e vs fork1 na mesma janela. Se o bruto do fork1 continuar ≈ +3–4/dia e o fork2 ficar perto disso líquido, a hipótese vai bem.
2. **`FARTCOIN_laya_relaxed__fork2`**: trades > 0? Quantas decisões tiveram buy com conf ≥ 0.07? Se 0 trades em 2 dias só por `low_confidence`, o passo seguinte (linhagem livre a 10-08) é conf 0.05, registando que é uma segunda ideia.
3. **`h1_exits_WIF_poorjev_relaxed__fork2`**: primeira venda? Quantas compras passaram o portão 0.75 e em que estados (juntar `lab_decisions` com `meme_decisions` por `source_decision_id`)? Se as compras do fork2 caírem em red/dumping e as do fork1 em qualquer estado, o mecanismo confirma-se mesmo antes da habilidade.
4. **BONK/MEW reentrada**: novas vendas? Em cada uma, preço médio da recompra do fork (2 h) vs do pai (30 min). Decisão só com ≥ 3 vendas por moeda e sentido igual nas duas.
5. **`h1_exits_von_relaxed__fork1`**: refutado por mim; ver se o tuner mantém "atrás da original". **`relaxed_expcap50__fork1`**: 7.º dia a 10-10; se < 5 trades, refutada.
6. **Lift do poorjev em memes (5.º dia)**: tight/pumping/jumpy/lifting nos erros e wide/red nos acertos continuam? **H1 memes**: a habilidade acumulada (+29.8) recupera ou continua a devolver? FARTCOIN H1 ainda p 0.01?
7. **`relaxed__fork1`**: continua à frente em 100% dos dias? Com 5 dias e ≥ 20 trades o tuner pode marcá-lo lead fork.
8. Linhagens que desbloqueiam: `h1_exits_von_relaxed` já livre (sem plano); BONK/MEW H1 a 10-07 01:35; `laya_relaxed`, `FARTCOIN_laya_relaxed` e `h1_exits_WIF_poorjev_relaxed` a 10-08 ~01:4x.

## 5. Recusas e limites

- **Recusas exit 2 (1):** `fork --parent h1_exits_WIF_poorjev_relaxed__fork1` recusado por `--reason` com 833 caracteres (limite 800). Erro meu, não limite do lab; repetido com texto encurtado e criado. Nenhuma recusa por linhagem ou por valor fora dos limites; as linhagens `laya_relaxed`, `FARTCOIN_laya_relaxed` e `h1_exits_WIF_poorjev_relaxed` estavam livres à hora das tentativas.
- Limites: **3/6 forks criados** (C, D, E; todos de parâmetros, zero forks de critérios, zero chamadas extra ao modelo); total 15/80; bot real 0/1.
- Nada apagado, pausado ou editado fora de `run/claude_night/2026-10-06/`. Nenhuma credencial lida.
