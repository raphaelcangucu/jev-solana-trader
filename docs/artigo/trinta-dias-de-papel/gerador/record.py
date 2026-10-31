import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
S = Path(sys.argv[1]); BASE = "http://127.0.0.1:8788"
user, _, pw = (S / "labroot/dashboard/.auth").read_text().partition(":")
shots = S / "shots"

def pause(p, ms): p.wait_for_timeout(ms)
def ready(p):
    try: p.wait_for_function("!document.body.innerText.includes('Carregando')", timeout=90000)
    except Exception as e: print("timeout carregando", p.url)
    p.wait_for_timeout(900)
def smooth(p, total, steps=12, wait=110):
    for _ in range(steps):
        p.mouse.wheel(0, total / steps); p.wait_for_timeout(wait)

with sync_playwright() as pw_:
    b = pw_.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                        record_video_dir=str(S / "video"), record_video_size={"width": 1440, "height": 900}, color_scheme="light")
    p = ctx.new_page()
    p.goto(BASE + "/login"); pause(p, 1200)
    p.screenshot(path=str(shots / "00_login.png"))
    p.locator("input[name=username]").click(); p.keyboard.type(user, delay=70)
    p.locator("input[name=password]").click(); p.keyboard.type("•" * 0 + pw, delay=35)
    pause(p, 400); p.keyboard.press("Enter")
    p.wait_for_load_state("load"); pause(p, 2500)
    p.screenshot(path=str(shots / "01_placar.png"))
    smooth(p, 1800); pause(p, 1200)
    p.screenshot(path=str(shots / "01b_placar_scroll.png"))
    smooth(p, 1800); pause(p, 1000)
    p.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pause(p, 1000)
    # detalhe 1: linha do von relaxado em FARTCOIN (3.ª do placar)
    p.locator("div[role=row][class*=cursor-pointer]").nth(2).click(); pause(p, 600); ready(p); pause(p, 1500)
    p.screenshot(path=str(shots / "02_detalhe_fartcoin.png"))
    p.mouse.move(1050, 500); smooth(p, 1400); pause(p, 900)
    p.screenshot(path=str(shots / "02_detalhe_fartcoin_b.png"))
    p.keyboard.press("Escape"); pause(p, 900)
    # detalhe 2: pesquisar RSI e abrir o primeiro
    box = p.get_by_placeholder("Buscar", exact=False); box.click(); p.keyboard.type("rsi", delay=120); pause(p, 1400)
    p.screenshot(path=str(shots / "03_busca_rsi.png"))
    p.locator("div[role=row][class*=cursor-pointer]").nth(0).click(); pause(p, 600); ready(p); pause(p, 1500)
    p.screenshot(path=str(shots / "03_detalhe_rsi.png"))
    p.mouse.move(1050, 500); smooth(p, 1400); pause(p, 900)
    p.screenshot(path=str(shots / "03_detalhe_rsi_b.png"))
    p.keyboard.press("Escape"); pause(p, 700)
    box.fill(""); pause(p, 500)
    p.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pause(p, 600)
    for page, extra, name, scroll in [
        ("familias", "", "04_familias", 1800),
        ("retroativo", "", "05_retroativo", 1600),
        ("retroativo", "?run=bt180_2026-10-06", "06_retroativo_6m", 1200),
        ("retroativo", "?view=comparar", "07_comparar_meses", 1200),
        ("retroativo", "?run=bt30x_2026-10-06", "08_moedas_novas", 1000),
        ("carteira", "", "09_carteira_real", 1600),
        ("controle", "", "10_controle", 1000),
        ("saude", "", "11_saude", 1000),
    ]:
        p.goto(f"{BASE}/#/{page}{extra}"); p.wait_for_load_state("load"); pause(p, 600); ready(p); pause(p, 1500)
        p.screenshot(path=str(shots / f"{name}.png"))
        smooth(p, scroll); pause(p, 900)
        p.screenshot(path=str(shots / f"{name}_b.png"))
        p.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pause(p, 700)
    p.goto(BASE + "/#/placar"); p.wait_for_load_state("load"); pause(p, 1800)
    vid = p.video.path(); ctx.close()
    # telemóvel (sem vídeo)
    m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    q = m.new_page(); q.goto(BASE + "/login"); q.fill("input[name=username]", user); q.fill("input[name=password]", pw); q.keyboard.press("Enter")
    q.wait_for_load_state("load"); q.wait_for_timeout(2500); q.screenshot(path=str(shots / "12_mobile_placar.png"))
    q.goto(BASE + "/#/carteira"); q.wait_for_load_state("load"); ready(q); q.wait_for_timeout(1500); q.screenshot(path=str(shots / "13_mobile_carteira.png"))
    m.close(); b.close()
    print(vid)
