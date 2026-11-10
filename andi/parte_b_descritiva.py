"""Parte B - Questões 3 a 8 (capítulos 1 a 7): descrição, probabilidade,
distribuições, estimação e testes de hipóteses. As bases são tratadas como
dados reais; os parâmetros do gerador só aparecem nas comparações pedidas."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from . import parametros as P
from .relator import Relator

ALFA = 0.05


def sturges(n: int) -> int:
    """K = 1 + 3,322 log10(N), arredondado ao inteiro mais próximo (Seção 1.7)."""
    return int(round(1 + 3.322 * np.log10(n)))


def moda_czuber(x) -> float:
    """Moda de dados agrupados pela fórmula de Czuber (Seção 1.8).

    As classes de Sturges são largas demais para localizar a moda de uma
    variável tão assimétrica (quase tudo cai na primeira classe). Usa-se aqui
    a amplitude de Freedman-Diaconis, h = 2·AIQ/n^(1/3), a partir de zero.
    """
    x = np.asarray(x, dtype=float)
    q1, q3 = np.percentile(x, [25, 75])
    h = 2 * (q3 - q1) / len(x) ** (1 / 3)
    f, limites = np.histogram(x, bins=np.arange(0.0, x.max() + h, h))
    h = int(np.argmax(f))
    d1 = f[h] - (f[h - 1] if h > 0 else 0)
    d2 = f[h] - (f[h + 1] if h + 1 < len(f) else 0)
    return limites[h] + (d1 / (d1 + d2) if d1 + d2 > 0 else 0.5) * (limites[1] - limites[0])


def distribuicao_classes(x, k: int, inicio=None, amplitude=None) -> pd.DataFrame:
    x = np.asarray(x, dtype=float)
    inicio = x.min() if inicio is None else inicio
    amplitude = (x.max() - inicio) / k if amplitude is None else amplitude
    limites = inicio + amplitude * np.arange(k + 1)
    limites[-1] = max(limites[-1], x.max())
    f, _ = np.histogram(x, bins=limites)
    tab = pd.DataFrame({
        "classe": [f"{a:,.2f} |— {b:,.2f}" for a, b in zip(limites[:-1], limites[1:])],
        "f": f, "fr": f / f.sum(), "F": np.cumsum(f), "Fr": np.cumsum(f) / f.sum()})
    return tab.set_index("classe")


# ----------------------------------------------------------------------------
# Questão 3 - Dos dados à decisão (cap. 1)
# ----------------------------------------------------------------------------
def questao_3(r: Relator, at: pd.DataFrame, pe: pd.DataFrame) -> None:
    r.secao("Questão 3 - Dos dados à decisão (cap. 1)")
    r.item("3-b) Distribuições de frequências")
    f = at["tipo"].value_counts()
    tab = pd.DataFrame({"f": f, "fr": f / f.sum(), "F": f.cumsum(), "Fr": f.cumsum() / f.sum()})
    r.tabela(tab, "q03b_freq_tipo", "Tipo de ataque (ordenado pela frequência).")

    n = len(pe)
    k = sturges(n)
    amplitude = np.ceil(pe["perda_rs"].max() / k / 10_000) * 10_000
    r.valor("q3b.n_perdas", n, "{:d}")
    r.valor("q3b.k_sturges_exato", 1 + 3.322 * np.log10(n))
    r.valor("q3b.k_sturges", k, "{:d}")
    r.valor("q3b.amplitude_classe", amplitude, "{:,.0f}")
    r.tabela(distribuicao_classes(pe["perda_rs"], k, 0.0, amplitude), "q03b_classes_perda",
             "perda_rs em classes de Sturges (início 0, amplitude conveniente).")
    r.tabela(distribuicao_classes(np.log(pe["perda_rs"]), k), "q03b_classes_ln_perda",
             "ln(perda_rs) em classes de Sturges (complemento: escala em que a forma aparece).")

    r.item("3-c) Média, mediana e moda da perda")
    grupos = [(t, g["perda_rs"]) for t, g in pe.groupby("tipo")] + [("Geral", pe["perda_rs"])]
    tab = pd.DataFrame({
        nome: {"n": len(x), "média": x.mean(), "mediana": x.median(),
               "moda (Czuber)": moda_czuber(x),
               "moda lognormal e^(μ−σ²)": np.exp(np.log(x).mean() - np.log(x).var(ddof=1)),
               "média/mediana": x.mean() / x.median()}
        for nome, x in grupos}).T
    tab = tab.loc[[t for t in P.TIPOS if t in tab.index] + ["Geral"]]
    r.tabela(tab, "q03c_posicao_perda", "Medidas de posição da perda (R$).", casas=2)
    acima = float((pe["perda_rs"] > pe["perda_rs"].mean()).mean())
    r.valor("q3c.fracao_perdas_acima_da_media", acima)


# ----------------------------------------------------------------------------
# Questão 4 - Dispersão, formato e associação (cap. 2)
# ----------------------------------------------------------------------------
def questao_4(r: Relator, pe: pd.DataFrame, painel: pd.DataFrame, serie: pd.DataFrame,
              semente: int) -> None:
    r.secao("Questão 4 - Dispersão, formato e associação (cap. 2)")
    tipos = [t for t in P.TIPOS if t in set(pe["tipo"])]

    r.item("4-a) Dispersão da perda por tipo")
    linhas = {}
    for nome, x in [(t, pe.loc[pe["tipo"] == t, "perda_rs"]) for t in tipos] + [("Geral", pe["perda_rs"])]:
        q1, q3 = x.quantile([0.25, 0.75])
        linhas[nome] = {"n": len(x), "média": x.mean(), "desvio-padrão": x.std(ddof=1),
                        "CV": x.std(ddof=1) / x.mean(), "Q1": q1, "Q3": q3, "AIQ": q3 - q1,
                        "AIQ/mediana": (q3 - q1) / x.median()}
    r.tabela(pd.DataFrame(linhas).T, "q04a_dispersao", "Dispersão absoluta e relativa (R$).", casas=3)

    r.item("4-b) Box-plots e outliers (1,5 × AIQ)")
    linhas = {}
    for t in tipos:
        x = pe.loc[pe["tipo"] == t, "perda_rs"]
        q1, q3 = x.quantile([0.25, 0.75])
        sup, inf = q3 + 1.5 * (q3 - q1), q1 - 1.5 * (q3 - q1)
        fora = x > sup
        linhas[t] = {"n": len(x), "cerca inferior": inf, "cerca superior": sup,
                     "outliers acima": int(fora.sum()), "outliers abaixo": int((x < inf).sum()),
                     "% de outliers": 100 * fora.mean(),
                     "% da perda total do tipo nos outliers": 100 * x[fora].sum() / x.sum(),
                     "maior perda": x.max()}
    tab = pd.DataFrame(linhas).T
    r.tabela(tab, "q04b_outliers", "Outliers pela regra de 1,5 × AIQ.", casas=2)
    x = pe["perda_rs"]
    q1, q3 = x.quantile([0.25, 0.75])
    fora = x > q3 + 1.5 * (q3 - q1)
    r.valor("q4b.outliers_geral", int(fora.sum()), "{:d}")
    r.valor("q4b.pct_outliers_geral", float(100 * fora.mean()), "{:.2f}")
    r.valor("q4b.pct_perda_nos_outliers_geral", float(100 * x[fora].sum() / x.sum()), "{:.2f}")

    fig, eixos = plt.subplots(1, 2, figsize=(11, 3.8))
    dados = [pe.loc[pe["tipo"] == t, "perda_rs"] / 1e3 for t in tipos]
    rotulos = [t.replace(" de ", "\nde ") for t in tipos]
    for ax, log in zip(eixos, (False, True)):
        ax.boxplot(dados, tick_labels=rotulos, flierprops=dict(markersize=3, alpha=0.5))
        ax.set_ylabel("perda (R$ mil)")
        ax.tick_params(axis="x", labelsize=7)
        ax.set_title("escala logarítmica" if log else "escala linear")
        if log:
            ax.set_yscale("log")
    r.figura(fig, "q04b_boxplot", "Box-plots da perda por tipo de ataque.")

    r.item("4-c) Assimetria e curtose")
    ln = np.log(pe["perda_rs"])
    tab = pd.DataFrame({
        "perda_rs": {"assimetria": stats.skew(x, bias=False),
                     "curtose (excesso)": stats.kurtosis(x, bias=False),
                     "curtose": stats.kurtosis(x, bias=False) + 3,
                     "média": x.mean(), "mediana": x.median()},
        "ln(perda_rs)": {"assimetria": stats.skew(ln, bias=False),
                         "curtose (excesso)": stats.kurtosis(ln, bias=False),
                         "curtose": stats.kurtosis(ln, bias=False) + 3,
                         "média": ln.mean(), "mediana": ln.median()}})
    r.tabela(tab, "q04c_formato", "Medidas de formato (Normal: assimetria 0, curtose 3).", casas=3)
    fig, eixos = plt.subplots(1, 2, figsize=(9, 3.2))
    eixos[0].hist(x / 1e3, bins=60)
    eixos[0].set(title="perda (R$ mil)", ylabel="frequência")
    eixos[1].hist(ln, bins=40, density=True)
    g = np.linspace(ln.min(), ln.max(), 200)
    eixos[1].plot(g, stats.norm.pdf(g, ln.mean(), ln.std(ddof=1)), "r-")
    eixos[1].set(title="ln(perda) com Normal ajustada")
    r.figura(fig, "q04c_histogramas", "A transformação logarítmica torna a perda quase simétrica.")

    r.item("4-d) Covariâncias e correlações (painel trimestral)")
    cols = ["n_ataques", "perda_total", "servicos", "patch", "treino", "soc"]
    r.tabela(painel[cols].cov(), "q04d_covariancias", "Matriz de covariâncias.", casas=2)
    r.tabela(painel[cols].corr(), "q04d_correlacoes", "Matriz de correlações de Pearson.", casas=3)

    r.item("4-e) VaR histórico de 95% da perda mensal")
    y = serie["perda_total"].to_numpy()
    var95 = np.percentile(y, 95)
    rng = np.random.default_rng([semente, 4])
    boot = np.percentile(rng.choice(y, size=(5000, len(y)), replace=True), 95, axis=1)
    r.valor("q4e.var95_mensal", var95, "{:,.2f}")
    r.valor("q4e.media_mensal", y.mean(), "{:,.2f}")
    r.valor("q4e.mediana_mensal", float(np.median(y)), "{:,.2f}")
    r.valor("q4e.ic95_bootstrap_inf", float(np.percentile(boot, 2.5)), "{:,.2f}")
    r.valor("q4e.ic95_bootstrap_sup", float(np.percentile(boot, 97.5)), "{:,.2f}")
    maiores = serie.sort_values("perda_total", ascending=False).head(4)[["mes_ref", "perda_total"]]
    r.tabela(maiores.set_index("mes_ref"), "q04e_maiores_meses",
             "Os quatro meses de maior perda: o P95 é interpolado entre os dois primeiros.", casas=2)


# ----------------------------------------------------------------------------
# Questão 5 - Probabilidade e Bayes (cap. 3)
# ----------------------------------------------------------------------------
def _arvore_triagem(prev, sens, espec, n, titulo):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")
    ax.set(xlim=(0, 1), ylim=(0, 1), title=titulo)

    def caixa(x, y, txt, cor="#eef"):
        ax.text(x, y, txt, ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round", fc=cor, ec="gray"))

    def ramo(x0, y0, x1, y1, txt):
        ax.plot([x0, x1], [y0, y1], color="gray", lw=0.9, zorder=0)
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.035, txt, ha="center", fontsize=7.5)

    caixa(0.08, 0.5, f"Ataque\n(n = {n:,})")
    nos = [(0.75, "Materializa", prev, [("Alarme (cvss ≥ 7)", sens, "#fdd"), ("Sem alarme", 1 - sens, "#ffd")]),
           (0.25, "Não materializa", 1 - prev, [("Alarme (cvss ≥ 7)", 1 - espec, "#ffd"), ("Sem alarme", espec, "#dfd")])]
    for y, nome, p1, filhos in nos:
        ramo(0.08, 0.5, 0.40, y, f"{p1:.3f}")
        caixa(0.40, y, nome)
        for dy, (nome2, p2, cor) in zip((0.13, -0.13), filhos):
            ramo(0.40, y, 0.78, y + dy, f"{p2:.3f}")
            caixa(0.78, y + dy, f"{nome2}\nP conjunta = {p1 * p2:.4f}  (≈ {p1 * p2 * n:,.0f})", cor)
    vpp = prev * sens / (prev * sens + (1 - prev) * (1 - espec))
    ax.text(0.5, 0.02, f"P(materializou | alarme) = {vpp:.3f}", ha="center", fontsize=9, weight="bold")
    return fig


def questao_5(r: Relator, at: pd.DataFrame) -> None:
    r.secao("Questão 5 - Probabilidade e Bayes (cap. 3)")
    n = len(at)

    r.item("5-a) Tabela de contingência tipo × materializou")
    cont = pd.crosstab(at["tipo"], at["materializou"]).reindex(P.TIPOS)
    cont.columns = ["não materializou", "materializou"]
    cont["total"] = cont.sum(axis=1)
    cont.loc["Total"] = cont.sum()
    r.tabela(cont, "q05a_contingencia", "Frequências absolutas.", casas=0)
    r.tabela(cont / n, "q05a_conjuntas", "Probabilidades conjuntas e marginais.")
    cond = pd.DataFrame({
        "P(tipo)": cont["total"] / n,
        "P(materializou | tipo)": cont["materializou"] / cont["total"],
        "P(tipo | materializou)": cont["materializou"] / cont.loc["Total", "materializou"]})
    r.tabela(cond, "q05a_condicionais", "Condicionais nas duas direções.")
    r.valor("q5a.P_mat_dado_ransomware", float(cond.loc["Ransomware", "P(materializou | tipo)"]))
    r.valor("q5a.P_ransomware_dado_mat", float(cond.loc["Ransomware", "P(tipo | materializou)"]))

    r.item("5-b) Independência entre SOC e materialização")
    p_a, p_b = (at["soc"] == 1).mean(), (at["materializou"] == 1).mean()
    p_ab = ((at["soc"] == 1) & (at["materializou"] == 1)).mean()
    r.valor("q5b.P_soc", float(p_a))
    r.valor("q5b.P_mat", float(p_b))
    r.valor("q5b.P_soc_e_mat", float(p_ab))
    r.valor("q5b.P_soc_x_P_mat", float(p_a * p_b))
    r.valor("q5b.P_mat_dado_soc", float(at.loc[at["soc"] == 1, "materializou"].mean()))
    r.valor("q5b.P_mat_dado_sem_soc", float(at.loc[at["soc"] == 0, "materializou"].mean()))
    qui2 = stats.chi2_contingency(pd.crosstab(at["soc"], at["materializou"]), correction=False)
    r.valor("q5b.qui2", float(qui2.statistic))
    r.valor("q5b.qui2_pvalor", float(qui2.pvalue), "{:.3e}")

    r.item("5-c) Triagem 'alarme se cvss ≥ 7' e Teorema de Bayes")
    alarme, mat = at["cvss"] >= 7, at["materializou"] == 1
    vp, fp = int((alarme & mat).sum()), int((alarme & ~mat).sum())
    fn, vn = int((~alarme & mat).sum()), int((~alarme & ~mat).sum())
    sens, espec, prev = vp / (vp + fn), vn / (vn + fp), mat.mean()
    bayes = sens * prev / (sens * prev + (1 - espec) * (1 - prev))
    r.tabela(pd.DataFrame({"materializou": [vp, fn], "não materializou": [fp, vn]},
                          index=["alarme", "sem alarme"]), "q05c_triagem", "Contagens.", casas=0)
    r.valor("q5c.sensibilidade", sens)
    r.valor("q5c.especificidade", espec)
    r.valor("q5c.prevalencia", float(prev))
    r.valor("q5c.P_alarme", float(alarme.mean()))
    r.valor("q5c.VPP_bayes", float(bayes))
    r.valor("q5c.VPP_contagem_direta", vp / (vp + fp))
    r.valor("q5c.VPN", vn / (vn + fn))

    r.item("5-d) Árvore de triagem e prevalência pela metade")
    r.figura(_arvore_triagem(prev, sens, espec, n, "Árvore de triagem - prevalência observada"),
             "q05d_arvore", "Árvore de triagem com os números da base.")
    metade = prev / 2
    vpp_metade = sens * metade / (sens * metade + (1 - espec) * (1 - metade))
    r.valor("q5d.prevalencia_metade", float(metade))
    r.valor("q5d.VPP_prevalencia_metade", float(vpp_metade))
    curva = pd.DataFrame({"prevalência": [0.05, 0.10, metade, 0.30, prev, 0.60]})
    curva["VPP"] = sens * curva["prevalência"] / (
        sens * curva["prevalência"] + (1 - espec) * (1 - curva["prevalência"]))
    r.tabela(curva.sort_values("prevalência").set_index("prevalência"), "q05d_vpp_prevalencia",
             "Valor preditivo positivo em função da prevalência (sens. e espec. fixas).")


# ----------------------------------------------------------------------------
# Questão 6 - Distribuições (cap. 4 e 5)
# ----------------------------------------------------------------------------
def questao_6(r: Relator, at: pd.DataFrame, pe: pd.DataFrame, unidades: pd.DataFrame) -> None:
    r.secao("Questão 6 - Distribuições (cap. 4 e 5)")

    r.item("6-a) Poisson: P(N ≥ 6) em um mês, unidade sem SOC")
    ref = at["data"].dt.to_period("M")
    meses = pd.period_range(f"{P.ANO_INICIAL}-01", periods=P.N_MESES, freq="M")
    cont = at.groupby(["unidade", ref]).size().unstack(fill_value=0).reindex(
        index=unidades["unidade"], columns=meses, fill_value=0)
    sem_soc = unidades.loc[unidades["soc"] == 0, "unidade"]
    tab = pd.DataFrame({"média mensal": cont.loc[sem_soc].mean(axis=1),
                        "variância": cont.loc[sem_soc].var(axis=1, ddof=1)})
    tab["P(N≥6) Poisson"] = stats.poisson.sf(5, tab["média mensal"])
    tab["freq. empírica N≥6"] = (cont.loc[sem_soc] >= 6).mean(axis=1)
    tab["meses com N≥6"] = (cont.loc[sem_soc] >= 6).sum(axis=1)
    r.tabela(tab, "q06a_poisson", "Unidades sem SOC (36 meses cada).")
    escolhida = tab["média mensal"].idxmax()
    r.valor("q6a.unidade_escolhida", escolhida)
    r.valor("q6a.media_mensal", float(tab.loc[escolhida, "média mensal"]))
    r.valor("q6a.P_teorica", float(tab.loc[escolhida, "P(N≥6) Poisson"]))
    r.valor("q6a.freq_empirica", float(tab.loc[escolhida, "freq. empírica N≥6"]))
    r.valor("q6a.meses_com_6_ou_mais", int(tab.loc[escolhida, "meses com N≥6"]), "{:d}")
    p = tab.loc[escolhida, "P(N≥6) Poisson"]
    r.valor("q6a.erro_padrao_freq", float(np.sqrt(p * (1 - p) / P.N_MESES)))

    r.item("6-b) Exponencial: P(tempo > 8 h), com SOC e em expediente")
    x = at.loc[(at["soc"] == 1) & (at["fora_expediente"] == 0), "tempo_deteccao_h"]
    r.valor("q6b.n", len(x), "{:d}")
    r.valor("q6b.media_observada", float(x.mean()))
    r.valor("q6b.desvio_observado", float(x.std(ddof=1)))
    r.valor("q6b.P_teorica_theta_estimado", float(np.exp(-8 / x.mean())))
    r.valor("q6b.P_teorica_theta_4", float(np.exp(-8 / 4)))
    r.valor("q6b.P_observada", float((x > 8).mean()))
    r.valor("q6b.erro_padrao", float(np.sqrt(np.exp(-2) * (1 - np.exp(-2)) / len(x))))

    r.item("6-c) Q-Q de ln(perda) e escore Z da maior perda")
    fig, eixos = plt.subplots(1, 2, figsize=(9, 3.6))
    linhas = {}
    for ax, tipo in zip(eixos, ("Ransomware", "Phishing")):
        perda = pe.loc[pe["tipo"] == tipo, "perda_rs"]
        ln = np.log(perda)
        (osm, osr), (incl, inter, rq) = stats.probplot(ln, dist="norm")
        ax.scatter(osm, osr, s=8)
        ax.plot(osm, inter + incl * osm, "r-", lw=1)
        ax.set(title=f"{tipo} (n = {len(ln)})", xlabel="quantis teóricos N(0,1)",
               ylabel="quantis de ln(perda)")
        sw = stats.shapiro(ln)
        linhas[tipo] = {
            "n": len(ln), "média ln": ln.mean(), "dp ln": ln.std(ddof=1),
            "mediana (R$)": perda.median(), "exp(média ln) (R$)": np.exp(ln.mean()),
            "r do Q-Q": rq, "Shapiro-Wilk W": sw.statistic, "Shapiro-Wilk p": sw.pvalue,
            "assimetria ln": stats.skew(ln, bias=False),
            "maior perda (R$)": perda.max(),
            "Z da maior (em ln)": (ln.max() - ln.mean()) / ln.std(ddof=1),
            "Z da maior (em R$)": (perda.max() - perda.mean()) / perda.std(ddof=1),
            "P(Z > z) em ln": stats.norm.sf((ln.max() - ln.mean()) / ln.std(ddof=1)),
            "nº esperado acima (n·P)": len(ln) * stats.norm.sf((ln.max() - ln.mean()) / ln.std(ddof=1)),
        }
    r.figura(fig, "q06c_qq", "Gráficos Q-Q de ln(perda) contra a Normal.")
    r.tabela(pd.DataFrame(linhas), "q06c_lognormal", "Aderência Lognormal e maior perda.", casas=4)


# ----------------------------------------------------------------------------
# Questão 7 - Amostragem e estimação (cap. 6)
# ----------------------------------------------------------------------------
def ic_media(x, conf=0.95):
    x = np.asarray(x, dtype=float)
    n, m, s = len(x), x.mean(), x.std(ddof=1)
    e = stats.t.ppf(1 - (1 - conf) / 2, n - 1) * s / np.sqrt(n)
    return n, m, s, m - e, m + e


def questao_7(r: Relator, at: pd.DataFrame, pe: pd.DataFrame, semente: int) -> None:
    r.secao("Questão 7 - Amostragem e estimação (cap. 6)")

    r.item("7-a) IC de 95% para o tempo médio de detecção")
    linhas = {}
    for soc, theta in ((1, P.THETA_COM_SOC), (0, P.THETA_SEM_SOC)):
        for filtro, nome in ((None, "todos os ataques"), (0, "só em expediente")):
            d = at[at["soc"] == soc]
            if filtro is not None:
                d = d[d["fora_expediente"] == filtro]
            n, m, s, li, ls = ic_media(d["tempo_deteccao_h"])
            media_real = theta * (1 + P.P_FORA_EXPEDIENTE * (P.FATOR_FORA_EXPEDIENTE - 1)) \
                if filtro is None else theta
            linhas[f"{'com' if soc else 'sem'} SOC - {nome}"] = {
                "n": n, "média": m, "desvio-padrão": s, "IC inf": li, "IC sup": ls,
                "θ programado": theta, "IC contém θ": bool(li <= theta <= ls),
                "média implícita no gerador": media_real,
                "IC contém a média implícita": bool(li <= media_real <= ls)}
    r.tabela(pd.DataFrame(linhas).T, "q07a_ic_tempo", "IC t de Student, 95%.", casas=3)
    r.valor("q7a.prop_fora_expediente", float(at["fora_expediente"].mean()))

    r.item("7-b) IC de 95% para a proporção de materializados e tamanho de amostra")
    n, p = len(at), at["materializou"].mean()
    z = stats.norm.ppf(0.975)
    e = z * np.sqrt(p * (1 - p) / n)
    r.valor("q7b.n", n, "{:d}")
    r.valor("q7b.p_chapeu", float(p))
    r.valor("q7b.margem", float(e))
    r.valor("q7b.ic_inf", float(p - e))
    r.valor("q7b.ic_sup", float(p + e))
    r.valor("q7b.n_para_2pp_com_p_chapeu", int(np.ceil(z**2 * p * (1 - p) / 0.02**2)), "{:d}")
    r.valor("q7b.n_para_2pp_conservador", int(np.ceil(z**2 * 0.25 / 0.02**2)), "{:d}")

    r.item("7-c) Teorema Central do Limite com perda_rs")
    x = pe["perda_rs"].to_numpy()
    mu, sigma = x.mean(), x.std(ddof=1)
    rng = np.random.default_rng([semente, 7])
    fig, eixos = plt.subplots(1, 3, figsize=(11, 3.2))
    linhas = {}
    for ax, tam in zip(eixos, (5, 30, 100)):
        medias = rng.choice(x, size=(2000, tam), replace=True).mean(axis=1)
        linhas[f"n = {tam}"] = {
            "média das médias": medias.mean(), "desvio das médias": medias.std(ddof=1),
            "σ/√n": sigma / np.sqrt(tam), "razão": medias.std(ddof=1) / (sigma / np.sqrt(tam)),
            "assimetria das médias": stats.skew(medias, bias=False),
            "curtose (excesso)": stats.kurtosis(medias, bias=False),
            "Shapiro-Wilk p": stats.shapiro(medias).pvalue,
            "% fora de μ ± 1,96σ/√n": 100 * np.mean(np.abs(medias - mu) > 1.96 * sigma / np.sqrt(tam))}
        ax.hist(medias / 1e3, bins=50, density=True, alpha=0.6)
        g = np.linspace(medias.min(), medias.max(), 200)
        ax.plot(g / 1e3, stats.norm.pdf(g, mu, sigma / np.sqrt(tam)) * 1e3, "r-", lw=1)
        ax.set(title=f"médias de amostras de n = {tam}", xlabel="média da perda (R$ mil)")
    r.figura(fig, "q07c_tcl", "2.000 médias amostrais por tamanho; em vermelho, N(μ, σ²/n).")
    r.valor("q7c.mu_base", float(mu), "{:,.2f}")
    r.valor("q7c.sigma_base", float(sigma), "{:,.2f}")
    r.valor("q7c.assimetria_base", float(stats.skew(x, bias=False)))
    r.tabela(pd.DataFrame(linhas), "q07c_tcl", "Distribuição amostral da média.", casas=3)


# ----------------------------------------------------------------------------
# Questão 8 - Testes de hipóteses e backtesting (cap. 7)
# ----------------------------------------------------------------------------
def kupiec(n_exc: int, total: int, p: float):
    """Teste POF de Kupiec: LR ~ qui-quadrado(1) sob H0 (Seção 7.10.2)."""
    def loglik(q):
        partes = 0.0
        if total - n_exc > 0:
            partes += (total - n_exc) * np.log(1 - q)
        if n_exc > 0:
            partes += n_exc * np.log(q)
        return partes
    lr = -2 * (loglik(p) - loglik(n_exc / total))
    return lr, stats.chi2.sf(lr, 1)


def questao_8(r: Relator, at: pd.DataFrame, pe: pd.DataFrame, unidades: pd.DataFrame) -> None:
    r.secao("Questão 8 - Testes de hipóteses e backtesting (cap. 7)")

    r.item("8-a) Teste t unilateral: H0 μ ≤ 4 h x Ha μ > 4 h (unidades com SOC)")
    for nome, x in (("todos", at.loc[at["soc"] == 1, "tempo_deteccao_h"]),
                    ("so_expediente", at.loc[(at["soc"] == 1) & (at["fora_expediente"] == 0),
                                             "tempo_deteccao_h"])):
        n, m, s = len(x), x.mean(), x.std(ddof=1)
        t = (m - 4.0) / (s / np.sqrt(n))
        r.valor(f"q8a.{nome}.n", n, "{:d}")
        r.valor(f"q8a.{nome}.media", float(m))
        r.valor(f"q8a.{nome}.desvio", float(s))
        r.valor(f"q8a.{nome}.t", float(t))
        r.valor(f"q8a.{nome}.t_critico", float(stats.t.ppf(1 - ALFA, n - 1)))
        r.valor(f"q8a.{nome}.p_valor", float(stats.t.sf(t, n - 1)), "{:.3e}")

    r.item("8-b) Teste para proporção: H0 p ≤ 0,40 x Ha p > 0,40")
    n, p = len(at), at["materializou"].mean()
    z = (p - 0.40) / np.sqrt(0.40 * 0.60 / n)
    r.valor("q8b.n", n, "{:d}")
    r.valor("q8b.p_chapeu", float(p))
    r.valor("q8b.z", float(z))
    r.valor("q8b.z_critico", float(stats.norm.ppf(1 - ALFA)))
    r.valor("q8b.p_valor", float(stats.norm.sf(z)), "{:.4f}")

    r.item("8-d) Backtesting do VaR de 95% da perda mensal por unidade (Kupiec)")
    ref = pe["data"].dt.to_period("M")
    meses = pd.period_range(f"{P.ANO_INICIAL}-01", periods=P.N_MESES, freq="M")
    perda_um = pe.groupby(["unidade", ref])["perda_rs"].sum().unstack(fill_value=0.0).reindex(
        index=unidades["unidade"], columns=meses, fill_value=0.0)
    treino = perda_um.loc[:, meses[:24]].to_numpy().ravel()
    teste = perda_um.loc[:, meses[24:]]
    var95 = np.percentile(treino, 95)
    exc = teste > var95
    n_exc, total = int(exc.to_numpy().sum()), exc.size
    lr, pv = kupiec(n_exc, total, 0.05)
    r.valor("q8d.n_treino", treino.size, "{:d}")
    r.valor("q8d.var95_unidade_mes", float(var95), "{:,.2f}")
    r.valor("q8d.media_treino", float(treino.mean()), "{:,.2f}")
    r.valor("q8d.media_teste", float(teste.to_numpy().mean()), "{:,.2f}")
    r.valor("q8d.T", total, "{:d}")
    r.valor("q8d.excecoes_esperadas", total * 0.05, "{:.1f}")
    r.valor("q8d.excecoes_observadas", n_exc, "{:d}")
    r.valor("q8d.taxa_excecoes", n_exc / total)
    r.valor("q8d.LR", float(lr))
    r.valor("q8d.qui2_critico", float(stats.chi2.ppf(0.95, 1)))
    r.valor("q8d.p_valor", float(pv), "{:.4f}")
    por_mes = pd.DataFrame({"exceções": exc.sum(axis=0).to_numpy(),
                            "perda total (R$)": teste.sum(axis=0).to_numpy()},
                           index=[str(m) for m in meses[24:]])
    r.tabela(por_mes, "q08d_excecoes_mes", "Exceções por mês de 2025 (24 unidades por mês).", casas=0)
    sem_abril = exc.drop(columns=[meses[27]])
    lr2, pv2 = kupiec(int(sem_abril.to_numpy().sum()), sem_abril.size, 0.05)
    r.valor("q8d.sem_abril.excecoes", int(sem_abril.to_numpy().sum()), "{:d}")
    r.valor("q8d.sem_abril.T", sem_abril.size, "{:d}")
    r.valor("q8d.sem_abril.LR", float(lr2))
    r.valor("q8d.sem_abril.p_valor", float(pv2), "{:.4f}")

    fig, ax = plt.subplots(figsize=(9, 3.2))
    xs = np.tile(np.arange(12), len(teste))
    ys = teste.to_numpy().ravel() / 1e3
    ax.scatter(xs, ys, s=8, c=np.where(ys * 1e3 > var95, "red", "gray"), alpha=0.7)
    ax.axhline(var95 / 1e3, color="k", ls="--", lw=0.9, label=f"VaR 95% (2023–2024) = R$ {var95/1e3:,.0f} mil")
    ax.set_xticks(range(12), [str(m)[5:] for m in meses[24:]])
    ax.set(xlabel="mês de 2025", ylabel="perda mensal da unidade (R$ mil)")
    ax.legend()
    r.figura(fig, "q08d_backtesting", "Backtesting: perdas por unidade-mês em 2025 e exceções (vermelho).")
