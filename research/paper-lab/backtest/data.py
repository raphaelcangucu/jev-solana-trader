"""Dados históricos públicos (sem chaves) para o backtest, com cache em gzip e relatório de cobertura.

Fontes (todas públicas, com pausas e novas tentativas):

- SOL 1 m: Coinbase Exchange `SOL-USD` (a mesma casa da marcação ao vivo do sol_bot, `fetch_sol_price`).
- SOL 1 s: Binance `SOLUSDT` (ficheiros diários de data.binance.vision + API para o dia corrente), reduzido a uma
  grelha de 5 s de "último preço". Serve para o estado do SOL (o histórico ao vivo tem ~6 marcas por minuto) e para o
  bot real, que lê as velas de 1 m da Binance.
- Memecoins 1 m: Bybit spot (BONK, WIF, POPCAT, PNUT, MEW, GOAT) e KuCoin (FARTCOIN, que não existe na Bybit spot);
  a Gate.io (fonte da marcação ao vivo) só guarda 10 000 pontos de 1 m (~7 dias), por isso fica como verificação de base
  na parte final da janela.
- 1 h: os mesmos fetchers do rules_bot (`rules_engine.fetch_coinbase_sol_1h`, `fetch_gate_1h`).

Velas: `ts` = início da vela (epoch s, UTC). O preço "agora" num instante T é o fecho da vela que começa em T − 60.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

UA = {"User-Agent": "paper-lab-backtest/0.1 (sim-only)"}
MEME_SOURCES = {
    "BONK": [("bybit", "BONKUSDT"), ("kucoin", "BONK-USDT")],
    "WIF": [("bybit", "WIFUSDT"), ("kucoin", "WIF-USDT")],
    "POPCAT": [("bybit", "POPCATUSDT"), ("kucoin", "POPCAT-USDT")],
    "FARTCOIN": [("kucoin", "FARTCOIN-USDT"), ("bybit", "FARTCOINUSDT")],
    "PNUT": [("bybit", "PNUTUSDT"), ("kucoin", "PNUT-USDT")],
    "MEW": [("bybit", "MEWUSDT"), ("kucoin", "MEW-USDT")],
    "GOAT": [("bybit", "GOATUSDT"), ("kucoin", "GOAT-USDT")],
}
MAX_FFILL_MIN = 5          # lacunas curtas (≤ 5 min) preenchidas com o último fecho
MIN_COVERAGE = 0.90        # abaixo disto o ativo fica inutilizável


def log(msg: str, logf=None):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logf:
        with open(logf, "a") as f:
            f.write(line + "\n")


# ------------------------------------------------------------------ HTTP

_LAST = {}


def http_get(url: str, *, host_gap: float = 0.25, retries: int = 6, timeout: float = 30.0) -> bytes:
    """GET com pausa mínima por host e novas tentativas com recuo (429/5xx/erros de rede)."""
    host = urllib.parse.urlparse(url).netloc
    err = None
    for attempt in range(retries):
        wait = _LAST.get(host, 0) + host_gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _LAST[host] = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            err = f"http_{e.code}"
            if e.code in (400, 404, 451):
                raise RuntimeError(f"{err} {url[:120]}") from None
        except Exception as e:  # rede
            err = f"{type(e).__name__}: {e}"
        time.sleep(min(60, 2 * (attempt + 1) ** 2))
    raise RuntimeError(f"falhou {url[:120]}: {err}")


def get_json(url: str, **kw):
    return json.loads(http_get(url, **kw).decode())


# ------------------------------------------------------------------ fetchers 1 m

def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_coinbase_1m(product: str, start: int, end: int, progress=None) -> list[tuple]:
    rows = []
    cur = start
    while cur < end:
        e = min(end, cur + 300 * 60)
        url = (f"https://api.exchange.coinbase.com/products/{product}/candles?granularity=60"
               f"&start={_iso(cur)}&end={_iso(e - 60)}")
        for c in get_json(url, host_gap=0.2):
            t, lo, hi, o, cl, vol = c
            if start <= int(t) < end:
                rows.append((int(t), float(o), float(hi), float(lo), float(cl), float(vol)))
        cur = e
        if progress:
            progress(cur)
    return rows


def fetch_bybit_1m(symbol: str, start: int, end: int, progress=None) -> list[tuple]:
    rows = []
    cur = start
    while cur < end:
        e = min(end, cur + 1000 * 60)
        url = (f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval=1"
               f"&start={cur * 1000}&end={(e - 60) * 1000}&limit=1000")
        d = get_json(url, host_gap=0.15)
        if d.get("retCode") != 0:
            raise RuntimeError(f"bybit {symbol}: {d.get('retMsg')}")
        for c in d["result"]["list"]:
            t = int(c[0]) // 1000
            if start <= t < end:
                rows.append((t, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])))
        cur = e
        if progress:
            progress(cur)
    return rows


def fetch_kucoin_1m(symbol: str, start: int, end: int, progress=None) -> list[tuple]:
    rows = []
    cur = start
    while cur < end:
        e = min(end, cur + 1500 * 60)
        url = f"https://api.kucoin.com/api/v1/market/candles?type=1min&symbol={symbol}&startAt={cur}&endAt={e - 1}"
        d = get_json(url, host_gap=0.35)
        if str(d.get("code")) != "200000":
            raise RuntimeError(f"kucoin {symbol}: {d.get('msg')}")
        for c in d["data"]:
            t = int(c[0])
            if start <= t < end:
                # KuCoin: [time, open, close, high, low, volume, turnover]
                rows.append((t, float(c[1]), float(c[3]), float(c[4]), float(c[2]), float(c[5])))
        cur = e
        if progress:
            progress(cur)
    return rows


def fetch_gate_1m(pair: str, start: int, end: int) -> list[tuple]:
    """Gate.io guarda só os últimos 10 000 pontos de 1 m: pede só essa parte (verificação de base)."""
    lo = max(start, int(time.time()) // 60 * 60 - 9990 * 60)
    rows = []
    cur = lo
    while cur < end:
        e = min(end, cur + 990 * 60)
        url = f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1m&from={cur}&to={e - 60}"
        try:
            d = get_json(url, host_gap=0.2)
        except RuntimeError:
            cur = e
            continue
        for c in d if isinstance(d, list) else []:
            t = int(float(c[0]))
            if start <= t < end:
                rows.append((t, float(c[5]), float(c[3]), float(c[4]), float(c[2]), float(c[6])))
        cur = e
    return rows


# ------------------------------------------------------------------ Binance 1 s → grelha de 5 s

def _binance_day_rows(symbol: str, day: str, raw_dir: Path) -> list[tuple]:
    """(open_s, close) das velas de 1 s de um dia (zip diário de data.binance.vision, guardado em raw_dir)."""
    zp = raw_dir / f"{symbol}-1s-{day}.zip"
    if not zp.exists():
        blob = http_get(f"https://data.binance.vision/data/spot/daily/klines/{symbol}/1s/{symbol}-1s-{day}.zip",
                        host_gap=0.3)
        zp.write_bytes(blob)
    out = []
    with zipfile.ZipFile(zp) as z:
        with z.open(z.namelist()[0]) as f:
            for line in io.TextIOWrapper(f):
                p = line.split(",")
                if not p or not p[0].strip().isdigit():
                    continue
                t = int(p[0])
                t = t // 1_000_000 if t > 10**14 else t // 1000   # µs (desde 2025) ou ms
                out.append((t, float(p[4])))
    return out


def _binance_api_1s(symbol: str, start: int, end: int) -> list[tuple]:
    out = []
    cur = start
    while cur < end:
        url = (f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1s"
               f"&startTime={cur * 1000}&endTime={(min(end, cur + 1000) - 1) * 1000}&limit=1000")
        d = get_json(url, host_gap=0.12)
        if not d:
            cur += 1000
            continue
        for c in d:
            out.append((int(c[0]) // 1000, float(c[4])))
        cur = max(cur + 1, int(d[-1][0]) // 1000 + 1)
    return out


def fetch_binance_grid(symbol: str, start: int, end: int, raw_dir: Path, grid: int = 5, logf=None) -> tuple[np.ndarray, np.ndarray]:
    """Grelha de `grid` s: preço em T = fecho da última vela de 1 s com abertura < T. NaN sem negócio há > 120 s."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    d0 = datetime.fromtimestamp(start, tz=timezone.utc).date()
    d1 = datetime.fromtimestamp(end - 1, tz=timezone.utc).date()
    today = datetime.now(tz=timezone.utc).date()
    day = d0
    while day <= d1:
        ds = day.isoformat()
        try:
            if day >= today:
                raise RuntimeError("dia corrente")
            rows += _binance_day_rows(symbol, ds, raw_dir)
        except RuntimeError as e:
            a = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
            log(f"binance {symbol} {ds}: sem ficheiro diário ({str(e)[:60]}); API 1 s", logf)
            rows += _binance_api_1s(symbol, max(a, start - 60), min(a + 86400, end))
        day += timedelta(days=1)
    rows = sorted(set(r for r in rows if start - 3600 <= r[0] < end))
    t = np.array([r[0] for r in rows], dtype=np.int64)
    c = np.array([r[1] for r in rows], dtype=float)
    g = np.arange(start, end + 1, grid, dtype=np.int64)
    idx = np.searchsorted(t, g, side="left") - 1          # última vela com abertura < T
    px = np.where(idx >= 0, c[np.clip(idx, 0, None)], np.nan)
    age = g - np.where(idx >= 0, t[np.clip(idx, 0, None)], -10**9)
    px = np.where(age <= 120, px, np.nan)
    return g, px


# ------------------------------------------------------------------ cache

def save_rows(path: Path, rows: list[tuple]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "volume"])
        for r in rows:
            w.writerow(r)


def load_rows(path: Path) -> list[tuple]:
    with gzip.open(path, "rt") as f:
        rd = csv.reader(f)
        next(rd)
        return [(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in rd]


def cached(path: Path, meta_need: dict, fetch, logf=None):
    """Lê `path` se o .meta.json cobrir o pedido; senão chama fetch() e grava."""
    mp = path.with_suffix(".meta.json")
    if path.exists() and mp.exists():
        m = json.loads(mp.read_text())
        if m.get("start") <= meta_need["start"] and m.get("end") >= meta_need["end"] and m.get("source") == meta_need.get("source"):
            rows = [r for r in load_rows(path) if meta_need["start"] <= r[0] < meta_need["end"]]
            return rows, True
    rows = fetch()
    save_rows(path, rows)
    mp.write_text(json.dumps(dict(meta_need, fetched_at=time.time(), n=len(rows))))
    return rows, False


# ------------------------------------------------------------------ cobertura e séries

def coverage(rows: list[tuple], start: int, end: int, step: int = 60) -> dict:
    ts = [r[0] for r in rows if start <= r[0] < end]
    uniq = sorted(set(ts))
    exp = (end - start) // step
    gaps = []
    prev = start - step
    for t in uniq + [end]:
        if t - prev > step:
            gaps.append((t - prev) // step - 1)
        prev = t
    return {"expected": exp, "present": len(uniq), "coverage": round(len(uniq) / exp, 5) if exp else 0.0,
            "duplicates": len(ts) - len(uniq), "gaps": len(gaps), "missing": int(sum(gaps)),
            "max_gap_min": int(max(gaps)) if gaps else 0,
            "gaps_gt_ffill": int(sum(1 for g in gaps if g > MAX_FFILL_MIN))}


class MinuteSeries:
    """OHLC por minuto alinhado a uma grelha [t0, t1). Lacunas ≤ MAX_FFILL_MIN preenchidas com o último fecho
    (o=h=l=c); lacunas maiores ficam NaN (o passo é saltado: 'sem preço', como skipped_no_price ao vivo)."""

    def __init__(self, rows: list[tuple], t0: int, t1: int, max_ffill: int = MAX_FFILL_MIN):
        self.t0, self.t1 = t0, t1
        n = (t1 - t0) // 60
        self.o = np.full(n, np.nan); self.h = np.full(n, np.nan); self.l = np.full(n, np.nan)
        self.c = np.full(n, np.nan); self.v = np.zeros(n)
        seen = set()
        for t, o, h, l, c, v in sorted(rows):
            i = (t - t0) // 60
            if 0 <= i < n and (t - t0) % 60 == 0 and i not in seen:
                seen.add(i)
                self.o[i], self.h[i], self.l[i], self.c[i], self.v[i] = o, h, l, c, v
        self.filled = 0
        last, run = np.nan, 0
        for i in range(n):
            if np.isnan(self.c[i]):
                run += 1
                if not np.isnan(last) and run <= max_ffill:
                    self.o[i] = self.h[i] = self.l[i] = self.c[i] = last
                    self.filled += 1
            else:
                run = 0
                last = self.c[i]

    def idx_at(self, t: int) -> int:
        """Índice da vela fechada mais recente no instante t (a que começa em t − 60)."""
        return (int(t) - self.t0) // 60 - 1

    def close_at(self, t: int) -> float:
        i = self.idx_at(t)
        return float(self.c[i]) if 0 <= i < len(self.c) else float("nan")


def bars_from_rows(rows: list[tuple]) -> list[dict]:
    return [{"ts": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in sorted(rows)]


def basis_check(a: MinuteSeries, b_rows: list[tuple]) -> dict | None:
    """Base mediana |a/b − 1| e correlação dos retornos de 5 min entre a série principal e outra fonte (sobreposição)."""
    if not b_rows:
        return None
    b = MinuteSeries(b_rows, a.t0, a.t1, max_ffill=0)
    m = ~np.isnan(a.c) & ~np.isnan(b.c)
    if m.sum() < 100:
        return None
    rel = np.abs(a.c[m] / b.c[m] - 1)
    k = 5
    ra = a.c[k:] / a.c[:-k] - 1
    rb = b.c[k:] / b.c[:-k] - 1
    mm = ~np.isnan(ra) & ~np.isnan(rb)
    corr = float(np.corrcoef(ra[mm], rb[mm])[0, 1]) if mm.sum() > 50 else None
    return {"n": int(m.sum()), "median_abs_basis_bps": round(float(np.median(rel) * 1e4), 2),
            "p95_abs_basis_bps": round(float(np.percentile(rel, 95) * 1e4), 2),
            "corr_ret_5m": None if corr is None else round(corr, 4)}


# ------------------------------------------------------------------ orquestração

def fetch_all(out: Path, start: int, end: int, symbols: list[str], *, warm_min: int = 1440, warm_h: int = 30 * 24,
              logf=None, binance_grid: int = 5) -> dict:
    """Busca e guarda tudo o que o backtest precisa. Devolve {"minute": {SYM: MinuteSeries}, "hourly": {SYM: bars},
    "sol_grid": (t, px), "coverage": {...}, "sources": {...}, "basis": {...}}."""
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    m0 = start - warm_min * 60
    h0 = (start - warm_h * 3600) // 3600 * 3600
    res = {"minute": {}, "hourly": {}, "coverage": {}, "sources": {}, "basis": {}, "rows": {}, "m0": m0}

    need = {"start": m0, "end": end, "source": "coinbase:SOL-USD"}
    rows, hit = cached(raw / "SOL_1m.csv.gz", need, lambda: fetch_coinbase_1m("SOL-USD", m0, end), logf)
    log(f"SOL 1m coinbase: {len(rows)} velas{' (cache)' if hit else ''}", logf)
    res["rows"]["SOL"] = rows
    res["sources"]["SOL"] = "coinbase:SOL-USD 1m"

    gate_rows = {}
    for sym in symbols:
        if sym == "SOL":
            continue
        pair = f"{sym}_USDT"
        need = {"start": m0, "end": end, "source": f"gate:{pair}"}
        try:
            gate_rows[sym], _ = cached(raw / f"{sym}_1m_gate_check.csv.gz", need, lambda pair=pair: fetch_gate_1m(pair, m0, end), logf)
        except Exception as e:
            gate_rows[sym] = []
            res["basis"][sym] = {"error": str(e)[:120]}

    for sym in symbols:
        if sym == "SOL":
            continue
        cands = []
        for src, inst in MEME_SOURCES[sym]:
            need = {"start": m0, "end": end, "source": f"{src}:{inst}"}
            fn = {"bybit": fetch_bybit_1m, "kucoin": fetch_kucoin_1m}[src]
            try:
                rows, hit = cached(raw / f"{sym}_1m_{src}.csv.gz", need, lambda fn=fn, inst=inst: fn(inst, m0, end), logf)
            except Exception as e:
                log(f"{sym} 1m {src}: erro {str(e)[:120]}", logf)
                continue
            cov = coverage(rows, start, end)
            if not rows:
                continue
            b = basis_check(MinuteSeries(rows, m0, end), gate_rows.get(sym) or []) or {}
            log(f"{sym} 1m {src}:{inst}: {len(rows)} velas, cobertura {cov['coverage']:.4f}, "
                f"corr 5m vs gate {b.get('corr_ret_5m')}{' (cache)' if hit else ''}", logf)
            cands.append((cov["coverage"] >= MIN_COVERAGE, b.get("corr_ret_5m") or 0.0, cov["coverage"], src, inst, rows, b))
        if not cands:
            res["rows"][sym] = []
            res["sources"][sym] = None
            continue
        # fonte com cobertura suficiente e retornos mais parecidos com os da Gate.io (marcação ao vivo)
        best = max(cands, key=lambda c: (c[0], c[1], c[2]))
        res["rows"][sym] = best[5]
        res["sources"][sym] = f"{best[3]}:{best[4]} 1m"
        res["basis"][sym] = dict(best[6], vs="gate.io (fonte da marcação ao vivo)",
                                 candidates={f"{c[3]}:{c[4]}": {"coverage": c[2], "corr_ret_5m": c[1]} for c in cands})

    for sym, rows in res["rows"].items():
        res["coverage"][sym] = coverage(rows, start, end)
        res["minute"][sym] = MinuteSeries(rows, m0, end)
        res["coverage"][sym]["ffilled"] = res["minute"][sym].filled
        res["coverage"][sym]["usable"] = res["coverage"][sym]["coverage"] >= MIN_COVERAGE

    gp = raw / f"SOLUSDT_grid{binance_grid}s.npz"
    gm = raw / f"SOLUSDT_grid{binance_grid}s.meta.json"
    meta = json.loads(gm.read_text()) if gm.exists() else {}
    if gp.exists() and meta.get("start", 1e18) <= m0 and meta.get("end", 0) >= end:
        z = np.load(gp)
        g, px = z["t"], z["px"]
        sel = (g >= m0) & (g <= end)
        g, px = g[sel], px[sel]
        log(f"SOL grelha {binance_grid}s binance: {len(g)} pontos (cache)", logf)
    else:
        g, px = fetch_binance_grid("SOLUSDT", m0, end, raw / "binance", grid=binance_grid, logf=logf)
        np.savez_compressed(gp, t=g, px=px)
        gm.write_text(json.dumps({"start": m0, "end": end, "grid": binance_grid}))
        log(f"SOL grelha {binance_grid}s binance: {len(g)} pontos, {int(np.isnan(px).sum())} NaN", logf)
    res["sol_grid"] = (g, px)
    sel = (g >= start) & (g < end)
    res["coverage"]["SOL_binance_grid"] = {"points": int(sel.sum()), "nan": int(np.isnan(px[sel]).sum()),
                                           "coverage": round(float((~np.isnan(px[sel])).mean()), 5) if sel.any() else 0.0}
    gmin = g[(g % 60) == 0]
    pmin = px[(g % 60) == 0]
    b_rows = [(int(t) - 60, p, p, p, p, 0.0) for t, p in zip(gmin, pmin) if not np.isnan(p)]
    res["basis"]["SOL"] = dict(basis_check(res["minute"]["SOL"], b_rows) or {}, vs="binance SOLUSDT (estado e bot real)")

    from bot.rules_engine import fetch_coinbase_sol_1h, fetch_gate_1h
    need = {"start": h0, "end": end, "source": "coinbase:SOL-USD:1h"}
    rows, _ = cached(raw / "SOL_1h.csv.gz", need,
                     lambda: [(b["ts"], b["open"], b["high"], b["low"], b["close"], b["volume"])
                              for b in fetch_coinbase_sol_1h(h0, end)], logf)
    res["hourly"]["SOL"] = bars_from_rows(rows)
    for sym in symbols:
        if sym == "SOL":
            continue
        need = {"start": h0, "end": end, "source": f"gate:{sym}_USDT:1h"}
        rows, _ = cached(raw / f"{sym}_1h.csv.gz", need,
                         lambda sym=sym: [(b["ts"], b["open"], b["high"], b["low"], b["close"], b["volume"])
                                          for b in fetch_gate_1h(f"{sym}_USDT", h0, end)], logf)
        res["hourly"][sym] = bars_from_rows(rows)
    for sym, bars in res["hourly"].items():
        cov = coverage([(b["ts"],) for b in bars], start, end, step=3600)
        res["coverage"].setdefault(sym, {})["hourly_coverage"] = cov["coverage"]
    return res
