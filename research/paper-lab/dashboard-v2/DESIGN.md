# Paper lab, o caderno do laboratório

Painel local de um experimento de 30 dias com ~110 carteiras simuladas. A pergunta que ele responde primeiro:
**quem está ganhando, e isso é habilidade ou só exposição ao mercado (beta)?**

Conceito: paper trading → caderno de laboratório em papel milimetrado frio. Tinta azul-marinho, réguas finas, e um
único elemento ousado: o **marca-texto amarelo** atrás dos líderes (nome do 1º colocado, top 3 da ordenação ativa).
Modo escuro = "blueprint" (papel azul-marinho, tinta de giz), com tokens próprios.

## Tokens

| Papel | Claro | Escuro |
|---|---|---|
| `--paper` (fundo + grade) | `#EEF2F6` | `#0F1B2D` |
| `--surface` (folhas, tabelas) | `#F8FAFC` | `#13233A` |
| `--sunk` (trilhos de medidor) | `#E3E9F0` | `#0B1626` |
| `--ink` / `--ink-2` / `--ink-3` | `#14213D` / `#475569` / `#64748B` | `#E8EEF6` / `#B4C1D3` / `#8798AF` |
| `--rule` / `--rule-strong` | `#D5DDE6` / `#B8C4D2` | `#22385A` / `#335079` |
| `--hl` (marca-texto) | `#FFE45C` | `#FFE45C` (texto marcado vira tinta escura) |
| `--gain` / `--loss` | `#1F7A4D` / `#C2372F` | `#56C994` / `#FF8577` |

Ganho/perda **nunca só por cor**: sempre sinal `+`/`−` e seta `▲`/`▼`.

Famílias (cor segue a entidade, ordem fixa da paleta documentada, validada com `validate_palette.js`
claro e escuro: CVD adjacente ≥ 8,4, visão normal ≥ 19,3; no claro 3 tons ficam < 3:1 → sempre com rótulo de texto):

| von | poorjev | Laya | Hipóteses | Regras | Híbridos |
|---|---|---|---|---|---|
| `#2a78d6` / `#3987e5` | `#eb6834` / `#d95926` | `#1baf7a` / `#199e70` | `#eda100` / `#c98500` | `#e87ba4` / `#d55181` | `#4a3aa7` / `#9085e9` |

Forks herdam a cor da família do pai (filtro próprio "Forks").

Gráfico de 6 meses (Retroativo): séries de estratégia usam `--series-1…8`, a paleta documentada inteira em ordem fixa
(validada com `validate_palette.js` nas superfícies do painel: claro `#F8FAFC` CVD adjacente ≥ 9,1 / visão normal ≥ 19,6,
3 tons < 3:1 → rótulos diretos + "Ver os valores em tabela"; escuro `#13233A` ≥ 8,4 / ≥ 19,3, todos ≥ 3:1). A cor é
fixada pela posição da linha no conjunto do run (top 3 habilidade, top 2 lucro, bot A, bot B, extras até 8) e não muda
ao ligar/desligar. Benchmarks nunca usam cor de série: tinta neutra e tracejado (só segurar SOL `--ink-2` tracejado,
cesta de memecoins `--ink-3` traço longo, USDC 6%/ano `--ink-3` pontilhado). "Por família" (gráfico e painel, via `familyInfo`/`parseFamilyKey` em `lib/backtest.ts`, que entende chaves como "SOL · von", "meme · poorjev", "SOL rule") usa as cores `--fam-*`,
com Jev em `--series-6` e Forks em `--series-8`. Um eixo y só (patrimônio, 1000 = início).

## Tipo

Uma família só: **Archivo variable** (local, `@fontsource-variable/archivo/wdth.css`, sem CDN). O eixo de largura é a
personalidade:

| Uso | Tamanho | wdth / wght |
|---|---|---|
| Números de destaque (frase da faixa, PnL do líder) | 28–40 | 125 / 720 (figuras proporcionais) |
| Títulos de seção | 20–24 | 118 / 680 |
| PnL na linha do placar | 19 | 112 / 650 (tabular) |
| Corpo | 14 | 100 / 420 |
| Chips, meta de tabela | 11–12 | 78 / 560 |

Sem CAIXA ALTA espaçada, sem mono para rótulos, sem "eyebrows", sem strings com ponto médio (usar chips separados).

## Layout

```
┌ Paper lab [simulação]                     SOL US$ 119,15   ● saúde   ◐ tema ┐
│ Placar  Famílias  Carteira real  Controle  Saúde  Funding                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Dia 2 de 30  ━━●──────────────────────────────┃21 primeiros vereditos──┃30   │
│ Na frente agora: ▇poorjev relaxado + saídas▇ (+5,8%)                          │
│ Mais habilidade (sem beta): von relaxado em FARTCOIN (+US$ 11)               │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Lucro|Habilidade|Vs. segurar]  (von)(Laya)(poorjev)(Regras)…  (SOL)(Memes)… 🔍│
│ #  Nome + chips          curva    PnL      vs. segurar   Habilidade  Exp  C/V  Veredito│
│ 1  ▇poorjev relaxado▇    ╱╲_╱‾   +5,8%    ──┼████        +US$ 50     ▮▮▮  60/2  ▮░ 2/21d│
│    [FARTCOIN][H1]                 +US$58                  p 0,03                 ▮░ 2/30RT│
│ …                                                                             │
└──────────────────────────────────────────────────────────────────────────────┘
Celular (≤ 640px): linha = nome + chips | PnL | habilidade; o resto abre no painel de detalhe.
```

Painel de detalhe (folha lateral, `#/placar?p=<nome>`): patrimônio × "só segurar" com marcas de compra/venda,
"O que este teste faz", números-chave, parâmetros efetivos com selo de origem (padrão, perfil, tipo, modelo, ativo,
portfólio, fork, ajuste manual), edição do ajuste manual com confirmação, pausa.

## Regras de nome (`src/lib/describe.ts`)

- Perfis: `baseline` → **artigo**, `relaxed` → **relaxado**, `v2` → **critérios v2**.
- Título = cérebro + perfil + o que o teste acrescenta: `h1_exits_FARTCOIN_poorjev_relaxed` → "poorjev relaxado + saídas".
- Chips separados: ativo (`FARTCOIN`) e família/hipótese (`hipótese H1`, `regra`, `híbrido`, `modelo`, `fork`).
- Uma frase simples do que o teste faz, com os números efetivos quando a API manda `params_brief`.
- Forks `<pai>__fork<N>` → "<título do pai>, ajuste N" + frase com o diff de parâmetros.

## Movimento e estados

Um único momento orquestrado: o marca-texto do líder "passa" uma vez no carregamento (desligado em
`prefers-reduced-motion`). Recarregar mantém o quadro anterior (sem esqueleto piscando). Estados vazios dizem o que
esperar ("Sem trades ainda — o primeiro aparece quando um teste passar os portões").
