# Notas técnicas de extração — Fenabrave (2022–2026)

Atualizado após processar os 55 PDFs mensais (jan/2022 a jul/2026). Documenta como o script `extract_fenabrave.py` funciona e os casos especiais tratados.

## 1. Fonte e cobertura

- 55 relatórios mensais "Emplacamento de Autoveículos" da Fenabrave.
- 12×2022, 12×2023, 12×2024, 12×2025, 7×2026 (jan–jul).
- Layout **não é estável** ao longo do tempo:
  - 2022–2023: relatório com ~46 páginas, **sem** seção "Mercado de Eletrificados".
  - 2024 em diante: relatório com ~52 páginas, **com** a seção de eletrificados.
  - A partir de fev/2026: as páginas de "Resumo Mensal" e "Participação por Motorização" deixam de rotular os blocos "A) Autos" / "B) Com. Leves" — a extração precisou passar a depender da ORDEM dos blocos, não do texto do rótulo.

## 2. Estratégia de classificação: por título, não por índice de página

Como o número/ordem das páginas varia entre edições, o script não assume "página X = tabela Y". Em vez disso, cada página é lida e comparada a uma lista de títulos conhecidos (`TITULOS_RECONHECIDOS`) nas primeiras linhas do texto extraído; o parser correspondente só roda se o título bater. Isso tornou a pipeline resiliente às mudanças de 2023→2024 e 2026.

## 3. Fallback de OCR

Extração de texto via `pdfplumber` falha (texto vazio ou cheio de `(cid:NN)`, indicando fonte com mapa ToUnicode quebrado) em alguns arquivos. Quando isso acontece, a página é renderizada como imagem (`pdf2image`, 200 dpi) e passada pelo Tesseract em português (`pytesseract`, `lang='por'`), com cache em disco por página para não repetir OCR em reprocessamentos.

**Arquivos que precisaram de OCR (parcial ou total):**
- `2023_09_2.pdf` — PDF inteiramente rasterizado (~7 MB, texto extraído vazio em todas as páginas).
- `2024_01_02.pdf`, `2024_04_02.pdf`, `2024_05_02.pdf` — fonte incorporada corrompida (100% do texto virou `(cid:NN)`).
- `2025_03` a `2025_06` e `2026_01`: OCR pontual em 2–3 páginas por mês (aviso "Could not get FontBBox..." no log — não impede a extração normal do restante do arquivo, apenas sinaliza fonte problemática em páginas específicas).

**Ajustes de parsing exigidos pelo texto OCR** (mais ruidoso que a extração nativa):
- Regex de nomes de marca/modelo ampliada para aceitar minúsculas (OCR às vezes normaliza para minúsculo).
- Detecção de colunas de cabeçalho ajustada para não quebrar no primeiro espaço em branco (comum em OCR).
- Marcador de tendência entre colunas (originalmente um "=" literal) trocado por qualquer token curto não-numérico, pois o OCR renderiza esse caractere como ruído variável.
- Nomes de categoria de modelo: linhas de cabeçalho corrompidas pelo OCR (ex.: "Roddlo Dez Jan Acumulado eus") passaram a ser explicitamente ignoradas como candidatas a nome de categoria.
- `parse_resumo_segmento`: restringido a buscar rótulos apenas no trecho ANTES do marcador "Participação no acumulado", porque o OCR às vezes corrompe a primeira ocorrência de um rótulo (ex. "Subtotal"→"Sire") e o parser caía para a segunda ocorrência (na seção de percentuais), retornando valores errados silenciosamente.

## 4. Outras correções relevantes (não relacionadas a OCR)

- **Duplicidade em `fato_marca`/`fato_modelo`**: algumas páginas repetem blocos agregados ("Automóveis + Comerciais Leves") ou uma segunda seção "Acumulado" com os mesmos dados — o parser agora trunca a leitura assim que detecta um segundo bloco/cabeçalho após já ter capturado linhas de dados.
- **`parse_motorizacao` com apenas 1 mês de dados**: a partir de fev/2026 os rótulos de segmento somem dessa página — resolvido usando a ORDEM de aparição dos trios "Até 1.0 / De 1.0 até 2.0 / Acima de 2.0" (1º = Autos, 2º = Com. Leves, 3º = agregado A+B, descartado).
- **Arquivo mal nomeado**: `2023_02_3.pdf` era na verdade a edição de março/2023 (erro no download); o arquivo foi renomeado para `2023_03_2.pdf`.

## 5. Tabelas fato geradas

| Arquivo | Conteúdo | Granularidade |
|---|---|---|
| `fato_resumo_segmento.csv` | Emplacamentos por segmento (Autos, Com. Leves, Caminhões, Ônibus, Subtotal, Motos, etc.) | mês × segmento |
| `fato_marca.csv` | Ranking de marcas (Top-N do relatório) | mês × marca |
| `fato_modelo.csv` | Ranking de modelos (Top-N) | mês × modelo |
| `fato_modelo_categoria.csv` | Ranking de modelos por categoria/segmento de mercado | mês × categoria × modelo |
| `fato_motorizacao.csv` | Participação por faixa de motorização (até 1.0 / 1.0–2.0 / acima de 2.0) | mês × segmento × faixa |
| `fato_eletrificados.csv` | Ranking de marcas eletrificadas (Top-N, só existe 2024+) | mês × marca |
| `fato_eletrificados_resumo.csv` | Totais oficiais de eletrificados por segmento e tipo (Híbridos/Elétricos/Total), não limitado a Top-N — só existe 2024+ | mês × segmento × tipo |

Nenhuma coluna de "acumulado" ou percentual é armazenada — ambos são deriváveis (soma/razão) a partir dos valores mensais, e ficam a cargo da camada de visualização.

## 6. Limitações conhecidas remanescentes

- Rankings de marca/modelo são Top-N conforme o próprio relatório da Fenabrave (não é a lista completa do mercado).
- Nos 4 arquivos com OCR mais pesado, pequenas imprecisões residuais são possíveis (dígito de ranking trocado, categoria mal atribuída pontualmente); nenhum erro sistemático foi identificado nas validações feitas, mas vale reprocessar/conferir manualmente esses 4 meses se algum número parecer fora da curva em análises futuras.

## 7. Correção (18/08/2026): texto em negrito "duplicado" quebrando `categoria`

Detectado ao revisar o campo `categoria` de `fato_modelo_categoria.csv`: em algumas edições (o caso mais visível é jan/2022, mas o mecanismo pode ocorrer em qualquer edição), o PDF renderiza certos textos em negrito duplicando cada caractere na camada de texto — ex.: o cabeçalho "Dez Jan Acumulado" saía como "DDeezz JJaann AAccuummuullaaddoo", e "Total 15.060" como "TToottaall 1155..006600". Como as checagens de cabeçalho procuravam pelas substrings literais ("Dez", "Jan", "Acumulado", "Total "), esse texto duplicado não era reconhecido como cabeçalho e "vazava" para dentro do parser como se fosse um nome de categoria — chegando a apagar a categoria correta do mês inteiro em jan/2022 (todas as 286 linhas caíram sob o mesmo valor quebrado).

Um segundo sintoma do mesmo tipo de corrupção: em algumas linhas de dado, um dígito isolado saía duplicado (ex.: quantidade real "1" extraída como "11", "7" como "77"), inflando artificialmente valores pequenos (cauda longa de marcas/modelos).

Também foi identificado, nos arquivos que passaram por OCR (`2023_09`, `2024_01`, `2024_04`, `2024_05`), um problema relacionado mas de causa diferente: o marcador de posição "1º" do primeiro modelo de cada categoria às vezes é lido incorretamente pelo Tesseract (ex.: "1º" virando "jo", "pe", "e"...). Isso fazia a primeira linha de cada bloco de categoria ser tratada como se fosse um novo nome de categoria (ao invés de uma linha de dado), perdendo esse registro e corrompendo o rótulo de categoria dos modelos seguintes no mesmo bloco.

**Correções aplicadas:**
- `undouble_line()`: normaliza qualquer token cujos caracteres apareçam todos duplicados em sequência (teste estrito — nenhuma palavra/número real do relatório passa por esse teste), aplicado a todas as linhas de todas as páginas (não só na tabela de categoria).
- Detecção de cabeçalho generalizada: qualquer linha com 2+ ocorrências de um token de ano (20XX) é tratada como ruído de cabeçalho, não como possível nome de categoria (cobre variações como "Modelo 2023 2023 2023 Part." que não continham "Acumulado" na mesma linha).
- Linhas de dado agora são reconhecidas mesmo com o marcador de posição corrompido: qualquer linha contendo "/" (todo modelo é MARCA/MODELO) terminando em percentual é aceita como linha de dado.
- O número de rank (1º, 2º, 3º...) deixou de ser lido do texto (que pode vir corrompido) e passou a ser recalculado pela ordem de aparição dentro do bloco de categoria — mais robusto.

**Resultado da correção**: `fato_modelo_categoria.csv` caiu de 75 para 30 valores distintos de `categoria` (todos legítimos agora); ganhou ~59 linhas recuperadas (dados que antes eram perdidos por cair no nome de categoria errado). As demais tabelas fato tiveram ~1 linha cada corrigida (dígito duplicado); nenhum outro campo foi afetado.
