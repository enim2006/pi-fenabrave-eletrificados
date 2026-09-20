---
title: Análise e identificação da estrutura dos dados — Fenabrave "Informativo - Emplacamentos"
data_analise: 2026-08-18
arquivos_analisados: 2026_01_02.pdf a 2026_07_02.pdf (7 edições, Jan a Jul/2026)
---

# 1. O que é o documento

Os 7 PDFs em `01_dados_brutos/` são edições mensais do boletim **"Informativo - Emplacamentos"**, publicado pela **Fenabrave** (Federação Nacional da Distribuição de Veículos Automotores). Cada edição:

- Tem exatamente **52 páginas**, com a **mesma estrutura de seções, na mesma ordem, em todas as edições analisadas** (Jan a Jul/2026).
- É publicada por volta do dia 02 do mês seguinte ao mês de referência (ex.: dados de Janeiro/2026 → arquivo criado em 02/02/2026).
- O nome de arquivo já usado por você (`AAAA_MM_02.pdf`, onde `MM` é o mês de referência dos dados) é consistente e recomendo mantê-lo para os próximos meses/anos — isso já facilita a automação.
- Título interno: "Informativo - Emplacamentos", com numeração de edição (ex.: Ed. 277 = Jan/2026, Ed. 278 = Fev/2026 → uma edição por mês).

**Boa notícia:** sua hipótese está correta. Apesar de o PDF ser longo e "consolidado" visualmente (tabelas, gráficos, textos repetidos em várias visões), os **dados atômicos por trás de tudo isso cabem em um número pequeno de tabelas** — a maior parte das 52 páginas são apenas **recortes, acumulados ou representações gráficas diferentes dos mesmos números**. Detalho isso abaixo.

# 2. Mapa de conteúdo (52 páginas, estável entre os 7 meses)

| Págs | Conteúdo |
|---|---|
| 1 | Resumo mensal por segmento (Autos, Com. Leves, Caminhões, Ônibus, Motos, Impl. Rodoviários, Outros) — mês, mês anterior, acumulado ano, mesmo mês ano anterior, acumulado ano anterior, variações % |
| 2 | Igual à pág. 1, mas só Autos + Com. Leves (subconjunto redundante) |
| 3–4 | Gráficos de pizza de participação de mercado por marca (mês e acumulado) — **texto extraído fica invertido/ilegível**, dado redundante com pág. 8–9 |
| 5 | Distribuição regional (Norte/Nordeste/Centro-Oeste/Sudeste/Sul) — Autos, Com. Leves, A+B, em % |
| 6–7 | Ranking de **modelos** mais emplacados (mês e acumulado) — Autos e Com. Leves lado a lado |
| 8–9 | Ranking de **marcas/fabricantes** (mês e acumulado) — Autos, Com. Leves, A+B |
| 10 | Participação por motorização (até 1.0 / 1.0–2.0 / acima de 2.0) — Autos, Com. Leves, A+B |
| 11–17 | Ranking de modelos por **subcategoria de Autos** (Entrada, Hatch Pequeno, Hatch Médio, Sedan Pequeno, Sedan Médio, SW Médio, Grandcab, SUV) + tabela-resumo de participação por subsegmento |
| 18–19 | Ranking de modelos por **subcategoria de Com. Leves** (Pick-up Pequena, Furgão Pequeno) |
| 20–22 | Eletrificados (Híbrido/Elétrico) por marca — Autos, Com. Leves, A+B (mês e acumulado) |
| 23 | Texto explicativo (não é dado) sobre o que é Venda Direta x Venda Varejo |
| 24–25 | Gráficos de pizza % Venda Direta x Varejo (mês e acumulado) |
| 26–29 | Ranking de marcas por tipo de venda (Varejo / Direta), mês e acumulado |
| 30–33 | Ranking de modelos por tipo de venda (Varejo / Direta), mês e acumulado |
| 34 | Resumo mensal Caminhões + Ônibus (redundante com pág. 1) |
| 35–36 | Gráficos de pizza de participação — Caminhões/Ônibus (mesmo problema de texto invertido) |
| 37 | Distribuição regional — Caminhões, Ônibus |
| 38 | Ranking de marcas — Caminhões, Ônibus (mês = acumulado, mesma tabela repetida) |
| 39–40 | Ranking de modelos — Caminhões, Ônibus |
| 41–42 | Eletrificados — Caminhões, Ônibus |
| 43 | Resumo mensal Motos (redundante com pág. 1) |
| 44 | Gráfico de pizza participação — Motos |
| 45 | Distribuição regional — Motos |
| 46 | Ranking de marcas — Motos |
| 47–49 | Ranking de modelos — Motos (por categoria) |
| 50 | Eletrificados — Motos |
| 51 | Resumo mensal Implementos Rodoviários (redundante com pág. 1) |
| 52 | Distribuição regional — Implementos Rodoviários |

# 3. Estabilidade entre os meses (validado nos 7 arquivos)

- A **ordem e o conteúdo das 52 seções é idêntico** em todas as 7 edições (Jan a Jul/2026) — o mesmo "mapa" acima vale para qualquer mês.
- **Atenção a uma variação de layout**: na edição de Janeiro (Ed. 277), a página 1 tinha uma linha extra `Total` (soma geral) que **não aparece** nas edições de Fevereiro a Julho (Ed. 278 em diante). Não é perda de informação — o total é sempre a soma dos segmentos e dá para recalcular — mas é um lembrete de que pequenas variações de layout podem acontecer entre edições e a extração precisa ser tolerante a isso (não assumir posição fixa de linha, e sim casar pelo rótulo do segmento).

# 4. Por que dá para reduzir a poucas tabelas

A maior parte das 52 páginas se explica por **3 fatores de "inchaço"**, todos redundantes ou deriváveis:

1. **Repetição por segmento**: o mesmo tipo de tabela (resumo, ranking de marca, ranking de modelo, regional, eletrificados) se repete para cada segmento de veículo (Autos, Com. Leves, Caminhões, Ônibus, Motos, Impl. Rodoviários). Isso não são tabelas diferentes — é a **mesma tabela com uma coluna `segmento` a mais**.
2. **Mês x Acumulado**: quase toda tabela aparece duas vezes — "do mês" e "acumulado no ano". O acumulado é só a soma dos meses anteriores do mesmo ano. **Não precisa ser armazenado**: com os dados mensais (granularidade atômica), o Power BI calcula acumulado, variação % e participação % via medidas DAX (SUM, running total, etc.), sem duplicar dado nem risco de inconsistência.
3. **Tabela x Gráfico**: os gráficos de pizza (páginas 3, 4, 24, 25, 26, 35, 36, 44) mostram os mesmos números que já aparecem em forma de tabela limpa em outras páginas (8, 9, 38, 46). **Recomendo ignorar essas páginas de gráfico na extração** — o texto delas sai invertido/embaralhado pela forma como o PDF foi gerado, e o dado já está disponível em tabela em outro lugar.

Com isso, a essência do relatório cabe em poucas tabelas de fato, na granularidade **mensal** (sem acumulado, sem % pré-calculado):

# 5. Modelo de dados proposto (estilo esquema estrela, pronto para Power BI)

## Dimensões

| Dimensão | Campos | Fonte |
|---|---|---|
| `Dim_Tempo` | ano, mês, mês_nome | nome do arquivo / título da página |
| `Dim_Segmento` | Autos, Com. Leves, Caminhões, Ônibus, Motos, Impl. Rodoviários | fixo (catálogo curto) |
| `Dim_Fabricante` | nome da marca | páginas de ranking por marca |
| `Dim_Modelo` | modelo, fabricante | páginas de ranking por modelo |
| `Dim_Regiao` | Norte, Nordeste, Centro-Oeste, Sudeste, Sul | fixo |
| `Dim_TipoVenda` | Total, Direta, Varejo | páginas 26–33 |
| `Dim_Motorizacao` | Até 1.0, De 1.0 a 2.0, Acima de 2.0 | página 10 |
| `Dim_Eletrificacao` | Híbrido, Elétrico | páginas 20–22, 41–42, 50 |
| `Dim_CategoriaVeiculo` | Hatch Pequeno, SUV, Pick-up Pequena, etc. | páginas 11–19, 47–49 |

## Fatos (todos na granularidade mensal — sem acumulado)

| Fato | Grão | Métrica | Origem |
|---|---|---|---|
| `Fato_Resumo_Segmento` | Segmento × Mês | Quantidade emplacada | pág. 1 |
| `Fato_Regiao` | Segmento × Região × Mês | % participação (ou quantidade, se decidirmos recalcular) | pág. 5, 37, 45, 52 |
| `Fato_Marca` | Segmento × Fabricante × TipoVenda × Mês | Quantidade | pág. 8, 9, 26–29, 38, 46 |
| `Fato_Modelo` | Segmento × Fabricante × Modelo × TipoVenda × Mês | Quantidade | pág. 6, 7, 30–33, 39, 40, 47–49 |
| `Fato_Modelo_Categoria` | Segmento × CategoriaVeículo × Modelo × Mês | Quantidade | pág. 11–19 |
| `Fato_Motorizacao` | Segmento × Motorização × Mês | Quantidade | pág. 10 |
| `Fato_Eletrificados` | Segmento × TipoEletrificação × Fabricante × Mês | Quantidade | pág. 20–22, 41–42, 50 |

Ou seja: **9 dimensões + 7 fatos**, todos simples (poucas colunas), no lugar de tentar replicar as 52 páginas visualmente. Isso também deixa o modelo pronto para as métricas que você provavelmente vai querer no dashboard: acumulado, variação ano a ano, participação de mercado, ranking dinâmico por período escolhido — tudo isso vira medida DAX em cima do dado mensal, em vez de coluna fixa herdada do PDF.

# 6. Prova de conceito

Já extraí a tabela `Fato_Resumo_Segmento` para os 7 meses disponíveis (Jan–Jul/2026), a partir da página 1 de cada PDF — é o arquivo `fato_resumo_segmento_2026_jan_a_jul.csv` em anexo. Ela mostra que a extração funciona e que o dado mensal por segmento já está limpo e pronto para entrar no Power BI (ou numa exploração inicial em pandas/Excel).

Ainda não extraí as tabelas de marca, modelo, região, motorização e eletrificados — eram o próximo passo natural, mas preferi confirmar com você o modelo de dados antes de automatizar a extração das ~50 páginas restantes por mês.

# 7. Pontos de atenção para a extração

- **Páginas de gráfico de pizza (3, 4, 24, 25, 26, 35, 36, 44)**: ignorar — texto sai invertido e o dado é redundante com as tabelas de ranking.
- **Páginas regionais (5, 37, 45, 52)**: os números aparecem em ordem no texto, mas a extração de texto não amarra automaticamente cada valor à sua região (Norte/Nordeste/etc.) — isso é um gráfico de barras empilhadas, não uma tabela. Vou precisar usar as coordenadas dos elementos no PDF (posição x/y) para garantir a associação correta antes de confiar nesses números.
- **"Outros" (pág. 1)**: a Fenabrave usa essa categoria para veículos fora da classificação principal — vale confirmar no site da Fenabrave o que exatamente compõe esse grupo, caso ele entre no dashboard.
- **Layout pode variar entre edições**: como visto no item 3, uma linha (`Total`) sumiu a partir de Fevereiro. A extração deve casar por rótulo de segmento/marca/modelo, não por posição fixa de linha.

# 8. Próximos passos sugeridos

1. Você confirma (ou ajusta) o modelo de dados da seção 5.
2. Eu automatizo a extração das páginas de marca, modelo, motorização e eletrificados para os 7 meses já recebidos, gerando os CSVs finais de cada fato.
3. Conforme for baixando os demais meses/anos, você só precisa soltar os PDFs em `01_dados_brutos/` seguindo o mesmo padrão de nome (`AAAA_MM_02.pdf`) — a extração é reaproveitável porque a estrutura do relatório é estável.
4. Os CSVs finais vão para `02_dados_extraidos/`, prontos para importar no Power BI (`04_power_bi/`).
