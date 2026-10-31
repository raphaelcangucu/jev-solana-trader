import json, gzip, re, glob, collections, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
BRT = timezone(timedelta(hours=-3))
LAB = Path.home()/"jev-lab/code/research/paper-lab"; REPO = LAB.parents[1]
out = {}

def num(s):
    s = s.replace("*", "").replace("%", "").strip()
    try: return float(s)
    except: return None

def table(md):
    rows = []
    for line in md.splitlines():
        if line.startswith("| ") and not line.startswith("| Portfólio") and not line.startswith("|---"):
            c = [x.strip() for x in line.strip("|").split("|")]
            if len(c) >= 18: rows.append(c)
    return rows

# 1) dias
days = []
for f in sorted(glob.glob(str(LAB/"reports/2026-10-*.md"))):
    md = Path(f).read_text(); day = Path(f).stem
    part = md.split("## Veredito")[0]
    rows = [r for r in table(part)]
    recs = [dict(name=r[0], group=r[1], pnl=num(r[5]), pct=num(r[6]), exb=num(r[7]), expo=num(r[8]), skill=num(r[9]), trades=r[12]) for r in rows]
    recs = [r for r in recs if r["pct"] is not None]
    act = [r for r in recs if r["pnl"] != 0]
    best = max(recs, key=lambda r: r["pct"]); worst = min(recs, key=lambda r: r["pct"])
    m = re.search(r"dia (\d+) do experimento", md)
    days.append(dict(day=day, n=len(recs), pos=sum(1 for r in recs if r["pnl"] > 0), neg=sum(1 for r in recs if r["pnl"] < 0),
                     sum_pnl=round(sum(r["pnl"] for r in recs), 2), best=best, worst=worst, exp_day=int(m.group(1)) if m else None,
                     ntr=sum(int(re.match(r"(\d+)", r["trades"]).group(1)) for r in recs if re.match(r"\d+", r["trades"]))))
out["days"] = days

# 2) preço SOL diário (fecho BRT) a partir dos ficheiros de equity do baseline (atuais + arquivados)
px = {}
files = sorted(glob.glob(str(LAB/"archive/data/equity_baseline.*"))) + [str(LAB/"data/equity_baseline.jsonl")]
for f in files:
    op = gzip.open if f.endswith(".gz") else open
    with op(f, "rt") as h:
        for l in h:
            try: d = json.loads(l)
            except: continue
            if d.get("price"):
                k = datetime.fromtimestamp(d["ts"], BRT).strftime("%Y-%m-%d")
                px.setdefault(k, [None, None, None, None])
                p = d["price"]; v = px[k]
                if v[0] is None: v[0] = p
                v[1] = max(v[1] or p, p); v[2] = min(v[2] or p, p); v[3] = p
out["sol_daily"] = {k: v for k, v in sorted(px.items())}

# 3) acumulado final
md = (LAB/"reports/cumulative.md").read_text()
out["cumulative_generated"] = re.search(r"até (\S+) \(BRT\)", md).group(1)
rows = table(md.split("## ")[0] if "## " in md else md)
cum = [dict(name=r[0], group=r[1], start=r[2], v0=num(r[3]), v1=num(r[4]), pnl=num(r[5]), pct=num(r[6]), exb=num(r[7]), expo=num(r[8]), skill=num(r[9]), timing=r[10], trades=r[12], fees=num(r[14]), mdd=num(r[16])) for r in rows]
cum = [c for c in cum if c["pct"] is not None]
out["cum_n"] = len(cum); out["cum_pos"] = sum(1 for c in cum if c["pnl"] > 0); out["cum_beat_bh"] = sum(1 for c in cum if (c["exb"] or 0) > 0)
out["cum_sum"] = round(sum(c["pnl"] for c in cum), 2)
cum.sort(key=lambda c: c["pct"], reverse=True)
out["top"] = cum[:12]; out["bottom"] = cum[-8:][::-1]
out["top_skill"] = sorted(cum, key=lambda c: c["skill"] or -1e9, reverse=True)[:10]
keys = ["baseline", "relaxed", "laya_relaxed", "poorjev_relaxed", "jev_article", "jev_relaxed", "rsi_sol_1h", "grid_sol_2pct", "hybrid_von_relaxed_cap2", "relaxed__fork1", "meme_FARTCOIN_relaxed", "h1_exits_FARTCOIN_poorjev_relaxed", "poorjev_relaxed__fork4", "relaxed_expcap50", "v2"]
out["refs"] = {c["name"]: c for c in cum if c["name"] in keys}
# grupos
g = collections.defaultdict(list)
for c in cum: g[c["group"]].append(c["pct"])
out["groups"] = {k: dict(n=len(v), avg=round(sum(v)/len(v), 2), pos=sum(1 for x in v if x > 0)) for k, v in g.items()}

# 4) vereditos
v = json.loads((LAB/"data/nightly/verdicts.json").read_text())
cnt = collections.Counter(x["verdict"] for x in v["verdicts"].values())
out["verdicts"] = dict(ts=v["ts_brt"], counts=cnt, losers=[k for k, x in v["verdicts"].items() if x["verdict"] != "inconclusivo"])
out["verdict_reasons"] = {k: x["reason"] for k, x in v["verdicts"].items() if x["verdict"] != "inconclusivo"}

# 5) forks
reg = json.loads((LAB/"data/lab/registry.json").read_text())["portfolios"]
forks = [e for e in reg.values() if e.get("parent")]
out["forks_n"] = len(forks); out["lab_n"] = len(reg)
out["forks_by_who"] = collections.Counter(e.get("who") for e in forks)
out["forks_by_day"] = collections.Counter((e.get("created_brt") or "")[:10] for e in forks)
out["forks_sample"] = [dict(name=e["name"], who=e.get("who"), created=e.get("created_brt", "")[:16], diff=e.get("params_diff"), reason=e.get("reason")) for e in sorted(forks, key=lambda e: e.get("created_brt", ""))]

# 6) bot real: valor diário dos livros A e B (marcado ao fecho do SOL)
def book_series(path):
    s = {}
    for l in open(path):
        d = json.loads(l); k = d["t"][:10]; s[k] = d["book_after"]
    return s
for lab_, p in (("A", REPO/"logs/paper_trades.jsonl"), ("B", REPO/"logs/paper_b/paper_trades.jsonl")):
    s = book_series(p); last = {"sol": 0.017392206, "usdt": 50.00929}; ser = []
    for k, v in sorted(out["sol_daily"].items()):
        if k < "2026-09-30" or k > "2026-10-30": continue
        last = s.get(k, last); ser.append([k, round(last["sol"]*v[3] + last["usdt"], 3), round(last["sol"]*v[3]/(last["sol"]*v[3]+last["usdt"]), 3)])
    out[f"book_{lab_}"] = ser
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ["cum_n", "cum_pos", "cum_beat_bh", "cum_sum", "verdicts", "forks_n", "forks_by_who", "lab_n", "cumulative_generated"]}, default=str, ensure_ascii=False))
for d in days: print(d["day"], d["exp_day"], d["n"], d["pos"], d["neg"], d["sum_pnl"], d["ntr"], d["best"]["name"], d["best"]["pct"], d["worst"]["name"], d["worst"]["pct"], out["sol_daily"].get(d["day"], [None]*4)[3])
print(list(out["sol_daily"].items())[:3])
print(out["book_A"][::5]); print(out["book_B"][::5])
