"""Ambiente simulado para correr as funções dos bots ao vivo sem rede nem ficheiros.

Os bots (sol_bot, meme_bot, rules_bot, lab_bot, jev_trader.paper) leem a hora com `time.time()`/`brt_now()`, gravam
estado com `write_json`/`append_jsonl` e pedem cotações à Jupiter com `jupiter_quote`. `SimEnv.install()` troca estes
nomes NOS MÓDULOS dos bots por:

- relógio simulado (`Clock.now`) — `time.time()` e `brt_now()` devolvem o instante do passo;
- `write_json` → nada; `append_jsonl` → sumidouro em memória (só as linhas de trade, identificadas por `fill`);
- `jupiter_quote` → cotação sintética = marca do minuto × (1 ± slippage estimado do ativo) (ver `fees_note`).

Assim o backtest corre o MESMO código de portões, saídas, teto de exposição, ordens limite e fills do run ao vivo.
`uninstall()` repõe tudo (os testes dependem disso).
"""
from __future__ import annotations

import time as _real_time
import types
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))
SOL_MINT = "So11111111111111111111111111111111111111112"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


class Clock:
    def __init__(self, now: float = 0.0):
        self.now = float(now)


def fake_time_module(clock: Clock):
    m = types.ModuleType("time_sim")
    for k in dir(_real_time):
        if not k.startswith("__"):
            setattr(m, k, getattr(_real_time, k))
    m.time = lambda: clock.now
    m.sleep = lambda s: None
    return m


class SimEnv:
    def __init__(self, clock: Clock, marks: dict, slippage_bps: dict, mint_to_sym: dict, regime_fn=None):
        self.clock = clock
        self.marks = marks                 # sym -> preço atual (atualizado pelo motor a cada passo)
        self.slip = slippage_bps           # sym -> bps contra o trader na cotação sintética
        self.mint_to_sym = dict(mint_to_sym, **{SOL_MINT: "SOL"})
        self.regime_fn = regime_fn or (lambda: None)
        self.trades: list[dict] = []
        self.orders: list[dict] = []
        self.quotes = 0
        self._saved: list = []

    # --- substitutos
    def brt_now(self):
        return datetime.fromtimestamp(self.clock.now, tz=BRT)

    def append_jsonl(self, path, row):
        if isinstance(row, dict):
            if "fill" in row and "side" in row:
                self.trades.append(row)
            elif row.get("event") in ("placed", "filled", "cancelled"):
                self.orders.append(row)

    def write_json(self, path, obj):
        return None

    def jupiter_quote(self, cfg, input_mint, output_mint, amount_in, in_decimals, slippage_bps=50):
        """Cotação sintética no formato da Jupiter (inAmount/outAmount em átomos)."""
        self.quotes += 1
        if input_mint == USDT_MINT:
            sym = self.mint_to_sym[output_mint]
            px = float(self.marks[sym])
            s = float(self.slip.get(sym, 0.0)) / 1e4
            out_ui = float(amount_in) / (px * (1 + s))
            dec = 9 if sym == "SOL" else int(self._decimals[sym])
        else:
            sym = self.mint_to_sym[input_mint]
            px = float(self.marks[sym])
            s = float(self.slip.get(sym, 0.0)) / 1e4
            out_ui = float(amount_in) * px * (1 - s)
            dec = 6
        return {"inAmount": str(int(round(float(amount_in) * 10 ** int(in_decimals)))),
                "outAmount": str(int(out_ui * 10 ** dec)), "priceImpactPct": "0", "routePlan": [],
                "_fill_mode": "sim_quote", "_quote_source": "backtest"}

    # --- instalação
    def _set(self, mod, name, value):
        self._saved.append((mod, name, getattr(mod, name)))
        setattr(mod, name, value)

    def install(self, decimals: dict):
        import bot.lib as L
        import bot.sol_bot as SB
        import bot.meme_bot as MB
        import bot.rules_bot as RB
        import bot.lab_bot as LB
        import bot.lab_registry as R
        import bot.params as P
        self._decimals = decimals
        ft = fake_time_module(self.clock)
        for mod in (L, SB, MB, RB, LB, R):
            self._set(mod, "time", ft)
        for mod in (SB, MB, LB, L):
            self._set(mod, "brt_now", self.brt_now)
        for mod in (SB, MB, RB, LB, R):
            self._set(mod, "append_jsonl", self.append_jsonl)
            self._set(mod, "write_json", self.write_json)
        for mod in (SB, MB, RB):
            self._set(mod, "jupiter_quote", self.jupiter_quote)
        self._set(P, "sol_regime_bull", lambda root=None: self.regime_fn())
        self._set(LB, "mark", lambda asset, max_age=120.0: self.marks.get(asset))
        try:
            import jev_trader.paper as JP
            self._set(JP, "append_jsonl", self.append_jsonl)
        except Exception:
            pass
        return self

    def uninstall(self):
        while self._saved:
            mod, name, val = self._saved.pop()
            setattr(mod, name, val)
