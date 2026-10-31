# Von relaxado em moedas novas — o que daria?

Gerado (BRT): 2026-10-17T20:47:18-03:00 · paper only (nenhuma ordem, nenhuma chave) · runs: `bt30x_2026-10-06` e `bt180x_2026-10-06` (moedas novas) contra `bt30_2026-10-06` e `bt180_2026-10-06` (as 7 memecoins atuais, mesma janela e mesmos parâmetros).

**Pergunta:** se aplicarmos o von relaxado (`meme_<SYM>_relaxed`: von, perfil relaxed — confiança ≥ 0,35, margem ≥ 0,20, skip < 0,5) a outras memecoins e moedas Solana negociáveis na Jupiter, qual seria o resultado, e algum fork novo se justifica?

## Resposta curta

**Nenhuma das 8 moedas novas passa a regra.** O von relaxado perde também nelas: PnL mediano em 180 dias -42.57% (as 7 atuais: -35.79%), habilidade positiva em 0/8 (nenhuma) e a bater o só segurar em 0/8 (nenhuma). A melhor foi JTO (habilidade -211.29 $, PnL -19.33%, PnL > 0 em 1/6 meses). Não recomendo nenhum fork von relaxado ao vivo com estas moedas.

**Porquê:** quase toda a perda é custo de execução. Em 180 dias o von relaxado faz 622–1244 trades por moeda e paga 173–614 US$ sobre a marca (de 1000 US$). Antes de custos a habilidade fica perto de zero (-110 a +59 US$; positiva só em JTO, POPCAT): o modelo não mostra vantagem de timing que pague os custos, nem nas moedas novas nem nas atuais. Trocar de moeda não muda isto.

Nas 7 memecoins atuais a mesma regra dá: nenhuma passa (referência).

## Regra de passagem

Só a janela de 180 dias decide. Uma moeda **passa** se o von relaxado nela tem, nos 180 dias: (1) habilidade > 0 (excesso ajustado à exposição: o PnL menos o que a exposição média ao ativo teria rendido), (2) excesso vs só segurar > 0 (PnL acima do buy & hold da moeda), e (3) PnL > 0 em ≥ 3 dos 6 blocos de 30 dias (contados do fim da janela). A janela de 30 dias e o veredito estatístico do run (bate B&H com p < 0,05, ≥ 30 round trips, consistência) ficam como informação; com 180 dias e ~1000 trades por moeda o veredito estatístico é mais exigente que esta regra.

## Moedas, mints e dados

Mints conferidos em 3 fontes públicas (Jupiter tokens v2 — `isVerified`, decimais, programa SPL Token; CoinGecko `platforms.solana` e decimais; DexScreener — `baseToken.address` dos pares Solana). Velas de 1 m de CEX spot; fonte escolhida pela cobertura e pela correlação com a Gate.io (fonte da marcação ao vivo das memecoins). A Gate.io só guarda ~7 dias de 1 m (depois do fim destas janelas), por isso a correlação é a dos retornos de 1 h com as barras de 1 h da Gate.io dentro da janela. Todas as moedas estavam listadas antes do início da janela de 180 dias (2026-04-09): cobertura total, sem janela parcial.

| Moeda | Mint | Dec. | Fonte 1 m (30 d / 180 d) | Cobertura 30 d | Cobertura 180 d | Corr. 1 h vs Gate.io (180 d) | Retorno 30 d | Retorno 180 d | Custo assumido (bps) | Liquidez on-chain US$ |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| JUP | `JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN` | 6 | bybit:JUPUSDT / bybit:JUPUSDT | 100.00% | 100.00% | 0.9854 | +28.81% | +119.48% | 12.7 | 16.1 M |
| JTO | `jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL` | 9 | bybit:JTOUSDT / bybit:JTOUSDT | 100.00% | 100.00% | 0.9948 | +26.10% | +107.58% | 12.7 | 11.9 M |
| PYTH | `HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3` | 6 | bybit:PYTHUSDT / bybit:PYTHUSDT | 100.00% | 100.00% | 0.9851 | +43.60% | +81.39% | 32.8 | 0.7 M |
| RAY | `4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R` | 6 | okx:RAY-USDT / okx:RAY-USDT | 100.00% | 100.00% | 0.9797 | +90.84% | +253.90% | 12.7 | 16.0 M |
| BOME | `ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82` | 6 | bybit:BOMEUSDT / bybit:BOMEUSDT | 100.00% | 100.00% | 0.9856 | +9.31% | +160.02% | 12.7 | 13.3 M |
| PENGU | `2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv` | 6 | bybit:PENGUUSDT / bybit:PENGUUSDT | 100.00% | 100.00% | 0.9965 | +8.76% | +51.21% | 12.7 | 8.0 M |
| TRUMP | `6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN` | 6 | bybit:TRUMPUSDT / bybit:TRUMPUSDT | 100.00% | 100.00% | 0.9978 | -14.19% | -30.57% | 12.7 | 21.5 M |
| MOODENG | `ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY` | 6 | okx:MOODENG-USDT / okx:MOODENG-USDT | 100.00% | 100.00% | 0.9468 | +4.18% | -3.23% | 32.8 | 2.5 M |

Fontes: Candidatas de 1 m: Bybit e KuCoin (as fontes das memecoins atuais); OKX onde a Bybit spot não tem o par (RAY, MOODENG). Binance spot existe para 7 das 8 (não MOODENG) mas ficou fora: a API pública de velas respondeu a ~4 s por pedido a partir desta máquina (~2 h só para descarregar), e 2 candidatas por moeda chegam para a escolha por cobertura e correlação. Correlação 1 h de cada candidata no `summary.json` (`assets.<SYM>.basis.candidates`).

Custos: Sem fills ao vivo destas moedas. Custo sobre a marca (antes do extra de 5 bps que o código soma) = mediana do custo medido nas 7 memecoins atuais (bt30_2026-10-06: BONK 1,4 · FARTCOIN 5,8 · WIF 8,5 · POPCAT 12,7 · MEW 24,3 · GOAT 29,8 · PNUT 32,8 → 12,7 bps). Moedas com liquidez on-chain (DexScreener, soma dos pares Solana; a API devolve no máximo 30 pares, por isso é um limite inferior) abaixo da da PNUT (~3,1 M US$, a mais cara das atuais) ficam com o custo da PNUT, 32,8 bps (conservador): PYTH e MOODENG.

Chamadas novas aos modelos (servidores próprios 8865–8867, nice 15, 2 threads, 1 worker): poorjev 140, von 152 (o resto veio da cache: os estados são só palavras, por isso muitos já tinham sido vistos nas memecoins atuais). Duração: bt30x_2026-10-06 10.8 min, bt180x_2026-10-06 67.3 min.

## 180 dias (2026-04-09 → 2026-10-06, 09:00 BRT) — moedas novas

| Moeda | Estratégia | PnL % | vs segurar $ | Habilidade $ | Trades | MDD % | Meses PnL>0 · >B&H | Veredito |
|---|---|---:|---:|---:|---:|---:|---:|---|
| JUP | **von relaxado** | -38.15 | -1576.36 | -403.36 | 928 | -38.2 | 0/6 · 2/6 | inconclusiva |
| JUP | von artigo | +0.00 | -1194.85 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| JUP | poorjev + saídas (H1) | +0.05 | -1194.35 | -978.33 | 4379 | -53.0 | 4/6 · 1/6 | perdedora |
| JUP | só segurar | +119.48 | – | – | 0 | -44.4 | – | – |
| JTO | **von relaxado** | -19.33 | -1269.08 | -211.29 | 628 | -19.4 | 1/6 · 3/6 | inconclusiva |
| JTO | von artigo | +0.00 | -1075.81 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| JTO | poorjev + saídas (H1) | -51.89 | -1594.74 | -1572.05 | 7142 | -79.9 | 2/6 · 2/6 | inconclusiva |
| JTO | só segurar | +107.58 | – | – | 0 | -53.1 | – | – |
| PYTH | **von relaxado** | -57.95 | -1393.38 | -594.18 | 850 | -58.1 | 0/6 · 1/6 | perdedora |
| PYTH | von artigo | +0.00 | -813.92 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| PYTH | poorjev + saídas (H1) | -76.90 | -1582.87 | -1571.07 | 4590 | -82.2 | 1/6 · 2/6 | perdedora |
| PYTH | só segurar | +81.39 | – | – | 0 | -51.2 | – | – |
| RAY | **von relaxado** | -44.23 | -2981.34 | -482.29 | 1051 | -44.9 | 1/6 · 1/6 | perdedora |
| RAY | von artigo | +0.00 | -2539.00 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| RAY | poorjev + saídas (H1) | +108.26 | -1456.44 | -395.67 | 4687 | -48.4 | 4/6 · 1/6 | perdedora |
| RAY | só segurar | +253.90 | – | – | 0 | -38.2 | – | – |
| BOME | **von relaxado** | -28.66 | -1886.81 | -309.37 | 622 | -28.7 | 0/6 · 1/6 | inconclusiva |
| BOME | von artigo | +0.00 | -1600.21 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| BOME | poorjev + saídas (H1) | -30.34 | -1903.57 | -1640.41 | 6074 | -60.4 | 2/6 · 0/6 | inconclusiva |
| BOME | só segurar | +160.02 | – | – | 0 | -46.4 | – | – |
| PENGU | **von relaxado** | -40.90 | -921.18 | -423.73 | 1027 | -40.9 | 0/6 · 2/6 | inconclusiva |
| PENGU | von artigo | +0.00 | -512.13 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| PENGU | poorjev + saídas (H1) | -61.86 | -1130.73 | -1236.04 | 4730 | -78.2 | 2/6 · 1/6 | perdedora |
| PENGU | só segurar | +51.21 | – | – | 0 | -51.3 | – | – |
| TRUMP | **von relaxado** | -46.25 | -156.83 | -460.15 | 1244 | -46.3 | 0/6 · 3/6 | inconclusiva |
| TRUMP | von artigo | +0.00 | +305.69 | +0.00 | 0 | 0.0 | 0/6 · 5/6 | inconclusiva |
| TRUMP | poorjev + saídas (H1) | -73.88 | -433.07 | -654.69 | 3393 | -76.6 | 0/6 · 1/6 | inconclusiva |
| TRUMP | só segurar | -30.57 | – | – | 0 | -55.7 | – | – |
| MOODENG | **von relaxado** | -62.75 | -595.16 | -632.10 | 974 | -62.7 | 0/6 · 1/6 | inconclusiva |
| MOODENG | von artigo | +0.00 | +32.33 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| MOODENG | poorjev + saídas (H1) | -84.10 | -808.65 | -1037.77 | 3890 | -86.4 | 0/6 · 2/6 | perdedora |
| MOODENG | só segurar | -3.23 | – | – | 0 | -50.8 | – | – |

## 180 dias — as 7 memecoins atuais (referência, bt180_2026-10-06)

| Moeda | Estratégia | PnL % | vs segurar $ | Habilidade $ | Trades | MDD % | Meses PnL>0 · >B&H | Veredito |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BONK | **von relaxado** | -25.29 | +89.43 | -248.40 | 1176 | -25.4 | 0/6 · 3/6 | inconclusiva |
| BONK | von artigo | +0.00 | +342.31 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| BONK | poorjev + saídas (H1) | -56.57 | -223.34 | -381.66 | 3942 | -74.5 | 3/6 · 1/6 | inconclusiva |
| BONK | só segurar | -34.23 | – | – | 0 | -71.5 | – | – |
| WIF | **von relaxado** | -35.79 | -685.67 | -370.34 | 1129 | -35.8 | 0/6 · 2/6 | inconclusiva |
| WIF | von artigo | +0.00 | -327.74 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| WIF | poorjev + saídas (H1) | -48.33 | -811.07 | -973.64 | 4194 | -62.2 | 2/6 · 0/6 | perdedora |
| WIF | só segurar | +32.77 | – | – | 0 | -46.6 | – | – |
| POPCAT | **von relaxado** | -35.04 | -426.58 | -357.79 | 1018 | -37.8 | 0/6 · 1/6 | inconclusiva |
| POPCAT | von artigo | +0.00 | -76.20 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| POPCAT | poorjev + saídas (H1) | -54.37 | -619.89 | -840.98 | 4287 | -66.8 | 2/6 · 0/6 | perdedora |
| POPCAT | só segurar | +7.62 | – | – | 0 | -49.0 | – | – |
| FARTCOIN | **von relaxado** | -20.76 | -191.93 | -212.72 | 744 | -21.2 | 0/6 · 3/6 | inconclusiva |
| FARTCOIN | von artigo | +0.00 | +15.69 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| FARTCOIN | poorjev + saídas (H1) | -49.92 | -483.55 | -792.75 | 6044 | -68.8 | 3/6 · 2/6 | inconclusiva |
| FARTCOIN | só segurar | -1.57 | – | – | 0 | -60.7 | – | – |
| PNUT | **von relaxado** | -63.58 | -947.79 | -646.74 | 938 | -63.6 | 0/6 · 1/6 | inconclusiva |
| PNUT | von artigo | +0.00 | -312.01 | +0.00 | 0 | 0.0 | 0/6 · 2/6 | inconclusiva |
| PNUT | poorjev + saídas (H1) | -76.58 | -1077.82 | -1268.14 | 3772 | -83.0 | 1/6 · 1/6 | inconclusiva |
| PNUT | só segurar | +31.20 | – | – | 0 | -49.4 | – | – |
| MEW | **von relaxado** | -56.86 | -488.60 | -571.13 | 1026 | -56.9 | 0/6 · 1/6 | inconclusiva |
| MEW | von artigo | +0.00 | +80.03 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| MEW | poorjev + saídas (H1) | -76.69 | -686.89 | -854.19 | 3105 | -80.1 | 1/6 · 1/6 | perdedora |
| MEW | só segurar | -8.00 | – | – | 0 | -56.0 | – | – |
| GOAT | **von relaxado** | -57.98 | -685.83 | -588.40 | 849 | -58.0 | 0/6 · 1/6 | inconclusiva |
| GOAT | von artigo | +0.00 | -106.06 | +0.00 | 0 | 0.0 | 0/6 · 3/6 | inconclusiva |
| GOAT | poorjev + saídas (H1) | -81.56 | -921.69 | -1146.79 | 3970 | -83.6 | 0/6 · 0/6 | perdedora |
| GOAT | só segurar | +10.61 | – | – | 0 | -51.1 | – | – |

## 30 dias (2026-09-06 → 2026-10-06, 09:00 BRT) — moedas novas

| Moeda | Estratégia | PnL % | vs segurar $ | Habilidade $ | Trades | MDD % | Semanas > B&H | Veredito |
|---|---|---:|---:|---:|---:|---:|---:|---|
| JUP | **von relaxado** | -4.58 | -333.88 | -47.92 | 76 | -4.7 | 1/4 | inconclusiva |
| JUP | von artigo | +0.00 | -288.09 | +0.00 | 0 | 0.0 | 1/4 | inconclusiva |
| JUP | poorjev + saídas (H1) | +1.93 | -268.79 | -274.18 | 965 | -28.2 | 0/4 | perdedora |
| JUP | só segurar | +28.81 | – | – | 0 | -23.9 | – | – |
| JTO | **von relaxado** | -2.07 | -281.62 | -23.79 | 69 | -2.5 | 0/4 | inconclusiva |
| JTO | von artigo | +0.00 | -260.96 | +0.00 | 0 | 0.0 | 0/4 | inconclusiva |
| JTO | poorjev + saídas (H1) | +0.41 | -256.87 | -264.88 | 1064 | -25.1 | 1/4 | perdedora |
| JTO | só segurar | +26.10 | – | – | 0 | -22.0 | – | – |
| PYTH | **von relaxado** | -7.14 | -507.39 | -76.44 | 86 | -7.6 | 0/4 | inconclusiva |
| PYTH | von artigo | +0.00 | -436.03 | +0.00 | 0 | 0.0 | 0/4 | inconclusiva |
| PYTH | poorjev + saídas (H1) | +1.04 | -425.60 | -384.90 | 975 | -24.2 | 0/4 | perdedora |
| PYTH | só segurar | +43.60 | – | – | 0 | -15.4 | – | – |
| RAY | **von relaxado** | -0.09 | -909.29 | -3.37 | 27 | -0.9 | 0/4 | inconclusiva |
| RAY | von artigo | +0.00 | -908.42 | +0.00 | 0 | 0.0 | 0/4 | inconclusiva |
| RAY | poorjev + saídas (H1) | +51.75 | -390.92 | -158.24 | 2024 | -31.7 | 0/4 | inconclusiva |
| RAY | só segurar | +90.84 | – | – | 0 | -29.5 | – | – |
| BOME | **von relaxado** | -7.06 | -163.68 | -72.91 | 138 | -7.9 | 2/4 | inconclusiva |
| BOME | von artigo | +0.00 | -93.12 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| BOME | poorjev + saídas (H1) | -15.24 | -245.50 | -285.41 | 848 | -30.6 | 0/4 | perdedora |
| BOME | só segurar | +9.31 | – | – | 0 | -23.6 | – | – |
| PENGU | **von relaxado** | -6.63 | -153.87 | -68.38 | 142 | -6.9 | 2/4 | inconclusiva |
| PENGU | von artigo | +0.00 | -87.58 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| PENGU | poorjev + saídas (H1) | -11.46 | -202.23 | -243.36 | 1125 | -34.0 | 1/4 | inconclusiva |
| PENGU | só segurar | +8.76 | – | – | 0 | -24.4 | – | – |
| TRUMP | **von relaxado** | -7.59 | +65.97 | -74.18 | 144 | -7.6 | 2/4 | inconclusiva |
| TRUMP | von artigo | +0.00 | +141.89 | +0.00 | 0 | 0.0 | 3/4 | inconclusiva |
| TRUMP | poorjev + saídas (H1) | -22.63 | -84.39 | -119.23 | 686 | -29.6 | 1/4 | inconclusiva |
| TRUMP | só segurar | -14.19 | – | – | 0 | -23.0 | – | – |
| MOODENG | **von relaxado** | -10.46 | -146.38 | -106.30 | 143 | -10.8 | 1/4 | inconclusiva |
| MOODENG | von artigo | +0.00 | -41.77 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| MOODENG | poorjev + saídas (H1) | -33.48 | -376.61 | -420.34 | 796 | -37.3 | 0/4 | perdedora |
| MOODENG | só segurar | +4.18 | – | – | 0 | -18.8 | – | – |

## 30 dias — as 7 memecoins atuais (referência, bt30_2026-10-06)

| Moeda | Estratégia | PnL % | vs segurar $ | Habilidade $ | Trades | MDD % | Semanas > B&H | Veredito |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BONK | **von relaxado** | -1.05 | -154.72 | -12.97 | 107 | -2.1 | 1/4 | inconclusiva |
| BONK | von artigo | +0.00 | -144.20 | +0.00 | 0 | 0.0 | 1/4 | inconclusiva |
| BONK | poorjev + saídas (H1) | -2.84 | -172.60 | -208.90 | 889 | -30.0 | 1/4 | inconclusiva |
| BONK | só segurar | +14.42 | – | – | 0 | -32.3 | – | – |
| WIF | **von relaxado** | -6.44 | -235.02 | -67.47 | 109 | -7.0 | 2/4 | inconclusiva |
| WIF | von artigo | +0.00 | -170.60 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| WIF | poorjev + saídas (H1) | -8.39 | -254.47 | -282.15 | 954 | -25.5 | 0/4 | perdedora |
| WIF | só segurar | +17.06 | – | – | 0 | -21.8 | – | – |
| POPCAT | **von relaxado** | -6.32 | -77.06 | -64.17 | 123 | -6.6 | 2/4 | inconclusiva |
| POPCAT | von artigo | +0.00 | -13.87 | +0.00 | 0 | 0.0 | 3/4 | inconclusiva |
| POPCAT | poorjev + saídas (H1) | -15.54 | -169.29 | -208.21 | 684 | -24.9 | 1/4 | perdedora |
| POPCAT | só segurar | +1.39 | – | – | 0 | -21.0 | – | – |
| FARTCOIN | **von relaxado** | -2.73 | +21.98 | -27.60 | 96 | -4.7 | 3/4 | inconclusiva |
| FARTCOIN | von artigo | +0.00 | +49.24 | +0.00 | 0 | 0.0 | 3/4 | inconclusiva |
| FARTCOIN | poorjev + saídas (H1) | -27.97 | -230.48 | -301.82 | 1163 | -33.9 | 1/4 | perdedora |
| FARTCOIN | só segurar | -4.92 | – | – | 0 | -27.5 | – | – |
| PNUT | **von relaxado** | -16.22 | -235.52 | -164.85 | 181 | -16.3 | 2/4 | inconclusiva |
| PNUT | von artigo | +0.00 | -73.32 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| PNUT | poorjev + saídas (H1) | -16.78 | -241.07 | -268.26 | 558 | -23.2 | 0/4 | inconclusiva |
| PNUT | só segurar | +7.33 | – | – | 0 | -16.8 | – | – |
| MEW | **von relaxado** | -11.65 | -320.48 | -123.19 | 184 | -12.0 | 1/4 | inconclusiva |
| MEW | von artigo | +0.00 | -203.99 | +0.00 | 0 | 0.0 | 1/4 | inconclusiva |
| MEW | poorjev + saídas (H1) | -15.47 | -358.70 | -368.47 | 646 | -25.0 | 0/4 | perdedora |
| MEW | só segurar | +20.40 | – | – | 0 | -16.7 | – | – |
| GOAT | **von relaxado** | -8.84 | -259.26 | -94.02 | 135 | -9.3 | 2/4 | inconclusiva |
| GOAT | von artigo | +0.00 | -170.88 | +0.00 | 0 | 0.0 | 2/4 | inconclusiva |
| GOAT | poorjev + saídas (H1) | -15.89 | -329.74 | -349.53 | 827 | -26.6 | 0/4 | perdedora |
| GOAT | só segurar | +17.09 | – | – | 0 | -16.7 | – | – |

## Quem passa (von relaxado, 180 dias)

| Moeda | Grupo | Habilidade 180 d $ | Custos 180 d $ | Hab. antes de custos $ | vs segurar 180 d $ | PnL 180 d % | Meses PnL > 0 | Habilidade 30 d $ | Passa? | Porquê |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| JTO | nova | -211.29 | 269.95 | +58.66 | -1269.08 | -19.33 | 1/6 | -23.79 | não | habilidade -211.29 $ ≤ 0; não bate o só segurar (-1269.08 $); PnL > 0 só em 1/6 meses |
| BOME | nova | -309.37 | 246.18 | -63.19 | -1886.81 | -28.66 | 0/6 | -72.91 | não | habilidade -309.37 $ ≤ 0; não bate o só segurar (-1886.81 $); PnL > 0 só em 0/6 meses |
| JUP | nova | -403.36 | 349.48 | -53.88 | -1576.36 | -38.15 | 0/6 | -47.92 | não | habilidade -403.36 $ ≤ 0; não bate o só segurar (-1576.36 $); PnL > 0 só em 0/6 meses |
| PENGU | nova | -423.73 | 383.66 | -40.07 | -921.18 | -40.90 | 0/6 | -68.38 | não | habilidade -423.73 $ ≤ 0; não bate o só segurar (-921.18 $); PnL > 0 só em 0/6 meses |
| TRUMP | nova | -460.15 | 437.71 | -22.44 | -156.83 | -46.25 | 0/6 | -74.18 | não | habilidade -460.15 $ ≤ 0; não bate o só segurar (-156.83 $); PnL > 0 só em 0/6 meses |
| RAY | nova | -482.29 | 372.39 | -109.90 | -2981.34 | -44.23 | 1/6 | -3.37 | não | habilidade -482.29 $ ≤ 0; não bate o só segurar (-2981.34 $); PnL > 0 só em 1/6 meses |
| PYTH | nova | -594.18 | 561.77 | -32.42 | -1393.38 | -57.95 | 0/6 | -76.44 | não | habilidade -594.18 $ ≤ 0; não bate o só segurar (-1393.38 $); PnL > 0 só em 0/6 meses |
| MOODENG | nova | -632.10 | 613.89 | -18.21 | -595.16 | -62.75 | 0/6 | -106.30 | não | habilidade -632.10 $ ≤ 0; não bate o só segurar (-595.16 $); PnL > 0 só em 0/6 meses |
| FARTCOIN | atual | -212.72 | 193.15 | -19.57 | -191.93 | -20.76 | 0/6 | -27.60 | não | habilidade -212.72 $ ≤ 0; não bate o só segurar (-191.93 $); PnL > 0 só em 0/6 meses |
| BONK | atual | -248.40 | 173.17 | -75.23 | +89.43 | -25.29 | 0/6 | -12.97 | não | habilidade -248.40 $ ≤ 0; PnL > 0 só em 0/6 meses |
| POPCAT | atual | -357.79 | 382.28 | +24.50 | -426.58 | -35.04 | 0/6 | -64.17 | não | habilidade -357.79 $ ≤ 0; não bate o só segurar (-426.58 $); PnL > 0 só em 0/6 meses |
| WIF | atual | -370.34 | 322.88 | -47.45 | -685.67 | -35.79 | 0/6 | -67.47 | não | habilidade -370.34 $ ≤ 0; não bate o só segurar (-685.67 $); PnL > 0 só em 0/6 meses |
| MEW | atual | -571.13 | 524.60 | -46.53 | -488.60 | -56.86 | 0/6 | -123.19 | não | habilidade -571.13 $ ≤ 0; não bate o só segurar (-488.60 $); PnL > 0 só em 0/6 meses |
| GOAT | atual | -588.40 | 528.13 | -60.27 | -685.83 | -57.98 | 0/6 | -94.02 | não | habilidade -588.40 $ ≤ 0; não bate o só segurar (-685.83 $); PnL > 0 só em 0/6 meses |
| PNUT | atual | -646.74 | 582.06 | -64.68 | -947.79 | -63.58 | 0/6 | -164.85 | não | habilidade -646.74 $ ≤ 0; não bate o só segurar (-947.79 $); PnL > 0 só em 0/6 meses |

## Leitura

- **von artigo** (perfil baseline) não negoceia (0 trades em todas as moedas e janelas): a confiança do von fica perto de 0,29 (P50) e o portão do artigo é mais alto. Fica em USDT; o 'vs segurar' dele é só o simétrico do retorno da moeda.
- **von relaxado** negoceia 622–1244 vezes em 180 dias por moeda, com exposição média de ~2% (compra uma fração do saldo e vende pouco depois). A curva desce quase sem recuperar (MDD ≈ PnL): é o custo de cada ida e volta, não um mau mês.
- **poorjev + saídas (H1)** faz 3393–7142 trades em 180 dias; o PnL só fica positivo quando a moeda sobe muito (RAY, JUP), sempre bem abaixo do só segurar e com habilidade negativa em todas as moedas novas.
- O poorjev relaxado sem saídas (no summary, `<SYM>_poorjev_relaxed`) compra uma vez e segura (20 compras, 0 vendas): é o buy & hold menos custos. A 'habilidade' de estratégias ~100% expostas inclui um termo de composição (o 'só segurar' da RAY tem +980 $ de 'habilidade'); compare-a com a do só segurar da mesma moeda.
- Habilidade positiva no mês mais recente (30 dias) do von relaxado nas moedas novas: nenhuma.

## Cuidados

- **Fidelidade do estado meme:** os estados são reconstruídos de fechos de 1 m de CEX (ao vivo: marcas Gate.io → Coinpaprika a ~1/min). Na validação do bt180 o estado de mercado reconstruído bateu com o ao vivo só em 15–47% das decisões das memecoins atuais (palavra 'move' 39–69%); para moedas sem histórico ao vivo não há validação nenhuma.
- **Um só regime:** 180 dias seguidos (abril → outubro de 2026), um caminho contínuo; JUP, JTO, PYTH, RAY e BOME subiram 80–250% neste período, o que torna o 'só segurar' muito difícil de bater por qualquer estratégia de exposição baixa. Noutro regime o 'vs segurar' mudaria; a habilidade (perto de zero antes de custos) é a parte que não depende tanto do regime.
- **Custos assumidos:** sem fills reais destas moedas; usei a mediana das memecoins atuais (12,7 bps sobre a marca, +5 bps do código) e o custo da PNUT (32,8 bps) para PYTH e MOODENG, de liquidez on-chain mais baixa. Os custos decidem o resultado: mesmo com custo zero a habilidade fica perto de zero (coluna 'Hab. antes de custos'), por isso custos reais mais baixos reduziriam a perda mas não criariam uma vantagem.
- **Mesmos parâmetros:** nenhuma afinação por moeda (params.json resolvido com asset=<SYM>, sem camada por moeda); um fork afinado para uma moeda seria avaliado dentro da amostra.
- **Cadência:** cada moeda decide a cada 7 min, como as memecoins ao vivo (com 8 moedas, JUP e MOODENG no mesmo minuto). Adicionar moedas à rotação ao vivo abrandaria a cadência de todas.
- **FARTCOIN ao vivo:** o único von relaxado positivo ao vivo (16 dias) também perde aqui em 180 dias (−20,8%, habilidade −213 $, 0/6 meses com PnL > 0): consistente com sorte de curto prazo.
- JUP, JTO, PYTH e RAY não são memecoins (tokens de protocolo); correram pelo mesmo caminho meme (mesmo bot, mesmos parâmetros) como pedido.
