# Evolução do mercado de veículos eletrificados no Brasil (2022–2026)

Análise produzida a partir dos relatórios mensais **Fenabrave — Emplacamento de Autoveículos** (janeiro/2022 a julho/2026, 55 arquivos), como parte da exploração de dados do Projeto Integrador (PI) de Ciência de Dados low-code.

## 1. Pergunta orientadora

Mapear a evolução do mercado de veículos eletrificados (híbridos + puramente elétricos) desde seu início até os dias atuais, e avaliar se os dados a partir de 2023 (ou 2022) são suficientes, ou se seria necessário recuar até 2021/2020.

## 2. Decisão: 2022 é o corte adequado; 2020 e 2021 não são necessários

Decisão: **usar 2022 em diante como base da análise histórica**, sem necessidade de incluir os arquivos de 2021 e 2020 já disponíveis. Motivos:

1. **A própria Fenabrave não rastreava eletrificados até 2022.** O relatório completo não tem nenhuma seção ou menção textual a "elétrico"/"híbrido" nos meses testados de 2020 e nos 12 meses de 2022 processados — confirmando um teste manual realizado previamente com o arquivo de janeiro/2020. A seção oficial "Mercado de Eletrificados" só passou a existir no relatório a partir de **janeiro/2024**.
2. **BYD (hoje a marca líder do segmento) tem participação nula em 2022.** Nos 12 meses de 2022 processados, BYD não aparece nem uma vez no ranking Top-N de marcas de Autos — ou seja, mesmo o maior player atual do mercado eletrificado brasileiro ainda não existia comercialmente nesse ano.
3. **Volume nacional de 2020/2021 é uma fração pequena do de 2022**, mas já não é desprezível — o que reforça 2022 como o ano em que o mercado começa a virar um fenômeno perceptível, enquanto 2020/2021 são, na prática, o "ano zero" que a própria fonte primária do projeto (Fenabrave) não documenta:
   - 2020: 19.745 unidades (elétricos + híbridos, todas as categorias)
   - 2021: 34.990 unidades
   - 2022: 49.245 unidades
   - (fonte: ABVE, via reportagem Vrum — ver Fontes)
4. **Cortar em ano cheio**: o corte em 2022 preserva anos completos (Jan–Dez) em todas as séries.

Conclusão prática: os PDFs de 2021 e 2020 já disponíveis não precisam ser incluídos em `01_dados_brutos/`. Caso o PI queira contextualizar o início do mercado com 1–2 frases e números oficiais no texto final (sem re-extrair PDFs), os dados da ABVE acima já cobrem isso.

## 3. O que os dados da Fenabrave permitem medir, e a partir de quando

| Métrica | Início da série | Fonte na Fenabrave |
|---|---|---|
| Ranking de marcas (Autos), incl. presença/ausência da BYD | 2022 | Seção "Ranking de Marcas" (todo mês) |
| Ranking de modelos, incl. modelos elétricos/híbridos específicos | 2022 | Seção "Ranking de Modelos" |
| Emplacamentos oficiais "Total Eletrificados" (híbridos + elétricos), por segmento (Autos, Com. Leves, Caminhões, Ônibus, Motos) | **Janeiro/2024** | Seção "Mercado de Eletrificados" (só existe a partir de 2024) |

Por isso a análise combina **duas séries complementares**:
- **Proxy BYD (2023–2026)**: emplacamentos mensais da marca BYD em Autos, extraídos do ranking de marcas. Existe desde antes da seção oficial de eletrificados, mas sub-representa o mercado total (não captura outras marcas híbridas/elétricas, nem o período anterior a 2023, quando BYD ainda não vendia no Brasil).
- **Total Eletrificados oficial (2024–2026)**: soma direta da seção "Mercado de Eletrificados" da Fenabrave, a métrica mais confiável e completa disponível.

## 4. Números principais

**Totais anuais oficiais (todos os segmentos: Autos + Com. Leves + Caminhões + Ônibus + Motos):**

| Ano | Total Eletrificados (unidades) |
|---|---|
| 2024 | 185.876 |
| 2025 | 294.971 |
| 2026 (jan–jul, parcial) | 325.739 |

**Totais anuais, apenas Autos + Com. Leves** (o recorte mais comparável a "carros" no sentido popular):

| Ano | Total Eletrificados — Autos + Com. Leves |
|---|---|
| 2024 | 177.379 |
| 2025 | 285.222 |
| 2026 (jan–jul, parcial) | 307.309 |

**Crescimento mês a mês (Autos + Com. Leves):** de 12.553 unidades em janeiro/2024 para 66.235 unidades em julho/2026 — mais de **5x** de crescimento em 2 anos e meio, com trajetória consistentemente ascendente (ver gráfico de evolução mensal).

**Proxy BYD (Autos):** de 143 unidades em janeiro/2023 para 23.423 unidades em julho/2026 — crescimento de mais de 160x nesse período, ilustrando a virada de "marca inexistente" para "líder de segmento" em pouco mais de 3 anos.

## 5. Nota sobre divergência com números de mercado (ABVE/imprensa)

O total anual de 2025 apurado a partir da Fenabrave (294.971 em todos os segmentos, ou 285.222 em Autos+Com. Leves) é **maior** do que o número frequentemente citado na imprensa para 2025 (~223–224 mil, segundo ABVE/Forbes/CNN Brasil). A diferença provável não é um erro de extração, mas sim **metodologia de classificação diferente entre fontes** — a Fenabrave inclui categorias (Caminhões, Ônibus, Motos elétricas) que o ABVE/imprensa podem contar separadamente ou excluir do "mercado de veículos eletrificados" no sentido de automóveis de passeio. Para os fins deste projeto, o número da própria Fenabrave é tratado como a referência primária, por ser a fonte-base de todo o dataset; os números do ABVE/imprensa servem apenas como validação de ordem de grandeza (mesma faixa, mesma tendência de forte crescimento).

## 6. Limitações e qualidade dos dados

- **Mudança de metodologia da fonte em fev/2026**: a partir desse mês, os rótulos de segmento ("A) Autos" / "B) Com. Leves") somem de duas páginas do relatório (Resumo Mensal e Participação por Motorização); a extração foi adaptada para usar a ordem posicional dos blocos em vez do rótulo textual — validado manualmente, mas é um ponto de atenção caso a Fenabrave mude a ordem novamente no futuro.
- **4 arquivos exigiram OCR** (`2024_01`, `2024_04`, `2024_05` — fonte corrompida no PDF original; `2023_09` — PDF integralmente rasterizado/sem camada de texto). O OCR (Tesseract, português) tem qualidade ligeiramente inferior à extração direta de texto; erros residuais conhecidos e mitigados: confusão eventual de dígitos de ranking e, raramente, nomes de categoria de modelo mal capturados nesses 4 meses específicos. Os totais oficiais de "Eletrificados" (seção dedicada, tabela simples) não foram afetados de forma perceptível nos meses testados.
- **Proxy BYD não é uma medida de mercado total** antes de 2024 — deve ser lido como "evolução de uma marca específica", não como "tamanho do mercado eletrificado".
- Nenhum arquivo de 2020/2021 foi processado (decisão do item 2) — se o projeto mudar de escopo e quiser esses anos, os PDFs já estão disponíveis e a mesma pipeline de extração deve funcionar, pois a estrutura de 2020/2021 é semelhante à de 2022/2023 (46 páginas, sem seção de eletrificados).
- **Corrigido (18/08/2026)**: bug de "texto em negrito duplicado" em algumas edições (mais visível em jan/2022) fazia cabeçalhos de tabela (ex.: "Dez Jan Acumulado") saírem com cada caractere repetido (ex.: "DDeezz JJaann..."), o que confundia o classificador de categoria e, em alguns casos raros, também duplicava dígitos de quantidades pequenas (ex.: "1" virando "11"). A correção normaliza esse texto antes do parsing. Efeito no `fato_modelo_categoria.csv`: caiu de 75 para 30 categorias distintas (eram 45 valores de "categoria" corrompidos, incl. um bug que apagava o mês inteiro de jan/2022, agora recuperado). Efeito nas demais tabelas: correção pontual de ~1 linha por arquivo (dígitos duplicados em modelos/marcas de cauda longa, ex.: "77"→"7"), sem impacto relevante nos totais agregados (Total Eletrificados 2024 ajustado de 185.896 para 185.876; 2026 parcial de 325.749 para 325.739 — a série mensal Autos+Com.Leves usada no gráfico não mudou).

## 7. Arquivos entregues

- `02_dados_extraidos/`: 7 CSVs atualizados (2022–2026, todas as tabelas fato), substituindo a versão anterior (que cobria só jan–jul/2026).
  - Novidade: `fato_eletrificados_resumo.csv` — série oficial "Total Eletrificados" por segmento e tipo (Híbridos/Elétricos/Total), não limitada a Top-N.
- `03_exploracao/scripts/extract_fenabrave.py`: script final, com classificação por título (robusto a mudanças de layout entre anos), fallback de OCR e tratamento de todos os casos especiais listados acima.
- Gráfico de evolução mensal (HTML autocontido): duas séries (proxy BYD e Total Eletrificados oficial), com marcador em jan/2024 indicando o início da publicação oficial da seção.

## Fontes

- [2020: o melhor ano da eletromobilidade no Brasil – ABVE](https://www.abve.org.br/2020-o-melhor-ano-da-eletromobilidade-no-brasil/)
- [Brasil emplacou quase 50 mil veículos híbridos e elétricos em 2022 — Vrum](https://www.vrum.com.br/noticias/emplacamentos-hibridos-eletricos-2022/)
- [Abve Data — ABVE](https://abve.org.br/abve-data/)
- [Emplacamentos de veículos eletrificados crescem mais de 25% em 2025 — Diário do Poder](https://diariodopoder.com.br/diario-motor/emplacamentos-de-veiculos-eletrificados-crescem-mais-de-25-em-2025)
- [Venda de eletrificados cresce 6 vezes mais que o mercado automotivo — CNN Brasil](https://www.cnnbrasil.com.br/auto/venda-de-eletrificados-cresce-6-vezes-mais-que-o-mercado-automotivo/)
- Dados de base: relatórios mensais Fenabrave "Emplacamento de Autoveículos" (2022–2026), processados pela pipeline própria deste projeto.
