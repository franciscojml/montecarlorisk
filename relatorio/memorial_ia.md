# Memorial do Uso de IA — Grupo 5

Prova AEDI — Estudo de caso ANDI (risco cibernético por Simulação de Monte Carlo)

> Este memorial foi iniciado pela própria IA durante a sessão, a pedido do grupo ("manter log automático"). Os campos marcados com **[PREENCHER]** são de responsabilidade exclusiva do grupo e não devem ser preenchidos pela IA: responsável, decisão do grupo e reflexão final. O histórico exportado da conversa deve ser anexado (Anexo A).

## Identificação

| Campo | Registro |
|---|---|
| Ferramenta | Claude Code (Anthropic), aplicativo desktop para Windows, aba Code: assistente de programação com acesso à pasta do projeto (lê arquivos, escreve código, executa comandos) |
| Modelo | Claude Fable 5.2 (`claude-fable-5-2`) nas interações 2 a 6; Claude Sonnet 5.5 na interação 1 |
| Forma de acesso | Assistente no computador do aluno, operando sobre o repositório local |
| Data | 10/11/2026 (sessão única) |
| Responsável | **[PREENCHER: integrante que conduziu a sessão]** |
| Extensão do uso | A IA escreveu todo o código (Partes A, B e C), executou-o, e redigiu a primeira versão do relatório técnico e do parecer executivo. O grupo forneceu o enunciado, o livro e as quatro decisões da interação 2 |

## Registro das interações

### Interação 1 — preparação do repositório

| Campo | Registro |
|---|---|
| Questão atendida | Nenhuma (infraestrutura) |
| Exigência feita à IA | Não versionar a pasta de documentos |
| Prompt | "não quero versionar o conteúdo da pasta .docs" |
| Resposta obtida | Criação de `.gitignore` com a pasta de documentos |
| Verificação | `git status` deixou de listar a pasta |
| Decisão do grupo | **[PREENCHER]** |
| Erros da IA | Nenhum identificado |

### Interação 2 — pedido principal (todas as questões)

| Campo | Registro |
|---|---|
| Questão atendida | Q1 a Q15 |
| Exigência feita à IA | Resolver a prova a partir do enunciado e do livro de referência |
| Prompt | "Sou aluno de mestrado e o professor da disciplina de Estatística solicitou a resolução de uma prova. 1. O arquivo "…\docs\trabalho.docx" contém todas as orientações relacionada a execução do trabalho. 2. O arquivo "…\docs\livro.pdf" é o livro de Referência contendo os capítulos." |
| Perguntas da IA e respostas do grupo | A IA leu o enunciado e perguntou quatro coisas antes de começar. Respostas: (1) número do grupo: **5**; (2) escopo: **"Tudo, incl. rascunho relatório"**; (3) memorial: **"Manter log automático"**; (4) linguagem: **"Python + uv"** |
| Resposta obtida | Ver interações 3 a 6, que detalham o que a IA produziu por parte |
| Verificação | Ver interações 3 a 6 |
| Decisão do grupo | **[PREENCHER]** |

### Interação 3 — Parte A: gerador e verificação (Q1, Q2)

| Campo | Registro |
|---|---|
| Questão atendida | Q1-a, Q1-b, Q1-c, Q2-a, Q2-b, Q2-c |
| Exigência feita à IA | Implementar o gerador (Etapas A1 a A5), produzir as cinco bases e verificar o gerador |
| Prompt | O da interação 2 (sem prompts adicionais) |
| Resposta obtida | `andi/parametros.py`, `andi/sorteio.py` (transformações inversas, com Triangular e Exponencial escritas à mão), `andi/gerador.py`, `andi/parte_a.py`, `main.py`. Bases em `dados/` (CSV e planilha Excel). Código no Anexo B |
| Decisões tomadas pela IA sem consultar o grupo | (i) fevereiro com 28 dias também em 2024, por leitura literal do enunciado; (ii) arredondamentos: patch e treino com 2 casas, cvss com 1, tempo com 2, perda em centavos, e uso dos valores arredondados no logit e na severidade; (iii) `id_ataque` atribuído após ordenar por data e unidade; (iv) Poisson e Normal por inversão numérica do SciPy; (v) gerador PCG64, fluxo único, ordem A1→A5 |
| Verificação | Feita pela IA: duas execuções geraram `ataques.csv` idêntico byte a byte; inversa própria igual à `ppf` do SciPy com o mesmo U; simulação independente de 2.000 histórias reproduziu taxas, proporções de tipo, P(fora) = 0,350, σ = 0,900 e θ = 4,00 e 12,00. **Feita pelo grupo: [PREENCHER]** |
| Decisão do grupo | **[PREENCHER: o que foi aceito, modificado ou rejeitado, em especial as decisões (i) a (v)]** |
| Erros da IA | Nenhum erro no gerador identificado. Observação: o KS da amostra NumPy da Triangular deu p = 0,009; a IA conferiu com oito outras sementes (p entre 0,21 e 1,00) e concluiu ser flutuação |

### Interação 4 — Parte B: análises (Q3 a Q13)

| Campo | Registro |
|---|---|
| Questão atendida | Q3 a Q13, todos os itens |
| Exigência feita à IA | Analisar as bases com os métodos dos capítulos 1 a 11 |
| Prompt | O da interação 2 (sem prompts adicionais) |
| Resposta obtida | `andi/parte_b_descritiva.py` (Q3–Q8), `andi/parte_b_modelos.py` (Q9–Q13), `andi/relator.py`; tabelas em `saidas/tabelas/`, figuras em `saidas/figuras/`, resumo em `saidas/resultados.md` |
| Decisões tomadas pela IA sem consultar o grupo | Q3-c: moda por Czuber com classes de Freedman-Diaconis em vez das de Sturges; Q6-a: escolha da unidade U06; Q8-d: VaR único para todas as unidades-mês; Q12-b: decomposição multiplicativa; Q12-d: acréscimo de uma versão robusta (mediana de três anos e σ de Poisson) ao método clássico pedido; Q13-e: custo do falso negativo pela mediana das perdas de 2023–2024 e limiar escolhido no treino |
| Verificação | Feita pela IA: comparação de cada estimativa com o parâmetro do gerador (ICs da Q11 e Q13 contêm os valores verdadeiros); F = t² na Q10; Bayes igual à contagem direta na Q5; contas de cabeça do relatório refeitas (por exemplo, limite de rejeição de Kupiec em 23 exceções). **Feita pelo grupo: [PREENCHER]** |
| Decisão do grupo | **[PREENCHER]** |
| Erros da IA | (1) **Erro de código:** `tabela_coeficientes` gravava ausente numa coluna booleana e o programa parava na Q11; corrigido. (2) **Erro conceitual:** a primeira versão da moda usava Czuber com classes de Sturges e devolvia valores absurdos (moda geral de R$ 157 mil, acima da média); trocado por classes mais finas. (3) **Erro conceitual:** o "efeito esperado" das dummies de trimestre (Q11-d) incluía a tendência; refeito só com o fator sazonal. (4) **Erro conceitual, duas tentativas:** na versão robusta da Q12-d, primeiro o índice "robusto" de abril saiu idêntico ao clássico (a média móvel só deixa dois abris); depois o σ por MAD colapsou (z = 40 e 14 falsos alarmes), porque a mediana de três anos zera um terço dos resíduos; resolvido com σ de Poisson. (5) No texto do relatório, a frase sobre erro relativo dos coeficientes da Q11-c estava imprecisa e foi reescrita |

### Interação 5 — Parte C: SMC de decisão (Q14)

| Campo | Registro |
|---|---|
| Questão atendida | Q14-a a Q14-g |
| Exigência feita à IA | Projetar a perda de 2026 só com os modelos estimados, avaliar o pacote de controles e medir o erro de modelo |
| Prompt | O da interação 2 (sem prompts adicionais) |
| Resposta obtida | `andi/parte_c.py`: perda agregada por célula (tipo × grupo de SOC), 100.000 réplicas, números aleatórios comuns, sensibilidade 3 × 3 e 10.000 anos do gerador verdadeiro |
| Decisões tomadas pela IA sem consultar o grupo | (i) frequência pelo modelo 11-d com campanha = 0, e não pelo modelo base 11-a; (ii) probabilidade de materialização por tipo e por unidade, com o tempo de detecção sorteado dos ataques de unidades com o mesmo status de SOC; (iii) efeito do SOC na severidade por um deslocamento δ comum a todos os tipos; (iv) logística da Q13 mantida como treinada em 2023–2024, sem reajuste com 2025; (v) sensibilidade com 50.000 réplicas por caso |
| Verificação | Feita pela IA: média simulada (R$ 31,433 mi) igual à analítica (R$ 31,436 mi); erro padrão caindo com 1/√n; ataques por ano do gerador verdadeiro (1.140,0) iguais à soma das taxas (1.139,4); δ = −0,248 coerente com β₁ × diferença de tempo (−0,271). **Feita pelo grupo: [PREENCHER]** |
| Decisão do grupo | **[PREENCHER: em especial a escolha (i), que muda a previsão de 1.222 para 1.095 ataques]** |
| Erros da IA | Rótulo do gráfico de tornado saía cortado; corrigido. Nenhum erro numérico identificado |

### Interação 6 — redação (relatório, Q15 e este memorial)

| Campo | Registro |
|---|---|
| Questão atendida | Relatório técnico (Q1–Q14), parecer executivo (Q15), memorial |
| Exigência feita à IA | Rascunho do relatório e do parecer, a pedido do grupo ("Tudo, incl. rascunho relatório") |
| Prompt | O da interação 2 (sem prompts adicionais) |
| Resposta obtida | `relatorio/relatorio.md`, `relatorio/parecer_executivo.md`, `relatorio/memorial_ia.md`, `README.md` |
| Verificação | Feita pela IA: números do texto conferidos contra `saidas/resultados.md`. **Feita pelo grupo: [PREENCHER — as interpretações são pontuadas e de responsabilidade do grupo]** |
| Decisão do grupo | **[PREENCHER]** |
| Erros da IA | No parecer, a primeira redação dizia crescimento de "4% ao ano" (correto: cerca de 5%) e que o benefício teria de ser "menos de um terço" (correto: 36%, ou queda de quase dois terços); corrigidos pela própria IA na revisão |

### Interação 7 — conversão para Word e limites de páginas

| Campo | Registro |
|---|---|
| Questão atendida | Entregáveis (relatório técnico, parecer da Q15, memorial) |
| Exigência feita à IA | Converter relatório e parecer para Word e conferir os limites de 30 páginas e 1 página |
| Prompt | "Sim, converter" (resposta à pergunta da IA: "Converter relatório e parecer para Word e conferir os limites de 30 e 1 página?") |
| Resposta obtida | `ferramentas/md_para_docx.py` (conversor Markdown → Word com python-docx) e os arquivos em `relatorio/word/` (.docx e .pdf). Páginas contadas no PDF gerado pelo LibreOffice: relatório 21, parecer 1, memorial 4 |
| Verificação | Feita pela IA: contagem de páginas no PDF e inspeção visual da primeira página do relatório. **Feita pelo grupo: [PREENCHER — abrir os .docx no Word, onde a paginação pode diferir da do LibreOffice]** |
| Decisão do grupo | **[PREENCHER]** |
| Erros da IA | A primeira versão do parecer ocupava 2 páginas; a IA cortou cerca de 60 palavras (sem alterar números nem a recomendação) para caber em 1 |

## Pontos que o grupo precisa conferir antes de entregar

A IA aponta os itens em que tomou decisões de julgamento ou em que o resultado contraria a expectativa do enunciado:

1. **Q8-d:** o teste de Kupiec **não rejeitou** o VaR (17 exceções em 288; p = 0,49), embora o enunciado sugira a possibilidade de rejeição. O relatório explica o porquê; o grupo deve confirmar que concorda.
2. **Q11-e:** o funil nos resíduos é moderado (Breusch-Pagan geral p = 0,11; dirigido aos ajustados p = 0,016). O enunciado diz "vocês devem observar um padrão de funil".
3. **Q11:** o coeficiente de patch não é significativo (p = 0,27) nesta amostra.
4. **Q12-d:** a regra dos 3σ clássica **não encontra** abril de 2025 (z = 2,39). A versão robusta foi iniciativa da IA.
5. **Q13-e:** com os custos dados, "investigar tudo" custa menos que o melhor limiar.
6. **Q14-g:** a SMC subestima a perda verdadeira em 7,9%.
7. **Limites de páginas:** relatório com 21 páginas e parecer com 1, medidos no LibreOffice. Reconferir no Word depois de qualquer edição do grupo.
8. O livro foi lido por extração de texto do PDF: fórmulas e figuras podem ter sido lidas com falhas. Conferir as citações de seção contra o livro.

## Reflexão final do grupo (até uma página)

**[PREENCHER: em que a IA ajudou; em que atrapalhou ou errou; qual parte do trabalho o grupo considera exclusivamente sua.]**

## Anexos

- **Anexo A:** histórico exportado da conversa com o Claude Code. **[ANEXAR]**
- **Anexo B:** código gerado pela IA — pasta `andi/` e `main.py`, integralmente.
