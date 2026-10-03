# Revisão noturna: corte por percentil vs barra fixa 0,8 (logs reais)

Gerado 2026-09-30T01:12:35-03:00 por `scripts/compare_review_cutoffs.py` (só leitura) sobre a raiz `paper` (exportação). Paper only.

## Definições

- **Respondida:** decisão com resposta real do modelo (sem `fail_closed`, `von_ok` ≠ false, `model` ≠ `rule`, conf > 0).
- **Corte:** barra fixa `conf > 0.8` (regra antiga) ou percentil P das confianças respondidas do grupo na janela (`conf >= Pxx`; com muitos empates no corte, `tie_rule=auto` passa a `>` — ver coluna Regra).
- **Candidatas:** chamadas direcionais do modelo (`chosen_action` buy/sell), antes dos portões de carteira. Motivo (visto nos logs): o `relaxed` ficou 100% investido e as decisões seguintes têm `final_action=hold` (`insufficient_usdt`); auditar só ordens deixaria o modelo sem auditoria. A variante `acted` (só ordens) aparece à parte.
- **Erro:** compra com retorno a 900 s < −0.10%, venda com retorno > +0.10%; acerto = movimento além da banda no sentido da chamada; flat = dentro da banda. Preço futuro: primeiro ponto da série do ativo (`data/prices.jsonl`, `data/meme/prices/*.jsonl`, completadas pelos preços das decisões) em [t+900 s, t+1200 s]; sem ponto → não resolvida.
- **Dedupe:** baseline e relaxed (e as variantes de cada modelo) partilham uma chamada por ciclo; as linhas iguais são fundidas (mesmo modelo, estado, confiança, escolha e preço em ≤ 5 s) para não contar a mesma chamada duas vezes.

## Leitura

- **Barra fixa 0,8 nesta execução:** von SOL 0, von SOL v2 0, Laya SOL 0, poorjev SOL 0, von memes 0, Laya memes 0, poorjev memes 0 chamadas confiantes. Com confianças do von ≤ ~0,40 e da Laya ≤ ~0,13 a regra antiga nunca tem o que auditar (questão 3 do HANDOFF confirmada nos logs).
- **O mesmo 0,8 no poorjev (`run_52usd_2026-09-24`):** marca 454 de 454 chamadas (100.0%) como confiantes. Barra fixa = nunca (von/Laya) ou sempre (poorjev): depende da escala de cada modelo; o percentil dá ~10% das respondidas em qualquer escala.
- **P90 por família (execução principal, janela de decisões disponível):**
  - von SOL, critérios baseline (baseline+relaxed; o híbrido é a mesma chamada): corte 0.361 (conf >= P90), 62 de 555 respondidas (11.2%), 62 resolvidas → 40 erros em 1 episódio(s) / 0 acertos / 22 flat (hit rate 0.0%); palavras dos erros: calm, deep, held, late, mid.
  - von SOL, critérios v2: corte 0.245 (conf > P90 (empates)), 22 de 555 respondidas (4.0%), 22 resolvidas → 4 erros em 1 episódio(s) / 0 acertos / 18 flat (hit rate 0.0%); palavras dos erros: buoyed, calm, deep, late, lifting.
  - Laya SOL: corte 0.036 (conf > P90 (empates)), 44 de 556 respondidas (7.9%), 44 resolvidas → 7 erros em 2 episódio(s) / 6 acertos / 31 flat (hit rate 13.6%); palavras dos erros: calm, deep, held, late, mid.
  - poorjev SOL: sem respostas do modelo na janela.
  - von memes (7 moedas): corte 0.366 (conf >= P90), 10 de 79 respondidas (12.7%), 9 resolvidas → 3 erros em 3 episódio(s) / 4 acertos / 2 flat (hit rate 44.4%); palavras dos erros: deep, fading, flat, late, mid.
  - Laya memes: corte 0.064 (conf >= P90), 8 de 79 respondidas (10.1%), 8 resolvidas → 2 erros em 2 episódio(s) / 4 acertos / 2 flat (hit rate 50.0%); palavras dos erros: deep, dumping, flat, jumpy, late.
  - poorjev memes: sem respostas do modelo na janela.
- **Compras agora auditadas (relaxed, todos os trades):** 39 resolvidos, 17 erros (16 em compras), 14 acertos → hit rate 35.9%. A revisão antiga só olhava `approx_pnl` de vendas (1 venda).
- **Compras agora auditadas (hybrid_von_relaxed_cap2, todos os trades):** 39 resolvidos, 16 erros (15 em compras), 13 acertos → hit rate 33.3%. A revisão antiga só olhava `approx_pnl` de vendas (1 venda).
- **Proposta (P90):** acrescenta {"buy": ["be wary when the tape reads wide, green, flat"]}; difere do `criteria_v2.json` em uso, que tem as frases "prefer …" acrescentadas sem erros em 2026-09-24. Continua só proposta (portão humano).
- **A janela manda mais que o corte:** o mesmo von SOL no P90 acertou 24/39 na janela da execução arquivada (2026-09-24 19:30→21:07, SOL +0.83%) e 0/62 na janela principal (2026-09-26 01:35→03:54, SOL -0.09%). O modelo chama quase só `buy`; com poucas horas o hit rate reflete o movimento local, não a qualidade do corte.

## Ressalvas

- Janela de decisões curta: 2.3 h de decisões SOL e 1.3 h de memes nesta raiz (os logs de decisão são rotacionados às 01:00 e ficam só as últimas linhas; os arquivos `archive/logs` não estão nesta raiz). Os trades (nunca rotacionados) cobrem 30.8 h, daí a secção sem corte de confiança.
- Movimento do SOL: 120.42 → 120.31 (-0.09%) na janela de decisões SOL; 117.30 → 120.31 (+2.56%) desde o início da execução. Como o von chama quase só `buy`, o hit rate depende sobretudo do movimento local; poucas horas não separam modelo de regime.
- Execução curta (≈1.3 dias desde o início até ao último dado) e já arquivada; nenhum portfólio atingiu os mínimos de veredito (≥30 RT e ≥21 dias). Serve para escolher a regra da revisão, não para avaliar modelos.
- Autocorrelação: decisões a cada 15 s repetem o mesmo estado; dezenas de "erros" podem ser um único episódio de poucos minutos (coluna/menção "episódios": erros separados por > 5 min). Contar episódios, não linhas, antes de tirar conclusões.
- Horizonte único (15 min) e banda fixa (0,10%) para SOL e memes; memes são mais voláteis, a banda devia ser por ativo.
- poorjev: 1349/1349 linhas sem resposta (fail-closed) na janela; erro mais comum: `http_500:RuntimeError:mat1 and mat2 must have the same dtype`.
- Empates: as confianças do von concentram-se em poucos valores; quando `>=` no percentil marcaria >1,5× a fração pedida, usa-se `>` (coluna Regra). P80 e P90 podem então coincidir.

## Execução de US$ 1.000 (desde 2026-09-24 21:07 BRT)

Pasta: `paper`

### Janela coberta

- decisões SOL (`logs/decisions.jsonl`): 5000 linhas, 2026-09-26 01:35 → 2026-09-26 03:54 BRT (2.3 h)
- decisões memes (`logs/meme_decisions.jsonl`): 5000 linhas, 2026-09-26 02:35 → 2026-09-26 03:54 BRT (1.3 h)
- decisões lab (`logs/lab_decisions.jsonl`): 7514 linhas, 2026-09-25 23:05 → 2026-09-26 03:54 BRT (4.8 h)
- trades SOL + lab SOL (`logs/trades.jsonl`, nunca rotacionado): 242 linhas, 2026-09-24 21:08 → 2026-09-25 21:25 BRT (24.3 h)
- trades memes (`logs/meme_trades.jsonl`, nunca rotacionado): 704 linhas, 2026-09-24 21:08 → 2026-09-26 03:53 BRT (30.8 h)
- séries de preço para o retorno a 900 s: BONK 2026-09-24 00:33→2026-09-26 03:54, FARTCOIN 2026-09-24 00:33→2026-09-26 03:54, GOAT 2026-09-24 00:33→2026-09-26 03:54, MEW 2026-09-24 00:33→2026-09-26 03:54, PNUT 2026-09-24 00:33→2026-09-26 03:54, POPCAT 2026-09-24 00:33→2026-09-26 03:54, SOL 2026-09-24 00:06→2026-09-26 03:54, WIF 2026-09-24 00:33→2026-09-26 03:54

### Grupos principais (candidatas = chamadas buy/sell do modelo, `chosen`)

Percentil calculado sobre as confianças respondidas (sem fail-closed/sem resposta) de cada grupo na janela. Memes agregados: um único percentil para as 7 moedas de cada modelo.

| Grupo | Variante | Respondidas | conf p50 / máx | Regra | Corte | Confiantes (% resp.) | Viraram ordem | Resolvidas | Erros (episódios) | Acertos | Flat | Hit rate | Palavras dos erros (top 5) |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SOL · laya | barra fixa 0,8 | 556 | 0.036 / 0.082 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · laya | P80 | 556 | 0.036 / 0.082 | conf > P80 (empates) | 0.036 | 44 (7.9%) | 0 | 44 | 7 (2) | 6 | 31 | 13.6% | calm:7, deep:7, held:7, late:7, mid:7 |
| SOL · laya | P90 | 556 | 0.036 / 0.082 | conf > P90 (empates) | 0.036 | 44 (7.9%) | 0 | 44 | 7 (2) | 6 | 31 | 13.6% | calm:7, deep:7, held:7, late:7, mid:7 |
| SOL · laya | P95 | 556 | 0.036 / 0.082 | conf > P95 (empates) | 0.042 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | calm:4, deep:4, held:4, late:4, lifting:4 |
| SOL · poorjev | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | P80 | 0 | – / – | conf >= P80 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | P95 | 0 | – / – | conf >= P95 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · baseline+relaxed | barra fixa 0,8 | 555 | 0.356 / 0.397 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · baseline+relaxed | P80 | 555 | 0.356 / 0.397 | conf > P80 (empates) | 0.356 | 72 (13.0%) | 0 | 72 | 40 (1) | 1 | 31 | 1.4% | calm:40, deep:40, held:40, late:40, mid:40 |
| SOL · von · baseline+relaxed | P90 | 555 | 0.356 / 0.397 | conf >= P90 | 0.361 | 62 (11.2%) | 0 | 62 | 40 (1) | 0 | 22 | 0.0% | calm:40, deep:40, held:40, late:40, mid:40 |
| SOL · von · baseline+relaxed | P95 | 555 | 0.356 / 0.397 | conf > P95 (empates) | 0.367 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | calm:4, deep:4, held:4, late:4, lifting:4 |
| SOL · von · v2 (critérios v2) | barra fixa 0,8 | 555 | 0.245 / 0.311 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · v2 (critérios v2) | P80 | 555 | 0.245 / 0.311 | conf > P80 (empates) | 0.245 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | buoyed:4, calm:4, deep:4, late:4, lifting:4 |
| SOL · von · v2 (critérios v2) | P90 | 555 | 0.245 / 0.311 | conf > P90 (empates) | 0.245 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | buoyed:4, calm:4, deep:4, late:4, lifting:4 |
| SOL · von · v2 (critérios v2) | P95 | 555 | 0.245 / 0.311 | conf > P95 (empates) | 0.245 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | buoyed:4, calm:4, deep:4, late:4, lifting:4 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | barra fixa 0,8 | 555 | 0.356 / 0.397 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P80 | 555 | 0.356 / 0.397 | conf > P80 (empates) | 0.356 | 72 (13.0%) | 0 | 72 | 40 (1) | 1 | 31 | 1.4% | calm:40, deep:40, held:40, late:40, mid:40 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P90 | 555 | 0.356 / 0.397 | conf >= P90 | 0.361 | 62 (11.2%) | 0 | 62 | 40 (1) | 0 | 22 | 0.0% | calm:40, deep:40, held:40, late:40, mid:40 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P95 | 555 | 0.356 / 0.397 | conf > P95 (empates) | 0.367 | 22 (4.0%) | 0 | 22 | 4 (1) | 0 | 18 | 0.0% | calm:4, deep:4, held:4, late:4, lifting:4 |
| Memes (7) · laya | barra fixa 0,8 | 79 | 0.054 / 0.126 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · laya | P80 | 79 | 0.054 / 0.126 | conf >= P80 | 0.057 | 23 (29.1%) | 0 | 23 | 7 (4) | 9 | 7 | 39.1% | deep:7, flat:7, jumpy:7, late:7, mid:7 |
| Memes (7) · laya | P90 | 79 | 0.054 / 0.126 | conf >= P90 | 0.064 | 8 (10.1%) | 0 | 8 | 2 (2) | 4 | 2 | 50.0% | deep:2, dumping:2, flat:2, jumpy:2, late:2 |
| Memes (7) · laya | P95 | 79 | 0.054 / 0.126 | conf >= P95 | 0.077 | 4 (5.1%) | 0 | 4 | 2 (2) | 0 | 2 | 0.0% | deep:2, dumping:2, flat:2, jumpy:2, late:2 |
| Memes (7) · poorjev | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev | P80 | 0 | – / – | conf >= P80 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev | P95 | 0 | – / – | conf >= P95 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | P80 | 0 | – / – | conf >= P80 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | P95 | 0 | – / – | conf >= P95 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · von | barra fixa 0,8 | 79 | 0.243 / 0.375 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · von | P80 | 79 | 0.243 / 0.375 | conf >= P80 | 0.335 | 17 (21.5%) | 4 | 14 | 4 (4) | 8 | 2 | 57.1% | deep:4, flat:4, late:4, mid:4, night:4 |
| Memes (7) · von | P90 | 79 | 0.243 / 0.375 | conf >= P90 | 0.366 | 10 (12.7%) | 2 | 9 | 3 (3) | 4 | 2 | 44.4% | deep:3, fading:3, flat:3, late:3, mid:3 |
| Memes (7) · von | P95 | 79 | 0.243 / 0.375 | conf > P95 (empates) | 0.367 | 3 (3.8%) | 0 | 3 | 2 (2) | 1 | 0 | 33.3% | calm:2, deep:2, fading:2, flat:2, late:2 |

### Memes por moeda e modelo (P90 vs barra fixa)

| Moeda · modelo | Respondidas | Corte P90 | Confiantes P90 | Resolvidas | Erros | Acertos | Hit rate | Confiantes barra 0,8 | Erros barra 0,8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BONK · laya | 11 | 0.054 | 1 | 1 | 1 | 0 | 0.0% | 0 | 0 |
| BONK · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| BONK · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| BONK · von | 11 | 0.349 | 1 | 1 | 0 | 1 | 100.0% | 0 | 0 |
| FARTCOIN · laya | 12 | 0.063 | 1 | 1 | 0 | 1 | 100.0% | 0 | 0 |
| FARTCOIN · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| FARTCOIN · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| FARTCOIN · von | 12 | 0.366 | 1 | 0 | 0 | 0 | – | 0 | 0 |
| GOAT · laya | 11 | 0.063 | 1 | 1 | 0 | 0 | 0.0% | 0 | 0 |
| GOAT · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| GOAT · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| GOAT · von | 11 | 0.335 | 1 | 1 | 1 | 0 | 0.0% | 0 | 0 |
| MEW · laya | 11 | 0.073 | 1 | 1 | 0 | 0 | 0.0% | 0 | 0 |
| MEW · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| MEW · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| MEW · von | 11 | 0.354 | 1 | 1 | 0 | 0 | 0.0% | 0 | 0 |
| PNUT · laya | 11 | 0.063 | 1 | 1 | 0 | 1 | 100.0% | 0 | 0 |
| PNUT · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| PNUT · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| PNUT · von | 11 | 0.375 | 3 | 3 | 2 | 1 | 33.3% | 0 | 0 |
| POPCAT · laya | 12 | 0.097 | 2 | 2 | 2 | 0 | 0.0% | 0 | 0 |
| POPCAT · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| POPCAT · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| POPCAT · von | 12 | 0.252 | 1 | 1 | 0 | 1 | 100.0% | 0 | 0 |
| WIF · laya | 11 | 0.057 | 1 | 1 | 0 | 1 | 100.0% | 0 | 0 |
| WIF · poorjev | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| WIF · poorjev+rules | 0 | – | 0 | 0 | 0 | 0 | – | 0 | 0 |
| WIF · von | 11 | 0.309 | 1 | 1 | 0 | 0 | 0.0% | 0 | 0 |

### Lab por portfólio (P90 vs barra fixa)

Linhas do lab copiam a decisão de origem (von/poorjev) ou, no H2, trazem a confiança do ensemble (percentil combinado). Cópias de um modelo em falha têm conf 0 e contam como não respondidas. Sem texto de estado → sem palavras.

| Portfólio | Respondidas | Corte P90 | Confiantes P90 | Resolvidas | Erros | Acertos | Hit rate | Confiantes barra 0,8 | Erros barra 0,8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lab · h1_exits_von_relaxed | 1157 | 0.367 | 120 | 120 | 72 | 12 | 10.0% | 0 | 0 |
| lab · h2_ensemble_BONK | 30 | 0.671 | 3 | 3 | 0 | 2 | 66.7% | 0 | 0 |
| lab · h2_ensemble_FARTCOIN | 27 | 0.821 | 3 | 3 | 1 | 2 | 66.7% | 4 | 1 |
| lab · h2_ensemble_GOAT | 28 | 0.748 | 3 | 3 | 1 | 0 | 0.0% | 2 | 1 |
| lab · h2_ensemble_MEW | 34 | 0.626 | 4 | 4 | 2 | 1 | 25.0% | 1 | 0 |
| lab · h2_ensemble_PNUT | 39 | 0.856 | 4 | 4 | 0 | 1 | 25.0% | 6 | 0 |
| lab · h2_ensemble_POPCAT | 34 | 0.762 | 4 | 4 | 0 | 2 | 50.0% | 1 | 0 |
| lab · h2_ensemble_WIF | 32 | 0.796 | 4 | 4 | 1 | 3 | 75.0% | 3 | 1 |
| lab · h2_ensemble_sol | 1094 | 0.659 | 111 | 111 | 61 | 13 | 11.7% | 84 | 34 |
| lab · h3_limit_hybrid_von_cap2 | 1157 | 0.367 | 120 | 120 | 72 | 12 | 10.0% | 0 | 0 |
| lab · h4_hours_von_relaxed | 1157 | 0.367 | 120 | 120 | 72 | 12 | 10.0% | 0 | 0 |

Sem respostas na janela (omitidos): h1_exits_BONK_poorjev_relaxed, h1_exits_FARTCOIN_poorjev_relaxed, h1_exits_GOAT_poorjev_relaxed, h1_exits_MEW_poorjev_relaxed, h1_exits_PNUT_poorjev_relaxed, h1_exits_POPCAT_poorjev_relaxed, h1_exits_WIF_poorjev_relaxed, h3_limit_poorjev_relaxed, h4_hours_poorjev_relaxed.

### Só o que virou ordem paper (`acted`: traded, join por decision_id ou final_action buy/sell)

| Grupo | Variante | Respondidas | conf p50 / máx | Regra | Corte | Confiantes (% resp.) | Viraram ordem | Resolvidas | Erros (episódios) | Acertos | Flat | Hit rate | Palavras dos erros (top 5) |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Memes (7) · laya | barra fixa 0,8 | 79 | 0.054 / 0.126 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · laya | P90 | 79 | 0.054 / 0.126 | conf >= P90 | 0.064 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · poorjev+rules | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · von | barra fixa 0,8 | 79 | 0.243 / 0.375 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · von | P90 | 79 | 0.243 / 0.375 | conf >= P90 | 0.366 | 2 (2.5%) | 2 | 1 | 0 (0) | 1 | 0 | 100.0% | – |
| SOL · laya | barra fixa 0,8 | 556 | 0.036 / 0.082 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · laya | P90 | 556 | 0.036 / 0.082 | conf > P90 (empates) | 0.036 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | barra fixa 0,8 | 0 | – / – | conf > 0.8 (barra fixa) | 0.800 | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | P90 | 0 | – / – | conf >= P90 | – | 0 (–) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · baseline+relaxed | barra fixa 0,8 | 555 | 0.356 / 0.397 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · baseline+relaxed | P90 | 555 | 0.356 / 0.397 | conf >= P90 | 0.361 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · v2 (critérios v2) | barra fixa 0,8 | 555 | 0.245 / 0.311 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · v2 (critérios v2) | P90 | 555 | 0.245 / 0.311 | conf > P90 (empates) | 0.245 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von+rules · hybrid_von_relaxed_cap2 | barra fixa 0,8 | 555 | 0.356 / 0.397 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P90 | 555 | 0.356 / 0.397 | conf >= P90 | 0.361 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |

### Auditoria de todos os trades (sem corte de confiança)

Cada trade paper conta como chamada (compra/venda) ao `price_mark`; mesmo critério de erro (900 s, ±0.10%). Cobre a execução inteira, porque os logs de trades não são rotacionados. Memes agregados por família (`{SYM}`).

| Família | Trades (C/V) | Resolvidos | Erros | Acertos | Flat | Hit rate | Erros compra / venda |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL · h1_exits_von_relaxed | 92 (88/4) | 91 | 34 | 38 | 19 | 41.8% | 33 / 1 |
| SOL · hybrid_von_relaxed_cap2 | 41 (40/1) | 39 | 16 | 13 | 10 | 33.3% | 15 / 1 |
| SOL · relaxed | 41 (40/1) | 39 | 17 | 14 | 8 | 35.9% | 16 / 1 |
| SOL · h2_ensemble_sol | 20 (20/0) | 20 | 15 | 3 | 2 | 15.0% | 15 / 0 |
| SOL · h3_limit_hybrid_von_cap2 | 20 (20/0) | 19 | 5 | 8 | 6 | 42.1% | 5 / 0 |
| SOL · h4_hours_von_relaxed | 20 (20/0) | 20 | 2 | 16 | 2 | 80.0% | 2 / 0 |
| SOL · h3_limit_poorjev_relaxed | 2 (2/0) | 2 | 1 | 0 | 1 | 0.0% | 1 / 0 |
| SOL · poorjev_baseline | 2 (2/0) | 2 | 1 | 1 | 0 | 50.0% | 1 / 0 |
| SOL · poorjev_relaxed | 2 (2/0) | 2 | 1 | 1 | 0 | 50.0% | 1 / 0 |
| SOL · rsi_sol_1h | 1 (0/1) | 1 | 0 | 1 | 0 | 100.0% | 0 / 0 |
| SOL · v2 | 1 (0/1) | 1 | 1 | 0 | 0 | 0.0% | 0 / 1 |
| Memes · h1_exits_{SYM}_poorjev_relaxed | 175 (167/8) | 170 | 93 | 58 | 19 | 34.1% | 88 / 5 |
| Memes · {SYM}_hybrid_poorjev_regime | 140 (140/0) | 140 | 71 | 48 | 21 | 34.3% | 71 / 0 |
| Memes · {SYM}_poorjev_baseline | 140 (140/0) | 140 | 69 | 49 | 22 | 35.0% | 69 / 0 |
| Memes · {SYM}_poorjev_relaxed | 140 (140/0) | 140 | 70 | 49 | 21 | 35.0% | 70 / 0 |
| Memes · h2_ensemble_{SYM} | 58 (39/19) | 58 | 25 | 25 | 8 | 43.1% | 16 / 9 |
| Memes · meme_{SYM}_relaxed | 29 (18/11) | 25 | 15 | 4 | 6 | 16.0% | 9 / 6 |
| Memes · {SYM}_rule_regime | 7 (7/0) | 7 | 0 | 5 | 2 | 71.4% | 0 / 0 |
| Memes · {SYM}_rule_regime_full | 7 (7/0) | 7 | 0 | 5 | 2 | 71.4% | 0 / 0 |
| Memes · {SYM}_rule_donch_regime | 4 (4/0) | 4 | 3 | 1 | 0 | 25.0% | 3 / 0 |
| Memes · {SYM}_rule_donch_regime_full | 4 (4/0) | 4 | 3 | 1 | 0 | 25.0% | 3 / 0 |
| **total** | 946 | 931 | 442 | 340 | 149 | 36.5% | |

### Proposta resultante vs `criteria_v2.json` atual

Reescrita determinística (`propose_criteria`) a partir do grupo `SOL · von · baseline+relaxed`; frases só entram quando há erros confiantes.

| Variante | Erros confiantes | Frases acrescentadas | Igual ao `criteria_v2.json` atual? |
|---|---:|---|---|
| barra fixa 0,8 | 0 | — (texto base) | não |
| P80 | 40 | {"buy": ["be wary when the tape reads green, wide, flat"]} | não |
| P90 | 40 | {"buy": ["be wary when the tape reads wide, green, flat"]} | não |
| P95 | 4 | {"buy": ["be wary when the tape reads green"]} | não |

`criteria_v2.json` atual (gerado em 2026-09-24 04:00 com 0 trades auditados) tem as frases "prefer …" que a revisão antiga acrescentava sempre; com a regra nova, sem erros confiantes a proposta é o texto base, logo também difere dele.

## Complemento: execução arquivada `run_52usd_2026-09-24`

Pasta: `run_52usd_2026-09-24`

### Janela coberta

- decisões SOL (`logs/decisions.jsonl`): 3496 linhas, 2026-09-24 19:30 → 2026-09-24 21:07 BRT (1.6 h)
- decisões memes (`logs/meme_decisions.jsonl`): 15233 linhas, 2026-09-24 00:33 → 2026-09-24 21:07 BRT (20.6 h)
- decisões lab (`logs/lab_decisions.jsonl`): 514 linhas, 2026-09-24 20:47 → 2026-09-24 21:07 BRT (0.3 h)
- trades SOL + lab SOL (`logs/trades.jsonl`, nunca rotacionado): 58 linhas, 2026-09-24 00:41 → 2026-09-24 21:06 BRT (20.4 h)
- trades memes (`logs/meme_trades.jsonl`, nunca rotacionado): 228 linhas, 2026-09-24 02:45 → 2026-09-24 21:06 BRT (18.4 h)
- séries de preço para o retorno a 900 s: BONK 2026-09-24 00:33→2026-09-26 03:54, FARTCOIN 2026-09-24 00:33→2026-09-26 03:54, GOAT 2026-09-24 00:33→2026-09-26 03:54, MEW 2026-09-24 00:33→2026-09-26 03:54, PNUT 2026-09-24 00:33→2026-09-26 03:54, POPCAT 2026-09-24 00:33→2026-09-26 03:54, SOL 2026-09-24 00:06→2026-09-26 03:54, WIF 2026-09-24 00:33→2026-09-26 03:54

### Grupos principais (candidatas = chamadas buy/sell do modelo, `chosen`)

Percentil calculado sobre as confianças respondidas (sem fail-closed/sem resposta) de cada grupo na janela. Memes agregados: um único percentil para as 7 moedas de cada modelo.

| Grupo | Variante | Respondidas | conf p50 / máx | Regra | Corte | Confiantes (% resp.) | Viraram ordem | Resolvidas | Erros (episódios) | Acertos | Flat | Hit rate | Palavras dos erros (top 5) |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SOL · laya | barra fixa 0,8 | 388 | 0.013 / 0.042 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · laya | P80 | 388 | 0.013 / 0.042 | conf > P80 (empates) | 0.017 | 41 (10.6%) | 0 | 41 | 19 (2) | 16 | 6 | 39.0% | calm:19, deep:19, fading:19, held:19, late:19 |
| SOL · laya | P90 | 388 | 0.013 / 0.042 | conf >= P90 | 0.033 | 41 (10.6%) | 0 | 41 | 19 (2) | 16 | 6 | 39.0% | calm:19, deep:19, fading:19, held:19, late:19 |
| SOL · laya | P95 | 388 | 0.013 / 0.042 | conf >= P95 | 0.034 | 20 (5.2%) | 0 | 20 | 19 (2) | 0 | 1 | 0.0% | calm:19, deep:19, fading:19, held:19, late:19 |
| SOL · poorjev | barra fixa 0,8 | 388 | 0.517 / 0.547 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · poorjev | P80 | 388 | 0.517 / 0.547 | conf >= P80 | 0.521 | 116 (29.9%) | 0 | 116 | 1 (1) | 42 | 73 | 36.2% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · poorjev | P90 | 388 | 0.517 / 0.547 | conf > P90 (empates) | 0.522 | 26 (6.7%) | 0 | 26 | 0 (0) | 21 | 5 | 80.8% | – |
| SOL · poorjev | P95 | 388 | 0.517 / 0.547 | conf >= P95 | 0.537 | 24 (6.2%) | 0 | 24 | 0 (0) | 21 | 3 | 87.5% | – |
| SOL · von · baseline+relaxed | barra fixa 0,8 | 388 | 0.334 / 0.394 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · baseline+relaxed | P80 | 388 | 0.334 / 0.394 | conf >= P80 | 0.350 | 111 (28.6%) | 3 | 111 | 1 (1) | 37 | 73 | 33.3% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · von · baseline+relaxed | P90 | 388 | 0.334 / 0.394 | conf >= P90 | 0.367 | 39 (10.1%) | 3 | 39 | 1 (1) | 24 | 14 | 61.5% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · von · baseline+relaxed | P95 | 388 | 0.334 / 0.394 | conf > P95 (empates) | 0.384 | 18 (4.6%) | 1 | 18 | 1 (1) | 8 | 9 | 44.4% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · von · v2 (critérios v2) | barra fixa 0,8 | 388 | 0.163 / 0.302 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von · v2 (critérios v2) | P80 | 388 | 0.163 / 0.302 | conf >= P80 | 0.196 | 98 (25.3%) | 0 | 98 | 28 (5) | 24 | 46 | 24.5% | buoyed:28, calm:28, deep:28, late:28, mid:28 |
| SOL · von · v2 (critérios v2) | P90 | 388 | 0.163 / 0.302 | conf >= P90 | 0.257 | 41 (10.6%) | 0 | 41 | 19 (2) | 16 | 6 | 39.0% | buoyed:19, calm:19, deep:19, fading:19, late:19 |
| SOL · von · v2 (critérios v2) | P95 | 388 | 0.163 / 0.302 | conf >= P95 | 0.272 | 22 (5.7%) | 0 | 22 | 1 (1) | 16 | 5 | 72.7% | buoyed:1, calm:1, deep:1, fading:1, late:1 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | barra fixa 0,8 | 388 | 0.334 / 0.394 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P80 | 388 | 0.334 / 0.394 | conf >= P80 | 0.350 | 111 (28.6%) | 0 | 111 | 1 (1) | 37 | 73 | 33.3% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P90 | 388 | 0.334 / 0.394 | conf >= P90 | 0.367 | 39 (10.1%) | 0 | 39 | 1 (1) | 24 | 14 | 61.5% | calm:1, deep:1, green:1, held:1, late:1 |
| SOL · von+rules · hybrid_von_relaxed_cap2 | P95 | 388 | 0.334 / 0.394 | conf > P95 (empates) | 0.384 | 18 (4.6%) | 0 | 18 | 1 (1) | 8 | 9 | 44.4% | calm:1, deep:1, green:1, held:1, late:1 |
| Memes (7) · laya | barra fixa 0,8 | 432 | 0.046 / 0.176 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · laya | P80 | 432 | 0.046 / 0.176 | conf >= P80 | 0.073 | 88 (20.4%) | 0 | 88 | 35 (26) | 36 | 17 | 40.9% | deep:35, flat:35, mid:35, quiet:35, wide:32 |
| Memes (7) · laya | P90 | 432 | 0.046 / 0.176 | conf >= P90 | 0.089 | 46 (10.6%) | 0 | 46 | 19 (16) | 19 | 8 | 41.3% | deep:19, flat:19, mid:19, quiet:19, wide:19 |
| Memes (7) · laya | P95 | 432 | 0.046 / 0.176 | conf >= P95 | 0.102 | 22 (5.1%) | 0 | 22 | 8 (7) | 8 | 6 | 36.4% | deep:8, flat:8, mid:8, quiet:8, wide:8 |
| Memes (7) · poorjev | barra fixa 0,8 | 454 | 0.932 / 0.968 | conf > 0.8 (barra fixa) | 0.800 | 454 (100.0%) | 104 | 454 | 197 (14) | 165 | 92 | 36.3% | deep:197, flat:197, mid:197, quiet:197, soft:171 |
| Memes (7) · poorjev | P80 | 454 | 0.932 / 0.968 | conf >= P80 | 0.948 | 93 (20.5%) | 47 | 93 | 41 (13) | 40 | 12 | 43.0% | deep:41, flat:41, mid:41, quiet:41, jumpy:35 |
| Memes (7) · poorjev | P90 | 454 | 0.932 / 0.968 | conf >= P90 | 0.954 | 46 (10.1%) | 22 | 46 | 19 (12) | 20 | 7 | 43.5% | deep:19, flat:19, loud:19, mid:19, quiet:19 |
| Memes (7) · poorjev | P95 | 454 | 0.932 / 0.968 | conf >= P95 | 0.957 | 23 (5.1%) | 10 | 23 | 13 (9) | 7 | 3 | 30.4% | deep:13, flat:13, loud:13, mid:13, quiet:13 |
| Memes (7) · poorjev+rules | barra fixa 0,8 | 359 | 0.930 / 0.968 | conf > 0.8 (barra fixa) | 0.800 | 358 (99.7%) | 63 | 358 | 138 (12) | 135 | 85 | 37.7% | deep:138, flat:138, mid:138, quiet:138, soft:120 |
| Memes (7) · poorjev+rules | P80 | 359 | 0.930 / 0.968 | conf >= P80 | 0.944 | 71 (19.8%) | 38 | 71 | 27 (10) | 27 | 17 | 38.0% | deep:27, flat:27, mid:27, quiet:27, jumpy:23 |
| Memes (7) · poorjev+rules | P90 | 359 | 0.930 / 0.968 | conf >= P90 | 0.950 | 38 (10.6%) | 27 | 38 | 12 (8) | 16 | 10 | 42.1% | deep:12, flat:12, mid:12, quiet:12, jumpy:8 |
| Memes (7) · poorjev+rules | P95 | 359 | 0.930 / 0.968 | conf >= P95 | 0.955 | 20 (5.6%) | 14 | 20 | 6 (5) | 8 | 6 | 40.0% | deep:6, flat:6, loud:6, mid:6, quiet:6 |
| Memes (7) · von | barra fixa 0,8 | 1216 | 0.295 / 0.395 | conf > 0.8 (barra fixa) | 0.800 | 0 (0.0%) | 0 | 0 | 0 (0) | 0 | 0 | – | – |
| Memes (7) · von | P80 | 1216 | 0.295 / 0.395 | conf >= P80 | 0.354 | 245 (20.1%) | 2 | 242 | 96 (51) | 100 | 46 | 41.3% | deep:96, flat:96, mid:96, quiet:96, soft:79 |
| Memes (7) · von | P90 | 1216 | 0.295 / 0.395 | conf >= P90 | 0.368 | 133 (10.9%) | 1 | 133 | 47 (32) | 55 | 31 | 41.4% | deep:47, flat:47, mid:47, quiet:47, fading:36 |
| Memes (7) · von | P95 | 1216 | 0.295 / 0.395 | conf >= P95 | 0.376 | 62 (5.1%) | 1 | 62 | 20 (17) | 26 | 16 | 41.9% | deep:20, fading:20, flat:20, mid:20, quiet:20 |

### Proposta resultante vs `criteria_v2.json` atual

Reescrita determinística (`propose_criteria`) a partir do grupo `SOL · von · baseline+relaxed`; frases só entram quando há erros confiantes.

| Variante | Erros confiantes | Frases acrescentadas | Igual ao `criteria_v2.json` atual? |
|---|---:|---|---|
| barra fixa 0,8 | 0 | — (texto base) | não |
| P80 | 1 | {"buy": ["be wary when the tape reads calm, deep, green"]} | não |
| P90 | 1 | {"buy": ["be wary when the tape reads calm, deep, green"]} | não |
| P95 | 1 | {"buy": ["be wary when the tape reads calm, deep, green"]} | não |

`criteria_v2.json` atual (gerado em 2026-09-24 04:00 com 0 trades auditados) tem as frases "prefer …" que a revisão antiga acrescentava sempre; com a regra nova, sem erros confiantes a proposta é o texto base, logo também difere dele.
