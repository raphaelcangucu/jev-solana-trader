#!/usr/bin/env python3
"""Simulação retroativa dos últimos N dias (padrão 30) de todas as estratégias do catálogo atual do lab e do bot real.

Paper only: nunca assina, nunca envia, nunca lê chaves de carteira, nunca liga LIVE_TRADING. Não toca no run ao vivo:
lê (só leitura) a configuração dele num instantâneo, usa servidores de modelos próprios nas portas 8865–8867 e grava
apenas em <live_root>/data/backtest/ (pasta `<run_id>/`, cache em `_cache/` e o ficheiro `latest`).

Uso:
    python research/paper-lab/scripts/backtest_30d.py [--days 30] [--end 2026-10-06T09:00-03:00] [--step 60]
        [--jev-max-calls 20000] [--no-jev] [--live-root ~/jev-lab/code/research/paper-lab] [--keep-servers]

Fases (progresso em <run>/progress.log e <run>/progress.json): dados → catálogo → modelos (cache) → simulação →
bot real → métricas → saídas. Contrato das saídas: backtest/report.py.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parents[1]
BRT = timezone(timedelta(hours=-3))


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=float, default=30)
    ap.add_argument("--end", default=None, help="fim da janela (ISO; padrão: agora arredondado ao minuto)")
    ap.add_argument("--step", type=int, default=60, help="passo de decisão em segundos (múltiplo de 60)")
    ap.add_argument("--jev-max-calls", type=int, default=20000)
    ap.add_argument("--no-jev", action="store_true")
    ap.add_argument("--live-root", default=str(Path.home() / "jev-lab/code/research/paper-lab"))
    ap.add_argument("--out-root", default=None, help="padrão: <live-root>/data/backtest")
    ap.add_argument("--cache-dir", default=None, help="padrão: <live-root>/data/backtest/_cache (dados e respostas dos modelos)")
    ap.add_argument("--jev-alts", default=os.environ.get("JEV_ALTS_ROOT") or str(Path.home() / "jev-alts"))
    ap.add_argument("--realbot-config", default=None, help="config/params.json do bot real (padrão: o do run ao vivo)")
    ap.add_argument("--keep-servers", action="store_true")
    ap.add_argument("--run-id", default=None)
    return ap.parse_args(argv)


class Progress:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.logf = run_dir / "progress.log"
        self.t0 = time.time()
        self.phases = {}

    def log(self, msg):
        line = f"[{datetime.now(tz=BRT).strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(self.logf, "a") as f:
            f.write(line + "\n")

    def phase(self, name, **kw):
        self.phases[name] = round(time.time() - self.t0, 1)
        self.log(f"fase: {name}")
        (self.run_dir / "progress.json").write_text(json.dumps({"phase": name, "elapsed_s": round(time.time() - self.t0, 1),
                                                                 "phases_at_s": self.phases, **kw}, ensure_ascii=False))


def slippage_from_live(live_root: Path, extra_bps: float, memecoins: dict, until_ts: float) -> tuple[dict, dict]:
    """Custo mediano por ativo nos fills reais (cotação Jupiter/Raydium) do run ao vivo até ao fim da janela, menos o
    extra que o código soma por cima (extra_slippage_bps). Só leitura dos logs de trades; reprodutível para o mesmo fim."""
    mints = {t["mint"]: t["symbol"] for t in memecoins["tokens"]}
    vals: dict = {}
    for f, cls in (("logs/trades.jsonl", "sol"), ("logs/meme_trades.jsonl", "meme")):
        p = live_root / f
        if not p.exists():
            continue
        with open(p) as fh:
            for line in fh:
                try:
                    t = json.loads(line)
                except Exception:
                    continue
                fl = t.get("fill") or {}
                if float(t.get("ts") or 0) >= until_ts or fl.get("fill_mode") in ("mark", "limit_sim", None):
                    continue
                sym = "SOL" if cls == "sol" else mints.get(fl.get("mint"))
                pm = float(t.get("price_mark") or 0)
                if not sym or pm <= 0:
                    continue
                if t["side"] == "buy":
                    q = float(fl.get("sol_out_net") or fl.get("token_out_net") or 0); n = float(fl["usdt_in"]); c = n - q * pm
                else:
                    q = float(fl.get("sol_in") or fl.get("token_in") or 0); n = q * pm; c = n - float(fl["usdt_out_net"])
                if n > 0:
                    vals.setdefault(sym, []).append(c / n * 1e4)
    out, info = {}, {}
    for sym in ["SOL"] + [t["symbol"] for t in memecoins["tokens"]]:
        v = vals.get(sym) or []
        if len(v) >= 20:
            med = statistics.median(v)
            out[sym] = max(0.0, med - extra_bps)
            info[sym] = {"n_fills": len(v), "median_total_bps": round(med, 2), "quote_slippage_bps": round(out[sym], 2)}
        else:
            out[sym] = 10.0 if sym == "SOL" else 25.0
            info[sym] = {"n_fills": len(v), "quote_slippage_bps": out[sym], "fallback": True}
    return out, info


def main(argv=None) -> int:
    a = parse_args(argv)
    live_root = Path(a.live_root).expanduser().resolve()
    out_root = Path(a.out_root).expanduser() if a.out_root else live_root / "data" / "backtest"
    cache_dir = Path(a.cache_dir).expanduser() if a.cache_dir else live_root / "data" / "backtest" / "_cache"
    if a.end:
        end_dt = datetime.fromisoformat(a.end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=BRT)
    else:
        end_dt = datetime.now(tz=BRT)
    end = int(end_dt.timestamp()) // 60 * 60
    start = int(end - a.days * 86400) // 60 * 60
    if a.step % 60 != 0 and 60 % a.step != 0:
        raise SystemExit("--step tem de dividir 60 ou ser múltiplo de 60")
    run_id = a.run_id or f"bt{int(a.days)}_{datetime.fromtimestamp(end, tz=BRT).strftime('%Y-%m-%d')}"
    run_dir = out_root / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    pg = Progress(run_dir)
    pg.log(f"backtest {run_id}: {datetime.fromtimestamp(start, tz=BRT).isoformat()} → {datetime.fromtimestamp(end, tz=BRT).isoformat()}"
           f" passo {a.step}s · run ao vivo (só leitura): {live_root}")

    # instantâneo da configuração ao vivo e PAPER_LAB_ROOT → instantâneo (antes de importar bot.*)
    sys.path.insert(0, str(LAB))
    from backtest import catalog as CAT
    inputs = run_dir / "inputs"
    snap = CAT.snapshot(live_root, inputs)
    rb_cfg_src = Path(a.realbot_config) if a.realbot_config else (live_root.parents[1] / "config" / "params.json")
    if not rb_cfg_src.exists():
        rb_cfg_src = REPO / "config" / "params.json"
    shutil.copy2(rb_cfg_src, inputs / "realbot_params.json")
    os.environ["PAPER_LAB_ROOT"] = str(inputs)
    os.environ.pop("LIVE_TRADING", None)

    from backtest import data as D, states as ST, models as M, engine as EN, metrics as MET, report as REP
    from bot import params as P, lab_registry as R, lab_criteria as LC
    from bot.backends import load_models_cfg
    cfg = json.loads((inputs / "config.json").read_text())
    memecoins = json.loads((inputs / "memecoins.json").read_text())
    models_cfg = load_models_cfg()
    syms = ["SOL"] + [t["symbol"] for t in memecoins["tokens"]]
    notes = []
    servers = cache_dir / "servers"
    started_servers = False
    try:
        # ------------------------------------------------------------ dados
        pg.phase("dados")
        data = D.fetch_all(cache_dir, start, end, syms, logf=pg.logf)
        unusable = [s for s in syms if not data["coverage"][s].get("usable")]
        if unusable:
            notes.append(f"ativos inutilizáveis (cobertura < 90%): {unusable}")
        slip, slip_info = slippage_from_live(live_root, float(cfg["fees"].get("extra_slippage_bps", 5)), memecoins, end)
        pg.log(f"slippage por ativo (bps sobre a marca, antes do extra de {cfg['fees'].get('extra_slippage_bps')} bps): {slip}")

        # ------------------------------------------------------------ catálogo
        pg.phase("catalogo")
        jev_names = M.load_secrets() if not a.no_jev else []
        jcfg = (models_cfg.get("backends") or {}).get("jev") or {}
        jev_ready = (not a.no_jev) and bool(jcfg.get("enabled")) and bool((os.environ.get(jcfg.get("api_key_env") or "JEV_API_KEY") or "").strip())
        items = CAT.build(models_cfg, jev_ready)
        items = [it for it in items if it["asset"] not in unusable]
        pg.log(f"catálogo: {len(items)} portfólios (+ bot real A/B); Jev {'ligado' if jev_ready else 'desligado'}"
               f"{' (segredos: ' + ','.join(jev_names) + ')' if jev_names else ''}")

        # ------------------------------------------------------------ modelos
        pg.phase("modelos")
        M.start_servers(servers, Path(a.jev_alts).expanduser(), logf=pg.logf)
        started_servers = True
        cache = M.ModelCache(cache_dir / "model_answers.sqlite")
        client = M.ModelClient(cache, jev_cfg=jcfg, jev_max_calls=a.jev_max_calls, workers=4, logf=pg.logf)
        client.guard = M.live_guard(live_root, log=pg.log)   # pré-busca pausa se o run ao vivo ficar lento
        crit_base = json.loads((inputs / "criteria_baseline.json").read_text())
        crit_v2 = json.loads((inputs / "criteria_v2.json").read_text())
        client.register("lab_baseline", crit_base)
        client.register("lab_v2", crit_v2)
        from jev_trader.criteria import DEFAULT_CRITERIA, questions_for
        from jev_trader.decide import ACTION_INSTRUCTIONS
        q = questions_for(DEFAULT_CRITERIA, ACTION_INSTRUCTIONS)
        client.register("realbot", {"action": {"instructions": q["action"]["instructions"], "criteria": q["action"]["criteria"]},
                                    "skip_this_cycle": {"instructions": q["skip_this_cycle"]["instructions"]}},
                        model_field=os.environ.get("VON_MODEL", "von-latest"))
        reg = R.load()
        crit_forks = []      # (nome, modelo, ativo, cid)
        for it in items:
            if it["runner"] != "lab_bot":
                continue
            e = dict(reg["portfolios"][it["name"]], name=it["name"])
            eff = P.effective(it["name"], meta=e, registry=reg)
            ref = eff.get("criteria")
            if ref:
                clean, sha = LC.load_ref(ref)
                cid = f"crit:{sha[:16]}"
                client.register(cid, clean)
                crit_forks.append((it["name"], (e.get("model") or "").split("+")[0], it["asset"], cid))
        pg.log(f"forks de critérios: {[(n, m, s) for n, m, s, _ in crit_forks]}")

        # estados de mercado de todos os passos → variantes de posição/humor → pré-busca paralela
        sol_ms = ST.MarketStates(ST.sol_sampler(*data["sol_grid"]))
        meme_ms = {s: ST.MarketStates(ST.minute_sampler(data["minute"][s])) for s in syms[1:]}
        V_SOL = [("held", "neutral"), ("sold", "neutral"), ("sold", "buoyed"), ("sold", "stung")]
        V_MEME = [("flat", "neutral"), ("held", "neutral"), ("sold", "neutral"), ("sold", "buoyed"), ("sold", "stung")]
        sol_keys, meme_keys = set(), {s: set() for s in syms[1:]}
        for t in range(start + a.step, end + 1, a.step):
            mk = sol_ms.at(t)
            if mk:
                sol_keys.add(mk)
            if t % 60 == 0:
                s = syms[1:][((t - start) // 60) % (len(syms) - 1)]
                mk = meme_ms[s].at(t)
                if mk:
                    meme_keys[s].add(mk)
        sol_states = sorted({ST.compose(mk, p, m) for mk in sol_keys for p, m in V_SOL})
        meme_states = {s: sorted({ST.compose(mk, p, m) for mk in ks for p, m in V_MEME}) for s, ks in meme_keys.items()}
        all_meme = sorted({x for v in meme_states.values() for x in v})
        pg.log(f"estados: SOL {len(sol_keys)} chaves de mercado → {len(sol_states)} estados; memecoins {sum(map(len, meme_keys.values()))} "
               f"chaves → {len(all_meme)} estados")
        jobs = [(m, c, s) for m, c in (("von", "lab_baseline"), ("von", "lab_v2"), ("laya", "lab_baseline"), ("poorjev", "lab_baseline"))
                for s in sol_states]
        jobs += [(m, "lab_baseline", s) for m in ("von", "laya", "poorjev") for s in all_meme]
        for n, m, asset, cid in crit_forks:
            if m in M.PORTS:
                jobs += [(m, cid, s) for s in (sol_states if asset == "SOL" else meme_states.get(asset, []))]
        pg.log(f"pré-busca local: {len(jobs)} pares (antes da cache)")
        r = client.prefetch(jobs, label="local")
        pg.log(f"pré-busca local: {r}")
        if jev_ready:
            r = client.prefetch([("jev", "lab_baseline", s) for s in sol_states], label="jev", progress_every=100)
            pg.log(f"pré-busca Jev: {r} (teto {a.jev_max_calls})")
            if client.jev_budget_hit:
                notes.append(f"Jev: teto/disjuntor atingido ({client.stats.get('jev', {}).get('last_error') or 'teto de chamadas'})")

        # ------------------------------------------------------------ simulação
        pg.phase("simulacao")
        rb_vals = {}
        from jev_trader.config import load_params as rb_load
        for prof in ("relaxed_paper", "relaxed_exits_paper"):
            vals, used, errs = rb_load(inputs / "realbot_params.json", prof)
            rb_vals[prof] = vals
            if errs:
                notes.append(f"bot real {prof}: {errs}")
        eng = EN.Engine(data=data, start=start, end=end, step=a.step, items=items, client=client, cfg=cfg,
                        memecoins=memecoins, slip_bps=slip, crit_files={}, logf=pg.logf, jev_ready=jev_ready,
                        progress=pg.log, realbot_params=rb_vals).setup()
        eng.run()
        pg.log(f"simulação: {eng.counts}, trades {len(eng.env.trades)}")
        pg.phase("bot_real")
        rb = eng.run_realbot({"A": "relaxed_paper", "B": "relaxed_exits_paper"})
        client.cache.commit()
        eng.env.uninstall()

        # ------------------------------------------------------------ métricas
        pg.phase("metricas")
        trades_by = {}
        for t in eng.env.trades:
            trades_by.setdefault(t.get("portfolio"), []).append(t)
        ports = []
        lookahead_from = datetime.fromisoformat("2026-10-01T22:24:00-03:00").timestamp()
        for it in items:
            n = it["name"]
            rows = eng.rec.rows.get(n) or []
            if len(rows) < 3:
                notes.append(f"{n}: sem série de equity")
                continue
            v = MET.verdict(n, dict(it["meta"], kind=it["kind"]), rows, trades_by.get(n, []), start, end)
            s = v["stats"]
            created = (it["meta"].get("created_brt") or "")
            look = bool(it["is_fork"]) and created and datetime.fromisoformat(created).timestamp() >= lookahead_from
            ports.append({
                "name": n, "family": it["family"], "asset": it["asset"], "model": it["model"], "test_type": it["test_type"],
                "profile": it["profile"], "parent": it["parent"], "is_fork": it["is_fork"], "label": it["label"],
                "start_value": REP._r(s["start_value"]), "end_value": REP._r(s["end_value"]), "pnl": REP._r(s["pnl"]),
                "pnl_pct": REP._r(s["pnl_pct"]), "vs_bh": REP._r(s["ex_bh"]), "vs_usdt": REP._r(s["ex_usdt"]),
                "skill": REP._r(s.get("ex_exposure")), "timing": REP._r(s.get("timing_usd")), "timing_p": REP._r(s.get("timing_p")),
                "max_dd_pct": REP._r(s["mdd_pct"]), "trades": s["trades"], "buys": s["buys"], "sells": s["sells"],
                "closed_rt": v["closed_rt"], "exposure_pct": REP._r(s.get("exposure_pct")), "weeks": v["weeks_pnl"],
                "weeks_beat_bh": v["weeks_beat_bh"], "verdict": v["verdict"], "verdict_reason": v["verdict_reason"],
                "p_bh": REP._r(v["p_bh"]), "p_usdc": REP._r(v["p_usdc"]), "fees": REP._r(s["fees"]),
                "cost_vs_mark": REP._r(s["cost_vs_mark"]), "look_ahead": look,
            })
            REP.write_equity(run_dir, n, rows)
            if trades_by.get(n):
                REP.write_trades(run_dir, n, [REP.slim_trade(t) for t in trades_by[n]])

        realbot = []
        g, px = data["sol_grid"]
        gf = ST.ffill(px)
        g0, gs = int(g[0]), int(g[1] - g[0])
        for label, d in rb.items():
            eq = d["equity"]
            e0, e1 = eq[0]["equity"], eq[-1]["equity"]
            hold0, hold1 = eq[0]["bh_equity"], eq[-1]["bh_equity"]
            hits = res = 0
            exits = {}
            for t in d["trades"]:
                if t.get("reason") in ("tp", "sl", "trail"):
                    exits[t["reason"]] = exits.get(t["reason"], 0) + 1
                if t.get("reason") != "gate":
                    continue
                ts = int(datetime.fromisoformat(t["t"]).timestamp())
                i = (ts + 900 - g0) // gs
                if 0 <= i < len(gf):
                    r_ = gf[i] / float(t["px_in"]) - 1
                    res += 1
                    hits += 1 if (r_ > 0 if t["side"] == "buy" else r_ < 0) else 0
            name = f"realbot_{label}"
            realbot.append({"book": label, "profile": d["profile"], "start_value": REP._r(e0, 6), "end_value": REP._r(e1, 6),
                            "pnl": REP._r(e1 - e0, 6), "pnl_pct": REP._r((e1 - e0) / e0 * 100, 4),
                            "vs_hold": REP._r((e1 - e0) - (hold1 - hold0), 6), "hit_15m": REP._r(hits / res, 4) if res else None,
                            "max_dd_pct": REP._r(MET.max_dd_pct([r["equity"] for r in eq]), 4), "trades": len(d["trades"]),
                            "exits": exits, "decisions": d["decisions"], "gate_executes": d["executes"]})
            REP.write_equity(run_dir, name, eq)
            REP.write_trades(run_dir, name, [REP.slim_real_trade(t) for t in d["trades"]])

        # ------------------------------------------------------------ validação contra o run ao vivo (só leitura)
        pg.phase("validacao")
        from backtest import validate as VAL
        live_t0 = max(start, int(lookahead_from))
        validation = {"overlap_brt": [datetime.fromtimestamp(live_t0, tz=BRT).isoformat(), datetime.fromtimestamp(end, tz=BRT).isoformat()]}
        try:
            validation["states"] = VAL.state_agreement(live_root, data, live_t0, end, syms)
            validation["models"] = VAL.model_agreement(live_root, client, live_t0, end)
            validation["trades_overlap"] = VAL.trade_counts(live_root, trades_by, live_t0, end, [p["name"] for p in ports])
        except Exception as ex:
            validation["error"] = f"{type(ex).__name__}: {ex}"
        pg.log(f"validação: estados {validation.get('states')} modelos {validation.get('models')}")

        # ------------------------------------------------------------ resumo
        pg.phase("saidas")
        assets = {}
        for s in syms:
            ms = data["minute"][s]
            p0, p1 = ms.close_at(start), ms.close_at(end)
            assets[s] = {"source": data["sources"].get(s), "coverage": data["coverage"][s]["coverage"],
                         "start_px": p0, "end_px": p1, "ret_pct": REP._r((p1 / p0 - 1) * 100, 4),
                         "basis": data["basis"].get(s), "slippage": slip_info.get(s)}
        models_out = {}
        for m, st in client.stats.items():
            confs = sorted(st["confs"])
            look = max(1, st["lookups"])
            models_out[m] = {"calls": st["calls"], "cache_hits": st["cache_hits"], "lookups": st["lookups"],
                             "coverage": REP._r(1 - st["fail_closed"] / look, 4), "errors": st["errors"],
                             "budget_skipped": st.get("budget_skipped", 0),
                             "conf_p50": REP._r(confs[len(confs) // 2]) if confs else None,
                             "conf_p90": REP._r(confs[int(len(confs) * 0.9)]) if confs else None}
        for m, n_ in client.cache.db.execute("SELECT model, COUNT(*) FROM answers GROUP BY model"):
            if m in models_out:
                models_out[m]["cached_total"] = n_    # respostas únicas na cache (todas as execuções)
        traded = [p for p in ports if p["trades"] > 0] or ports
        by_skill = max(traded, key=lambda p: p["skill"] if p["skill"] is not None else -1e18)["name"]
        by_pnl = max(ports, key=lambda p: p["pnl_pct"])["name"]
        winners = [p for p in ports if p["verdict"] == "vencedora"]
        by_verdict = max(winners, key=lambda p: p["skill"] or 0)["name"] if winners else None
        assumptions = [
            f"Janela {a.days:g} dias até {datetime.fromtimestamp(end, tz=BRT).isoformat()} (BRT); decisão a cada {a.step} s; "
            "memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.",
            f"Capital: portfólios SOL com US$ {cfg['starting_balances'].get('total_usd', 1000):g} na mistura do config.json "
            f"({cfg['starting_balances'].get('sol_frac')} em SOL ao preço do início da janela); memecoins com "
            f"{memecoins.get('start_usdt_each')} USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam "
            "com o capital da família no início da janela (não com o estado do pai).",
            "Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/), resolvidos por bot/params.py; "
            "nenhuma pausa do dashboard é aplicada.",
            "Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas "
            "Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); "
            "memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas "
            "e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.",
            "Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a "
            "Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.",
            "Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do "
            f"run ao vivo menos o extra de {cfg['fees'].get('extra_slippage_bps')} bps que o código soma: "
            + ", ".join(f"{k} {v:.1f} bps" for k, v in slip.items()) + "; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).",
            "Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing "
            "avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).",
            "Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo "
            "depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.",
            "Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado "
            "uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de "
            "decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.",
            "Veredito: regra do run ao vivo (≥30 round trips fechados; dias cumpridos pela janela; bate B&H com p<0,05 por "
            "block-bootstrap, PnL acima da barra de 6%/a USDC, excesso positivo em ≥3 de 4 semanas). Semanas = 4 blocos de 7 dias "
            "contados do fim da janela.",
            "Look-ahead: forks criados a partir de 2026-10-03 usaram dados de 2026-10-01 a 2026-10-06 (fim desta janela).",
        ]
        if jev_ready:
            assumptions.append(f"Jev hospedado: só portfólios SOL; teto de {a.jev_max_calls} chamadas.")
        else:
            assumptions.append("Jev hospedado desligado (sem chave ou --no-jev): portfólios jev_* fora do catálogo.")
        summary = {
            "run_id": run_id, "generated_brt": datetime.now(tz=BRT).isoformat(timespec="seconds"),
            "window": {"start_brt": datetime.fromtimestamp(start, tz=BRT).isoformat(), "end_brt": datetime.fromtimestamp(end, tz=BRT).isoformat(),
                       "days": a.days, "step_s": a.step},
            "assets": assets, "assumptions": assumptions, "models": models_out,
            "winner": {"by_skill": by_skill, "by_pnl": by_pnl, "by_verdict": by_verdict,
                       "text": REP.winner_text(by_skill, by_pnl, by_verdict, ports, a.days)},
            "families": REP.families(ports), "portfolios": ports, "realbot": realbot,
            "runtime": {"phases_at_s": pg.phases, "total_s": round(time.time() - pg.t0, 1), "engine": eng.counts,
                        "lab_criteria_calls": eng.lab.crit.stats},
            "inputs": snap, "notes": notes, "validation": validation,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
        (run_dir / "report.md").write_text(REP.report_md(summary, {"notes": notes}))
        (out_root / "latest").write_text(run_id + "\n")
        pg.phase("fim", total_s=round(time.time() - pg.t0, 1))
        pg.log(f"pronto: {run_dir} ({len(ports)} portfólios + bot real A/B) em {time.time() - pg.t0:.0f}s")
        return 0
    except Exception as ex:
        pg.log(f"ERRO: {type(ex).__name__}: {ex}\n{traceback.format_exc()}")
        (run_dir / "progress.json").write_text(json.dumps({"phase": "erro", "error": f"{type(ex).__name__}: {ex}"}))
        return 1
    finally:
        if started_servers and not a.keep_servers:
            from backtest import models as M2
            M2.stop_servers(servers)


if __name__ == "__main__":
    raise SystemExit(main())
