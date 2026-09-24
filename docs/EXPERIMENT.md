# Experimento — livro inicial

Data da foto: **2026-09-23, cerca de 23:30 America/Sao_Paulo**.

Carteira pública: `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`.

## Estado de partida

| Ativo | Quantidade |
| --- | ---: |
| SOL | 0.017392206 |
| USDT | 50.00929 |

Esse par é o livro contra o qual o PnL do loop é medido. “Só segurar USDT” no critério de sucesso usa este mesmo livro, marcado a mercado no preço corrente do SOL, sem novos swaps depois da foto.

## Como o livro chegou aqui

1. **Depósito de cerca de 10 USDT.**  
   Transação `5UUY8TSN2d9Das9mkSyeUw93GovCg4KAmJ2XsNsCTA6fPXExk7efE7S5y1ZVAhuuhqjBwn8wRy6mejYrWDomxyjD`.  
   https://solscan.io/tx/5UUY8TSN2d9Das9mkSyeUw93GovCg4KAmJ2XsNsCTA6fPXExk7efE7S5y1ZVAhuuhqjBwn8wRy6mejYrWDomxyjD

2. **Swap gasless de 2 USDT para 0.017392206 SOL.**  
   Transação `3AKqGKjnAavB8P1o5CUqhB3GMQG2BBqZt6ZKoby7krYPsZ9zs3HUv1mrrf7FWt8NX4yVVtEwtXqnxbB9oe2xfvL3`.  
   https://solscan.io/tx/3AKqGKjnAavB8P1o5CUqhB3GMQG2BBqZt6ZKoby7krYPsZ9zs3HUv1mrrf7FWt8NX4yVVtEwtXqnxbB9oe2xfvL3  
   A taxa de rede saiu do próprio swap (gasless): o saldo de SOL depois do swap é o saldo da foto. Esta linha está semeada em `logs/trades.jsonl`.

3. **Reforço de cerca de 42 USDT.**  
   10 − 2 + ~42 fecha em 50.00929 USDT. A assinatura desse reforço não entrou no relato de partida; o número que vale para o experimento é o saldo da foto.

## O que o loop passa a fazer

Cada ciclo de cerca de 15 segundos lê o mercado, monta doze adjetivos, pergunta ao von e, só com `LIVE_TRADING=1` e sem `--dry-run`, pode trocar USDT e SOL na Jupiter Ultra. As decisões entram em `logs/decisions.jsonl`. Swaps novos entram no fim de `logs/trades.jsonl`, sem reescrever a linha seed.
