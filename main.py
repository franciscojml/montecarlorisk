"""Prova AEDI - Estudo de caso ANDI: risco cibernético por Simulação de Monte Carlo.

Execução do início ao fim, com um único comando:

    uv run python main.py --grupo 5

A semente é 202600 + número do grupo. O comando recria exatamente as cinco
bases em `dados/` e todas as tabelas e figuras em `saidas/`.
"""

import argparse
import time
from pathlib import Path

from andi import gerador, parte_a, parte_b, parte_c
from andi.parametros import semente_do_grupo
from andi.relator import Relator

RAIZ = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grupo", type=int, default=5, help="número do grupo (semente = 202600 + grupo)")
    ap.add_argument("--replicas", type=int, default=100_000, help="réplicas anuais da SMC da Parte C")
    args = ap.parse_args()

    semente = semente_do_grupo(args.grupo)
    inicio = time.time()
    print(f"Grupo {args.grupo} | semente {semente}")

    # ---- Parte A: gerar e gravar as bases --------------------------------------
    gerador.salvar_bases(gerador.gerar_bases(semente), RAIZ / "dados")
    bases = gerador.carregar_bases(RAIZ / "dados")      # daqui em diante: só os arquivos

    r = Relator(RAIZ / "saidas")
    r.linhas += [f"# Resultados - grupo {args.grupo} (semente {semente})", "",
                 "Arquivo gerado automaticamente por `main.py`. Não editar à mão."]
    parte_a.questao_1(r, semente, bases)
    parte_a.questao_2(r, bases)

    # ---- Parte B: capítulos 1 a 11 ----------------------------------------------
    modelos = parte_b.executar(r, bases, semente)

    # ---- Parte C: SMC de risco e decisão ------------------------------------------
    parte_c.executar(r, bases, modelos, semente, args.replicas)

    r.salvar()
    print(f"Concluído em {time.time() - inicio:.1f} s. Saídas em {RAIZ / 'saidas'}")


if __name__ == "__main__":
    main()
