#!/usr/bin/env python3
"""PNG do gráfico de 6 meses do Retroativo, para compartilhar.

Abre o painel num Chromium headless (Playwright, navegadores em ~/Library/Caches/ms-playwright), vai para
#/retroativo?run=<run de 6 meses> e fotografa só a seção do gráfico ([data-shot="chart-6m"]).

    python3 scripts/render_chart_6m.py --url https://lab.exemplo --out /tmp/6meses.png
    python3 scripts/render_chart_6m.py --url http://127.0.0.1:5173 --out shot.png --theme dark --families

Autenticação: o arquivo `user:pass` de DASH_AUTH_FILE (ou --auth-file) vira um cabeçalho Basic enviado só para a
origem de --url (nunca para outro host). O conteúdo nunca é impresso. Sem arquivo, segue sem auth (ex.: o servidor de
desenvolvimento do Vite, que já injeta a auth no proxy).
Só leitura: abre páginas e faz GET; não clica em nada que grave.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


def auth_header(path: str | None) -> str | None:
    if not path:
        return None
    try:
        raw = Path(path).expanduser().read_text().strip()
    except OSError:
        print("aviso: não consegui ler o arquivo de auth; seguindo sem auth", file=sys.stderr)
        return None
    if ":" not in raw:
        print("aviso: o arquivo de auth não tem o formato user:pass; seguindo sem auth", file=sys.stderr)
        return None
    return "Basic " + base64.b64encode(raw.encode()).decode()


def origin(url: str) -> str:
    u = urlsplit(url)
    return f"{u.scheme}://{u.netloc}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="endereço do painel (raiz), ex.: http://127.0.0.1:8787")
    ap.add_argument("--out", required=True, help="arquivo PNG de saída")
    ap.add_argument("--run", help="run de 6 meses (padrão: o mais recente do índice)")
    ap.add_argument("--theme", choices=("light", "dark"), default="light")
    ap.add_argument("--width", type=int, default=1440, help="largura da janela em px (390 = celular)")
    ap.add_argument("--scale", type=float, default=2.0, help="device scale factor (2 = nítido para compartilhar)")
    ap.add_argument("--families", action="store_true", help="mostra a mediana por família em vez das estratégias")
    ap.add_argument("--table", action="store_true", help="inclui a tabela de valores finais")
    ap.add_argument("--auth-file", default=os.environ.get("DASH_AUTH_FILE"), help="arquivo user:pass (padrão: $DASH_AUTH_FILE)")
    ap.add_argument("--timeout", type=float, default=30.0, help="segundos")
    a = ap.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("erro: falta o Playwright para Python (pip install playwright)", file=sys.stderr)
        return 2

    base = a.url.rstrip("/")
    host = origin(base)
    auth = auth_header(a.auth_file)
    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    ms = int(a.timeout * 1000)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": a.width, "height": 1000}, device_scale_factor=a.scale,
                                      color_scheme=a.theme, locale="pt-BR", timezone_id="America/Sao_Paulo")
            # o painel guarda o tema em localStorage; fixa antes de qualquer script da página
            ctx.add_init_script(f"try {{ localStorage.setItem('paperlab.theme', {json.dumps(a.theme)}) }} catch (e) {{}}")
            if auth:
                def add_auth(route):
                    r = route.request
                    if origin(r.url) == host:
                        route.continue_(headers={**r.headers, "authorization": auth})
                    else:
                        route.continue_()
                ctx.route("**/*", add_auth)
            page = ctx.new_page()

            run = a.run
            if not run:
                resp = page.request.get(f"{base}/api/v2/backtest/index", headers={"authorization": auth} if auth else None)
                if not resp.ok:
                    print(f"erro: /api/v2/backtest/index respondeu {resp.status}", file=sys.stderr)
                    return 1
                runs = [r for r in (resp.json().get("runs") or []) if r.get("kind") != "30d" and r.get("available", True)]
                if not runs:
                    print("erro: nenhum run de 6 meses no índice", file=sys.stderr)
                    return 1
                run = runs[0]["run_id"]

            page.goto(f"{base}/#/retroativo?run={run}", wait_until="domcontentloaded", timeout=ms)  # o painel mantém um SSE aberto: nunca fica "networkidle"
            sec = page.locator('[data-shot="chart-6m"]')
            sec.wait_for(state="visible", timeout=ms)
            if a.families:
                sec.get_by_role("button", name="Por família").click()
            sec.locator("canvas").first.wait_for(state="visible", timeout=ms)
            if a.table:
                sec.get_by_role("button", name="Ver os valores em tabela").click()
            # a barra do topo é sticky e cobriria o começo da seção na foto
            page.add_style_tag(content="header.sticky{position:static!important}")
            page.mouse.move(0, 0)  # sem tooltip na foto
            page.wait_for_timeout(900)  # rótulos diretos e a escala assentarem
            sec.screenshot(path=str(out), animations="disabled")
            print(f"ok: {out} (run {run}, tema {a.theme}, {a.width}px)")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
