"""Parte A - Questão 1 (item b: transformação inversa) e Questão 2 (verificação)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from . import gerador as G
from . import parametros as P
from . import sorteio as S
from .relator import Relator


# ----------------------------------------------------------------------------
# Questão 1-b: F^-1(U) próprio versus biblioteca
# ----------------------------------------------------------------------------
def questao_1(r: Relator, semente: int, bases: dict) -> None:
    r.secao("Questão 1 - Implementação do gerador")
    r.valor("q1.semente", semente, "{:d}")
    for nome in G.ARQUIVOS:
        r.valor(f"q1.linhas_{nome}", len(bases[nome]), "{:d}")
    r.tabela(bases["unidades"].set_index("unidade"), "q01_unidades",
             "Perfil sorteado das 24 unidades (Etapa A1).", casas=2)

    r.item("1-b) Transformação inversa própria x biblioteca")
    n = 200_000
    u = np.random.default_rng([semente, 1]).random(n)
    rng_lib = np.random.default_rng([semente, 101])
    a, c, b = P.PATCH_TRI
    casos = {
        "Triangular(60; 80; 95)": dict(
            meu=S.triangular_inv(u, a, c, b),
            ppf=stats.triang.ppf(u, (c - a) / (b - a), loc=a, scale=b - a),
            lib=rng_lib.triangular(a, c, b, n),
            dist=stats.triang((c - a) / (b - a), loc=a, scale=b - a)),
        "Exponencial(θ = 4 h)": dict(
            meu=S.exponencial_inv(u, 4.0),
            ppf=stats.expon.ppf(u, scale=4.0),
            lib=rng_lib.exponential(4.0, n),
            dist=stats.expon(scale=4.0)),
        "Exponencial(θ = 12 h)": dict(
            meu=S.exponencial_inv(u, 12.0),
            ppf=stats.expon.ppf(u, scale=12.0),
            lib=rng_lib.exponential(12.0, n),
            dist=stats.expon(scale=12.0)),
    }
    linhas = []
    for nome, d in casos.items():
        linhas.append({
            "distribuição": nome,
            "média teórica": d["dist"].mean(),
            "média F⁻¹ própria": d["meu"].mean(),
            "média biblioteca": d["lib"].mean(),
            "dp teórico": d["dist"].std(),
            "dp F⁻¹ própria": d["meu"].std(ddof=1),
            "dp biblioteca": d["lib"].std(ddof=1),
            "máx |própria − ppf SciPy|": np.max(np.abs(d["meu"] - d["ppf"])),
            "KS p-valor (própria)": stats.kstest(d["meu"], d["dist"].cdf).pvalue,
            "KS p-valor (biblioteca)": stats.kstest(d["lib"], d["dist"].cdf).pvalue,
        })
    r.tabela(pd.DataFrame(linhas).set_index("distribuição").T, "q01b_inversa",
             f"Comparação com n = {n:,} sorteios (mesmo U para a própria e a ppf do SciPy).", casas=5)

    fig, eixos = plt.subplots(1, 3, figsize=(11, 3.2))
    for ax, (nome, d) in zip(eixos, casos.items()):
        x = np.linspace(*np.quantile(d["meu"], [0, 0.995]), 300)
        ax.hist(d["meu"], bins=60, density=True, alpha=0.5, label="F⁻¹(U) própria",
                range=(x[0], x[-1]))
        ax.hist(d["lib"], bins=60, density=True, histtype="step", color="k",
                label="NumPy (biblioteca)", range=(x[0], x[-1]))
        ax.plot(x, d["dist"].pdf(x), "r-", lw=1.2, label="densidade teórica")
        ax.set_title(nome)
    eixos[0].legend(fontsize=7)
    r.figura(fig, "q01b_inversa", "Transformação inversa própria, função pronta e densidade teórica.")


# ----------------------------------------------------------------------------
# Questão 2: verificação do gerador
# ----------------------------------------------------------------------------
def questao_2(r: Relator, bases: dict) -> None:
    r.secao("Questão 2 - Verificação do gerador")
    unidades, ataques = bases["unidades"], bases["ataques"]
    t = np.arange(1, P.N_MESES + 1)

    # contagem mensal por unidade (matriz 24 x 36, com zeros)
    mes_t = (ataques["ano"] - P.ANO_INICIAL) * 12 + ataques["mes"]
    cont = (ataques.assign(t=mes_t).groupby(["unidade", "t"]).size()
            .unstack(fill_value=0).reindex(index=unidades["unidade"], columns=t, fill_value=0))
    lam = pd.DataFrame(G.taxa_mensal(unidades, t), index=unidades["unidade"], columns=t)

    # --- a) média observada x teórica ---------------------------------------
    r.item("2-a) Média mensal de ataques: observada x teórica")
    tab = pd.DataFrame({
        "soc": unidades.set_index("unidade")["soc"],
        "média teórica": lam.mean(axis=1),
        "média observada": cont.mean(axis=1),
    })
    tab["diferença"] = tab["média observada"] - tab["média teórica"]
    tab["erro padrão"] = np.sqrt(tab["média teórica"] / P.N_MESES)
    tab["z"] = tab["diferença"] / tab["erro padrão"]
    r.tabela(tab, "q02a_media_unidade", "Erro padrão = raiz(λ̄/36); |z| > 1,96 seria atípico.", casas=3)
    r.valor("q2a.unidades_fora_2ep", int((tab["z"].abs() > 1.96).sum()), "{:d}")
    soma_z2 = float((tab["z"] ** 2).sum())                  # ~ qui-quadrado(24) se o gerador está certo
    r.valor("q2a.soma_z2", soma_z2)
    r.valor("q2a.soma_z2_pvalor", float(stats.chi2.sf(soma_z2, len(tab))))
    r.valor("q2a.total_observado", int(cont.to_numpy().sum()), "{:d}")
    r.valor("q2a.total_teorico", float(lam.to_numpy().sum()), "{:.1f}")
    r.valor("q2a.z_total", float((cont.to_numpy().sum() - lam.to_numpy().sum())
                                 / np.sqrt(lam.to_numpy().sum())), "{:.3f}")

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    cores = np.where(tab["soc"] == 1, "tab:green", "tab:red")
    ax.errorbar(tab["média teórica"], tab["média observada"], yerr=1.96 * tab["erro padrão"],
                fmt="none", ecolor="gray", lw=0.8)
    ax.scatter(tab["média teórica"], tab["média observada"], c=cores, zorder=3, s=22)
    lim = [0, tab[["média teórica", "média observada"]].to_numpy().max() * 1.1]
    ax.plot(lim, lim, "k--", lw=0.8)
    ax.set(xlabel="média teórica λ̄ (ataques/mês)", ylabel="média observada",
           title="Verificação por unidade (verde = com SOC)")
    r.figura(fig, "q02a_media_unidade", "Média mensal observada x teórica, com banda de ±1,96 EP.")

    # --- b) variância x média -------------------------------------------------
    r.item("2-b) Variância x média (Poisson) e heterogeneidade")
    disp = pd.DataFrame({
        "soc": unidades.set_index("unidade")["soc"],
        "média": cont.mean(axis=1),
        "variância": cont.var(axis=1, ddof=1),
        "var. teórica (λ̄ + Var λ_t)": lam.mean(axis=1) + lam.var(axis=1, ddof=0),
    })
    disp["variância/média"] = disp["variância"] / disp["média"]
    r.tabela(disp, "q02b_dispersao_unidade",
             "Índice de dispersão por unidade (36 meses cada).", casas=3)
    sem = disp[disp["soc"] == 0]
    todas = cont.to_numpy().ravel()
    r.valor("q2b.indice_medio_sem_soc", float(sem["variância/média"].mean()))
    r.valor("q2b.indice_min_sem_soc", float(sem["variância/média"].min()))
    r.valor("q2b.indice_max_sem_soc", float(sem["variância/média"].max()))
    r.valor("q2b.media_todas", float(todas.mean()))
    r.valor("q2b.variancia_todas", float(todas.var(ddof=1)))
    r.valor("q2b.indice_todas", float(todas.var(ddof=1) / todas.mean()))
    # decomposição: Var total = E[Var dentro] + Var[médias entre unidades]
    r.valor("q2b.var_dentro_media", float(cont.var(axis=1, ddof=1).mean()))
    r.valor("q2b.var_entre_medias", float(cont.mean(axis=1).var(ddof=0)))

    # --- c) tipos e materialização ---------------------------------------------
    r.item("2-c) Frequências dos tipos e taxa de materialização")
    n = len(ataques)
    freq = ataques["tipo"].value_counts().reindex(P.TIPOS)
    tipos = pd.DataFrame({"prob. programada": P.PROB_TIPO, "frequência": freq.to_numpy(),
                          "freq. relativa": freq.to_numpy() / n}, index=P.TIPOS)
    tipos["diferença"] = tipos["freq. relativa"] - tipos["prob. programada"]
    tipos["erro de simulação"] = np.sqrt(P.PROB_TIPO * (1 - P.PROB_TIPO) / n)
    tipos["z"] = tipos["diferença"] / tipos["erro de simulação"]
    r.tabela(tipos, "q02c_tipos", f"n = {n:,} ataques; erro = raiz(p(1−p)/n).")
    qui2 = stats.chisquare(freq.to_numpy(), P.PROB_TIPO * n)
    r.valor("q2c.qui2_aderencia", float(qui2.statistic))
    r.valor("q2c.qui2_pvalor", float(qui2.pvalue))

    a = ataques.merge(unidades, on="unidade")
    p = G.prob_materializacao(a["cvss"], a["tempo_deteccao_h"], a["soc"], a["treino"],
                              a["fora_expediente"]).to_numpy()
    ep = np.sqrt(np.sum(p * (1 - p))) / n
    r.valor("q2c.n_ataques", n, "{:d}")
    r.valor("q2c.taxa_materializacao", float(ataques["materializou"].mean()))
    r.valor("q2c.media_p_i", float(p.mean()))
    r.valor("q2c.erro_simulacao", float(ep))
    r.valor("q2c.z", float((ataques["materializou"].mean() - p.mean()) / ep))
