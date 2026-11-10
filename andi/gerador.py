"""Parte A - modelo gerador das bases (primeira SMC: o "mundo real").

Correspondência com os quatro passos da Seção 12.2 do livro
-----------------------------------------------------------
Passo 1 - MODELAR : `parametros.py` (distribuições e coeficientes) e as
                    funções `taxa_trimestral`, `taxa_mensal`,
                    `prob_materializacao` e `log_mediana_perda`, que
                    escrevem a relação entre entradas e saídas.
Passo 2 - SORTEAR : `gerar_unidades` (Etapa A1) e `sortear_ataques`
                    (Etapas A2 a A5), sempre por transformação inversa de
                    U ~ Uniforme[0,1) (módulo `sorteio.py`).
Passo 3 - CALCULAR: dentro de `sortear_ataques` (taxa -> contagem ->
                    atributos -> p_i -> perda) e em `montar_bases`,
                    `derivar_painel_trimestral`, `derivar_serie_mensal`.
Passo 4 - ANALISAR: módulos `parte_a.py` (verificação do gerador),
                    `parte_b.py` (capítulos 1 a 11) e `parte_c.py`.

Ordem dos sorteios (fixa, para reprodutibilidade com a semente do grupo):
A1 servicos, patch, treino, soc -> A2 contagens N[u,t] -> A3 dia, tipo,
fora_expediente, cvss, tempo -> A4 materializou -> A5 ruído da perda.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from . import parametros as P
from . import sorteio as S

ARQUIVOS = ["unidades", "ataques", "perdas", "painel_trimestral", "serie_mensal"]


# ----------------------------------------------------------------------------
# Passo 1 - MODELAR: relações determinísticas do gerador
# ----------------------------------------------------------------------------
def trimestre_de(t):
    """q(t) = teto(t/3): 1 a 12 no histórico, 13 a 16 em 2026."""
    return np.ceil(np.asarray(t) / 3).astype(int)


def mes_calendario(t):
    """m(t): mês do calendário (1 a 12)."""
    return (np.asarray(t) - 1) % 12 + 1


def ano_de(t):
    return P.ANO_INICIAL + (np.asarray(t) - 1) // 12


def taxa_trimestral(unidades: pd.DataFrame, q, beta=None) -> np.ndarray:
    """lambda^trim[u, q] da Etapa A2 (matriz unidades x trimestres)."""
    b = P.BETA_FREQ if beta is None else beta
    base = (b["intercepto"]
            + b["servicos"] * unidades["servicos"].to_numpy(float)
            + b["patch"] * unidades["patch"].to_numpy(float)
            + b["treino"] * unidades["treino"].to_numpy(float)
            + b["soc"] * unidades["soc"].to_numpy(float))
    return base[:, None] + b["trimestre"] * np.atleast_1d(q)[None, :]


def taxa_mensal(unidades: pd.DataFrame, t, campanha: bool = True) -> np.ndarray:
    """lambda[u, t] = lambda^trim[u, q(t)] / 3 * S_m(t) * C_t."""
    t = np.atleast_1d(t)
    lam = taxa_trimestral(unidades, trimestre_de(t)) / 3.0
    lam = lam * P.SAZONAL[mes_calendario(t) - 1][None, :]
    if campanha:
        lam = lam * np.where(t == P.MES_CAMPANHA, P.FATOR_CAMPANHA, 1.0)[None, :]
    return lam


def prob_materializacao(cvss, tempo, soc, treino, fora, beta=None):
    """p_i do modelo logístico da Etapa A4."""
    b = P.BETA_LOGIT if beta is None else beta
    logit = (b["intercepto"] + b["cvss"] * cvss + b["tempo_deteccao_h"] * tempo
             + b["soc"] * soc + b["treino"] * treino + b["fora_expediente"] * fora)
    return 1.0 / (1.0 + np.exp(-logit))


def log_mediana_perda(tipo_idx, tempo):
    """Média de ln(perda) na Etapa A5: ln(mediana do tipo) + 0,02 * tempo."""
    return np.log(P.MEDIANA_PERDA[tipo_idx]) + P.SEV_BETA_TEMPO * tempo


# ----------------------------------------------------------------------------
# Passo 2 - SORTEAR (e Passo 3 - CALCULAR, encadeado)
# ----------------------------------------------------------------------------
def gerar_unidades(rng: np.random.Generator) -> pd.DataFrame:
    """Etapa A1 - perfil fixo das 24 unidades."""
    n = P.N_UNIDADES
    servicos = S.uniforme_discreta(rng.random(n), P.SERVICOS_MIN, P.SERVICOS_MAX)
    patch = np.round(S.triangular_inv(rng.random(n), *P.PATCH_TRI), 2)
    treino = np.round(S.uniforme_continua(rng.random(n), P.TREINO_MIN, P.TREINO_MAX), 2)
    soc = S.bernoulli(rng.random(n), P.P_SOC)
    return pd.DataFrame({
        "unidade": [f"U{i:02d}" for i in range(1, n + 1)],
        "servicos": servicos, "patch": patch, "treino": treino, "soc": soc,
    })


def sortear_ataques(rng: np.random.Generator, unidades: pd.DataFrame, t,
                    campanha: bool = True, replicas: int = 1) -> dict:
    """Etapas A2 a A5 para os meses `t`, em `replicas` histórias independentes.

    Devolve um dicionário de vetores (uma posição por ataque). `replicas` > 1
    é usado na Questão 14-g (10.000 anos de 2026 com os parâmetros verdadeiros).
    """
    t = np.atleast_1d(t)
    n_u, n_t = len(unidades), len(t)
    soc_u = unidades["soc"].to_numpy(int)
    treino_u = unidades["treino"].to_numpy(float)

    # --- A2: N[u,t] ~ Poisson(lambda[u,t]) -----------------------------------
    lam = taxa_mensal(unidades, t, campanha)                 # (unidade, mês)
    contagens = S.poisson_inv(rng.random((replicas, n_t, n_u)), lam.T[None, :, :])
    celula = np.repeat(np.arange(contagens.size), contagens.ravel())
    rep = celula // (n_t * n_u)
    i_t = (celula // n_u) % n_t
    i_u = celula % n_u
    n = celula.size
    mes_t = t[i_t]

    # --- A3: atributos de cada ataque ----------------------------------------
    dia = S.uniforme_discreta(rng.random(n), 1, P.DIAS_NO_MES[mes_calendario(mes_t) - 1])
    tipo = S.categorica(rng.random(n), P.PROB_TIPO)
    fora = S.bernoulli(rng.random(n), P.P_FORA_EXPEDIENTE)
    tri = P.CVSS_TRI[tipo]
    cvss = np.round(S.triangular_inv(rng.random(n), tri[:, 0], tri[:, 1], tri[:, 2]), 1)
    theta = np.where(soc_u[i_u] == 1, P.THETA_COM_SOC, P.THETA_SEM_SOC)
    tempo = S.exponencial_inv(rng.random(n), theta)
    tempo = np.round(tempo * np.where(fora == 1, P.FATOR_FORA_EXPEDIENTE, 1.0), 2)

    # --- A4: materialização ---------------------------------------------------
    p = prob_materializacao(cvss, tempo, soc_u[i_u], treino_u[i_u], fora)
    materializou = S.bernoulli(rng.random(n), p)

    # --- A5: severidade (somente se materializou = 1) -------------------------
    perda = np.full(n, np.nan)
    m = materializou == 1
    ruido = P.SEV_SIGMA * S.normal_padrao_inv(rng.random(int(m.sum())))
    perda[m] = np.round(np.exp(log_mediana_perda(tipo[m], tempo[m]) + ruido), 2)

    return {"replica": rep, "i_unidade": i_u, "t": mes_t, "dia": dia, "tipo": tipo,
            "fora_expediente": fora, "cvss": cvss, "tempo_deteccao_h": tempo,
            "p_verdadeiro": p, "materializou": materializou, "perda_rs": perda}


# ----------------------------------------------------------------------------
# Passo 3 - CALCULAR: montagem das bases
# ----------------------------------------------------------------------------
def montar_bases(unidades: pd.DataFrame, sorteio: dict) -> dict:
    """Transforma os vetores sorteados em ataques.csv e perdas.csv."""
    t = sorteio["t"]
    df = pd.DataFrame({
        "unidade": unidades["unidade"].to_numpy()[sorteio["i_unidade"]],
        "t": t,
        "ano": ano_de(t),
        "mes": mes_calendario(t),
        "dia": sorteio["dia"],
        "trimestre": trimestre_de(t),
        "tipo": np.array(P.TIPOS, dtype=object)[sorteio["tipo"]],
        "fora_expediente": sorteio["fora_expediente"],
        "cvss": sorteio["cvss"],
        "tempo_deteccao_h": sorteio["tempo_deteccao_h"],
        "materializou": sorteio["materializou"],
        "perda_rs": sorteio["perda_rs"],
    })
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=df["dia"]))
    df = df.sort_values(["data", "unidade"], kind="stable").reset_index(drop=True)
    df.insert(0, "id_ataque", np.arange(1, len(df) + 1))

    ataques = df[["id_ataque", "unidade", "data", "ano", "mes", "trimestre", "tipo",
                  "fora_expediente", "cvss", "tempo_deteccao_h", "materializou"]].copy()
    perdas = df.loc[df["materializou"] == 1,
                    ["id_ataque", "unidade", "data", "tipo", "tempo_deteccao_h", "perda_rs"]].copy()
    perdas.insert(0, "id_perda", np.arange(1, len(perdas) + 1))
    return {"unidades": unidades.copy(), "ataques": ataques,
            "perdas": perdas.reset_index(drop=True)}


def derivar_painel_trimestral(unidades, ataques, perdas) -> pd.DataFrame:
    """unidade x trimestre (24 x 12 = 288 linhas), com zeros explícitos."""
    grade = pd.MultiIndex.from_product(
        [unidades["unidade"], range(1, P.N_MESES // 3 + 1)], names=["unidade", "trimestre"])
    n_at = ataques.groupby(["unidade", "trimestre"]).size()
    p = perdas.merge(ataques[["id_ataque", "trimestre"]], on="id_ataque")
    ag = p.groupby(["unidade", "trimestre"])["perda_rs"].agg(["size", "sum"])
    painel = pd.DataFrame({
        "n_ataques": n_at.reindex(grade, fill_value=0),
        "n_perdas": ag["size"].reindex(grade, fill_value=0),
        "perda_total": ag["sum"].reindex(grade, fill_value=0.0).round(2),
    }).reset_index()
    return painel.merge(unidades, on="unidade")


def derivar_serie_mensal(ataques, perdas) -> pd.DataFrame:
    """Uma linha por mês (36), com zeros explícitos."""
    meses = pd.period_range(f"{P.ANO_INICIAL}-01", periods=P.N_MESES, freq="M")
    ref_a = ataques["data"].dt.to_period("M")
    ref_p = perdas["data"].dt.to_period("M")
    ag = perdas.groupby(ref_p)["perda_rs"].agg(["size", "sum"])
    serie = pd.DataFrame({
        "n_ataques": ataques.groupby(ref_a).size().reindex(meses, fill_value=0),
        "n_perdas": ag["size"].reindex(meses, fill_value=0),
        "perda_total": ag["sum"].reindex(meses, fill_value=0.0).round(2),
    })
    serie.insert(0, "mes_ref", meses.astype(str))
    return serie.reset_index(drop=True)


def gerar_bases(semente: int) -> dict:
    """Gera as cinco bases a partir da semente do grupo."""
    rng = np.random.default_rng(semente)
    unidades = gerar_unidades(rng)
    sorteio = sortear_ataques(rng, unidades, np.arange(1, P.N_MESES + 1), campanha=True)
    bases = montar_bases(unidades, sorteio)
    bases["painel_trimestral"] = derivar_painel_trimestral(
        bases["unidades"], bases["ataques"], bases["perdas"])
    bases["serie_mensal"] = derivar_serie_mensal(bases["ataques"], bases["perdas"])
    return bases


# ----------------------------------------------------------------------------
# Entrada e saída
# ----------------------------------------------------------------------------
def salvar_bases(bases: dict, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS:
        df = bases[nome].copy()
        if "data" in df:
            df["data"] = df["data"].dt.strftime("%Y-%m-%d")
        df.to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    with pd.ExcelWriter(pasta / "bases_andi.xlsx") as planilha:
        for nome in ARQUIVOS:
            bases[nome].to_excel(planilha, sheet_name=nome, index=False)


def carregar_bases(pasta: Path) -> dict:
    """Lê as bases do disco: a Parte B trabalha só com os arquivos entregues."""
    bases = {n: pd.read_csv(pasta / f"{n}.csv", encoding="utf-8-sig") for n in ARQUIVOS}
    for nome in ("ataques", "perdas"):
        bases[nome]["data"] = pd.to_datetime(bases[nome]["data"])
    return bases
