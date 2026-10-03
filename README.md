# jev-solana-trader

Bot local de teste de trades em Solana. O ciclo segue o padrão de alex saint (@alexsssaint) / System One: a cada ~15 segundos o mercado vira uma frase curta de adjetivos, um modelo escolhe `buy`, `sell` ou `hold`, e um veto `skip_this_cycle` pode anular o ciclo. O Jev hospedado da TypeSafe entra aqui como o modelo aberto **von** (`von-sdk`), em `POST /v1/systemone`. A troca, quando existe, é USDT ↔ SOL na Jupiter Ultra. O log do experimento é público e só cresce.

Carteira do experimento: `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`.

A comparação que escolheu o von está em `research/jev-alts/`. O livro de partida está em `docs/EXPERIMENT.md`.

Passagem de contexto (estado do projeto, laboratório de paper trading e próximos passos): `docs/HANDOFF.md`.

## Objetivo

Ver se um loop curto, com estado só em adjetivos e portões de confiança, melhora o resultado desse livro pequeno em relação a deixar o saldo da foto parado.

O ponto de partida, em 2026-09-23 por volta de 23:30 BRT, é **0.017392206 SOL + 50.00929 USDT**. O experimento foi reiniciado em **2026-09-30T00:50:19-03:00** com o mesmo livro, agora em **paper trading** (`config/experiment.json`, `run1_2026-09-30`, SOL de referência 119.305 USD). Os logs da execução anterior estão em `logs/archive/run0_2026-09-23/`.

## Arquitetura

```text
preço, book, quote Jupiter, fees e saldos públicos
        → 12 adjetivos (nenhum número no texto do modelo)
        → POST /v1/systemone  (von serve; se cair, von.system_one no processo)
        → portões: skip alto ou confiança baixa viram hold
        → dry-run: fill simulado no livro de papel (logs/paper_book.json, logs/paper_trades.jsonl)
        → LIVE_TRADING=1: Jupiter GET /ultra/v1/order + POST /ultra/v1/execute
        → logs/decisions.jsonl e logs/trades.jsonl
```

Módulos em `src/jev_trader/`:

| Módulo | Função |
| --- | --- |
| `config.py` | Ambiente. O endereço público é fixo. A chave só entra por `SOLANA_KEYPAIR_PATH` na hora do swap. |
| `state.py` | Contas e a frase de doze adjetivos. |
| `decide.py` | Perguntas do artigo (ou critérios aprovados), cliente von, portões. |
| `criteria.py` | Frases do artigo por omissão, leitura e validação de `config/criteria.json`. |
| `swap.py` | Ordem e execução Ultra, assinatura só do taker. |
| `paper.py` | Livro de papel: tamanho igual ao do swap ao vivo, fill ao `px_in` com custo em bps. |
| `experiment.py` | Início do run corrente (`config/experiment.json`). |
| `loop.py` | Um ciclo e os JSONL. |
| `score.py` | Placar dos quatro critérios de sucesso. |
| `rewrite.py` | Reescrita noturna com corte por percentil e portão humano. |
| `records.py` | JSONL, escrita atómica e relógio BRT. |
| `__main__.py` | `python -m jev_trader --dry-run --once`, `score`, `rewrite`. |

As doze palavras, nesta ordem:

| Slot | Palavra | Regra que fica no código |
| --- | --- | --- |
| depth | `thin` / `deep` | impacto de 1000 USDT > 0.006, ou quote ausente → `thin` |
| fees | `bot_war` / `quiet` | mediana da priority fee / 1000 microlamports > 2.5 → `bot_war` |
| move | `pumping` / `fading` / `dumping` / `flat` | retorno 15 min > 0.02, < −0.02, < −0.05, senão `flat` |
| vol | `violent` / `calm` | desvio dos retornos de 1 min > 0.008 → `violent` |
| shape | `flat` ou o move | abs(retorno) ≤ 0.02 → `flat` |
| color | `green` / `red` / `gray` / `yellow` | sinal do retorno; `yellow` se violento e quase parado |
| spread | `wide` / `tight` | (ask − bid) / mid > 0.002, ou book ausente → `wide` |
| tone | `harsh` / `calm` | fee de bot war e vol violenta juntos → `harsh` |
| phase | `early` / `mid` / `late` | posição do preço na faixa de 15 min |
| pocket | `early` / `mid` / `late` | a mesma faixa, com cortes mais extremos |
| noise | `loud` / `quiet` | o mesmo corte de volatilidade |
| inventory | `held` / `sold` / `bare` | viés SOL contra USDT; livro vazio → `bare` |

Perguntas mandadas ao modelo, iguais às do artigo:

- buy: “the move is strong and depth is not thin”
- sell: “the move is fading or fees are climbing”
- hold: “anything else”
- skip: “conditions are too hostile to trade at all”

Portões, também os do artigo:

1. Sem resposta utilizável do von → `hold`, motivo `fail_closed`.
2. Sem preço → `hold`, motivo `market_unavailable`.
3. `skip >= 0.55` → `hold`, motivo `skip`.
4. `confiança < 0.55` → `hold`, motivo `low_confidence`.
5. Escolha `hold` → não opera.
6. `buy` ou `sell` com confiança suficiente → pode operar. O tamanho é o valor de `BUY_USDT` ou `SELL_SOL` vezes a confiança, limitado por `MAX_BUY_USDT` (5) e `MAX_SELL_SOL` (0.01).

`px_in` no log é o preço na hora do ciclo. `px_15m` é o preço cerca de 15 minutos antes, o insumo do retorno. O preço de saída, para o hit rate, é o `px_in` de um ciclo posterior.

## Dry-run e ao vivo

Dry-run é o padrão e, nesta execução, o único modo em uso. `LIVE_TRADING` diferente de `1` também não envia swap. `--dry-run` ganha mesmo se `LIVE_TRADING=1`: o processo não abre o arquivo da chave.

### Paper trading

Em dry-run, quando os portões mandam executar (`buy` ou `sell` com confiança suficiente), o ciclo simula o trade num livro de papel em vez de não fazer nada:

- O livro vive em `logs/paper_book.json` (`sol`, `usdt`, `n_trades`, `updated_t`, `run_id`) e nasce do livro de `config/experiment.json` no primeiro ciclo. Um livro de outro `run_id` ou partido não é reescrito: o ciclo segue e o erro fica na decisão.
- Tamanho igual ao do swap ao vivo (`swap.order_size_ui`): compra de `BUY_USDT` × confiança, venda de `SELL_SOL` × confiança, com os tetos `MAX_BUY_USDT` e `MAX_SELL_SOL`. Depois disso, limitado pelo saldo do livro. Se o que sobra é pó (menos de 0.01 USDT ou 0.0001 SOL), não há fill e o motivo fica em `paper_reason` (`insufficient_usdt` ou `insufficient_sol`).
- Preço: o `px_in` do ciclo, com `PAPER_COST_BPS` (10 por omissão) de slippage + fee contra o trader. Compra a `px_in × (1 + bps/10000)`, venda a `px_in × (1 − bps/10000)`. O fill é marcado `fill_mode: "mark"`; não há cotação Jupiter ao tamanho da ordem.
- Cada fill entra em `logs/paper_trades.jsonl` com `t`, `run_id`, `decision_t`, lado, confiança, `px_in`, `fill_px`, quantidades de entrada e saída, `cost_bps` e o livro depois do fill.
- A decisão ganha `paper`, `paper_fill`, `paper_reason`, `paper_sol`, `paper_usdt` e `run_id`. Todos os ciclos em dry-run gravam o livro de papel, mesmo sem trade; é dele que sai a série de valor marcado a mercado.
- Ao vivo (`LIVE_TRADING=1` sem `--dry-run`) não há livro de papel: `paper` é `false` e o swap segue o caminho de sempre.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
python -m jev_trader --dry-run --once
```

O ciclo imprime um JSON por linha e acrescenta o mesmo objeto em `logs/decisions.jsonl`. Se o `von serve` não está no ar e o pacote `von` não importa, a linha é um hold `fail_closed`. Isso é o comportamento esperado, não um crash.

O `von-sdk` pede Python 3.12+ (ele puxa o torch). O ciclo em si roda em Python 3.10+. Num 3.12+:

```bash
von serve --model von-1.2 --port 8000
```

Ao vivo, noutro terminal, com a chave só na máquina do operador:

```bash
export SOLANA_KEYPAIR_PATH=/caminho/local/keypair.json
export LIVE_TRADING=1
python -m jev_trader --once
```

Sem `--once`, o processo repete a cada `LOOP_SECONDS` (15).

Os subcomandos `score` e `rewrite` (abaixo) não mudam o ciclo: `python -m jev_trader --dry-run --once` e `python -m jev_trader --once` continuam iguais.

## Segurança da carteira

- O repositório guarda o endereço público. Chave, `keypair.json`, `secret.b58`, seed e `.env` ficam de fora do git.
- `SOLANA_KEYPAIR_PATH` é lido só na hora de um swap ao vivo. O dry-run não abre esse arquivo.
- A pubkey do arquivo tem de ser `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`. Outro endereço não opera.
- `HOT_WALLET_ADDRESS` no ambiente, se apontar para outra carteira, também bloqueia o swap.
- Teto por ciclo: 5 USDT na compra e 0.01 SOL na venda, antes da escala pela confiança.
- Swap gasless tem dois signatários. O gas payer da Jupiter é o primeiro; o taker é o segundo. O código assina a mensagem com `solders.message.to_bytes_versioned` e remonta com `VersionedTransaction.populate`, escrevendo só o slot do taker. O slot do payer continua `Signature.default()` quando a Jupiter ainda não assinou; uma assinatura que já veio nesse slot é mantida. O construtor que assinaria o taker como primeiro signatário não é usado.
- Quando o taker é o único signatário (a Jupiter devolveu `gasless: false` e `signatureFeePayer` igual à carteira), o único slot recebe a assinatura do taker.
- Erros gravados no JSONL não incluem o conteúdo da chave. Uma API key da Jupiter, se existir no ambiente, é removida do texto do erro.

## Critérios de sucesso

Quatro números, calculados para o **livro de papel** a partir dos logs desde `start_t` de `config/experiment.json`:

```bash
python -m jev_trader score                 # tabela
python -m jev_trader score --json          # JSON
python -m jev_trader score --since 2026-09-30T12:00:00-03:00
```

1. **PnL contra segurar o livro.** Livro de papel marcado no último `px_in` menos o livro inicial (0.017392206 SOL + 50.00929 USDT) marcado no mesmo preço, em USD e em %. O excedente é o que os trades acrescentaram em relação a não ter operado. Ao lado, o PnL simples do livro de papel contra o valor inicial no preço de referência (119.305 USD/SOL).
2. **Hit rate a 15 min.** Para cada fill de papel, o `px_in` da primeira decisão com `t` entre +15 e +20 minutos. Compra quer alta, venda quer queda; retorno zero conta como erro. Sem decisão com preço nesse intervalo, o fill fica "por resolver" e sai do denominador.
3. **Max drawdown.** Maior queda, do pico ao vale, da série livro de papel depois de cada decisão × `px_in` dessa decisão, em USD e em % do pico.
4. **Número de trades.** Linhas de `logs/paper_trades.jsonl` do run, separadas em compras e vendas.

`--since` limita os números 2, 3 e 4 a uma janela. O PnL (1) é sempre desde o início do run.

## Reescrita noturna

O artigo prevê um passe noturno que relê os casos confiantes que deram errado e reescreve os critérios. A barra fixa do artigo (confiança > 0.8) não serve para o von: as confianças dele concentram-se em ~0.2–0.45 e nunca passam 0.8. O corte aqui é um **percentil** das confianças observadas.

Proposta, pensada para 03:30 BRT:

```bash
python -m jev_trader rewrite --propose --date 2026-09-30          # um dia BRT
python -m jev_trader rewrite --propose                            # tudo desde start_t
python -m jev_trader rewrite --propose --percentile 90 --fixed 0.8 --band 0.001
```

1. Lê `logs/decisions.jsonl` do run e fica com as decisões em que o von respondeu (fonte diferente de `fail-closed`, `model_action` presente).
2. Corte = percentil P (90 por omissão) dessas confianças, pelo método **nearest-rank**: com as n confianças ordenadas, o valor na posição ⌈P/100 × n⌉. O corte é sempre uma confiança observada.
3. Confiante = confiança ≥ corte e ação final `buy` ou `sell`, isto é, passou os portões. Em paper trading não há swap real, por isso as decisões de dry-run contam. Com `CONFIDENCE_THRESHOLD` em 0.55 e o von em ~0.2–0.45, nenhuma decisão passa os portões e a auditoria sai vazia; a auditoria regista quantas escolhas `buy`/`sell` acima do corte foram bloqueadas.
4. Erro: compra seguida de retorno abaixo de −banda, ou venda seguida de retorno acima de +banda (banda 0.001 = 0.1%), com o `px_in` da decisão entre +15 e +20 minutos, a mesma regra do hit rate.
5. A mesma conta com a barra fixa (`--fixed`, 0.8) entra na proposta em `audit.fixed`, só para comparação. O texto proposto sai de `audit.percentile`.
6. Reescrita determinística: para cada lado, as palavras de estado que aparecem em pelo menos metade dos erros disparam frases fixas (por exemplo `thin` numa compra errada acrescenta “only when depth is deep not thin” ao critério de compra). Sem erros, a proposta é igual aos critérios atuais e vem com `"changed": false`. Frase já presente não se repete.
7. Escreve `logs/rewrite_proposals/AAAA-MM-DD.json` (dia revisto, ou o dia BRT corrente sem `--date`) com critérios atuais, propostos, auditoria e `"status": "pending"`. Uma proposta já aprovada ou rejeitada nesse dia não é sobrescrita.

O portão humano:

```bash
python -m jev_trader rewrite --approve logs/rewrite_proposals/2026-09-30.json [--by nome]
python -m jev_trader rewrite --reject  logs/rewrite_proposals/2026-09-30.json [--by nome]
```

- Nenhum processo carrega uma proposta sozinho.
- `--approve` só aceita proposta `pending`, com `buy`, `sell`, `hold` e `skip` em texto não vazio, sem dígitos (o modelo nunca vê números) e com até 400 caracteres cada, feita sobre os critérios que estão no ar. Promove o texto para `config/criteria.json` com escrita atómica, marca a proposta `approved` com `approved_t` e anexa a `logs/rewrite_approvals.jsonl` o instante, o arquivo, o sha256 de `config/criteria.json` e quem aprovou (`--by`, senão `$USER`).
- Proposta inválida sai com código diferente de zero e nada muda.
- `--reject` marca a proposta `rejected` e também deixa uma linha em `logs/rewrite_approvals.jsonl`.
- `decide.py` lê `config/criteria.json` a cada ciclo. Ficheiro ausente, partido ou inválido → as frases do artigo, fixas no código. O repositório não traz `config/criteria.json`.

## Logs

Cada execução começa com a pasta `logs/` vazia; os ficheiros nascem no primeiro ciclo. A execução 0, com a linha seed do swap gasless de 2 USDT → 0.017392206 SOL em `trades.jsonl`, está em `logs/archive/run0_2026-09-23/`.

| Ficheiro | Conteúdo |
| --- | --- |
| `decisions.jsonl` | Uma linha por ciclo. |
| `trades.jsonl` | Swaps ao vivo (vazio em paper). |
| `paper_book.json` | Livro de papel corrente. |
| `paper_trades.jsonl` | Fills de papel. |
| `rewrite_proposals/AAAA-MM-DD.json` | Propostas da reescrita noturna. |
| `rewrite_approvals.jsonl` | Aprovações e rejeições. |

Campos da decisão, no espírito do artigo: `t`, `state`, `action`, `conf`, `skip`, `px_in`, `px_15m`. Em volta deles: motivo do portão, fonte da resposta (`von-http`, `von-local` ou `fail-closed`), `dry_run`, `submitted`, saldos públicos quando o RPC responde, a carteira e, em dry-run, os campos do livro de papel (`paper`, `paper_fill`, `paper_reason`, `paper_sol`, `paper_usdt`, `run_id`).

## O que este corte faz e o que fica de fora

Faz: estado em adjetivos, chamada HTTP ao von com fallback no processo, portões, dry-run sem chave com paper trading no livro de papel, swap Ultra quando `LIVE_TRADING=1`, logs append-only, placar dos quatro critérios (`score`), reescrita noturna com corte por percentil e aprovação humana (`rewrite --propose/--approve/--reject`).

Fica de fora: agendamento da reescrita (o comando corre quando alguém o chama, por exemplo num cron às 03:30), fill de papel com cotação Jupiter ao tamanho da ordem, painel de PnL, e qualquer envio de transação no dry-run.
