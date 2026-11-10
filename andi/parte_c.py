"""Parte C - Questão 14: segunda SMC (ferramenta de decisão).

Só usa o que foi ESTIMADO na Parte B (arquitetura da Seção 12.7):
    frequência      <- regressão múltipla da Questão 11
    materialização  <- regressão logística da Questão 13
    severidade      <- Lognormal por tipo, estimada em perdas.csv
Os parâmetros verdadeiros do gerador só voltam no item (g), para medir o
erro de modelo.

Quatro passos da Seção 12.2:
    1 MODELAR  -> `estimar_severidade`, `montar_cenario`
    2 SORTEAR  -> `simular` (Poisson das contagens, Normal dos log-custos)
    3 CALCULAR -> `simular` (soma das perdas de cada réplica anual)
    4 ANALISAR -> `metricas_de_risco` e os itens (b) a (g)
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from . import gerador as G
from . import parametros as P
from . import sorteio as S
from .relator import Relator

TRIMESTRES_2026 = [13, 14, 15, 16]
MI = 1e6


# ----------------------------------------------------------------------------
# Passo 1 - MODELAR
# ----------------------------------------------------------------------------
def estimar_severidade(pe: pd.DataFrame):
    """ln(perda) = mu_tipo + delta·soc + erro, com sigma por tipo.

    `delta` é o quanto as perdas de unidades com SOC são menores (em log):
    é por onde entra, na Parte C, o efeito do SOC sobre o tempo de detecção
    e, por consequência, sobre a severidade.
    """
    modelo = smf.ols("ln_perda ~ 0 + C(tipo) + soc", data=pe).fit()
    mu = np.array([modelo.params[f"C(tipo)[{t}]"] for t in P.TIPOS])
    delta = float(modelo.params["soc"])
    sigma = np.array([modelo.resid[pe["tipo"] == t].std(ddof=1) for t in P.TIPOS])
    return mu, delta, sigma, modelo


def frequencia_anual(modelo_freq, perfil: pd.DataFrame) -> np.ndarray:
    """Soma das previsões dos trimestres 13 a 16 por unidade (sem campanha)."""
    grade = perfil.merge(pd.DataFrame({"trimestre": TRIMESTRES_2026}), how="cross")
    grade["tri_ano"] = (grade["trimestre"] - 1) % 4 + 1
    grade["campanha"] = 0
    grade["prev"] = np.clip(modelo_freq.predict(grade), 0.0, None)
    return grade.groupby("unidade", sort=False)["prev"].sum().to_numpy()


def prob_media_materializacao(logit, at: pd.DataFrame, perfil: pd.DataFrame) -> np.ndarray:
    """p[u, k]: média da probabilidade prevista para ataques do tipo k na unidade u.

    cvss e fora_expediente vêm dos ataques observados daquele tipo; o tempo de
    detecção vem dos ataques observados em unidades com o MESMO status de SOC
    do perfil avaliado. Assim, dar um SOC a uma unidade troca também a sua
    distribuição de tempos de detecção (efeito indireto do SOC).
    """
    b = logit.params
    p = np.zeros((len(perfil), len(P.TIPOS)))
    for s in (0, 1):
        for k, tipo in enumerate(P.TIPOS):
            pool = at[(at["soc"] == s) & (at["tipo"] == tipo)]
            parcial = (b["Intercept"] + b["cvss"] * pool["cvss"].to_numpy()
                       + b["tempo_deteccao_h"] * pool["tempo_deteccao_h"].to_numpy()
                       + b["fora_expediente"] * pool["fora_expediente"].to_numpy() + b["soc"] * s)
            for i in np.flatnonzero(perfil["soc"].to_numpy() == s):
                eta = parcial + b["treino"] * perfil["treino"].iloc[i]
                p[i, k] = np.mean(1.0 / (1.0 + np.exp(-eta)))
    return p


def montar_cenario(unidades, at, modelos, sev, controles: bool, modelo_freq="freq_sazonal") -> dict:
    """Parâmetros da perda agregada por célula (tipo k, grupo g de unidades).

    g = status ORIGINAL de SOC da unidade (0 ou 1): mantém as células iguais
    nos dois cenários, o que permite usar números aleatórios comuns.
    """
    mu, delta, sigma, _ = sev
    perfil = unidades.copy()
    if controles:
        perfil["patch"], perfil["treino"], perfil["soc"] = (
            P.CONTROLES["patch"], P.CONTROLES["treino"], P.CONTROLES["soc"])
    lam = frequencia_anual(modelos[modelo_freq], perfil)                 # ataques/ano por unidade
    pi = at["tipo"].value_counts(normalize=True).reindex(P.TIPOS).to_numpy()
    p = prob_media_materializacao(modelos["logit"], at, perfil)          # (unidade, tipo)
    taxa_perdas = lam[:, None] * pi[None, :] * p                         # thinning: lambda·pi·p
    grupo = unidades["soc"].to_numpy()
    soc_cenario = np.array([1, 1]) if controles else np.array([0, 1])
    return {
        "lam_unidade": lam, "p_unidade_tipo": p, "pi": pi,
        "Lambda": np.stack([taxa_perdas[grupo == g].sum(axis=0) for g in (0, 1)], axis=1),  # (k, g)
        "mu": mu[:, None] + delta * soc_cenario[None, :],                                   # (k, g)
        "sigma": sigma,
    }


def resumo_cenario(c: dict) -> dict:
    media_sev = np.exp(c["mu"] + (c["sigma"][:, None] ** 2) / 2)
    eventos = c["Lambda"].sum()
    return {"ataques por ano (Σλ)": c["lam_unidade"].sum(),
            "prob. média de materialização": eventos / c["lam_unidade"].sum(),
            "eventos de perda por ano (Σλ·p)": eventos,
            "severidade média (R$)": (c["Lambda"] * media_sev).sum() / eventos,
            "perda anual esperada, analítica (R$)": (c["Lambda"] * media_sev).sum()}


# ----------------------------------------------------------------------------
# Passos 2 e 3 - SORTEAR e CALCULAR
# ----------------------------------------------------------------------------
def simular(semente, atual: dict, controles: dict, n: int, f_freq: float = 1.0,
            f_sigma: float = 1.0, bloco: int = 20_000):
    """Perda anual agregada nos dois cenários, com números aleatórios comuns.

    Para cada célula (tipo, grupo) e réplica: o mesmo U gera as duas contagens
    de Poisson (por inversão) e o mesmo z gera a severidade do j-ésimo evento
    nos dois cenários. A diferença entre os cenários fica livre do ruído de
    simulação que seria comum aos dois.
    """
    rng = np.random.default_rng(semente)
    perda_a, perda_c = np.zeros(n), np.zeros(n)
    k_tipos = len(P.TIPOS)
    for ini in range(0, n, bloco):
        m = min(bloco, n - ini)
        for k in range(k_tipos):
            for g in (0, 1):
                la, lc = atual["Lambda"][k, g] * f_freq, controles["Lambda"][k, g] * f_freq
                u = rng.random(m)
                n_a = S.poisson_inv(u, la) if la > 0 else np.zeros(m, int)
                n_c = S.poisson_inv(u, lc) if lc > 0 else np.zeros(m, int)
                n_max = np.maximum(n_a, n_c)
                total = int(n_max.sum())
                if total == 0:
                    continue
                z = rng.standard_normal(total)
                rep = np.repeat(np.arange(m), n_max)
                pos = np.arange(total) - np.repeat(np.cumsum(n_max) - n_max, n_max)
                sig = atual["sigma"][k] * f_sigma
                sev_a = np.exp(atual["mu"][k, g] + sig * z) * (pos < n_a[rep])
                sev_c = np.exp(controles["mu"][k, g] + sig * z) * (pos < n_c[rep])
                perda_a[ini:ini + m] += np.bincount(rep, weights=sev_a, minlength=m)
                perda_c[ini:ini + m] += np.bincount(rep, weights=sev_c, minlength=m)
    return perda_a, perda_c


# ----------------------------------------------------------------------------
# Passo 4 - ANALISAR
# ----------------------------------------------------------------------------
def metricas_de_risco(x: np.ndarray) -> dict:
    var95, var99 = np.percentile(x, [95, 99])
    return {"média": x.mean(), "mediana": np.median(x), "desvio-padrão": x.std(ddof=1),
            "VaR 95%": var95, "VaR 99%": var99, "CVaR 95%": x[x >= var95].mean(),
            "CVaR 99%": x[x >= var99].mean(),
            "P(perda > R$ 30 mi)": np.mean(x > P.LIMIAR_PERDA_RELEVANTE)}


def _tabela_comparativa(a: np.ndarray, c: np.ndarray) -> pd.DataFrame:
    tab = pd.DataFrame({"Atual": metricas_de_risco(a), "Com controles": metricas_de_risco(c)})
    tab["Redução"] = tab["Atual"] - tab["Com controles"]
    tab["Redução (%)"] = 100 * tab["Redução"] / tab["Atual"]
    reais = [i for i in tab.index if not i.startswith("P(")]
    tab.loc[reais, ["Atual", "Com controles", "Redução"]] /= MI
    return tab


def _decisao(a: np.ndarray, c: np.ndarray, custo: float = P.CUSTO_PACOTE) -> dict:
    ganho = a - c
    return {"redução da perda média (R$ mi)": ganho.mean() / MI,
            "erro padrão da redução (R$ mi)": ganho.std(ddof=1) / np.sqrt(len(a)) / MI,
            "benefício líquido médio (R$ mi)": (ganho.mean() - custo) / MI,
            "ROI (%)": 100 * (ganho.mean() - custo) / custo,
            "P(perda c/ controles + custo > perda atual)": np.mean(c + custo > a),
            "custo máximo que se paga na média (R$ mi)": ganho.mean() / MI,
            "redução do VaR 95% (R$ mi)": (np.percentile(a, 95) - np.percentile(c, 95)) / MI,
            "redução do CVaR 95% (R$ mi)": (metricas_de_risco(a)["CVaR 95%"]
                                            - metricas_de_risco(c)["CVaR 95%"]) / MI}


def _anos_verdadeiros(semente, unidades: pd.DataFrame, anos: int, bloco: int = 2_500):
    """Item (g): gerador da Parte A, parâmetros verdadeiros, 2026 (t = 37..48), sem campanha."""
    rng = np.random.default_rng(semente)
    t = np.arange(P.N_MESES + 1, P.N_MESES + 13)
    perdas, n_at, n_pe = [], [], []
    for ini in range(0, anos, bloco):
        m = min(bloco, anos - ini)
        s = G.sortear_ataques(rng, unidades, t, campanha=False, replicas=m)
        perdas.append(np.bincount(s["replica"], weights=np.nan_to_num(s["perda_rs"]), minlength=m))
        n_at.append(np.bincount(s["replica"], minlength=m))
        n_pe.append(np.bincount(s["replica"], weights=s["materializou"], minlength=m))
    return np.concatenate(perdas), np.concatenate(n_at), np.concatenate(n_pe)


def executar(r: Relator, bases: dict, modelos: dict, semente: int, n: int = 100_000) -> None:
    r.secao("Questão 14 - Perda anual de 2026 e o pacote de controles (cap. 12)")
    unidades, at, pe = bases["unidades"], modelos["ataques"], modelos["perdas"]
    semente_smc = [semente, 14]

    # ---- a) Modelar ---------------------------------------------------------------
    r.item("14-a) Insumos estimados")
    sev = estimar_severidade(pe)
    mu, delta, sigma, modelo_sev = sev
    direto = pe.groupby("tipo")["ln_perda"].agg(["size", "mean", "std"]).reindex(P.TIPOS)
    tab = pd.DataFrame({
        "n perdas": direto["size"], "μ̂ (média de ln perda)": direto["mean"],
        "σ̂ (dp de ln perda)": direto["std"],
        "mediana implícita e^μ̂ (R$)": np.exp(direto["mean"]),
        "média implícita e^(μ̂+σ̂²/2) (R$)": np.exp(direto["mean"] + direto["std"]**2 / 2),
        "média amostral (R$)": pe.groupby("tipo")["perda_rs"].mean().reindex(P.TIPOS),
        "μ̂ sem SOC (modelo)": mu, "μ̂ com SOC (modelo)": mu + delta, "σ̂ residual (modelo)": sigma,
        "participação do tipo π̂": at["tipo"].value_counts(normalize=True).reindex(P.TIPOS)})
    r.tabela(tab, "q14a_severidade", "Lognormal de severidade por tipo, estimada em perdas.csv.", casas=4)
    r.valor("q14a.delta_soc", delta)
    r.valor("q14a.delta_soc_erro_padrao", float(modelo_sev.bse["soc"]))
    r.valor("q14a.delta_soc_pvalor", float(modelo_sev.pvalues["soc"]), "{:.3e}")
    r.valor("q14a.fator_severidade_com_soc", float(np.exp(delta)))
    b1 = float(modelos["ols_tempo_tipo"].params["tempo_deteccao_h"])
    dif_tempo = float(pe.loc[pe["soc"] == 1, "tempo_deteccao_h"].mean()
                      - pe.loc[pe["soc"] == 0, "tempo_deteccao_h"].mean())
    r.valor("q14a.tempo_medio_perdas_com_soc", float(pe.loc[pe["soc"] == 1, "tempo_deteccao_h"].mean()))
    r.valor("q14a.tempo_medio_perdas_sem_soc", float(pe.loc[pe["soc"] == 0, "tempo_deteccao_h"].mean()))
    r.valor("q14a.delta_via_beta1_x_dif_tempo", b1 * dif_tempo)

    atual = montar_cenario(unidades, at, modelos, sev, controles=False)
    ctrl = montar_cenario(unidades, at, modelos, sev, controles=True)
    por_unidade = unidades.set_index("unidade").copy()
    por_unidade["λ anual (atual)"] = atual["lam_unidade"]
    por_unidade["p médio (atual)"] = (atual["p_unidade_tipo"] * atual["pi"]).sum(axis=1)
    por_unidade["λ·p (atual)"] = por_unidade["λ anual (atual)"] * por_unidade["p médio (atual)"]
    por_unidade["λ anual (controles)"] = ctrl["lam_unidade"]
    por_unidade["p médio (controles)"] = (ctrl["p_unidade_tipo"] * ctrl["pi"]).sum(axis=1)
    por_unidade["λ·p (controles)"] = por_unidade["λ anual (controles)"] * por_unidade["p médio (controles)"]
    r.tabela(por_unidade, "q14a_unidades", "Frequência de 2026 e probabilidade de materialização.", casas=3)
    p_tipo = pd.DataFrame({
        "p médio sem SOC (atual)": atual["p_unidade_tipo"][unidades["soc"].to_numpy() == 0].mean(axis=0),
        "p médio com SOC (atual)": atual["p_unidade_tipo"][unidades["soc"].to_numpy() == 1].mean(axis=0),
        "p médio (controles)": ctrl["p_unidade_tipo"].mean(axis=0),
        "taxa observada": at.groupby("tipo")["materializou"].mean().reindex(P.TIPOS)}, index=P.TIPOS)
    r.tabela(p_tipo, "q14a_p_por_tipo", "Probabilidade média de materialização por tipo.")
    insumos = pd.DataFrame({"Atual": resumo_cenario(atual), "Com controles": resumo_cenario(ctrl)})
    insumos["Variação (%)"] = 100 * (insumos["Com controles"] / insumos["Atual"] - 1)
    r.tabela(insumos, "q14a_insumos", "Insumos agregados da SMC.", casas=3)
    alt = montar_cenario(unidades, at, modelos, sev, controles=False, modelo_freq="freq_base")
    r.valor("q14a.ataques_2026_modelo_11d", float(atual["lam_unidade"].sum()), "{:.1f}")
    r.valor("q14a.ataques_2026_modelo_11a", float(alt["lam_unidade"].sum()), "{:.1f}")
    r.valor("q14a.ataques_observados_2025", int((at["ano"] == 2025).sum()), "{:d}")
    r.valor("q14a.perdas_observadas_por_ano", len(pe) / 3, "{:.1f}")
    r.valor("q14a.perda_observada_media_anual", float(pe["perda_rs"].sum() / 3), "{:,.0f}")

    # ---- b) Sortear, calcular, analisar ---------------------------------------------
    r.item(f"14-b) Distribuição da perda anual (n = {n:,} réplicas)")
    perda_a, perda_c = simular(semente_smc, atual, ctrl, n)
    met = metricas_de_risco(perda_a)
    for nome, v in met.items():
        r.valor(f"q14b.{nome}", float(v), "{:,.4f}" if nome.startswith("P(") else "{:,.0f}")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.hist(perda_a / MI, bins=120, color="tab:blue", alpha=0.7, range=(0, np.percentile(perda_a, 99.9) / MI))
    for rotulo, v, cor in (("média", met["média"], "k"), ("VaR 95%", met["VaR 95%"], "tab:orange"),
                           ("VaR 99%", met["VaR 99%"], "tab:red"), ("CVaR 95%", met["CVaR 95%"], "purple")):
        ax.axvline(v / MI, color=cor, ls="--", lw=1.2, label=f"{rotulo} = R$ {v / MI:.1f} mi")
    ax.set(xlabel="perda anual de 2026 (R$ milhões)", ylabel="réplicas",
           title="Distribuição simulada da perda anual - cenário atual")
    ax.legend()
    r.figura(fig, "q14b_distribuicao", "Perda anual simulada (cenário atual) com as métricas de risco.")

    # ---- c) Convergência ---------------------------------------------------------------
    r.item("14-c) Convergência")
    tamanhos = [t for t in (1_000, 4_000, 16_000, 64_000, 100_000) if t <= n]
    linhas = {}
    for tam in tamanhos:
        x = perda_a[:tam]
        linhas[f"{tam:,}"] = {"média (R$ mi)": x.mean() / MI,
                              "erro padrão da média (R$ mi)": x.std(ddof=1) / np.sqrt(tam) / MI,
                              "VaR 95% (R$ mi)": np.percentile(x, 95) / MI}
    conv = pd.DataFrame(linhas).T
    conv["EP relativo ao de n = 1.000"] = conv.iloc[:, 1] / conv.iloc[0, 1]
    conv["1/√(n/1.000) teórico"] = [np.sqrt(tamanhos[0] / t) for t in tamanhos]
    r.tabela(conv, "q14c_convergencia", "Estimativas com as primeiras n réplicas.")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    idx = np.unique(np.geomspace(100, n, 300).astype(int))
    soma, soma2 = np.cumsum(perda_a), np.cumsum(perda_a**2)
    media = soma[idx - 1] / idx
    ep = np.sqrt(np.maximum(soma2[idx - 1] / idx - media**2, 0) / idx)
    ax.plot(idx, media / MI, lw=1.2)
    ax.fill_between(idx, (media - 1.96 * ep) / MI, (media + 1.96 * ep) / MI, alpha=0.25)
    ax.axhline(perda_a.mean() / MI, color="k", ls="--", lw=0.8)
    ax.set(xscale="log", xlabel="número de réplicas n", ylabel="perda média (R$ mi)",
           title="Convergência da média (banda de ±1,96 EP)")
    r.figura(fig, "q14c_convergencia", "A banda de incerteza encolhe na proporção 1/√n.")

    # ---- d) Cenário com controles ---------------------------------------------------------
    r.item("14-d) Cenário com controles")
    r.tabela(_tabela_comparativa(perda_a, perda_c), "q14d_comparativo",
             "Formato da Seção 12.7.3 (valores em R$ milhões; probabilidade em fração).", casas=3)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    lim = (0, np.percentile(perda_a, 99.9) / MI)
    ax.hist(perda_a / MI, bins=120, range=lim, alpha=0.6, label="atual")
    ax.hist(perda_c / MI, bins=120, range=lim, alpha=0.6, color="tab:green", label="com controles")
    ax.hist((perda_c + P.CUSTO_PACOTE) / MI, bins=120, range=lim, histtype="step", color="darkgreen",
            label="com controles + custo de R$ 8 mi")
    ax.set(xlabel="perda anual de 2026 (R$ milhões)", ylabel="réplicas")
    ax.legend()
    r.figura(fig, "q14d_comparacao", "O pacote desloca toda a distribuição para a esquerda.")

    # ---- e) Decisão --------------------------------------------------------------------------
    r.item("14-e) Decisão")
    dec = _decisao(perda_a, perda_c)
    for nome, v in dec.items():
        r.valor(f"q14e.{nome}", float(v))

    # ---- f) Sensibilidade -----------------------------------------------------------------------
    r.item("14-f) Sensibilidade")
    n_sens = min(n, 50_000)
    linhas = {}
    for f_sigma in (0.8, 1.0, 1.2):
        for f_freq in (0.9, 1.0, 1.1):
            a, c = simular(semente_smc, atual, ctrl, n_sens, f_freq=f_freq, f_sigma=f_sigma)
            d = _decisao(a, c)
            linhas[(f"σ × {f_sigma:.1f}", f"freq. × {f_freq:.1f}")] = {
                "perda média atual (R$ mi)": a.mean() / MI,
                "VaR 95% atual (R$ mi)": np.percentile(a, 95) / MI,
                "redução média (R$ mi)": d["redução da perda média (R$ mi)"],
                "benefício líquido (R$ mi)": d["benefício líquido médio (R$ mi)"],
                "ROI (%)": d["ROI (%)"],
                "P(não se pagar no ano)": d["P(perda c/ controles + custo > perda atual)"],
                "decisão": "investir" if d["benefício líquido médio (R$ mi)"] > 0 else "não investir"}
    sens = pd.DataFrame(linhas).T
    r.tabela(sens, "q14f_sensibilidade", f"n = {n_sens:,} réplicas por caso, mesmas sementes.", casas=3)
    r.valor("q14f.casos_em_que_a_decisao_muda", int((sens["decisão"] != "investir").sum()), "{:d}")
    base = sens.loc[("σ × 1.0", "freq. × 1.0"), "benefício líquido (R$ mi)"]
    barras = [("σ da Lognormal ±20%", sens.loc[("σ × 0.8", "freq. × 1.0"), "benefício líquido (R$ mi)"],
               sens.loc[("σ × 1.2", "freq. × 1.0"), "benefício líquido (R$ mi)"]),
              ("frequência ±10%", sens.loc[("σ × 1.0", "freq. × 0.9"), "benefício líquido (R$ mi)"],
               sens.loc[("σ × 1.0", "freq. × 1.1"), "benefício líquido (R$ mi)"])]
    barras.sort(key=lambda b: abs(b[2] - b[1]))
    fig, ax = plt.subplots(figsize=(7, 2.6))
    for i, (nome, baixo, alto) in enumerate(barras):
        ax.barh(i, baixo - base, left=base, color="tab:blue")
        ax.barh(i, alto - base, left=base, color="tab:orange")
        ax.text(baixo, i, f" {baixo:.1f}", va="center", ha="right", fontsize=8)
        ax.text(alto, i, f" {alto:.1f}", va="center", ha="left", fontsize=8)
    ax.set_yticks(range(len(barras)), [b[0] for b in barras])
    ax.axvline(base, color="k", lw=0.8)
    ax.axvline(0, color="red", ls="--", lw=1)
    ax.set(xlabel="benefício líquido médio do pacote (R$ mi/ano)",
           title="Sensibilidade (linha vermelha: ponto em que a decisão mudaria)")
    r.figura(fig, "q14f_tornado", "Tornado: azul = parâmetro para baixo; laranja = para cima.")

    # ---- g) Erro de modelo -----------------------------------------------------------------------
    r.item("14-g) Erro de modelo: gerador verdadeiro em 2026 (10.000 anos)")
    anos = 10_000
    verd_a, n_at, n_pe = _anos_verdadeiros([semente, 140], unidades, anos)
    perfil_c = unidades.copy()
    perfil_c["patch"], perfil_c["treino"], perfil_c["soc"] = (
        P.CONTROLES["patch"], P.CONTROLES["treino"], P.CONTROLES["soc"])
    verd_c, n_at_c, n_pe_c = _anos_verdadeiros([semente, 140], perfil_c, anos)
    tab = pd.DataFrame({"SMC com modelos estimados (b)": metricas_de_risco(perda_a),
                        "Gerador verdadeiro (g)": metricas_de_risco(verd_a)})
    reais = [i for i in tab.index if not i.startswith("P(")]
    tab.loc[reais] /= MI
    tab["erro (estimado − verdadeiro)"] = tab.iloc[:, 0] - tab.iloc[:, 1]
    tab["erro (%)"] = 100 * tab["erro (estimado − verdadeiro)"] / tab.iloc[:, 1]
    r.tabela(tab, "q14g_erro_modelo", "R$ milhões (probabilidade em fração). Cenário atual.", casas=3)
    comp = pd.DataFrame({
        "estimado": {"ataques por ano": atual["lam_unidade"].sum(),
                     "eventos de perda por ano": atual["Lambda"].sum(),
                     "prob. de materialização": atual["Lambda"].sum() / atual["lam_unidade"].sum(),
                     "severidade média (R$)": resumo_cenario(atual)["severidade média (R$)"]},
        "verdadeiro": {"ataques por ano": n_at.mean(), "eventos de perda por ano": n_pe.mean(),
                       "prob. de materialização": n_pe.sum() / n_at.sum(),
                       "severidade média (R$)": verd_a.sum() / n_pe.sum()}})
    comp["erro (%)"] = 100 * (comp["estimado"] / comp["verdadeiro"] - 1)
    r.tabela(comp, "q14g_componentes", "De onde vem o erro: frequência, materialização ou severidade.", casas=3)
    ep_v = verd_a.std(ddof=1) / np.sqrt(anos)
    r.valor("q14g.erro_padrao_media_verdadeira_mi", float(ep_v / MI))
    dec_v = _decisao(verd_a, verd_c)
    dec_tab = pd.DataFrame({"estimado (Parte C)": dec, "verdadeiro (gerador)": dec_v})
    r.tabela(dec_tab, "q14g_decisao", "A decisão sobrevive ao erro de modelo?", casas=3)
    r.tabela(_tabela_comparativa(verd_a, verd_c), "q14g_comparativo_verdadeiro",
             "Atual x controles com os parâmetros verdadeiros (R$ milhões).", casas=3)
    # caudas: quantis extremos lado a lado
    qs = [50, 75, 90, 95, 99, 99.9]
    caudas = pd.DataFrame({"estimado": np.percentile(perda_a, qs) / MI,
                           "verdadeiro": np.percentile(verd_a, qs) / MI},
                          index=[f"P{q}" for q in qs])
    caudas["razão est./verd."] = caudas["estimado"] / caudas["verdadeiro"]
    r.tabela(caudas, "q14g_quantis", "Quantis da perda anual (R$ milhões).", casas=3)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    lim = (0, max(np.percentile(perda_a, 99.9), np.percentile(verd_a, 99.9)) / MI)
    ax.hist(perda_a / MI, bins=100, range=lim, density=True, alpha=0.55, label="SMC com modelos estimados")
    ax.hist(verd_a / MI, bins=100, range=lim, density=True, alpha=0.55, color="tab:red",
            label="gerador verdadeiro (10.000 anos)")
    ax.set(xlabel="perda anual de 2026 (R$ milhões)", ylabel="densidade")
    ax.legend()
    r.figura(fig, "q14g_erro_modelo", "Distribuição 'verdadeira' x distribuição da SMC de decisão.")
