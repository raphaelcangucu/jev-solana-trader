"""JSONL log rotation + archive-aware readers (no data loss, no writer changes).

Rotation (daily, run by the nightly daemon at 01:00 BRT, after the 00:30 review so it sees the full day): for each large JSONL file
  1. read its last N lines (seed),
  2. hard-link live -> archive/<rel>/<stem>.<stamp>.jsonl (same inode, so any line a writer appends to the
     old inode afterwards still lands in the archive),
  3. atomically rename a seed file (last N lines) over the live path.
Writers open-append-close per row (lib.append_jsonl), so new rows go to the new live file.
Archives older than 1 day are gzipped. Readers merge archives + live and drop the seeded duplicates
(live rows with ts <= the newest archived ts).
Text *.log files: copy-truncate when > 50 MB (tiny race acceptable for human logs), gzipped.
"""
from __future__ import annotations
import gzip, json, os, shutil, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/home/box/solana-trader/paper")
ARCH = ROOT / "archive"
BRT = timezone(timedelta(hours=-3))
SEED_LINES = 3000
MIN_BYTES = 5 * 1024 * 1024
EXCLUDE = {"logs/trades.jsonl", "logs/meme_trades.jsonl", "logs/param_changes.jsonl", "logs/lab_orders.jsonl"}


def _arch_dir(path: Path) -> Path:
    rel = path.resolve().relative_to(ROOT)
    return ARCH / rel.parent


def archives(path: Path):
    """Archive files for a live path, oldest first."""
    path = Path(path); d = _arch_dir(path)
    if not d.exists():
        return []
    stem = path.stem
    fs = [f for f in d.iterdir() if f.name.startswith(stem + ".") and (f.name.endswith(".jsonl") or f.name.endswith(".jsonl.gz"))
          and f.name[len(stem) + 1:len(stem) + 2].isdigit()]
    return sorted(fs, key=lambda f: f.name.replace(".gz", ""))


def _stamp_of(f: Path) -> float:
    try:
        return datetime.strptime(f.name.split(".")[1], "%Y%m%dT%H%M%S").replace(tzinfo=BRT).timestamp()
    except Exception:
        return 0.0


def _lines(f: Path):
    op = gzip.open if f.name.endswith(".gz") else open
    with op(f, "rt") as fh:
        for l in fh:
            if l.strip():
                try: yield json.loads(l)
                except Exception: pass


def iter_rows(path, since_ts: float | None = None, contains: str | None = None):
    """All rows of a JSONL log across archives + live (deduped), optionally only archives rotated after since_ts."""
    path = Path(path); max_ts = None
    for f in archives(path):
        if since_ts is not None and _stamp_of(f) and _stamp_of(f) < since_ts:
            continue  # archive rotated before the window: all its rows are older
        op = gzip.open if f.name.endswith(".gz") else open
        with op(f, "rt") as fh:
            for l in fh:
                if contains and contains not in l:
                    continue
                try: r = json.loads(l)
                except Exception: continue
                t = r.get("ts")
                if t is not None:
                    max_ts = t if max_ts is None else max(max_ts, t)
                yield r
    if path.exists():
        with open(path) as fh:
            for l in fh:
                if contains and contains not in l:
                    continue
                try: r = json.loads(l)
                except Exception: continue
                if max_ts is not None and r.get("ts") is not None and r["ts"] <= max_ts:
                    continue
                yield r


def _tail_lines(path: Path, n: int) -> bytes:
    with open(path, "rb") as f:
        f.seek(0, 2); size = f.tell(); block = min(size, max(4096, n * 1500)); f.seek(size - block)
        data = f.read()
    lines = data.split(b"\n")
    if block < size:
        lines = lines[1:]
    lines = [l for l in lines if l.strip()]
    return b"\n".join(lines[-n:]) + (b"\n" if lines else b"")


def rotate_file(path: Path, stamp: str, seed=SEED_LINES):
    d = _arch_dir(path); d.mkdir(parents=True, exist_ok=True)
    arch = d / f"{path.stem}.{stamp}.jsonl"
    if arch.exists():
        return None
    seed_b = _tail_lines(path, seed)
    tmp = path.with_suffix(".rot_tmp")
    tmp.write_bytes(seed_b)
    os.link(path, arch)           # archive shares the inode (late appends preserved)
    os.replace(tmp, path)         # atomic swap: new live file = seed
    return arch


def compress_old(max_age_s=86400):
    n = 0
    if not ARCH.exists():
        return 0
    for f in ARCH.rglob("*.jsonl"):
        if time.time() - f.stat().st_mtime > max_age_s:
            with open(f, "rb") as a, gzip.open(str(f) + ".gz", "wb", compresslevel=6) as b:
                shutil.copyfileobj(a, b)
            os.remove(f); n += 1
    return n


def rotate_all(min_bytes=MIN_BYTES):
    stamp = datetime.now(BRT).strftime("%Y%m%dT%H%M%S")
    done = []
    for base in (ROOT / "logs", ROOT / "data"):
        for f in base.rglob("*.jsonl"):
            rel = str(f.relative_to(ROOT))
            if rel in EXCLUDE or "archive" in f.parts or f.stat().st_size < min_bytes:
                continue
            try:
                a = rotate_file(f, stamp)
                if a: done.append(rel)
            except Exception as e:
                done.append(f"{rel}:ERR:{e}")
    for f in (ROOT / "logs").glob("*.log"):
        if f.stat().st_size > 50 * 1024 * 1024:
            d = ARCH / "logs"; d.mkdir(parents=True, exist_ok=True)
            with open(f, "rb") as a, gzip.open(d / f"{f.stem}.{stamp}.log.gz", "wb") as b:
                shutil.copyfileobj(a, b)
            with open(f, "r+b") as fh:
                fh.truncate(0)
            done.append(str(f.relative_to(ROOT)) + ":copytruncate")
    z = compress_old()
    return {"stamp": stamp, "rotated": done, "compressed": z}
