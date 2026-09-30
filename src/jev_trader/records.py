"""Leitura e escrita de JSON/JSONL e relógio BRT, partilhados pelo loop, paper, placar e reescrita."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BRT_FIXED = timezone(timedelta(hours=-3))


def brt_clock():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/Sao_Paulo")
    except Exception:
        return BRT_FIXED


def now_iso() -> str:
    return datetime.now(brt_clock()).isoformat(timespec="seconds")


def parse_t(text: object) -> datetime | None:
    """ISO 8601 → datetime com fuso. Sem fuso, assume BRT. Texto inválido → None."""
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=BRT_FIXED)
    return moment


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Linhas JSON de um ficheiro append-only. Linha partida ou não-objeto é ignorada."""
    if not path.is_file():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_json_atomic(path: Path, data: object) -> None:
    """Escreve num temporário na mesma pasta e troca com `os.replace`: ou fica o antigo, ou o novo inteiro."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
