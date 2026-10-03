# Experimento — livro inicial

## Execução 1 — reinício em paper trading (2026-09-30)

Início: **2026-09-30T00:50:19-03:00** (America/Sao_Paulo). `run_id`: `run1_2026-09-30`. Modo: **paper**.

Carteira pública: `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`, lida por RPC público sem chave no slot **451848237**.

| Ativo | Quantidade |
| --- | ---: |
| SOL | 0.017392206 |
| USDT | 50.00929 |

O saldo é o mesmo da foto de 2026-09-23: nenhum swap real aconteceu entre as duas datas. Preço de referência do SOL no reinício: **119.305 USD** (Coinbase spot), o que dá cerca de 52.084 USD para o livro.

Estes números estão em `config/experiment.json`, que o bot lê para iniciar o livro de papel e o placar.

O que muda nesta execução:

- O bot corre só em dry-run. Quando os portões mandam executar, o fill é simulado num livro de papel (`logs/paper_book.json`, `logs/paper_trades.jsonl`) com o mesmo tamanho que o swap ao vivo teria, ao `px_in` do ciclo com um custo de `PAPER_COST_BPS` (10 bps por omissão) contra o trader. A carteira real não se mexe.
- O placar dos quatro critérios de sucesso sai de `python -m jev_trader score`.
- A reescrita noturna existe (`python -m jev_trader rewrite --propose`), com corte de confiança por percentil e aprovação humana.

Os logs da execução 0 foram arquivados sem alterações em `logs/archive/run0_2026-09-23/` (`decisions.jsonl` com os dois ciclos `fail_closed` de 2026-09-24 e `trades.jsonl` com a linha seed do swap gasless). Os logs novos nascem vazios no primeiro ciclo.

## Execução 0 — foto de 2026-09-23 (histórico)

Data da foto: **2026-09-23, cerca de 23:30 America/Sao_Paulo**.

Carteira pública: `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`.

### Estado de partida

| Ativo | Quantidade |
| --- | ---: |
| SOL | 0.017392206 |
| USDT | 50.00929 |

Esse par é o livro contra o qual o PnL do loop é medido. “Só segurar USDT” no critério de sucesso usa este mesmo livro, marcado a mercado no preço corrente do SOL, sem novos swaps depois da foto.

### Como o livro chegou aqui

1. **Depósito de cerca de 10 USDT.**  
   Transação `5UUY8TSN2d9Das9mkSyeUw93GovCg4KAmJ2XsNsCTA6fPXExk7efE7S5y1ZVAhuuhqjBwn8wRy6mejYrWDomxyjD`.  
   https://solscan.io/tx/5UUY8TSN2d9Das9mkSyeUw93GovCg4KAmJ2XsNsCTA6fPXExk7efE7S5y1ZVAhuuhqjBwn8wRy6mejYrWDomxyjD

2. **Swap gasless de 2 USDT para 0.017392206 SOL.**  
   Transação `3AKqGKjnAavB8P1o5CUqhB3GMQG2BBqZt6ZKoby7krYPsZ9zs3HUv1mrrf7FWt8NX4yVVtEwtXqnxbB9oe2xfvL3`.  
   https://solscan.io/tx/3AKqGKjnAavB8P1o5CUqhB3GMQG2BBqZt6ZKoby7krYPsZ9zs3HUv1mrrf7FWt8NX4yVVtEwtXqnxbB9oe2xfvL3  
   A taxa de rede saiu do próprio swap (gasless): o saldo de SOL depois do swap é o saldo da foto. Esta linha está semeada em `logs/trades.jsonl` (hoje em `logs/archive/run0_2026-09-23/trades.jsonl`).

3. **Reforço de cerca de 42 USDT.**  
   10 − 2 + ~42 fecha em 50.00929 USDT. A assinatura desse reforço não entrou no relato de partida; o número que vale para o experimento é o saldo da foto.

### O que o loop fazia

Cada ciclo de cerca de 15 segundos lê o mercado, monta doze adjetivos, pergunta ao von e, só com `LIVE_TRADING=1` e sem `--dry-run`, pode trocar USDT e SOL na Jupiter Ultra. As decisões entram em `logs/decisions.jsonl`. Swaps novos entram no fim de `logs/trades.jsonl`, sem reescrever a linha seed.
