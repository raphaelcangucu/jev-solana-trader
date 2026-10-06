# Simulação retroativa, 30 dias

Run `20261006-0300`, janela de 6 set a 6 out de 2026 (horário de Brasília).

## Resumo

Nos últimos 30 dias quem mais lucrou foi FARTCOIN_poorjev_relaxed (+28,4%). Tirando o efeito do mercado, a maior habilidade foi de h2_ensemble_FARTCOIN (+US$ 82). 7 teste(s) passaram o critério de vencedora; o melhor é poorjev_relaxed__fork1.

## Contexto de mercado

| Ativo | Variação |
|---|---|
| SOL | -7.7% |
| WIF | +18.0% |
| BONK | -22.0% |
| FARTCOIN | +35.0% |
| POPCAT | -12.0% |
| GOAT | -30.0% |
| MEW | +4.0% |

## Como ler

- **Lucro**: quanto a carteira ganhou em 30 dias, em % dos US$ 1.000 iniciais.
- **Habilidade**: lucro menos o que a exposição média ao ativo teria rendido sozinha.
- **Veredito**: o mesmo critério do run ao vivo (habilidade com p < 0,05 e semanas consistentes).

## Limitações

1. Os modelos de hoje respondem sobre o passado: não sabemos se teriam respondido igual na época.
2. Liquidez de memecoins no minuto pode ser pior do que o slippage assumido.

```
python scripts/backtest_30d.py --days 30
```
