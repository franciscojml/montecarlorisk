"""Coletor de resultados: grava tabelas (CSV), figuras (PNG) e um resumo em
Markdown (`saidas/resultados.md`) com tudo o que o relatório técnico cita."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
    "axes.spines.right": False, "figure.autolayout": True,
})


class Relator:
    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.tabelas = pasta / "tabelas"
        self.figuras = pasta / "figuras"
        self.tabelas.mkdir(parents=True, exist_ok=True)
        self.figuras.mkdir(parents=True, exist_ok=True)
        self.linhas: list[str] = []
        self.valores: dict = {}

    # -- texto ---------------------------------------------------------------
    def secao(self, titulo: str) -> None:
        print(f"[{titulo}]")
        self.linhas += ["", f"## {titulo}", ""]

    def item(self, titulo: str) -> None:
        self.linhas += ["", f"### {titulo}", ""]

    def texto(self, txt: str) -> None:
        self.linhas += [txt, ""]

    # -- números ---------------------------------------------------------------
    def valor(self, chave: str, v, fmt: str = "{:,.4f}") -> None:
        """Registra um escalar (vai para o Markdown e para resultados.json)."""
        if isinstance(v, (np.floating, np.integer, np.bool_)):
            v = v.item()
        self.valores[chave] = v
        txt = fmt.format(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
        self.linhas.append(f"- `{chave}` = {txt}")

    # -- tabelas e figuras -------------------------------------------------------
    def tabela(self, df: pd.DataFrame, nome: str, titulo: str = "",
               casas: int = 4, indice: bool = True) -> None:
        df.to_csv(self.tabelas / f"{nome}.csv", index=indice, encoding="utf-8-sig")
        self.linhas += ["", f"**Tabela `{nome}`** {titulo}", "",
                        df.to_markdown(index=indice, floatfmt=f",.{casas}f"), ""]

    def figura(self, fig, nome: str, legenda: str = "") -> None:
        fig.savefig(self.figuras / f"{nome}.png")
        plt.close(fig)
        self.linhas += ["", f"![{legenda}](figuras/{nome}.png)", f"*Figura `{nome}`* {legenda}", ""]

    def salvar(self) -> None:
        (self.pasta / "resultados.md").write_text("\n".join(self.linhas), encoding="utf-8")
        (self.pasta / "resultados.json").write_text(
            json.dumps(self.valores, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
