"""Parâmetros "verdadeiros" do modelo gerador (Parte A do enunciado).

Este módulo é a única fonte dos parâmetros programados. As análises da
Parte B e a simulação da Parte C só o consultam quando a questão pede a
comparação explícita entre o estimado e o verdadeiro.
"""

import numpy as np

# ----------------------------------------------------------------------------
# Horizonte
# ----------------------------------------------------------------------------
N_UNIDADES = 24
N_MESES = 36                      # t = 1 (jan/2023) ... 36 (dez/2025)
ANO_INICIAL = 2023
# O enunciado fixa "28, 30 ou 31" dias: fevereiro tem sempre 28 dias no gerador
# (inclusive em 2024), para seguir a especificação à risca.
DIAS_NO_MES = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

# ----------------------------------------------------------------------------
# Etapa A1 - perfil das unidades
# ----------------------------------------------------------------------------
SERVICOS_MIN, SERVICOS_MAX = 10, 30           # Uniforme discreta
PATCH_TRI = (60.0, 80.0, 95.0)                # Triangular (mín., moda, máx.)
TREINO_MIN, TREINO_MAX = 0.0, 12.0            # Uniforme contínua
P_SOC = 0.40                                  # Bernoulli

# ----------------------------------------------------------------------------
# Etapa A2 - frequência
# ----------------------------------------------------------------------------
BETA_FREQ = {
    "intercepto": 8.0,
    "servicos": 0.50,
    "patch": -0.08,
    "treino": -0.20,
    "soc": -1.40,
    "trimestre": 0.15,
}
SAZONAL = np.array([0.90, 0.85, 1.10, 1.10, 1.00, 0.95,
                    0.90, 0.95, 1.00, 1.05, 1.15, 1.05])   # S_m, média 1
MES_CAMPANHA = 28                 # t = 28 -> abril de 2025
FATOR_CAMPANHA = 1.8

# ----------------------------------------------------------------------------
# Etapa A3 - atributos do ataque
# ----------------------------------------------------------------------------
TIPOS = ["Phishing", "Força bruta", "Malware",
         "Exploração de vulnerabilidade", "DDoS", "Ransomware"]
PROB_TIPO = np.array([0.35, 0.20, 0.15, 0.15, 0.10, 0.05])
CVSS_TRI = np.array([            # (mín., moda, máx.) por tipo
    [2.0, 5.0, 8.0],
    [2.0, 4.0, 7.0],
    [4.0, 6.0, 9.0],
    [5.0, 7.5, 10.0],
    [3.0, 5.0, 8.0],
    [6.0, 8.5, 10.0],
])
MEDIANA_PERDA = np.array([15_000.0, 10_000.0, 30_000.0,
                          45_000.0, 25_000.0, 150_000.0])
P_FORA_EXPEDIENTE = 0.35
THETA_COM_SOC = 4.0               # média da Exponencial (h)
THETA_SEM_SOC = 12.0
FATOR_FORA_EXPEDIENTE = 1.5

# ----------------------------------------------------------------------------
# Etapa A4 - materialização (logística)
# ----------------------------------------------------------------------------
BETA_LOGIT = {
    "intercepto": -2.8,
    "cvss": 0.45,
    "tempo_deteccao_h": 0.06,
    "soc": -0.80,
    "treino": -0.08,
    "fora_expediente": 0.50,
}

# ----------------------------------------------------------------------------
# Etapa A5 - severidade (Lognormal condicional)
# ----------------------------------------------------------------------------
SEV_BETA_TEMPO = 0.02
SEV_SIGMA = 0.9

# ----------------------------------------------------------------------------
# Decisão (Parte C)
# ----------------------------------------------------------------------------
CUSTO_PACOTE = 8_000_000.0
CONTROLES = {"patch": 95.0, "treino": 12.0, "soc": 1}
LIMIAR_PERDA_RELEVANTE = 30_000_000.0


def semente_do_grupo(grupo: int) -> int:
    """semente = 202600 + número do grupo (grupo 7 -> 202607)."""
    return 202600 + int(grupo)
