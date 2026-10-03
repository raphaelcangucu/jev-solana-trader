#!/usr/bin/env python3
"""Ferramenta ÚNICA que a revisão noturna autónoma (Claude Code, `scripts/macos/night_claude.sh`) pode executar.

Decisão do utilizador (2026-10-03): à noite, sem aprovação humana, o Claude decide sozinho e cria forks (nunca altera os
originais) com parâmetros ou critérios novos, e acompanha-os nos dias seguintes. SÓ paper, com limites duros:

  context [--hours 24]         contexto compacto (≤ ~6k tokens) para a reflexão
  fork --parent N --diff JSON --reason T [--dry-run]            fork de parâmetros (lab_registry.create_fork; pais de
                               regra → fork executado pelo rules_bot, diff em rule/gates.buy_fraction_usdt/exits/regime_filter)
  criteria-fork --parent N --criteria-file F --reason T [--dry-run]   fork cuja diferença é o texto dos critérios
  realbot-criteria --criteria-file F --reason T                 critérios do bot real, aprovação autónoma SÓ em paper
  journal --file F             copia o diário da noite para reviews/claude_night_<data BRT>.md (nunca sobrescreve)
  status                       ações desta noite e limites restantes

Escreve apenas por caminhos validados (resolver de params.json, lab_registry, jev_trader.rewrite) e regista cada ação em
logs/param_changes.jsonl com who="claude-night". Limites em config.json `claude_night`. Ficheiros de entrada
(critérios, diário) têm de estar em <PAPER_LAB_ROOT>/run/. Raiz do bot real: env JEV_TRADER_ROOT, senão LAB/../..
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from bot.paths import ROOT, LAB_DIR  # noqa: E402
from bot.lib import BRT, brt_iso, load_cfg, append_jsonl  # noqa: E402
from bot import lab_registry as R  # noqa: E402
from bot import params as P  # noqa: E402
from bot import lab_criteria as LC  # noqa: E402

WHO = "claude-night"
PARAM_LOG = ROOT / "logs" / "param_changes.jsonl"
DEFAULTS = {"enabled": True, "model": "claude-fable-5-1", "max_forks_per_night": 6, "per_lineage_days": 2,
            "total_forks": 80, "max_realbot_per_night": 1, "run_at": "01:30", "experiment_days": 30}
# Grupos que um fork de parâmetros pode mudar. limits/tuning (segurança e tuner) e criteria (só criteria-fork) ficam
# de fora. Pais de regra (kind=rule, executados pelo rules_bot): só rule.* do tipo, gates.buy_fraction_usdt, exits.* e
# regime_filter.* (lab_registry.RULE_KEYS / RULE_FORK_GROUPS).
DIFF_GROUPS = ("gates", "exec", "exits", "hours", "ensemble", "regime_filter")
RULE_TYPES = tuple(R.RULE_KEYS)
REASON_MIN, REASON_MAX = 40, 800
TYPES_SHOWN = ("model_gated", "hybrid", "lab_h1_exits", "lab_h2_ensemble", "lab_h3_limit", "lab_h4_hours")
SYMS = R.SYMS


# ------------------------------------------------------------------ utilitários

def ncfg() -> dict:
    out = dict(DEFAULTS)
    try:
        out.update(load_cfg().get("claude_night") or {})
    except Exception:
        pass
    return out


def night_key(ts: float | None = None) -> str:
    """Noite = de meio-dia a meio-dia (BRT): a corrida das 01:30 de 04/10 pertence à noite de 03/10."""
    return (datetime.fromtimestamp(ts if ts is not None else time.time(), BRT) - timedelta(hours=12)).date().isoformat()


def real_root() -> Path:
    env = os.environ.get("JEV_TRADER_ROOT", "").strip()
    return Path(env).expanduser() if env else LAB_DIR.resolve().parents[1]


def _import_jev():
    src = real_root() / "src"
    for s in (LAB_DIR.resolve().parents[1] / "src", src):
        if (s / "jev_trader" / "rewrite.py").exists():
            if str(s) not in sys.path:
                sys.path.insert(0, str(s))
            break
    import jev_trader  # noqa: F401
    return jev_trader


def out_json(d: dict, code: int = 0) -> int:
    print(json.dumps(d, ensure_ascii=False, indent=1, default=str))
    return code


def log_action(row: dict):
    append_jsonl(PARAM_LOG, dict({"ts": time.time(), "ts_brt": brt_iso(), "who": WHO, "night": night_key()}, **row))


def tonight(key: str | None = None) -> list[dict]:
    key = key or night_key()
    out = []
    try:
        with open(PARAM_LOG) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("who") == WHO and (r.get("night") or night_key(float(r.get("ts") or 0))) == key:
                    out.append(r)
    except FileNotFoundError:
        pass
    return out


def caps_status(reg: dict | None = None) -> dict:
    c = ncfg(); reg = reg or R.load()
    acts = tonight()
    forks_all = [e for e in reg["portfolios"].values() if e.get("parent")]
    now = time.time(); blocked = {}
    for e in forks_all:
        try:
            until = datetime.fromisoformat(e["created_brt"]).timestamp() + float(c["per_lineage_days"]) * 86400
        except Exception:
            continue
        if until > now:
            blocked[e["lineage"]] = max(blocked.get(e["lineage"], 0), until)
    n_night = sum(1 for a in acts if a.get("type") == "fork_created")
    n_rb = sum(1 for a in acts if a.get("type") == "realbot_criteria_approved")
    return {"enabled": bool(c["enabled"]), "night": night_key(),
            "forks_tonight": n_night, "max_forks_per_night": int(c["max_forks_per_night"]),
            "forks_left_tonight": max(0, int(c["max_forks_per_night"]) - n_night),
            "forks_total": len(forks_all), "total_forks_cap": int(c["total_forks"]),
            "per_lineage_days": float(c["per_lineage_days"]),
            "lineages_blocked": {k: datetime.fromtimestamp(v, BRT).strftime("%m-%d %H:%M") for k, v in sorted(blocked.items())},
            "realbot_tonight": n_rb, "max_realbot_per_night": int(c["max_realbot_per_night"]),
            "journal_tonight": [a.get("file") for a in acts if a.get("type") == "claude_night_journal"]}


def input_file(path: str) -> Path:
    """Ficheiros de entrada só de <ROOT>/run/ (o Claude escreve lá; nada de ler outros ficheiros por esta via)."""
    p = Path(path)
    p = (p if p.is_absolute() else Path.cwd() / p).resolve()
    run = (ROOT / "run").resolve()
    if run not in p.parents:
        raise ValueError(f"o ficheiro tem de estar em {run}/ (recebido {p})")
    if not p.is_file():
        raise ValueError(f"{p} não existe")
    if p.stat().st_size > 256_000:
        raise ValueError(f"{p} grande demais")
    return p


def check_reason(reason: str) -> str:
    t = " ".join((reason or "").split())
    if not REASON_MIN <= len(t) <= REASON_MAX:
        raise ValueError(f"--reason com {len(t)} caracteres (entre {REASON_MIN} e {REASON_MAX}: hipótese + o que a confirma/refuta)")
    return t


def gate_write(caps: dict):
    if not caps["enabled"]:
        raise ValueError("claude_night.enabled=false em config.json: nenhuma escrita")
    if caps["forks_left_tonight"] <= 0:
        raise ValueError(f"cap da noite atingido ({caps['forks_tonight']}/{caps['max_forks_per_night']} forks)")
    if caps["forks_total"] >= caps["total_forks_cap"]:
        raise ValueError(f"cap total atingido ({caps['forks_total']}/{caps['total_forks_cap']} forks)")


def parent_meta(parent: str, reg: dict) -> dict:
    if parent in reg["portfolios"]:
        e = dict(reg["portfolios"][parent])
        e.setdefault("runner", "lab_bot")
        return e
    o = R.originals().get(parent)
    if o is None:
        raise ValueError(f"pai desconhecido: {parent} (use um nome de `context`)")
    return dict(o, name=parent)


def _leaves(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_leaves(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def check_diff(parent: str, diff, reg: dict) -> list[str]:
    """Erros do diff ANTES do resolver: grupos permitidos, limites do tipo (tuning.bounds) e clamp duro do lab
    (lab_registry.HARD) para chaves de portões; o resto dos limites fica com params.validate (create_fork)."""
    if not isinstance(diff, dict) or not diff:
        return ["--diff tem de ser um objeto JSON não vazio, ex.: {\"gates\": {\"cooldown_seconds\": 300}}"]
    errs = []
    pm = reg["portfolios"].get(parent) or R.originals().get(parent) or {}
    if pm.get("kind") == "rule":
        errs = R.check_rule_diff(pm.get("test_type"), diff)
    else:
        for g, v in diff.items():
            if g not in DIFF_GROUPS:
                errs.append(f"grupo '{g}' não permitido (permitidos: {', '.join(DIFF_GROUPS)})")
            elif g != "hours" and not isinstance(v, dict):
                errs.append(f"{g}: tem de ser um objeto")
    if errs:
        return errs
    peff, _prov, perr, _m = P.explain(parent, meta=reg["portfolios"].get(parent), use_overlay=False, registry=reg)
    if perr:
        return [f"pai {parent} com parâmetros inválidos: {'; '.join(perr[:3])}"]
    bounds = (peff.get("tuning") or {}).get("bounds") or {}
    same = True
    for path, v in _leaves({k: v for k, v in diff.items() if k != "hours"}).items():
        g, _, k = path.partition(".")
        pv = (peff.get(g) or {}).get(k) if isinstance(peff.get(g), dict) else None
        if pv != v:
            same = False
        b = bounds.get(path) or (R.HARD.get(k) if g == "gates" else None)
        if b is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
            if not float(b[0]) <= float(v) <= float(b[1]):
                errs.append(f"{path} = {v} fora dos limites [{b[0]}, {b[1]}]")
    if "hours" in diff and diff["hours"] != peff.get("hours"):
        same = False
    if same:
        errs.append("diff sem efeito: todos os valores já são os do pai")
    return errs


def criteria_parent_ok(meta: dict) -> str | None:
    model = (meta.get("model") or "").split("+")[0]
    if meta.get("kind") != "gated":
        return f"pai kind={meta.get('kind')}: critérios só em portfólios com portões de um modelo"
    if model not in P.CRITERIA_MODELS:
        return f"pai com modelo '{meta.get('model')}': só {', '.join(P.CRITERIA_MODELS)}"
    try:
        b = (json.loads((ROOT / "models.json").read_text()).get("backends") or {}).get(model) or {}
    except Exception:
        b = {}
    if not b.get("enabled") or b.get("kind") == "hosted_typesafe" or not b.get("base_url"):
        return f"backend '{model}' desligado ou sem HTTP local em models.json"
    return None


# ------------------------------------------------------------------ fork / criteria-fork

def cmd_fork(a) -> int:
    reg = R.load()
    try:
        reason = check_reason(a.reason)
        diff = json.loads(a.diff)
        meta = parent_meta(a.parent, reg)
        if meta.get("kind") not in ("gated", "ensemble", "rule"):
            raise ValueError(f"pai {a.parent} kind={meta.get('kind')}: só forks de portões/ensemble (lab_bot) ou de regras (rules_bot)")
        errs = check_diff(a.parent, diff, reg)
        if errs:
            raise ValueError("; ".join(errs))
        caps = caps_status(reg)
        if not a.dry_run:
            gate_write(caps)
        name, why = R.create_fork(a.parent, diff, f"[claude-night] {reason}", dry_run=a.dry_run,
                                  caps_override={"per_lineage_days": caps["per_lineage_days"], "total": caps["total_forks_cap"]},
                                  who=WHO, extra={"night": night_key(), "fork_kind": "params"})
    except (ValueError, KeyError, json.JSONDecodeError) as ex:
        if not a.dry_run:
            log_action({"type": "claude_night_refused", "command": "fork", "parent": a.parent, "error": str(ex)[:400]})
        return out_json({"ok": False, "command": "fork", "parent": a.parent, "error": str(ex)}, 2)
    if name is None:
        if not a.dry_run:
            log_action({"type": "claude_night_refused", "command": "fork", "parent": a.parent, "error": why})
        return out_json({"ok": False, "command": "fork", "parent": a.parent, "error": why}, 2)
    eff = None
    if not a.dry_run:
        eff = P.explain(name, meta=R.load()["portfolios"].get(name), use_overlay=False)[0]
    return out_json({"ok": True, "command": "fork", "fork": name, "status": why, "parent": a.parent, "diff": diff,
                     "effective": P.summary(eff) if eff else None,
                     "caps": {k: v for k, v in caps_status().items() if k.startswith("forks")}})


def cmd_criteria_fork(a) -> int:
    reg = R.load()
    try:
        reason = check_reason(a.reason)
        meta = parent_meta(a.parent, reg)
        bad = criteria_parent_ok(meta)
        if bad:
            raise ValueError(bad)
        clean = LC.load_file(input_file(a.criteria_file))
        peff, _prov, perr, _m = P.explain(a.parent, meta=reg["portfolios"].get(a.parent), use_overlay=False, registry=reg)
        if perr:
            raise ValueError(f"pai com parâmetros inválidos: {'; '.join(perr[:3])}")
        base, base_label = LC.base_criteria(meta.get("source"), peff)
        if LC.digest(base) == LC.digest(clean):
            raise ValueError(f"critérios iguais aos do pai ({base_label})")
        caps = caps_status(reg)
        if not a.dry_run:
            gate_write(caps)
        name, why = R.create_fork(a.parent, {}, f"[claude-night] {reason}", dry_run=a.dry_run,
                                  caps_override={"per_lineage_days": caps["per_lineage_days"], "total": caps["total_forks_cap"]},
                                  who=WHO, criteria=clean,
                                  extra={"night": night_key(), "fork_kind": "criteria", "criteria_summary": LC.summary(clean, 60),
                                         "criteria_parent": base_label})
    except (ValueError, KeyError, LC.CriteriaTextError) as ex:
        if not a.dry_run:
            log_action({"type": "claude_night_refused", "command": "criteria-fork", "parent": a.parent, "error": str(ex)[:400]})
        return out_json({"ok": False, "command": "criteria-fork", "parent": a.parent, "error": str(ex)}, 2)
    if name is None:
        if not a.dry_run:
            log_action({"type": "claude_night_refused", "command": "criteria-fork", "parent": a.parent, "error": why})
        return out_json({"ok": False, "command": "criteria-fork", "parent": a.parent, "error": why}, 2)
    return out_json({"ok": True, "command": "criteria-fork", "fork": name, "status": why, "parent": a.parent,
                     "criteria_sha256": LC.digest(clean), "criteria_file": LC.rel_path(name), "parent_criteria": base_label,
                     "summary": LC.summary(clean), "caps": {k: v for k, v in caps_status().items() if k.startswith("forks")}})


# ------------------------------------------------------------------ bot real

def realbot_paths(root: Path) -> dict:
    jt = _import_jev()  # noqa: F841
    from jev_trader.rewrite import GUARD_ENV_KEYS, _dotenv_keys, _under
    dot = _dotenv_keys(root / ".env", GUARD_ENV_KEYS + ("LOG_DIR", "CRITERIA_PATH"))
    env = os.environ
    log_dir = _under(root, env.get("LOG_DIR") or dot.get("LOG_DIR") or "logs")
    return {"decisions": log_dir / "decisions.jsonl", "paper_trades": log_dir / "paper_trades.jsonl",
            "proposals": log_dir / "rewrite_proposals", "approvals": log_dir / "rewrite_approvals.jsonl",
            "criteria": _under(root, env.get("CRITERIA_PATH") or dot.get("CRITERIA_PATH") or "config/criteria.json"),
            "experiment": _under(root, env.get("EXPERIMENT_PATH") or dot.get("EXPERIMENT_PATH") or "config/experiment.json")}


def to_realbot_criteria(doc) -> tuple[dict, list[str]]:
    """Aceita {buy, sell, hold, skip} ou o esquema criteria_*.json do lab. As instruções da ação do bot real são fixas."""
    notes = []
    if isinstance(doc, dict) and "action" in doc:
        crit = (doc.get("action") or {}).get("criteria") or {}
        out = {"buy": crit.get("buy"), "sell": crit.get("sell"), "hold": crit.get("hold"),
               "skip": (doc.get("skip_this_cycle") or {}).get("instructions")}
        if (doc.get("action") or {}).get("instructions"):
            notes.append("action.instructions ignorado: as instruções da ação do bot real são fixas (decide.ACTION_INSTRUCTIONS)")
        return out, notes
    if isinstance(doc, dict):
        return {k: doc.get(k) for k in ("buy", "sell", "hold", "skip")}, notes
    return {}, ["critérios: tem de ser um objeto"]


def cmd_realbot(a) -> int:
    root = real_root()
    try:
        _import_jev()
        from jev_trader import rewrite as RW
    except Exception as ex:
        return out_json({"ok": False, "command": "realbot-criteria", "error": f"jev_trader indisponível: {ex}"}, 2)
    refused = RW.paper_guard(root, os.environ)
    if refused:  # nada é escrito, nem log
        return out_json({"ok": False, "command": "realbot-criteria", "refused": refused, "root": str(root)}, 2)
    caps = caps_status()
    if not caps["enabled"]:
        return out_json({"ok": False, "command": "realbot-criteria", "error": "claude_night.enabled=false"}, 2)
    if caps["realbot_tonight"] >= caps["max_realbot_per_night"]:
        return out_json({"ok": False, "command": "realbot-criteria",
                         "error": f"cap da noite: {caps['realbot_tonight']}/{caps['max_realbot_per_night']} reescritas do bot real"}, 2)
    try:
        reason = check_reason(a.reason)
        doc = json.loads(input_file(a.criteria_file).read_text())
        proposed, notes = to_realbot_criteria(doc)
        from jev_trader.criteria import load_criteria
        from jev_trader.experiment import load_experiment
        from jev_trader.records import now_iso, read_jsonl
        paths = realbot_paths(root)
        current, source = load_criteria(paths["criteria"])
        today = RW.today_brt()
        review = datetime.fromisoformat(night_key()).date()
        proposal = RW.build_autonomous_proposal(
            read_jsonl(paths["decisions"]), load_experiment(paths["experiment"]), current, source, proposed,
            author=WHO, reason=reason, review_date=review, today=today, now_t=now_iso())
        paths["proposals"].mkdir(parents=True, exist_ok=True)
        fname = f"{proposal['date']}_{WHO}.json"; i = 2
        while (paths["proposals"] / fname).exists():
            fname = f"{proposal['date']}_{WHO}_{i}.json"; i += 1
        ppath = RW.write_proposal(paths["proposals"], proposal, filename=fname)
        rec = RW.approve(ppath, criteria_path=paths["criteria"], approvals_path=paths["approvals"], approver=WHO,
                         now_t=now_iso(), autonomous=True, guard_root=root, env=os.environ)
    except Exception as ex:  # RewriteError, ValueError, ExperimentError, JSON
        return out_json({"ok": False, "command": "realbot-criteria", "error": f"{type(ex).__name__}: {ex}"}, 2)
    log_action({"type": "realbot_criteria_approved", "proposal": str(ppath), "criteria_path": str(paths["criteria"]),
                "criteria_sha256": rec["criteria_sha256"], "previous": current, "criteria": proposal["proposed_criteria"],
                "reason": reason})
    au = proposal["audit"]["percentile"]
    return out_json({"ok": True, "command": "realbot-criteria", "approved": rec, "notes": notes,
                     "previous_source": source, "criteria": proposal["proposed_criteria"],
                     "audit": {k: au.get(k) for k in ("cutoff", "n_answered", "n_confident", "n_resolved", "n_mistakes")}})


# ------------------------------------------------------------------ journal / status

def cmd_journal(a) -> int:
    try:
        src = input_file(a.file)
        if src.suffix.lower() != ".md":
            raise ValueError("o diário tem de ser um .md")
        day = datetime.now(BRT).date().isoformat()
        dest = ROOT / "reviews" / f"claude_night_{day}.md"; i = 2
        while dest.exists():
            dest = ROOT / "reviews" / f"claude_night_{day}_{i}.md"; i += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "x") as f:  # "x": nunca sobrescreve
            f.write(src.read_text())
    except (ValueError, OSError) as ex:
        return out_json({"ok": False, "command": "journal", "error": str(ex)}, 2)
    log_action({"type": "claude_night_journal", "file": str(dest.relative_to(ROOT)), "source": str(src)})
    return out_json({"ok": True, "command": "journal", "file": str(dest)})


def cmd_status(a) -> int:
    acts = [{k: r.get(k) for k in ("ts_brt", "type", "portfolio", "parent", "fork_kind", "params_diff", "file", "error",
                                   "criteria_sha256") if r.get(k) is not None} for r in tonight()]
    return out_json({"caps": caps_status(), "actions_tonight": acts})


# ------------------------------------------------------------------ context

def _f(x, n=2, sign=False):
    if x is None:
        return "–"
    try:
        return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"
    except (TypeError, ValueError):
        return "–"


def family_of(n: str, m: dict) -> str:
    cls = "SOL" if (m.get("asset") or "SOL") == "SOL" else "memes"
    if m.get("parent"):
        return "forks"
    if m.get("hyp"):
        return f"{m['hyp']} {cls}"
    if m.get("kind") == "rule":
        return f"regras {cls}"
    if m.get("test_type") == "hybrid":
        return f"híbridos {cls}"
    return f"{(m.get('model') or '?').split('+')[0]} {m.get('profile') or ''} {cls}".replace("  ", " ")


def _stats_line(name, s):
    tp = s.get("timing_p")
    return (f"| {name} | {_f(s.get('pnl_pct'), 2, True)} | {_f(s.get('ex_bh'), 1, True)} | {_f(s.get('ex_exposure'), 1, True)} | "
            f"{_f(s.get('timing_usd'), 1, True)}{'' if tp is None else f' (p {tp:.2f})'} | {_f(s.get('exposure_pct'), 0)} | "
            f"{s.get('buys', 0)}/{s.get('sells', 0)} | {_f(s.get('mdd_pct'), 1)} |")


def sec_market(now, hours):
    from bot import logio
    L = [f"## Mercado ({hours:g} h)", ""]
    parts = []
    for sym in ["SOL"] + SYMS:
        p = ROOT / "data" / "prices.jsonl" if sym == "SOL" else ROOT / "data" / "meme" / "prices" / f"{sym}.jsonl"
        try:
            pts = [(float(r["ts"]), float(r["price_usd"])) for r in logio.iter_rows(p, since_ts=now - hours * 3600 - 3600)
                   if r.get("price_usd") and r.get("ts") and float(r["ts"]) >= now - hours * 3600 and not r.get("fabricated")]
        except Exception:
            pts = []
        if len(pts) < 2:
            parts.append(f"{sym} sem dados")
            continue
        pts.sort(); px = [x[1] for x in pts]
        parts.append(f"{sym} {(px[-1] / px[0] - 1) * 100:+.1f}% (faixa {(max(px) / min(px) - 1) * 100:.1f}%)")
    L.append("- " + " · ".join(parts))
    return L


def sec_portfolios(now, hours, cat, tb):
    from bot import analytics as A
    t24 = now - hours * 3600
    rows = []
    for n, m in cat.items():
        try:
            c = A.window_stats(m, tb, 0, now); d = A.window_stats(m, tb, t24, now)
        except Exception:
            continue
        if c.get("empty"):
            continue
        rows.append((n, m, c, d))
    fam = {}
    for n, m, c, d in rows:
        fam.setdefault(family_of(n, m), []).append((c, d))
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    L = ["## Famílias (média por portfólio; habilidade = excesso ajustado à exposição, soma)", "",
         f"| Família | n | PnL % {hours:g}h | PnL % acum. | ex. B&H acum. US$ | habilidade acum. US$ | exposição % | trades C/V acum. | pior MDD % |",
         "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for k in sorted(fam):
        xs = fam[k]
        cs = [c for c, _ in xs]; ds = [d for _, d in xs if not d.get("empty")]
        L.append(f"| {k} | {len(xs)} | {_f(mean([d.get('pnl_pct') or 0 for d in ds]), 2, True)} | "
                 f"{_f(mean([c.get('pnl_pct') or 0 for c in cs]), 2, True)} | {_f(sum(c.get('ex_bh') or 0 for c in cs), 1, True)} | "
                 f"{_f(sum(c.get('ex_exposure') or 0 for c in cs), 1, True)} | {_f(mean([c.get('exposure_pct') or 0 for c in cs]), 0)} | "
                 f"{sum(c.get('buys', 0) for c in cs)}/{sum(c.get('sells', 0) for c in cs)} | "
                 f"{_f(min((c.get('mdd_pct') or 0) for c in cs), 1)} |")
    hdr = ["| Portfólio | PnL % | ex. B&H US$ | habilidade US$ | timing US$ (p) | exposição % | C/V | MDD % |",
           "|---|---:|---:|---:|---:|---:|---|---:|"]
    by_skill = sorted([r for r in rows if r[2].get("ex_exposure") is not None], key=lambda r: r[2]["ex_exposure"], reverse=True)
    L += ["", "### Notáveis desde o início (por habilidade)", "", "Melhores:", ""] + hdr + \
         [_stats_line(n, c) for n, _m, c, _d in by_skill[:6]] + ["", "Piores:", ""] + hdr + \
         [_stats_line(n, c) for n, _m, c, _d in by_skill[-4:][::-1]]
    d24 = sorted([r for r in rows if not r[3].get("empty") and r[3].get("ex_exposure") is not None],
                 key=lambda r: r[3]["ex_exposure"], reverse=True)
    if d24:
        L += ["", f"### Últimas {hours:g} h (por habilidade)", ""] + hdr + [_stats_line(n, d) for n, _m, _c, d in d24[:3]] + \
             [_stats_line(n, d) for n, _m, _c, d in d24[-2:][::-1]]
    return L, {n: (m, c) for n, m, c, _d in rows}


def sec_forks(now, cat, tb, reg):
    from bot import analytics as A
    forks = sorted([e for e in reg["portfolios"].values() if e.get("parent")], key=lambda e: e.get("created_brt") or "")
    L = [f"## Forks existentes ({len(forks)}) — margem contra o pai desde a criação do fork", ""]
    if not forks:
        return L + ["- nenhum."]
    L += ["| Fork | quem | o que mudou | idade d | PnL fork−pai pp | habilidade fork−pai US$ | trades f/p | rótulo |",
          "|---|---|---|---:|---:|---:|---|---|"]
    shown = forks[-30:]
    for e in shown:
        m = cat.get(e["name"]); par = cat.get(e["parent"])
        what = R.describe_fork(e)[:90]
        age = (now - m["start_ts"]) / 86400 if m else None
        mp = ms = None; tr = "–"
        if m and par:
            try:
                f = A.window_stats(m, tb, m["start_ts"], now); p = A.window_stats(par, tb, m["start_ts"], now)
                if not f.get("empty") and not p.get("empty"):
                    mp = f["pnl_pct"] - p["pnl_pct"]
                    ms = (f.get("ex_exposure") or 0) - (p.get("ex_exposure") or 0)
                    tr = f"{f.get('trades', 0)}/{p.get('trades', 0)}"
            except Exception:
                pass
        L.append(f"| {e['name']} (pai {e['parent']}) | {R.fork_who(e)} | {what} | {_f(age, 1)} | {_f(mp, 2, True)} | "
                 f"{_f(ms, 1, True)} | {tr} | {e.get('report_label') or '–'} |")
    if len(forks) > len(shown):
        L.append(f"- (+{len(forks) - len(shown)} forks mais antigos omitidos)")
    reasons = [e for e in shown if R.fork_who(e) == WHO][-8:]
    if reasons:
        L += ["", "Hipóteses dos forks do Claude (mais recentes):"]
        L += [f"- {e['name']}: {str(e.get('reason') or '').replace('[claude-night] ', '')[:220]}" for e in reasons]
    return L


def _audit_rows(now, hours):
    from bot import logio
    t0 = now - hours * 3600
    groups = {}
    for cls, fn in (("SOL", "decisions.jsonl"), ("memes", "meme_decisions.jsonl")):
        for r in logio.iter_rows(ROOT / "logs" / fn, since_ts=t0 - 60):
            raw = str(r.get("model") or "von")
            if float(r.get("ts") or 0) < t0 or raw == "rule" or "+" in raw:
                continue  # regras e híbridos (reaproveitam a chamada do modelo; contariam a mesma chamada duas vezes)
            model = raw
            key = f"{model}{' · v2' if r.get('portfolio') == 'v2' else ''} {cls}"
            r = dict(r, model=model)
            groups.setdefault(key, []).append(r)
    for r in logio.iter_rows(ROOT / "logs" / "lab_decisions.jsonl", since_ts=t0 - 60, contains="criteria_sha256"):
        if float(r.get("ts") or 0) < t0 or not r.get("criteria_sha256"):
            continue
        groups.setdefault(f"fork {r.get('portfolio')} ({r.get('criteria_model')})", []).append(r)
    return groups


def _price_series(now, hours):
    from bot import confidence_audit as CA, logio
    # + janela da banda por volatilidade (review.band_window_s, 3 dias) antes da janela auditada
    since = now - hours * 3600 - 3600 - float(CA.review_cfg(load_cfg())["band_window_s"])
    out = {}
    try:
        out.update(CA.build_series(logio.iter_rows(ROOT / "data" / "prices.jsonl", since_ts=since), asset="SOL"))
    except Exception:
        pass
    for s in SYMS:
        p = ROOT / "data" / "meme" / "prices" / f"{s}.jsonl"
        if p.exists():
            out.update(CA.build_series(logio.iter_rows(p, since_ts=since), asset=s))
    return out


def sec_mistakes(now, hours):
    from bot import confidence_audit as CA
    rc = CA.review_cfg(load_cfg())
    groups = _audit_rows(now, hours); prices = _price_series(now, hours)
    L = [f"## Erros confiantes por família de modelo ({hours:g} h; corte P{rc['confidence_percentile']:g} por família, "
         f"erro = {int(rc['horizon_s'] / 60)} min contra a chamada além da banda "
         + (f"por ativo = {rc['band_k']:g} × mediana |ret. 15 min| em {rc['band_window_s'] / 86400:g} d" if rc["band_mode"] == "vol"
            else f"{rc['band'] * 100:.1f}%") + "; palavras por lift = % erros − % acertos)", ""]
    if not groups:
        return L + ["- sem decisões na janela."]
    for key in sorted(groups):
        rows = CA.dedupe_calls(groups[key])
        a = CA.audit(rows, prices=prices, percentile_p=rc["confidence_percentile"], horizon_s=rc["horizon_s"],
                     band=rc["band"], tolerance_s=rc["tolerance_s"], candidates="chosen", tie_rule=rc["tie_rule"],
                     lift_params=CA.lift_kwargs(rc), **CA.band_kwargs(rc))
        ans = [r for r in rows if CA.is_answered(r)]
        if not ans:
            L.append(f"- **{key}**: {len(rows)} chamadas, nenhuma respondida (fail-closed)."); continue
        act = Counter(r.get("chosen_action") for r in ans)
        L.append(f"- **{key}**: corte {_f(a['cutoff'], 3)} ({a['rule']}); {a['n_answered']} respondidas "
                 f"(buy {act['buy']}/sell {act['sell']}/hold {act['hold']}), {a['n_confident']} confiantes buy/sell → "
                 f"{a['n_resolved']} resolvidas: **{a['n_mistakes']} erros** ({a['mistake_episodes']} episódios), "
                 f"{a['n_correct']} acertos, {a['n_flat']} flat; hit {_f((a['hit_rate'] or 0) * 100, 0)}%.")
        if a["band_by_asset"]:
            L.append("  - banda usada: " + ", ".join(f"{k} {b * 100:.3f}% ({a['bands'][k].get('source')})"
                                                     for k, b in sorted(a["band_by_asset"].items())))
        outs = a.get("outcomes") or []
        mis = [o for o in outs if o["outcome"] == "mistake"]; cor = [o for o in outs if o["outcome"] == "correct"]
        if mis:
            states = Counter((o["side"], o["state"]) for o in mis).most_common(3)
            L.append("  - estados dos erros: " + "; ".join(f"{s} `{st}` ×{c}" for (s, st), c in states))
            rows_l = CA.word_lift(outs, **CA.lift_kwargs(rc))
            pc = lambda x: "–" if x is None else f"{x * 100:.0f}%"
            fmtw = lambda r: f"{r['word']} {pc(r['err_share'])}/{pc(r['ok_share'])} (lift {_f(r['lift'], 2, sign=True)})"
            L.append("  - adjetivos (% nos erros / % nos acertos): mais nos erros " + ", ".join(fmtw(r) for r in rows_l[:5])
                     + (" · mais nos acertos " + ", ".join(fmtw(r) for r in rows_l[::-1][:3]) if cor else "")
                     + f" · elegíveis p/ frases (lift ≥ {rc['lift_min']:g}, suporte): {', '.join(a['lift_words']['all']) or '–'}")
        rest = [r for r in ans if r.get("chosen_action") not in ("buy", "sell") or CA._conf(r) is None
                or (a["cutoff"] is not None and CA._conf(r) < a["cutoff"])]
        confs = sorted(CA._conf(r) for r in ans)
        L.append(f"  - resto: {len(rest)} chamadas abaixo do corte ou hold; conf p50 {_f(CA.percentile(confs, 50), 3)}, "
                 f"máx {_f(confs[-1], 3)}; fail-closed {len(rows) - len(ans)}.")
    return L


def sec_criteria(reg):
    L = ["## Critérios em uso (texto enviado ao modelo; sem números)", ""]

    def line(label, c):
        a = c["action"]
        return (f"- **{label}**: instr. «{a['instructions']}» · buy «{a['criteria']['buy']}» · sell «{a['criteria']['sell']}» · "
                f"hold «{a['criteria']['hold']}» · skip «{c['skip_this_cycle']['instructions']}»")
    for label, fn in (("baseline (von/laya/poorjev SOL e memes)", "criteria_baseline.json"), ("v2 (portfólio v2)", "criteria_v2.json")):
        try:
            L.append(line(label, LC.load_file(ROOT / fn)))
        except Exception as ex:
            L.append(f"- {label}: erro {ex}")
    for e in [e for e in reg["portfolios"].values() if (e.get("params_diff") or {}).get("criteria")]:
        try:
            c, sha = LC.load_ref(e["params_diff"]["criteria"])
            L.append(line(f"{e['name']} (fork de critérios, {sha[:10]})", c))
        except Exception as ex:
            L.append(f"- {e['name']}: critérios inválidos ({ex}) → hold")
    try:
        _import_jev()
        from jev_trader.criteria import load_criteria
        from jev_trader.decide import ACTION_INSTRUCTIONS
        c, src = load_criteria(realbot_paths(real_root())["criteria"])
        L.append(f"- **bot real** ({'config/criteria.json' if src == 'file' else 'frases do artigo'}): instr. fixa "
                 f"«{ACTION_INSTRUCTIONS}» · buy «{c['buy']}» · sell «{c['sell']}» · hold «{c['hold']}» · skip «{c['skip']}»")
    except Exception as ex:
        L.append(f"- bot real: indisponível ({type(ex).__name__}: {str(ex)[:120]})")
    return L


def sec_caps(reg):
    c = caps_status(reg)
    bl = c["lineages_blocked"]
    return ["## Limites (claude_night)", "",
            f"- Esta noite ({c['night']}): {c['forks_tonight']}/{c['max_forks_per_night']} forks (fork + criteria-fork); "
            f"bot real {c['realbot_tonight']}/{c['max_realbot_per_night']}; total {c['forks_total']}/{c['total_forks_cap']} forks; "
            f"1 fork por linhagem a cada {c['per_lineage_days']:g} dias; habilitado: {'sim' if c['enabled'] else 'NÃO'}.",
            f"- Linhagens bloqueadas até (BRT): " + (", ".join(f"{k} {v}" for k, v in bl.items()) if bl else "nenhuma")]


def sec_tunables():
    L = ["## Parâmetros ajustáveis por tipo (fork --diff; limites = tuning.bounds, senão validação dura)", "",
         f"- Grupos permitidos no diff (pais com portões/ensemble): {', '.join(DIFF_GROUPS)} (nunca limits/tuning; critérios só por criteria-fork). "
         "Tetos duros: compra ≤ 50% do USDT, ≤ 8 trades/h, exposição ≤ 100%, sem alavancagem; cooldown 30–3600 s."]
    by_list: dict = {}
    for t in TYPES_SHOWN:
        try:
            eff, _prov, _errs = P.type_view(t)
        except Exception:
            continue
        tu = eff.get("tuning") or {}
        b = tu.get("bounds") or {}
        ps = [f"{p}{' [' + ', '.join(f'{x:g}' for x in b[p]) + ']' if p in b else ''}" for p in tu.get("params") or []]
        by_list.setdefault(", ".join(ps) or "–", []).append(t)
    for ps, ts in by_list.items():
        L.append(f"- {', '.join(ts)}: {ps}")
    L.append("- Saídas (exits.*) e limite (exec.*) só têm efeito com exits.enabled=true / exec.mode=limit no efetivo; "
             "hours = lista de horas BRT; regime_filter = só compra com SOL em alta.")
    L += ["", "Regras (pais grid_sol_2pct, rsi_sol_1h, {SYM}_rule_regime[_full], {SYM}_rule_donch_regime[_full] e os seus "
          "forks; executadas pelo rules_bot em barras de 1 h). Diff só em `rule.*` do tipo, `gates.buy_fraction_usdt`, "
          "`exits.*` (TP/SL/trailing a cada ciclo; enabled=true usa os níveis do ativo) e `regime_filter.*` (compras só com "
          "SOL EMA12>26); nada de cooldown/trades/h/exec/hours:"]
    fmt = lambda b, p: f" [{', '.join(f'{x:g}' for x in b[p])}]" if p in b else ""
    for t in RULE_TYPES:
        try:
            eff, _prov, _errs = P.type_view(t, asset_class="sol" if t in ("rule_grid", "rule_rsi") else "meme")
        except Exception:
            continue
        b = (eff.get("tuning") or {}).get("bounds") or {}
        cur = eff.get("rule") or {}
        ks = ", ".join(f"rule.{k}={cur.get(k)}{fmt(b, 'rule.' + k)}" for k in R.RULE_KEYS[t])
        bf = (eff.get("gates") or {}).get("buy_fraction_usdt")
        L.append(f"- {t}: {ks}; gates.buy_fraction_usdt={bf:g}{fmt(b, 'gates.buy_fraction_usdt')}"
                 + (" (variante _full: 1, limites [0.05, 1])" if t in ("rule_regime", "rule_donchian") else ""))
    return L


def sec_realbot():
    L = ["## Bot real (paper, livro da carteira)", ""]
    try:
        _import_jev()
        from jev_trader.score import scoreboard
        from jev_trader.experiment import load_experiment
        from jev_trader.records import read_jsonl
        from jev_trader import rewrite as RW
        root = real_root(); paths = realbot_paths(root)
        exp = load_experiment(paths["experiment"])
        dec = read_jsonl(paths["decisions"])
        rb = scoreboard(dec, read_jsonl(paths["paper_trades"]), exp)
        ph, hr, dd, tr = rb["pnl_vs_hold"], rb["hit_rate"], rb["drawdown"], rb["trades"]
        L.append(f"- PnL contra segurar o livro: {ph['usd']:+.2f} US$ ({ph['pct']:+.2f}%); hit a 15 min {hr['hits']}/{hr['resolved']}; "
                 f"MDD {dd['pct']:.2f}%; trades {tr['total']} ({tr['buy']}C/{tr['sell']}V); modo {exp.mode}.")
        try:
            from jev_trader.criteria import load_criteria
            cur, src = load_criteria(paths["criteria"])
            day = datetime.fromisoformat(night_key()).date()
            pr = RW.build_proposal(dec, exp, cur, src, review_date=day, today=day, now_t=brt_iso())
            au = pr["audit"]["percentile"]
            L.append(f"- Auditoria do dia {day} (P90 nearest-rank, só ações que passaram os portões): corte {_f(au['cutoff'], 3)}, "
                     f"{au['n_answered']} respondidas, {au['n_confident']} confiantes, {au['n_resolved']} resolvidas, "
                     f"**{au['n_mistakes']} erros**, {au['n_correct']} acertos (banda {au['band'] * 100:.3f}%, "
                     f"{pr['audit']['band_mode']}); palavras com lift (compra/venda): "
                     f"{', '.join(au['lift_words']['buy']) or '–'} / {', '.join(au['lift_words']['sell']) or '–'}.")
        except Exception as ex:
            L.append(f"- auditoria indisponível: {str(ex)[:120]}")
        guard = RW.paper_guard(root, os.environ)
        L.append(f"- realbot-criteria: {'permitido (paper confirmado)' if not guard else 'RECUSADO: ' + '; '.join(guard)}.")
    except Exception as ex:
        L.append(f"- indisponível: {type(ex).__name__}: {str(ex)[:160]}")
    return L


def build_context(hours: float = 24.0) -> str:
    from bot import analytics as A
    now = time.time(); c = ncfg()
    cfg = load_cfg()
    try:
        d1 = datetime.fromisoformat(((cfg.get("experiment") or {}).get("day1_start_brt"))).timestamp()
        day = int((now - d1) / 86400) + 1
    except Exception:
        day = None
    cat, reg = A.catalog(); tb = A.load_trades()
    L = [f"# Contexto da noite — {brt_iso()[:16].replace('T', ' ')} BRT · dia {day or '?'}/{c['experiment_days']} · paper only", "",
         "Legenda: PnL % = variação do valor; ex. B&H = PnL − PnL de segurar o livro inicial; habilidade = PnL − exposição média × "
         "retorno do ativo (o que não é beta); timing = parte da habilidade vinda de mudar a exposição (p = placebo por rotação; "
         "< 0,05 sugere sinal); C/V = compras/vendas; MDD = maior queda. Amostras de 1–3 dias são pequenas e autocorrelacionadas.", ""]
    for sec in (lambda: sec_market(now, hours), lambda: sec_portfolios(now, hours, cat, tb)[0], lambda: sec_forks(now, cat, tb, reg),
                lambda: sec_mistakes(now, hours), lambda: sec_criteria(reg), lambda: sec_caps(reg), sec_tunables, sec_realbot):
        try:
            L += sec() + [""]
        except Exception as ex:
            L += [f"- secção indisponível: {type(ex).__name__}: {str(ex)[:160]}", ""]
    txt = "\n".join(L)
    return txt + f"\n_{len(txt)} caracteres ≈ {len(txt) // 4} tokens._\n"


def cmd_context(a) -> int:
    print(build_context(a.hours))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="night_cli.py", description="Revisão noturna autónoma (paper only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("context"); p.add_argument("--hours", type=float, default=24.0)
    p = sub.add_parser("fork"); p.add_argument("--parent", required=True); p.add_argument("--diff", required=True)
    p.add_argument("--reason", required=True); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("criteria-fork"); p.add_argument("--parent", required=True); p.add_argument("--criteria-file", required=True)
    p.add_argument("--reason", required=True); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("realbot-criteria"); p.add_argument("--criteria-file", required=True); p.add_argument("--reason", required=True)
    p = sub.add_parser("journal"); p.add_argument("--file", required=True)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    return {"context": cmd_context, "fork": cmd_fork, "criteria-fork": cmd_criteria_fork, "realbot-criteria": cmd_realbot,
            "journal": cmd_journal, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
