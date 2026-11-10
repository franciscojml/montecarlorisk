"""Parte B - Questões 9 a 13 (capítulos 8 a 11): regressão simples e múltipla,
séries temporais e classificação. Os modelos estimados aqui são as únicas
entradas da segunda SMC (Parte C)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn import metrics
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

from . import gerador as G
from . import parametros as P
from .relator import Relator

FORMULA_FREQ = "n_ataques ~ servicos + patch + treino + soc + trimestre"
FORMULA_FREQ_SAZONAL = FORMULA_FREQ + " + C(tri_ano) + campanha"
FORMULA_LOGIT = "materializou ~ cvss + tempo_deteccao_h + soc + treino + fora_expediente"
CUSTO_FALSO_POSITIVO = 3_000.0


def tabela_coeficientes(modelo, verdadeiros: dict | None = None) -> pd.DataFrame:
    """Saída no formato da tabela da Seção 10.7 (+ comparação com o gerador)."""
    ic = modelo.conf_int()
    tab = pd.DataFrame({"coeficiente": modelo.params, "erro padrão": modelo.bse,
                        "t": modelo.tvalues, "p-valor": modelo.pvalues,
                        "IC 95% inf": ic[0], "IC 95% sup": ic[1]})
    if verdadeiros is not None:
        tab["verdadeiro"] = pd.Series(verdadeiros).reindex(tab.index)
        dentro = (tab["IC 95% inf"] <= tab["verdadeiro"]) & (tab["verdadeiro"] <= tab["IC 95% sup"])
        tab["IC contém o verdadeiro"] = np.where(
            tab["verdadeiro"].isna(), "-", np.where(dentro, "sim", "não"))
    return tab


# ----------------------------------------------------------------------------
# Questões 9 e 10 - regressão simples e sua inferência (cap. 8 e 9)
# ----------------------------------------------------------------------------
def questao_9(r: Relator, pe: pd.DataFrame):
    r.secao("Questão 9 - Correlação e regressão simples (cap. 8)")
    n = len(pe)

    r.item("9-a) Dispersão e correlação")
    linhas = {}
    for nome, y in (("perda_rs", pe["perda_rs"]), ("ln(perda_rs)", pe["ln_perda"])):
        rho = np.corrcoef(pe["tempo_deteccao_h"], y)[0, 1]
        t = rho * np.sqrt(n - 2) / np.sqrt(1 - rho**2)
        linhas[nome] = {"r": rho, "r²": rho**2, "t": t, "g.l.": n - 2,
                        "p-valor (bilateral)": 2 * stats.t.sf(abs(t), n - 2)}
    r.tabela(pd.DataFrame(linhas), "q09a_correlacao", "Teste de H0: ρ = 0.", casas=6)

    modelo = smf.ols("ln_perda ~ tempo_deteccao_h", data=pe).fit()
    nivel = smf.ols("perda_rs ~ tempo_deteccao_h", data=pe).fit()
    fig, eixos = plt.subplots(1, 2, figsize=(10, 3.6))
    g = np.linspace(0, pe["tempo_deteccao_h"].max(), 100)
    eixos[0].scatter(pe["tempo_deteccao_h"], pe["perda_rs"] / 1e3, s=5, alpha=0.4)
    eixos[0].plot(g, (nivel.params.iloc[0] + nivel.params.iloc[1] * g) / 1e3, "r-")
    eixos[0].set(xlabel="tempo de detecção (h)", ylabel="perda (R$ mil)",
                 title=f"perda × tempo (r = {linhas['perda_rs']['r']:.3f})")
    eixos[1].scatter(pe["tempo_deteccao_h"], pe["ln_perda"], s=5, alpha=0.4)
    eixos[1].plot(g, modelo.params.iloc[0] + modelo.params.iloc[1] * g, "r-")
    eixos[1].set(xlabel="tempo de detecção (h)", ylabel="ln(perda)",
                 title=f"ln(perda) × tempo (r = {linhas['ln(perda_rs)']['r']:.3f})")
    r.figura(fig, "q09a_dispersao", "Diagramas de dispersão com a reta de mínimos quadrados.")

    r.item("9-b/c) Mínimos quadrados: ln(perda) = β0 + β1·tempo + erro")
    r.tabela(tabela_coeficientes(modelo), "q09b_coeficientes", "Regressão simples.", casas=5)
    b1 = modelo.params["tempo_deteccao_h"]
    r.valor("q9b.beta0", float(modelo.params["Intercept"]), "{:.5f}")
    r.valor("q9b.beta1", float(b1), "{:.5f}")
    r.valor("q9b.variacao_pct_por_hora", float(100 * (np.exp(b1) - 1)))
    r.valor("q9b.variacao_pct_por_10h", float(100 * (np.exp(10 * b1) - 1)))
    r.valor("q9b.exp_beta0", float(np.exp(modelo.params["Intercept"])), "{:,.2f}")
    r.valor("q9c.R2", float(modelo.rsquared))
    r.valor("q9c.erro_padrao_regressao", float(np.sqrt(modelo.mse_resid)))
    r.valor("q9c.n", n, "{:d}")
    # variável omitida: o tipo de ataque
    r.valor("q9c.variancia_ln_perda", float(pe["ln_perda"].var(ddof=1)))
    r.valor("q9c.variancia_entre_tipos", float(
        pe.groupby("tipo")["ln_perda"].transform("mean").var(ddof=1)))
    r.valor("q9d.corr_tempo_soc", float(np.corrcoef(pe["tempo_deteccao_h"], pe["soc"])[0, 1]))
    return modelo


def questao_10(r: Relator, pe: pd.DataFrame, modelo):
    r.secao("Questão 10 - Inferência na regressão (cap. 9)")
    n = len(pe)

    r.item("10-a) Tabela ANOVA e F = t²")
    anova = pd.DataFrame({
        "SQ": [modelo.ess, modelo.ssr, modelo.centered_tss],
        "g.l.": [1, n - 2, n - 1],
        "QM": [modelo.ess, modelo.ssr / (n - 2), np.nan],
        "F": [modelo.fvalue, np.nan, np.nan],
        "p-valor": [modelo.f_pvalue, np.nan, np.nan]},
        index=["Regressão", "Resíduo", "Total"])
    r.tabela(anova, "q10a_anova", "ANOVA da regressão simples.")
    t = modelo.tvalues["tempo_deteccao_h"]
    r.valor("q10a.F", float(modelo.fvalue))
    r.valor("q10a.t_beta1", float(t))
    r.valor("q10a.t_ao_quadrado", float(t**2))
    r.valor("q10a.F_critico", float(stats.f.ppf(0.95, 1, n - 2)))

    r.item("10-b) IC de 95% para β1")
    li, ls = modelo.conf_int().loc["tempo_deteccao_h"]
    r.valor("q10b.beta1", float(modelo.params["tempo_deteccao_h"]), "{:.5f}")
    r.valor("q10b.ic_inf", float(li), "{:.5f}")
    r.valor("q10b.ic_sup", float(ls), "{:.5f}")
    r.valor("q10b.contem_0_02", bool(li <= P.SEV_BETA_TEMPO <= ls))

    r.item("10-c) Intervalos para um ataque detectado em 24 h")
    prev = modelo.get_prediction(pd.DataFrame({"tempo_deteccao_h": [24.0]})).summary_frame(alpha=0.05)
    linha = prev.iloc[0]
    tab = pd.DataFrame({
        "ln(perda)": [linha["mean"], linha["mean_ci_lower"], linha["mean_ci_upper"],
                      linha["obs_ci_lower"], linha["obs_ci_upper"]]},
        index=["estimativa pontual", "IC da média - inf", "IC da média - sup",
               "IP individual - inf", "IP individual - sup"])
    tab["R$"] = np.exp(tab["ln(perda)"])
    r.tabela(tab, "q10c_intervalos_24h", "IC para a média e intervalo de previsão (95%).", casas=3)
    r.valor("q10c.razao_ic_media", float(np.exp(linha["mean_ci_upper"] - linha["mean_ci_lower"])))
    r.valor("q10c.razao_ip_individual", float(np.exp(linha["obs_ci_upper"] - linha["obs_ci_lower"])))
    r.valor("q10c.tempo_medio_amostra", float(pe["tempo_deteccao_h"].mean()))

    r.item("10-d) Regressão com dummies de tipo de ataque")
    com_tipo = smf.ols("ln_perda ~ tempo_deteccao_h + C(tipo, Treatment(reference='Phishing'))",
                       data=pe).fit()
    tab = tabela_coeficientes(com_tipo)
    tab.index = [i.replace("C(tipo, Treatment(reference='Phishing'))[T.", "tipo: ").rstrip("]")
                 for i in tab.index]
    # medianas implícitas x programadas
    base = com_tipo.params["Intercept"]
    med = {"Phishing": np.exp(base)}
    for nome, v in com_tipo.params.items():
        if "[T." in nome:
            med[nome.split("[T.")[1].rstrip("]")] = np.exp(base + v)
    r.tabela(tab, "q10d_coeficientes", "ln(perda) ~ tempo + tipo (base: Phishing).", casas=5)
    medianas = pd.DataFrame({"mediana estimada (tempo = 0)": pd.Series(med).reindex(P.TIPOS),
                             "mediana programada": P.MEDIANA_PERDA}, index=P.TIPOS)
    medianas["razão"] = medianas.iloc[:, 0] / medianas.iloc[:, 1]
    r.tabela(medianas, "q10d_medianas", "exp(β0 + dummy) x mediana do gerador.", casas=3)
    li2, ls2 = com_tipo.conf_int().loc["tempo_deteccao_h"]
    comp = pd.DataFrame({
        "só tempo": {"R²": modelo.rsquared, "R² ajustado": modelo.rsquared_adj,
                     "erro padrão da regressão": np.sqrt(modelo.mse_resid),
                     "β1": modelo.params["tempo_deteccao_h"], "EP(β1)": modelo.bse["tempo_deteccao_h"],
                     "IC inf": li, "IC sup": ls, "amplitude do IC": ls - li},
        "tempo + tipo": {"R²": com_tipo.rsquared, "R² ajustado": com_tipo.rsquared_adj,
                         "erro padrão da regressão": np.sqrt(com_tipo.mse_resid),
                         "β1": com_tipo.params["tempo_deteccao_h"],
                         "EP(β1)": com_tipo.bse["tempo_deteccao_h"],
                         "IC inf": li2, "IC sup": ls2, "amplitude do IC": ls2 - li2}})
    r.tabela(comp, "q10d_comparacao", "Efeito de controlar o tipo (σ programado = 0,9).", casas=5)
    r.valor("q10d.contem_0_02", bool(li2 <= P.SEV_BETA_TEMPO <= ls2))
    return com_tipo


# ----------------------------------------------------------------------------
# Questão 11 - regressão múltipla (cap. 10)
# ----------------------------------------------------------------------------
def questao_11(r: Relator, painel: pd.DataFrame, semente: int):
    r.secao("Questão 11 - Regressão múltipla (cap. 10)")
    painel = painel.copy()
    painel["tri_ano"] = (painel["trimestre"] - 1) % 4 + 1
    trimestre_campanha = int(G.trimestre_de(P.MES_CAMPANHA))
    painel["campanha"] = (painel["trimestre"] == trimestre_campanha).astype(int)

    r.item("11-a/b/c) Modelo base, testes e comparação com o gerador")
    verdadeiros = {"Intercept": P.BETA_FREQ["intercepto"],
                   **{k: v for k, v in P.BETA_FREQ.items() if k != "intercepto"}}
    base = smf.ols(FORMULA_FREQ, data=painel).fit()
    tab = tabela_coeficientes(base, verdadeiros)
    r.tabela(tab, "q11a_coeficientes", "n_ataques por unidade-trimestre (n = 288).", casas=4)
    r.valor("q11b.F", float(base.fvalue))
    r.valor("q11b.F_pvalor", float(base.f_pvalue), "{:.3e}")
    r.valor("q11b.R2", float(base.rsquared))
    r.valor("q11b.R2_ajustado", float(base.rsquared_adj))
    r.valor("q11b.erro_padrao_regressao", float(np.sqrt(base.mse_resid)))
    r.valor("q11b.media_n_ataques", float(painel["n_ataques"].mean()))
    r.valor("q11c.ics_que_contem_inclinacoes", int((tab["IC contém o verdadeiro"].iloc[1:] == "sim").sum()), "{:d}")
    r.valor("q11c.ics_que_contem_total", int((tab["IC contém o verdadeiro"] == "sim").sum()), "{:d}")

    r.item("11-d) Dummies de trimestre do ano e indicador da campanha")
    saz = smf.ols(FORMULA_FREQ_SAZONAL, data=painel).fit()
    tab_s = tabela_coeficientes(saz, verdadeiros)
    tab_s.index = [i.replace("C(tri_ano)[T.", "Q").rstrip("]") for i in tab_s.index]
    r.tabela(tab_s, "q11d_coeficientes", f"Campanha = trimestre {trimestre_campanha}.", casas=4)
    f_parcial = saz.compare_f_test(base)
    comp = pd.DataFrame({
        "base": {"R²": base.rsquared, "R² ajustado": base.rsquared_adj, "AIC": base.aic,
                 "BIC": base.bic, "erro padrão": np.sqrt(base.mse_resid)},
        "com dummies": {"R²": saz.rsquared, "R² ajustado": saz.rsquared_adj, "AIC": saz.aic,
                        "BIC": saz.bic, "erro padrão": np.sqrt(saz.mse_resid)}})
    r.tabela(comp, "q11d_comparacao", "Ajuste com e sem as dummies.")
    r.valor("q11d.F_parcial", float(f_parcial[0]))
    r.valor("q11d.F_parcial_pvalor", float(f_parcial[1]), "{:.3e}")
    r.valor("q11d.gl_F_parcial", int(f_parcial[2]), "{:d}")
    # efeitos esperados pelo gerador (em ataques por unidade-trimestre, na média das unidades)
    unid = painel.drop_duplicates("unidade")
    lam = G.taxa_mensal(unid, np.arange(1, P.N_MESES + 1), campanha=True)
    lam_sem = G.taxa_mensal(unid, np.arange(1, P.N_MESES + 1), campanha=False)
    # efeito sazonal puro (sem tendência): nível médio de lambda^trim x fator do trimestre
    nivel = G.taxa_trimestral(unid, np.arange(1, 13)).mean()
    fator = P.SAZONAL.reshape(4, 3).mean(axis=1)             # Q1..Q4: média dos S_m do trimestre
    r.valor("q11d.nivel_medio_lambda_trim", float(nivel))
    r.valor("q11d.esperado_Q2_menos_Q1", float(nivel * (fator[1] - fator[0])))
    r.valor("q11d.esperado_Q3_menos_Q1", float(nivel * (fator[2] - fator[0])))
    r.valor("q11d.esperado_Q4_menos_Q1", float(nivel * (fator[3] - fator[0])))
    r.valor("q11d.esperado_campanha", float((lam - lam_sem).mean(axis=0).sum()))

    r.item("11-e) VIFs e diagnóstico de resíduos")
    exog = pd.DataFrame(base.model.exog, columns=base.model.exog_names)
    vif = pd.Series({c: variance_inflation_factor(exog.to_numpy(), i)
                     for i, c in enumerate(exog.columns) if c != "Intercept"}, name="VIF")
    r.tabela(vif.to_frame(), "q11e_vif", "Fatores de inflação da variância (modelo base).", casas=3)
    bp = het_breuschpagan(base.resid, base.model.exog)
    r.valor("q11e.breusch_pagan_LM", float(bp[0]))
    r.valor("q11e.breusch_pagan_pvalor", float(bp[1]), "{:.3e}")
    r.valor("q11e.shapiro_residuos_p", float(stats.shapiro(base.resid).pvalue), "{:.3e}")
    # teste dirigido ao funil: a variância do resíduo cresce com o valor ajustado?
    bp_aj = het_breuschpagan(base.resid, sm.add_constant(base.fittedvalues.to_numpy()))
    r.valor("q11e.breusch_pagan_ajustados_LM", float(bp_aj[0]))
    r.valor("q11e.breusch_pagan_ajustados_pvalor", float(bp_aj[1]), "{:.4f}")
    sp = stats.spearmanr(base.fittedvalues, base.resid.abs())
    r.valor("q11e.spearman_absres_ajustado", float(sp.statistic))
    r.valor("q11e.spearman_pvalor", float(sp.pvalue), "{:.4f}")
    r.valor("q11e.variancia_residuos", float(base.resid.var(ddof=len(base.params))))
    tercis = pd.qcut(base.fittedvalues, 3, labels=["ajustados baixos", "médios", "altos"])
    funil = pd.DataFrame({"média dos ajustados": base.fittedvalues.groupby(tercis, observed=True).mean(),
                          "variância dos resíduos": base.resid.groupby(tercis, observed=True).var()})
    funil["variância/média"] = funil["variância dos resíduos"] / funil["média dos ajustados"]
    r.tabela(funil, "q11e_funil", "Poisson: variância do erro ≈ média ajustada.", casas=3)
    fig, eixos = plt.subplots(1, 2, figsize=(10, 3.6))
    eixos[0].scatter(base.fittedvalues, base.resid, s=8, alpha=0.5)
    eixos[0].axhline(0, color="k", lw=0.8)
    g = np.linspace(max(base.fittedvalues.min(), 0.1), base.fittedvalues.max(), 100)
    eixos[0].plot(g, 2 * np.sqrt(g), "r--", lw=0.9, label="±2·raiz(ajustado)")
    eixos[0].plot(g, -2 * np.sqrt(g), "r--", lw=0.9)
    eixos[0].set(xlabel="valores ajustados", ylabel="resíduos", title="Resíduos × ajustados")
    eixos[0].legend()
    (osm, osr), (incl, inter, _) = stats.probplot(base.resid, dist="norm")
    eixos[1].scatter(osm, osr, s=8)
    eixos[1].plot(osm, inter + incl * osm, "r-", lw=1)
    eixos[1].set(xlabel="quantis teóricos", ylabel="resíduos", title="Q-Q dos resíduos")
    r.figura(fig, "q11e_residuos", "Diagnóstico de resíduos do modelo base.")

    r.item("11-f) Sobreajuste: cinco variáveis de ruído puro")
    rng = np.random.default_rng([semente, 11])
    ruido = [f"ruido{i}" for i in range(1, 6)]
    painel[ruido] = rng.standard_normal((len(painel), 5))
    tr, te = painel[painel["trimestre"] <= 8], painel[painel["trimestre"] > 8]
    linhas = {}
    for nome, formula in (("sem ruído", FORMULA_FREQ),
                          ("com 5 ruídos", FORMULA_FREQ + " + " + " + ".join(ruido))):
        m = smf.ols(formula, data=tr).fit()
        erro = te["n_ataques"] - m.predict(te)
        linhas[nome] = {
            "parâmetros": len(m.params), "R² treino": m.rsquared, "R² ajustado treino": m.rsquared_adj,
            "REQM treino": np.sqrt(np.mean(m.resid**2)), "REQM teste": np.sqrt(np.mean(erro**2)),
            "EAM teste": np.mean(np.abs(erro)), "viés teste (obs − prev)": erro.mean(),
            "R² teste": 1 - np.sum(erro**2) / np.sum((te["n_ataques"] - te["n_ataques"].mean())**2)}
    r.tabela(pd.DataFrame(linhas), "q11f_sobreajuste",
             "Treino: trimestres 1–8 (2023–2024); teste: 9–12 (2025).")
    return base, saz


# ----------------------------------------------------------------------------
# Questão 12 - séries temporais (cap. 11, Parte A)
# ----------------------------------------------------------------------------
def suavizacao_exponencial(y: np.ndarray, alfa: float) -> np.ndarray:
    """S_t = alfa·Y_t + (1 − alfa)·S_{t−1}, com S_1 = Y_1 (Seção 11.3)."""
    s = np.empty(len(y))
    s[0] = y[0]
    for i in range(1, len(y)):
        s[i] = alfa * y[i] + (1 - alfa) * s[i - 1]
    return s


def questao_12(r: Relator, serie: pd.DataFrame, unidades: pd.DataFrame):
    r.secao("Questão 12 - Séries temporais (cap. 11, Parte A)")
    y = serie["n_ataques"].to_numpy(float)
    n = len(y)
    t = np.arange(1, n + 1)
    mes = G.mes_calendario(t)
    indice = pd.PeriodIndex(serie["mes_ref"], freq="M")
    ys = pd.Series(y, index=indice.to_timestamp())

    r.item("12-a) Médias móveis e suavização exponencial")
    mm3 = ys.rolling(3, center=True).mean()
    mm12 = ys.rolling(12).mean().shift(-6).rolling(2).mean()        # 2×12 centrada
    grade = np.round(np.arange(0.05, 1.0, 0.05), 2)
    sqe = [np.sum((y[1:] - suavizacao_exponencial(y, a)[:-1])**2) for a in grade]
    alfa_otimo = float(grade[int(np.argmin(sqe))])
    se03 = suavizacao_exponencial(y, 0.3)
    r.valor("q12a.alfa_otimo_previsao_1_passo", alfa_otimo, "{:.2f}")
    r.valor("q12a.media_2023", float(y[:12].mean()), "{:.2f}")
    r.valor("q12a.media_2024", float(y[12:24].mean()), "{:.2f}")
    r.valor("q12a.media_2025", float(y[24:].mean()), "{:.2f}")
    r.valor("q12a.media_2025_sem_abril", float(np.delete(y[24:], 3).mean()), "{:.2f}")
    tend = sm.OLS(y, sm.add_constant(t)).fit()
    r.valor("q12a.tendencia_linear_por_mes", float(tend.params[1]))
    r.valor("q12a.tendencia_pvalor", float(tend.pvalues[1]), "{:.4f}")
    r.valor("q12a.tendencia_programada_por_mes", float(
        P.BETA_FREQ["trimestre"] / 3 / 3 * len(unidades)))
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.plot(ys.index, y, "o-", ms=3, lw=0.9, color="gray", label="n_ataques")
    ax.plot(ys.index, mm3, lw=1.3, label="média móvel 3")
    ax.plot(ys.index, mm12, lw=1.8, label="média móvel 12 (centrada)")
    ax.plot(ys.index, se03, lw=1.3, ls="--", label="suav. exponencial (α = 0,3)")
    ax.set(ylabel="ataques por mês", title="Série mensal de ataques da ANDI")
    ax.legend(ncol=2, fontsize=7)
    r.figura(fig, "q12a_serie", "Série, médias móveis e suavização exponencial.")

    r.item("12-b) Decomposição multiplicativa")
    dec = sm.tsa.seasonal_decompose(ys, model="multiplicative", period=12)
    saz = dec.seasonal.iloc[:12].to_numpy()
    nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    tab = pd.DataFrame({"índice estimado": saz, "S_m programado": P.SAZONAL}, index=nomes)
    tab["diferença"] = tab["índice estimado"] - tab["S_m programado"]
    r.tabela(tab, "q12b_indices_sazonais", "Índices sazonais (decomposição clássica, período 12).", casas=3)
    r.valor("q12b.correlacao_indices", float(np.corrcoef(saz, P.SAZONAL)[0, 1]))
    r.valor("q12b.erro_abs_medio_indices", float(np.mean(np.abs(saz - P.SAZONAL))))
    # o coeficiente de variação por ano é estável? (argumento pró-multiplicativo)
    r.valor("q12b.dp_2023", float(y[:12].std(ddof=1)), "{:.2f}")
    r.valor("q12b.dp_2024", float(y[12:24].std(ddof=1)), "{:.2f}")
    fig = dec.plot()
    fig.set_size_inches(9, 6)
    r.figura(fig, "q12b_decomposicao", "Decomposição multiplicativa: tendência, sazonalidade e resíduo.")

    r.item("12-c) Função de autocorrelação")
    acf = sm.tsa.acf(y, nlags=12, fft=False)
    limite = 1.96 / np.sqrt(n)
    tab = pd.DataFrame({"ACF": acf[1:], "significativa (|r| > 1,96/√n)": np.abs(acf[1:]) > limite},
                       index=pd.Index(range(1, 13), name="defasagem"))
    r.tabela(tab, "q12c_acf", f"Limite de significância ±{limite:.3f}.", casas=3)
    r.valor("q12c.limite", float(limite))
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(range(1, 13), acf[1:], width=0.5)
    ax.axhline(limite, color="r", ls="--", lw=0.8)
    ax.axhline(-limite, color="r", ls="--", lw=0.8)
    ax.axhline(0, color="k", lw=0.8)
    ax.set(xlabel="defasagem (meses)", ylabel="autocorrelação", xticks=range(1, 13))
    r.figura(fig, "q12c_acf", "ACF de n_ataques até a defasagem 12.")

    r.item("12-d) Previsão de 2026 e regra dos 3σ")
    dessaz = y / saz[mes - 1]
    reta = sm.OLS(dessaz, sm.add_constant(t)).fit()
    ajustado = reta.fittedvalues * saz[mes - 1]
    residuo = y - ajustado
    sigma = residuo.std(ddof=2)
    z = residuo / sigma
    tab = pd.DataFrame({"mes_ref": serie["mes_ref"], "observado": y, "ajustado": ajustado,
                        "resíduo": residuo, "z": z}).set_index("mes_ref")
    r.tabela(tab.loc[tab["z"].abs().sort_values(ascending=False).index].head(6),
             "q12d_maiores_residuos", "Os seis maiores |z| (tendência × sazonalidade).", casas=3)
    r.valor("q12d.sigma_residuos", float(sigma))
    r.valor("q12d.z_abril_2025", float(z[P.MES_CAMPANHA - 1]))
    r.valor("q12d.alarmes_3sigma", ", ".join(serie["mes_ref"][np.abs(z) > 3]) or "nenhum")
    r.valor("q12d.alarmes_2sigma", ", ".join(serie["mes_ref"][np.abs(z) > 2]) or "nenhum")
    # Versão robusta (complemento): a decomposição clássica só tem dois abris utilizáveis
    # (a média móvel centrada perde 6 meses em cada ponta) e tira a MÉDIA deles, de modo
    # que a campanha contamina o próprio índice de abril e infla o sigma (mascaramento).
    # Aqui: razão à reta de tendência nos 36 meses e MEDIANA dos três anos por mês do
    # calendário. O sigma não é estimado dos resíduos (que a anomalia contamina): como a
    # série é uma contagem de Poisson (Questões 2 e 6), usa-se sigma_t = raiz(ajustado_t).
    razao = y / tend.fittedvalues
    saz_rob = np.array([np.median(razao[mes == m]) for m in range(1, 13)])
    saz_rob = saz_rob / saz_rob.mean()
    reta_rob = sm.OLS(y / saz_rob[mes - 1], sm.add_constant(t)).fit()
    ajustado_rob = reta_rob.fittedvalues * saz_rob[mes - 1]
    res_rob = y - ajustado_rob
    z_rob = res_rob / np.sqrt(ajustado_rob)
    r.valor("q12d.z_abril_2025_classico_sigma_poisson", float(
        residuo[P.MES_CAMPANHA - 1] / np.sqrt(ajustado[P.MES_CAMPANHA - 1])))
    tab_rob = pd.DataFrame({"índice clássico": saz, "índice robusto": saz_rob,
                            "S_m programado": P.SAZONAL}, index=nomes)
    r.tabela(tab_rob, "q12d_indices_robustos", "Índices sazonais: média de 2 anos x mediana de 3 anos.", casas=3)
    r.valor("q12d.robusto.erro_abs_medio_indices", float(np.mean(np.abs(saz_rob - P.SAZONAL))))
    r.valor("q12d.robusto.sigma_abril_2025", float(np.sqrt(ajustado_rob[P.MES_CAMPANHA - 1])))
    r.valor("q12d.robusto.z_abril_2025", float(z_rob[P.MES_CAMPANHA - 1]))
    r.valor("q12d.robusto.maior_z_fora_abril_2025", float(
        np.max(np.abs(np.delete(z_rob, P.MES_CAMPANHA - 1)))))
    r.valor("q12d.robusto.alarmes_3sigma", ", ".join(serie["mes_ref"][np.abs(z_rob) > 3]) or "nenhum")
    tab_z = pd.DataFrame({"mes_ref": serie["mes_ref"], "observado": y, "ajustado": ajustado_rob,
                          "resíduo": res_rob, "z robusto": z_rob}).set_index("mes_ref")
    r.tabela(tab_z.loc[tab_z["z robusto"].abs().sort_values(ascending=False).index].head(6),
             "q12d_maiores_residuos_robusto", "Os seis maiores |z| na versão robusta.", casas=3)

    t_fut = np.arange(n + 1, n + 13)
    prev = reta.get_prediction(sm.add_constant(t_fut, has_constant="add")).summary_frame(alpha=0.05)
    s_fut = saz[G.mes_calendario(t_fut) - 1]
    verdadeiro = G.taxa_mensal(unidades, t_fut, campanha=False).sum(axis=0)
    tab = pd.DataFrame({
        "previsão": prev["mean"].to_numpy() * s_fut,
        "limite inf (95%)": prev["obs_ci_lower"].to_numpy() * s_fut,
        "limite sup (95%)": prev["obs_ci_upper"].to_numpy() * s_fut,
        "previsão (índices robustos)": reta_rob.predict(sm.add_constant(t_fut, has_constant="add"))
        * saz_rob[G.mes_calendario(t_fut) - 1],
        "esperado pelo gerador (Σλ)": verdadeiro},
        index=[f"2026-{m:02d}" for m in range(1, 13)])
    tab.loc["Total 2026"] = tab.sum()
    tab.loc["Total 2026", ["limite inf (95%)", "limite sup (95%)"]] = np.nan
    r.tabela(tab, "q12d_previsao_2026", "Tendência linear × índices sazonais.", casas=1)
    r.valor("q12d.total_previsto_2026", float(tab.loc["Total 2026", "previsão"]), "{:.1f}")
    r.valor("q12d.total_previsto_2026_robusto", float(
        tab.loc["Total 2026", "previsão (índices robustos)"]), "{:.1f}")
    r.valor("q12d.total_verdadeiro_2026", float(verdadeiro.sum()), "{:.1f}")
    r.valor("q12d.eam_previsao_classica_vs_gerador", float(
        np.mean(np.abs(tab["previsão"].iloc[:12] - verdadeiro))))
    r.valor("q12d.eam_previsao_robusta_vs_gerador", float(
        np.mean(np.abs(tab["previsão (índices robustos)"].iloc[:12] - verdadeiro))))
    r.valor("q12d.total_observado_2025", float(y[24:].sum()), "{:.0f}")

    fig, ax = plt.subplots(figsize=(10, 3.6))
    fut = pd.period_range("2026-01", periods=12, freq="M").to_timestamp()
    ax.plot(ys.index, y, "o-", ms=3, lw=0.9, color="gray", label="observado")
    ax.plot(ys.index, ajustado, lw=1.2, label="ajustado")
    ax.plot(fut, tab["previsão"].iloc[:12], "b-", lw=1.5, label="previsão 2026")
    ax.fill_between(fut, tab["limite inf (95%)"].iloc[:12].astype(float),
                    tab["limite sup (95%)"].iloc[:12].astype(float), alpha=0.2, label="banda de 95%")
    ax.plot(fut, verdadeiro, "g--", lw=1, label="esperado pelo gerador")
    anom = np.abs(z_rob) > 3
    ax.scatter(ys.index[anom], y[anom], color="red", zorder=5, s=40, label="|z robusto| > 3")
    ax.set(ylabel="ataques por mês")
    ax.legend(ncol=3, fontsize=7)
    r.figura(fig, "q12d_previsao", "Previsão de 2026 com banda de incerteza e anomalias (3σ).")


# ----------------------------------------------------------------------------
# Questão 13 - classificação (cap. 11, Parte B)
# ----------------------------------------------------------------------------
def _metricas(y, prob, limiar: float) -> dict:
    prev = (prob >= limiar).astype(int)
    vn, fp, fn, vp = metrics.confusion_matrix(y, prev, labels=[0, 1]).ravel()
    return {"limiar": limiar, "VP": vp, "FP": fp, "FN": fn, "VN": vn,
            "acurácia": metrics.accuracy_score(y, prev),
            "precisão": metrics.precision_score(y, prev, zero_division=0),
            "recall": metrics.recall_score(y, prev, zero_division=0),
            "F1": metrics.f1_score(y, prev, zero_division=0),
            "AUC": metrics.roc_auc_score(y, prob)}


def questao_13(r: Relator, at: pd.DataFrame, pe: pd.DataFrame):
    r.secao("Questão 13 - Classificação (cap. 11, Parte B)")
    tr, te = at[at["ano"] <= 2024], at[at["ano"] == 2025]
    atributos = ["cvss", "tempo_deteccao_h", "soc", "treino", "fora_expediente"]
    r.valor("q13.n_treino", len(tr), "{:d}")
    r.valor("q13.n_teste", len(te), "{:d}")
    r.valor("q13.prevalencia_treino", float(tr["materializou"].mean()))
    r.valor("q13.prevalencia_teste", float(te["materializou"].mean()))

    r.item("13-a) Regressão logística")
    logit = smf.logit(FORMULA_LOGIT, data=tr).fit(disp=0)
    verdadeiros = {"Intercept": P.BETA_LOGIT["intercepto"],
                   **{k: v for k, v in P.BETA_LOGIT.items() if k != "intercepto"}}
    tab = tabela_coeficientes(logit, verdadeiros).rename(columns={"t": "z"})
    tab.insert(1, "razão de chances e^β", np.exp(tab["coeficiente"]))
    tab["e^β verdadeiro"] = np.exp(tab["verdadeiro"])
    r.tabela(tab, "q13a_logistica", "Treino 2023–2024.", casas=4)
    r.valor("q13a.pseudo_R2", float(logit.prsquared))
    r.valor("q13a.ics_que_contem", int((tab["IC contém o verdadeiro"] == "sim").sum()), "{:d}")

    r.item("13-b) Dummies de tipo de ataque")
    com_tipo = smf.logit(FORMULA_LOGIT + " + C(tipo, Treatment(reference='Phishing'))",
                         data=tr).fit(disp=0)
    tab_t = tabela_coeficientes(com_tipo).rename(columns={"t": "z"})
    tab_t.index = [i.replace("C(tipo, Treatment(reference='Phishing'))[T.", "tipo: ").rstrip("]")
                   for i in tab_t.index]
    r.tabela(tab_t, "q13b_logistica_tipo", "Com dummies de tipo (base: Phishing).", casas=4)
    rv = 2 * (com_tipo.llf - logit.llf)
    r.valor("q13b.razao_verossimilhanca", float(rv))
    r.valor("q13b.gl", 5, "{:d}")
    r.valor("q13b.p_valor", float(stats.chi2.sf(rv, 5)), "{:.4f}")
    r.valor("q13b.AIC_sem_tipo", float(logit.aic), "{:.2f}")
    r.valor("q13b.AIC_com_tipo", float(com_tipo.aic), "{:.2f}")
    r.valor("q13b.dummies_significativas_5pct", int((tab_t.loc[
        [i for i in tab_t.index if i.startswith("tipo: ")], "p-valor"] < 0.05).sum()), "{:d}")
    so_tipo = smf.logit("materializou ~ C(tipo, Treatment(reference='Phishing'))", data=tr).fit(disp=0)
    r.valor("q13b.so_tipo_LR_pvalor", float(so_tipo.llr_pvalue), "{:.3e}")

    r.item("13-c) Árvore de decisão (profundidade máxima 3)")
    arvore = DecisionTreeClassifier(max_depth=3, random_state=0).fit(tr[atributos], tr["materializou"])
    regras = export_text(arvore, feature_names=atributos, show_weights=True, decimals=2)
    r.texto("```\n" + regras + "```")
    r.tabela(pd.Series(arvore.feature_importances_, index=atributos, name="importância").to_frame(),
             "q13c_importancias", "Importância das variáveis na árvore.")
    fig, ax = plt.subplots(figsize=(13, 5))
    plot_tree(arvore, feature_names=atributos, class_names=["não", "materializa"], filled=True,
              proportion=True, impurity=False, fontsize=7, ax=ax, precision=2)
    r.figura(fig, "q13c_arvore", "Árvore de decisão (treino 2023–2024).")

    r.item("13-d) Avaliação no teste (2025)")
    y = te["materializou"].to_numpy()
    prob = {"Logística": logit.predict(te).to_numpy(),
            "Árvore": arvore.predict_proba(te[atributos])[:, 1]}
    tab = pd.DataFrame({nome: _metricas(y, p, 0.5) for nome, p in prob.items()})
    r.tabela(tab, "q13d_metricas", "Limiar 0,5. Matriz de confusão em VP/FP/FN/VN.")
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    for nome, p in prob.items():
        fpr, tpr, _ = metrics.roc_curve(y, p)
        ax.plot(fpr, tpr, label=f"{nome} (AUC = {metrics.roc_auc_score(y, p):.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set(xlabel="taxa de falsos positivos", ylabel="taxa de verdadeiros positivos (recall)",
           title="Curva ROC - teste 2025")
    ax.legend()
    r.figura(fig, "q13d_roc", "Curvas ROC dos dois classificadores.")

    r.item("13-e) Limiar de custo mínimo")
    custo_fn = float(pe.loc[pe["data"].dt.year <= 2024, "perda_rs"].median())
    r.valor("q13e.custo_FN_mediana_treino", custo_fn, "{:,.2f}")
    r.valor("q13e.mediana_perda_base_inteira", float(pe["perda_rs"].median()), "{:,.2f}")
    r.valor("q13e.custo_FP", CUSTO_FALSO_POSITIVO, "{:,.2f}")
    r.valor("q13e.limiar_teorico", CUSTO_FALSO_POSITIVO / (CUSTO_FALSO_POSITIVO + custo_fn))
    limiares = np.round(np.arange(0.01, 1.0, 0.01), 2)

    def custo(yv, pv, lim):
        prev = pv >= lim
        return custo_fn * np.sum((yv == 1) & ~prev) + CUSTO_FALSO_POSITIVO * np.sum((yv == 0) & prev)

    y_tr = tr["materializou"].to_numpy()
    prob_tr = {"Logística": logit.predict(tr).to_numpy(),
               "Árvore": arvore.predict_proba(tr[atributos])[:, 1]}
    fig, ax = plt.subplots(figsize=(7, 3.4))
    linhas = {}
    for nome in prob:
        c_tr = np.array([custo(y_tr, prob_tr[nome], l) for l in limiares])
        c_te = np.array([custo(y, prob[nome], l) for l in limiares])
        otimo = float(limiares[int(np.argmin(c_tr))])
        ax.plot(limiares, c_te / 1e6, label=f"{nome} (teste)")
        ax.axvline(otimo, ls=":", lw=0.8, color="gray")
        for rotulo, lim in (("limiar 0,5", 0.5), ("limiar de custo mínimo", otimo)):
            m = _metricas(y, prob[nome], lim)
            m["custo no teste (R$)"] = custo(y, prob[nome], lim)
            m["custo por ataque (R$)"] = m["custo no teste (R$)"] / len(y)
            linhas[f"{nome} - {rotulo}"] = m
        linhas[f"{nome} - limiar 0,5"]["limiar ótimo no próprio teste"] = float(
            limiares[int(np.argmin(c_te))])
    ax.set(xlabel="limiar de classificação", ylabel="custo total no teste (R$ milhões)")
    ax.legend()
    r.figura(fig, "q13e_custo", "Custo esperado por limiar (linha pontilhada: limiar escolhido no treino).")
    r.tabela(pd.DataFrame(linhas), "q13e_custo", "Limiar escolhido no treino e avaliado no teste.", casas=3)
    r.valor("q13e.custo_alarmar_tudo", float(CUSTO_FALSO_POSITIVO * np.sum(y == 0)), "{:,.2f}")
    r.valor("q13e.custo_nunca_alarmar", float(custo_fn * np.sum(y == 1)), "{:,.2f}")
    return logit
