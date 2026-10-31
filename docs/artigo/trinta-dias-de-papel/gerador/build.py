"""Gera ../index.html (artigo do run de 30 dias) a partir de data.json e template.html."""
import json, sys, html
from pathlib import Path
from datetime import date

S = Path(__file__).parent
d = json.loads((S / "data.json").read_text())
WD = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MES = {9: "set", 10: "out"}


def dlabel(iso):
    y, m, dd = map(int, iso.split("-"))
    return f"{WD[date(y, m, dd).weekday()]}, {dd} {MES[m]}"


def br(x, n=2, sign=False):
    s = f"{x:+,.{n}f}" if sign else f"{x:,.{n}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


NOTES = {
    "2026-09-29": ("Recomeçar do zero", "Uma sessão anterior, na nuvem, tinha deixado um bilhete de passagem: quatro de seis etapas prontas. O branch com o trabalho dela tinha sumido. Aceitei a perda e refiz tudo a partir da cópia local. Melhor começar limpo do que herdar dúvida."),
    "2026-09-30": ("Dia zero", "Às 00:50 nasce o livro de papel: 0,0174 SOL e 50,01 USDT, a mesma carteira de 23 de setembro, com a SOL a 119,31. O primeiro susto vem dos modelos. A barra fixa de confiança de 0,8 nunca dispara no von nem na Laya e dispara em 100% das chamadas do poorjev. Um não fala, o outro não cala. Troco a barra fixa por percentil. Horas depois, instalar os modelos lota o disco e tudo para. A noite termina numa faxina de dezenas de gigabytes: Docker, dumps de banco, apps, modelos velhos."),
    "2026-10-01": ("O laboratório acorda", "Às 22:24 o laboratório sobe sozinho, com um serviço que impede o Mac de dormir: 109 robôs, cada um com seus parâmetros. Às 23:12 o bot real faz a primeira compra de papel. Daqui em diante, ninguém precisa apertar botão."),
    "2026-10-02": ("O primeiro tombo", "A SOL sobe a 123,66 e despenca a 117,21 no mesmo dia. 70 dos 109 robôs fecham no vermelho. Um bot de regras morre tentando dormir um tempo negativo, e eu conserto. O painel ganha senha e nasce o resumo de 4 em 4 horas."),
    "2026-10-03": ("O dia mais cheio do mês", "Redesenho o painel como um caderno de laboratório. Entra o Claude Code noturno, um pesquisador autônomo que toda madrugada lê os relatórios e cria variações com hipótese e critério de refutação. Na primeira noite ele me pega num erro: os robôs com saídas estavam com as saídas desligadas. Nasce também o livro B do bot real, com saídas automáticas e no máximo metade da carteira em SOL. O Jev hospedado entra em papel, e um túnel leva o painel para o celular."),
    "2026-10-04": ("Um dia verde", "69 robôs no positivo. As saídas mecânicas em FARTCOIN lideram com +6,95%. É o tipo de dia que faz a gente acreditar, e é exatamente por isso que a régua pede 21 dias."),
    "2026-10-05": ("Não correr atrás do preço", "O vermelho volta, com 78 robôs negativos. O Claude noturno anota que nada se repetiu três dias seguidos e transforma uma intuição velha de trader, não perseguir o preço, num parâmetro: 120 minutos de pausa depois de cada saída, em BONK e MEW."),
    "2026-10-06": ("Olhar para trás", "Só 3 de 124 robôs no positivo. Preciso de perspectiva, e o mês corrente não vai me dar. Ponho o mesmo código do ao vivo para rodar sobre 30 dias de passado, vela a vela de 1 minuto."),
    "2026-10-07": ("Seis meses de memória", "O retroativo vira histórico: julho, agosto, setembro e uma corrida de seis meses. À noite, um arquivo de PID velho engana o supervisor, que lança um segundo bot de regras. Quatro operações saem em dobro. É pouco, mas com dinheiro real esse tipo de erro custa."),
    "2026-10-08": ("Um favorito", "A SOL perde 5% e fecha a 110,23. O Claude noturno elege um favorito: o relaxed__fork1, o von com saídas e no máximo 50% exposto, à frente do pai em 4 de 4 dias."),
    "2026-10-09": ("Doze forks numa noite", "O supervisor aprende a adotar processos vivos em vez de duplicar. O ajustador automático cria 12 forks de uma vez. As saídas em memecoins somam +134,7 US$ de habilidade."),
    "2026-10-10": ("O pesquisador some", "A sessão do Claude noturno expira. Nenhum alarme toca. Ele simplesmente para de aparecer. Dali até o fim, o ajustador automático segue sozinho."),
    "2026-10-11": ("Respiro", "68 robôs no positivo e a SOL de volta a 111,86. Dura pouco."),
    "2026-10-12": ("O pior dia até ali", "92 de 146 robôs no vermelho, −3.862 US$ somados num só dia. SOL a 106,65."),
    "2026-10-13": ("Rebote", "71 robôs no positivo. O laboratório respira junto com o mercado."),
    "2026-10-14": ("Abaixo de 104", "A SOL fecha a 103,23. Só 2 robôs terminam o dia no positivo."),
    "2026-10-15": ("Nasce quem ia ganhar", "O ajustador cria o rsi_sol_1h__fork1, uma regra RSI de 1 hora com período 17, sem modelo de linguagem nenhum. Parece só mais um fork no meio de dezenas. Ele terminaria o mês em primeiro lugar por lucro."),
    "2026-10-16": ("Recorde de forks", "16 forks numa noite, o máximo do mês. O laboratório cresce mais rápido do que dá para ler."),
    "2026-10-17": ("O disco, de novo", "Outros projetos na mesma máquina enchem o disco com caches de build: 111 GB num único dia. Escrevo uma guarda que limpa esses caches sempre que sobram menos de 30 GB. Em experimento longo numa máquina pessoal, o inimigo às vezes mora no projeto ao lado."),
    "2026-10-18": ("Moedas novas", "Testo o von relaxado em oito moedas que ele nunca tinha visto (JUP, JTO, PYTH, RAY, BOME, PENGU, TRUMP e MOODENG), em 30 dias e em seis meses de passado. Falha nas oito, como já tinha falhado nas sete memecoins. Pelo menos é consistente."),
    "2026-10-19": ("Lateral", "Dia sem direção. 86 robôs no vermelho, comidos por taxas e pequenas perdas. Mercado parado também cobra."),
    "2026-10-20": ("O melhor dia do mês", "101 de 179 robôs no positivo, +2.803 US$ somados. O híbrido poorjev com regime em MEW sobe 25% num dia só. Se existiu um dia para acreditar, foi esse."),
    "2026-10-21": ("Hora do juiz", "Primeiro dia em que um veredito é possível. A regra que escrevi no dia zero entra em campo: 30 operações fechadas, bater o segurar e o USDC a 6% ao ano com p < 0,05 e consistência em 3 das últimas 4 semanas."),
    "2026-10-22": ("O fork paciente", "O ajustador cria o poorjev_relaxed__fork4. Ele espera 54 minutos entre compras, usa 20% do caixa por vez e sai com 3% de ganho, 1,8% de perda ou 0,8% de recuo. Em nove dias seria o robô de SOL com mais habilidade e lucro do mês. O entusiasta, domado pela paciência."),
    "2026-10-23": ("Casa cheia", "O laboratório chega a 189 robôs. 102 fecham o dia no vermelho."),
    "2026-10-24": ("Escorregando", "SOL a 102,32. Sem drama, só a ladeira."),
    "2026-10-25": ("Escorregando", "SOL a 100,50 e 104 robôs negativos. Os 100 dólares aparecem no horizonte."),
    "2026-10-26": ("Na beirada", "SOL a 100,10. Por dez centavos."),
    "2026-10-27": ("Rebote curto", "97 robôs no positivo. Curto."),
    "2026-10-28": ("Abaixo de 100", "A SOL fecha a 99,91. A barreira dos 100 cai sem barulho."),
    "2026-10-29": ("O fundo", "O pior dia do mês. SOL a 95,23, 123 robôs no vermelho, −4.220 US$ somados. Às 21:23 o livro A do bot real bate o fundo, 25,4% abaixo do pico. O livro B, com saídas, nunca caiu mais que 12,4%."),
    "2026-10-30": ("Último dia", "Rebote, com 85 robôs no positivo. Às 23:59:59 o bot real se desliga sozinho, como combinado."),
    "2026-10-31": ("Não era o fim", "De madrugada, a surpresa: o laboratório continuava rodando, porque o supervisor não tinha hora para parar. Desliguei tudo às 02:36 e corrigi o script. O fechamento oficial é o relatório das 00:41. Até no último dia o experimento ensinou alguma coisa."),
}
WEEKS = [
    ("Semana 0", "Arrumar a casa", "2026-09-29", "2026-10-01"),
    ("Semana 1", "Liga tudo, e tudo cai", "2026-10-02", "2026-10-08"),
    ("Semana 2", "Os forks tomam conta", "2026-10-09", "2026-10-15"),
    ("Semana 3", "O disco, as moedas novas e um dia bom", "2026-10-16", "2026-10-22"),
    ("Semana 4", "O fundo e o apagar das luzes", "2026-10-23", "2026-10-31"),
]
days = {x["day"]: x for x in d["days"]}
sol = d["sol_daily"]
sol["2026-09-30"] = [119.305, 119.305, 119.305, 119.305]


def pretty(name):
    return html.escape(name)


def entry(day):
    t, note = NOTES[day]
    x = days.get(day)
    meta = []
    if day in sol and day >= "2026-10-01":
        prev = sorted(k for k in sol if k < day)
        chg = (sol[day][3] / sol[prev[-1]][3] - 1) * 100 if prev else 0
        cls = "up" if chg >= 0 else "down"
        meta.append(f'<span class="m">SOL <b>{br(sol[day][3])}</b> <i class="{cls}">{br(chg, 1, True)}%</i></span>')
    bar = ""
    if x:
        n = x["n"]; p = x["pos"]; ng = x["neg"]; z = n - p - ng
        meta.append(f'<span class="m"><b>{p}</b> no positivo · <b>{ng}</b> no negativo de {n} robôs</span>')
        bar = (f'<div class="breadth" role="img" aria-label="{p} positivos, {z} neutros, {ng} negativos">'
               f'<span class="bp" style="flex:{p}"></span><span class="bz" style="flex:{z}"></span><span class="bn" style="flex:{ng}"></span></div>')
        best = x["best"]; worst = x["worst"]
        meta.append(f'<span class="m">melhor <code>{pretty(best["name"])}</code> {br(best["pct"], 2, True)}%</span>')
        meta.append(f'<span class="m">pior <code>{pretty(worst["name"])}</code> {br(worst["pct"], 2, True)}%</span>')
    dayn = x["exp_day"] - 1 if x and x.get("exp_day") else None
    tag = f'<span class="dn">dia {dayn}</span>' if dayn else ""
    return (f'<li class="day" id="d{day}"><div class="when"><time datetime="{day}">{dlabel(day)}</time>{tag}</div>'
            f'<div class="what"><h4>{html.escape(t)}</h4><p>{html.escape(note)}</p>'
            f'{bar}<div class="meta">{"".join(meta)}</div></div></li>')


tl = []
for wk, title, a, b in WEEKS:
    items = "".join(entry(k) for k in sorted(NOTES) if a <= k <= b)
    tl.append(f'<section class="week"><header><span class="wk">{wk}</span><h3>{title}</h3></header><ol>{items}</ol></section>')

# séries para os gráficos
series_days = sorted(k for k in sol if "2026-09-30" <= k <= "2026-10-30")
sol_series = [[k, sol[k][3]] for k in series_days]
hold = [[k, round(0.017392206 * sol[k][3] + 50.00929, 3)] for k in series_days]
start = 0.017392206 * 119.305 + 50.00929
A = {k: v for k, v, _ in d["book_A"]}; B = {k: v for k, v, _ in d["book_B"]}
bookA = [["2026-09-30", round(start, 3)]] + [[k, A[k]] for k in series_days if k in A]
bookB = [["2026-09-30", round(start, 3)]] + [[k, B[k]] for k in series_days if k in B]
breadth = [[x["day"], x["pos"], x["neg"], x["n"], x["best"]["name"], x["best"]["pct"], x["worst"]["name"], x["worst"]["pct"]] for x in d["days"]]
chart = dict(sol=sol_series, hold=hold, A=bookA, B=bookB, breadth=breadth)

tpl = (S / "template.html").read_text()
out = tpl.replace("<!--TIMELINE-->", "\n".join(tl)).replace("/*CHART_DATA*/null", json.dumps(chart, ensure_ascii=False))
(S.parent / "index.html").write_text(out)
print("ok", len(out))
