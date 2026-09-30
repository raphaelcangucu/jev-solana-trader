# jev-solana-trader

Bot local de teste de trades em Solana. O ciclo segue o padrão de alex saint (@alexsssaint) / System One: a cada ~15 segundos o mercado vira uma frase curta de adjetivos, um modelo escolhe `buy`, `sell` ou `hold`, e um veto `skip_this_cycle` pode anular o ciclo. O Jev hospedado da TypeSafe entra aqui como o modelo aberto **von** (`von-sdk`), em `POST /v1/systemone`. A troca, quando existe, é USDT ↔ SOL na Jupiter Ultra. O log do experimento é público e só cresce.

Carteira do experimento: `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`.

A comparação que escolheu o von está em `research/jev-alts/`. O livro de partida está em `docs/EXPERIMENT.md`.

Passagem de contexto (estado do projeto, laboratório de paper trading e próximos passos): `docs/HANDOFF.md`.

## Objetivo

Ver se um loop curto, com estado só em adjetivos e portões de confiança, melhora o resultado desse livro pequeno em relação a deixar o saldo da foto parado.

O ponto de partida, em 2026-09-23 por volta de 23:30 BRT, é **0.017392206 SOL + 50.00929 USDT**.

## Arquitetura

```text
preço, book, quote Jupiter, fees e saldos públicos
        → 12 adjetivos (nenhum número no texto do modelo)
        → POST /v1/systemone  (von serve; se cair, von.system_one no processo)
        → portões: skip alto ou confiança baixa viram hold
        → dry-run para por aqui
        → LIVE_TRADING=1: Jupiter GET /ultra/v1/order + POST /ultra/v1/execute
        → logs/decisions.jsonl e logs/trades.jsonl
```

Módulos em `src/jev_trader/`:

| Módulo | Função |
| --- | --- |
| `config.py` | Ambiente. O endereço público é fixo. A chave só entra por `SOLANA_KEYPAIR_PATH` na hora do swap. |
| `state.py` | Contas e a frase de doze adjetivos. |
| `decide.py` | Perguntas do artigo, cliente von, portões. |
| `swap.py` | Ordem e execução Ultra, assinatura só do taker. |
| `loop.py` | Um ciclo e os JSONL. |
| `__main__.py` | `python -m jev_trader --dry-run --once`. |

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

Dry-run é o padrão. `LIVE_TRADING` diferente de `1` também não envia swap. `--dry-run` ganha mesmo se `LIVE_TRADING=1`: o processo não abre o arquivo da chave.

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

Quatro números, calculados a partir dos logs e do saldo da carteira. O v0 não fecha esse placar sozinho; ele deixa o log para a conta.

1. **PnL contra segurar o livro.** Valor marcado a mercado agora (SOL × preço + USDT) menos o valor do livro inicial (0.017392206 SOL + 50.00929 USDT) no mesmo preço. O excedente é o que os swaps acrescentaram em relação a não ter operado depois da foto.
2. **Hit rate.** Entre os swaps com `ok: true` depois da linha seed, a fração em que o retorno do SOL nos 15 minutos seguintes tem o sinal do lado: compra quer alta, venda quer queda.
3. **Max drawdown.** Maior queda, do pico ao vale, da série de valor marcado a mercado. `sol_ui` e `usdt_ui` entram na decisão quando o RPC público responde.
4. **Número de trades.** Linhas de `logs/trades.jsonl` com `ok: true`, sem contar a linha seed do swap gasless.

## Reescrita noturna (desenho do v0, sem execução)

O artigo prevê um passe noturno que relê os casos com confiança acima de 0.8 que deram errado e reescreve os critérios. Neste repositório isso está só desenhado.

O passe futuro, pensado para 03:30 BRT:

1. Lê `logs/decisions.jsonl`.
2. Para cada ciclo com confiança > 0.8, ação `buy` ou `sell`, skip abaixo do portão e swap realmente enviado, compara `px_in` com o `px_in` de cerca de 15 minutos depois.
3. Erro: compra seguida de queda, ou venda seguida de alta, fora de uma banda pequena.
4. Agrupa os adjetivos desses erros e escreve `logs/rewrite_proposals/AAAA-MM-DD.json` com os critérios atuais, o texto proposto e `"status": "pending"`.

O portão humano:

- Nenhum processo carrega uma proposta sozinho.
- A pessoa lê o JSON e, num comando futuro `python -m jev_trader rewrite --approve <arquivo>`, promove o texto para `config/criteria.json` e anexa um registro de aprovação.
- Critério inválido ou proposta ainda `pending` não substitui o texto que está no ar.
- Enquanto isso não existe, as frases do artigo permanecem fixas em `decide.py`.

O v0 não tem o comando `rewrite`, não tem `config/criteria.json` e não altera o prompt de madrugada.

## Logs

`logs/trades.jsonl` começa com o swap gasless de 2 USDT → 0.017392206 SOL. `logs/decisions.jsonl` nasce no primeiro ciclo.

Campos da decisão, no espírito do artigo: `t`, `state`, `action`, `conf`, `skip`, `px_in`, `px_15m`. Em volta deles: motivo do portão, fonte da resposta (`von-http`, `von-local` ou `fail-closed`), `dry_run`, `submitted`, saldos públicos quando o RPC responde, e a carteira.

## O que este corte faz e o que fica de fora

Faz: estado em adjetivos, chamada HTTP ao von com fallback no processo, portões, dry-run sem chave, swap Ultra quando `LIVE_TRADING=1`, logs append-only.

Fica de fora: a reescrita noturna (só este desenho), painel de PnL, e qualquer envio de transação no dry-run.
