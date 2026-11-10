"""Parte B - orquestra as Questões 3 a 13 e devolve os modelos estimados."""

import numpy as np

from . import parte_b_descritiva as D
from . import parte_b_modelos as M
from .relator import Relator


def executar(r: Relator, bases: dict, semente: int) -> dict:
    unidades = bases["unidades"]
    at = bases["ataques"].merge(unidades[["unidade", "soc", "treino"]], on="unidade")
    pe = bases["perdas"].merge(unidades[["unidade", "soc"]], on="unidade")
    pe["ln_perda"] = np.log(pe["perda_rs"])
    painel, serie = bases["painel_trimestral"], bases["serie_mensal"]

    D.questao_3(r, at, pe)
    D.questao_4(r, pe, painel, serie, semente)
    D.questao_5(r, at)
    D.questao_6(r, at, pe, unidades)
    D.questao_7(r, at, pe, semente)
    D.questao_8(r, at, pe, unidades)

    ols_tempo = M.questao_9(r, pe)
    ols_tempo_tipo = M.questao_10(r, pe, ols_tempo)
    freq_base, freq_sazonal = M.questao_11(r, painel, semente)
    M.questao_12(r, serie, unidades)
    logit = M.questao_13(r, at, pe)

    return {"ols_tempo": ols_tempo, "ols_tempo_tipo": ols_tempo_tipo,
            "freq_base": freq_base, "freq_sazonal": freq_sazonal, "logit": logit,
            "ataques": at, "perdas": pe}
