"""Converte os Markdown de `relatorio/` em Word (.docx).

Uso:  uv run --with python-docx python ferramentas/md_para_docx.py

Cobre o subconjunto de Markdown usado nos relatórios: títulos, parágrafos,
negrito/itálico/código, citações, listas, tabelas e imagens.
"""

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parent.parent
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|(?<![\*\w])\*[^\*\s][^\*]*?\*(?!\*))")


def _runs(par, texto: str, tamanho=None, negrito=False):
    for parte in INLINE.split(texto):
        if not parte:
            continue
        if parte.startswith("**"):
            run = par.add_run(parte[2:-2])
            run.bold = True
        elif parte.startswith("`"):
            run = par.add_run(parte[1:-1])
            run.font.name = "Consolas"
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            run = par.add_run(parte[1:-1])
            run.italic = True
        else:
            run = par.add_run(parte.replace("\\|", "|"))
        if negrito:
            run.bold = True
        if tamanho:
            run.font.size = Pt(tamanho)


def _sombrear(celula, cor: str):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), cor)
    celula._tc.get_or_add_tcPr().append(sh)


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", linha.strip().strip("|"))]


def _tabela(doc, linhas: list[str], fonte: float):
    cab = _celulas(linhas[0])
    alinh = [WD_ALIGN_PARAGRAPH.RIGHT if c.endswith(":") and not c.startswith(":")
             else WD_ALIGN_PARAGRAPH.LEFT for c in _celulas(linhas[1])]
    corpo = [_celulas(l) for l in linhas[2:]]
    tab = doc.add_table(rows=1, cols=len(cab))
    tab.style = "Table Grid"
    tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, txt in enumerate(cab):
        cel = tab.rows[0].cells[j]
        _sombrear(cel, "D9E2F3")
        par = cel.paragraphs[0]
        par.alignment = alinh[j] if j < len(alinh) else WD_ALIGN_PARAGRAPH.LEFT
        _runs(par, txt, fonte, negrito=True)
    for lin in corpo:
        cels = tab.add_row().cells
        for j, txt in enumerate(lin[:len(cab)]):
            par = cels[j].paragraphs[0]
            par.alignment = alinh[j] if j < len(alinh) else WD_ALIGN_PARAGRAPH.LEFT
            _runs(par, txt, fonte)
    for linha in tab.rows:
        for cel in linha.cells:
            fmt = cel.paragraphs[0].paragraph_format
            fmt.space_before = fmt.space_after = Pt(0)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def converter(origem: Path, destino: Path, corpo=10.5, fonte_tabela=8.5,
              margem=2.0, largura_img=14.0, altura_max_img=7.0):
    doc = Document()
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(margem)
        sec.top_margin = sec.bottom_margin = Cm(margem)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(corpo)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.0
    for nivel, tam in ((1, 15), (2, 13), (3, 11.5)):
        est = doc.styles[f"Heading {nivel}"]
        est.font.name, est.font.size, est.font.bold = "Calibri", Pt(tam), True
        est.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        est.paragraph_format.space_before, est.paragraph_format.space_after = Pt(8), Pt(3)
        est.paragraph_format.keep_with_next = True

    linhas = origem.read_text(encoding="utf-8").splitlines()
    i, buffer = 0, []

    def descarregar():
        if buffer:
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _runs(par, " ".join(buffer))
            buffer.clear()

    while i < len(linhas):
        linha = linhas[i]
        s = linha.strip()
        if not s or s == "---":
            descarregar()
        elif s.startswith("#"):
            descarregar()
            nivel = len(s) - len(s.lstrip("#"))
            doc.add_heading(level=min(nivel, 3)).add_run(
                re.sub(r"\*\*|`", "", s.lstrip("#").strip()))
        elif s.startswith("|") and i + 1 < len(linhas) and re.match(r"^\s*\|[\s:\-|]+\|\s*$", linhas[i + 1]):
            descarregar()
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            _tabela(doc, bloco, fonte_tabela)
            continue
        elif m := re.match(r"!\[(.*?)\]\((.+?)\)", s):
            descarregar()
            caminho = (origem.parent / m.group(2)).resolve()
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            fig = par.add_run().add_picture(str(caminho), width=Cm(largura_img))
            if fig.height > Cm(altura_max_img):
                escala = Cm(altura_max_img) / fig.height
                fig.height, fig.width = Cm(altura_max_img), int(fig.width * escala)
            leg = doc.add_paragraph()
            leg.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = leg.add_run(m.group(1))
            run.italic, run.font.size = True, Pt(8.5)
        elif s.startswith(">"):
            descarregar()
            par = doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.6)
            _runs(par, s.lstrip("> ").strip(), corpo - 1)
            for run in par.runs:
                run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        elif m := re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", linha):
            descarregar()
            estilo = "List Number" if m.group(2)[0].isdigit() else "List Bullet"
            par = doc.add_paragraph(style=estilo)
            par.paragraph_format.space_after = Pt(1)
            _runs(par, m.group(3))
        else:
            buffer.append(s)
        i += 1
    descarregar()
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destino)
    print(f"{origem.name} -> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    pasta = RAIZ / "relatorio"
    converter(pasta / "relatorio.md", pasta / "word" / "relatorio_tecnico.docx")
    converter(pasta / "parecer_executivo.md", pasta / "word" / "parecer_executivo.docx",
              corpo=10, fonte_tabela=9, margem=1.8)
    converter(pasta / "memorial_ia.md", pasta / "word" / "memorial_ia.docx")
    sys.exit(0)
