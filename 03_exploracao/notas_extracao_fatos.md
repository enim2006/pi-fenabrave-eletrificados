---
title: Notas sobre a extração dos fatos (marca, modelo, categoria, motorização, eletrificados)
data: 2026-08-18
---

# O que foi extraído

A partir do modelo de dados aceito (`analise_estrutura_dados_fenabrave.md`), a extração dos 7 PDFs (Jan–Jul/2026) foi automatizada para os fatos que faltavam. Script: `extract_fenabrave.py` (mesma pasta). Resultado em `02_dados_extraidos/`:

| Arquivo | Linhas (7 meses) | Conteúdo |
|---|---|---|
| `fato_marca.csv` | 596 | Ranking de fabricantes por segmento (Autos, Com. Leves, Caminhões, Ônibus, Motos), quantidade do mês |
| `fato_modelo.csv` | 2.025 | Ranking de modelos (Autos, Com. Leves), com `tipo_venda` = Total / Direta / Varejo |
| `fato_modelo_categoria.csv` | 1.993 | Ranking de modelos por subcategoria (ex.: Hatch Pequeno, Pick-up Grande, Semi-Pesado, Custom) — Autos, Com. Leves, Caminhões, Motos |
| `fato_motorizacao.csv` | 42 | Autos e Com. Leves por faixa de motorização (Até 1.0 / 1.0–2.0 / Acima de 2.0) |
| `fato_eletrificados.csv` | 440 | Ranking de fabricantes de híbridos/elétricos — Autos, Com. Leves, Caminhões, Ônibus, Motos |

Todas na granularidade **mensal** (sem acumulado — conforme definido, acumulado/variação fica a cargo da camada de visualização).

# Descobertas durante a extração (importantes para quando o modelo for para o dashboard)

1. **Rankings são "Top N", não a lista completa de marcas/modelos.** Conferência: soma de `fato_marca` (Autos, Jan) = 122.551 contra o total oficial da pág. 1 = 125.136 — faltam ~2.585 unidades de marcas fora do top 21 mostrado. O mesmo vale para modelos e categorias (ex.: "Hatch Pequenos" soma 28.287 contra o Total de 28.414 informado pela Fenabrave — a diferença é resíduo de modelos não listados individualmente). **Não é erro de extração**: é como a Fenabrave publica o boletim. Se o dashboard precisar do total exato por segmento, usar `fato_resumo_segmento` (que vem da pág. 1, sempre completo) — não somar `fato_marca`/`fato_modelo`.
2. **Duas páginas (1 e 10) perderam os rótulos de segmento a partir de Fevereiro.** Nas edições de Fev a Jul, as linhas "A) Autos", "B) Com. Leves" somem dessas duas páginas (só ficam os números). A extração dessas páginas passou a depender da **posição** dos valores (1º grupo = Autos, 2º = Com. Leves, 3º = agregado A+B, ignorado) em vez do rótulo textual. Vale reconferir se isso se repetir ou mudar em edições futuras (ex. 2027).
3. Páginas de gráfico de pizza (3, 4, 24–29, 35, 36, 44) continuam fora do escopo — texto invertido, dado redundante com as tabelas já extraídas.
4. Região (pág. 5, 37, 45, 52) ainda não foi extraída — precisa de leitura por coordenada (x/y) no PDF, não por texto puro, porque é gráfico de barras empilhadas sem tabela. Fica como possível próximo passo, caso essa dimensão seja incorporada ao dashboard.

# Como rodar para os próximos meses

1. Coloque os novos PDFs em `01_dados_brutos/`, mantendo o padrão de nome `AAAA_MM_02.pdf`.
2. Rode `python3 extract_fenabrave.py <pasta 01_dados_brutos> <pasta de saída>` — processa todos os PDFs da pasta de uma vez (não precisa rodar mês a mês) e regrava os CSVs com todos os meses presentes.
3. Cole os CSVs atualizados em `02_dados_extraidos/`.

Ao receber um novo lote de PDFs, o procedimento padrão é rodar o script e conferir os totais batendo com a pág. 1 antes de considerar a extração validada, como feito aqui.

> Nota: este arquivo documenta uma etapa inicial da extração (7 meses, ago/2026). A versão mais completa e atualizada, cobrindo os 56 meses (2022–2026) e todas as correções aplicadas, está em `scripts/notas_extracao_fatos.md`.
