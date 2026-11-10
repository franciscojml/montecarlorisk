# Prova AEDI — Risco cibernético por Simulação de Monte Carlo (ANDI)

Grupo 5 — semente 202605 (= 202600 + número do grupo).

## Executar

Requer [uv](https://docs.astral.sh/uv/). Um único comando gera as bases e todas as análises:

```bash
uv run python main.py --grupo 5
```

Leva cerca de 45 segundos. A mesma semente recria exatamente as mesmas bases.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `main.py` | Ponto de entrada: Parte A → Parte B → Parte C |
| `andi/parametros.py` | Parâmetros verdadeiros do gerador |
| `andi/sorteio.py` | Transformações inversas F⁻¹(U) |
| `andi/gerador.py` | Parte A: Etapas A1 a A5 e bases derivadas |
| `andi/parte_a.py` | Questões 1-b e 2 |
| `andi/parte_b_descritiva.py` | Questões 3 a 8 |
| `andi/parte_b_modelos.py` | Questões 9 a 13 |
| `andi/parte_c.py` | Questão 14 |
| `dados/` | `unidades.csv`, `ataques.csv`, `perdas.csv`, `painel_trimestral.csv`, `serie_mensal.csv` e `bases_andi.xlsx` |
| `saidas/resultados.md` | Todos os números, por questão (gerado) |
| `saidas/tabelas/`, `saidas/figuras/` | Tabelas em CSV e figuras em PNG (geradas) |
| `relatorio/relatorio.md` | Relatório técnico (Questões 1 a 14) |
| `relatorio/parecer_executivo.md` | Parecer de uma página (Questão 15) |
| `relatorio/memorial_ia.md` | Memorial do Uso de IA |
| `relatorio/word/` | Versões Word e PDF dos três documentos (`uv run --with python-docx python ferramentas/md_para_docx.py`) |
