"""Testes do laboratório paper (offline, determinísticos).

- Põe `research/paper-lab` no sys.path para `import bot.*`.
- Aponta `PAPER_LAB_ROOT` para uma pasta temporária ANTES de qualquer import de `bot.*` (bot.paths lê a
  variável na importação), para nenhum teste ler ou escrever no estado real do lab.
"""
from __future__ import annotations
import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="paper-lab-tests-")).resolve()
atexit.register(shutil.rmtree, TEST_ROOT, True)
os.environ["PAPER_LAB_ROOT"] = str(TEST_ROOT)
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))
