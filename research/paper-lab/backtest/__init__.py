"""Simulação retroativa (backtest) do laboratório paper: repete as estratégias do run ao vivo sobre os últimos N dias.

Só simulação: nunca assina, nunca envia, nunca lê chaves de carteira. Módulos:

- `data`     — velas públicas (1 m, 1 s→grelhas, 1 h), cache em gzip, cobertura por ativo.
- `states`   — estado de 12 adjetivos do lab (bot/lib.build_state) e do bot real (jev_trader.state) por passo.
- `models`   — servidores próprios dos modelos (portas 8865–8867), cache sqlite das respostas, Jev hospedado com teto.
- `catalog`  — catálogo atual do run ao vivo (instantâneo de registry/params/models) e parâmetros efetivos.
- `simenv`   — relógio simulado e sumidouros de I/O para reutilizar as funções dos bots ao vivo sem tocar em ficheiros.
- `engine`   — réplica dos bots (sol_bot, meme_bot, rules_bot, lab_bot) e do bot real (livros A/B).
- `metrics`  — métricas do analytics ao vivo sobre séries simuladas e veredito adaptado a 30 dias.
- `report`   — summary.json, equity/, trades/, report.md.
- `history`  — histórico dos runs: index.json, latest (run mensal mais recente), chart.json das janelas longas, history.md.
"""
