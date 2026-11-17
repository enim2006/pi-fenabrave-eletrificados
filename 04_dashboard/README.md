# Dashboard

Painel interativo em Streamlit sobre emplacamentos de veículos no Brasil, com foco em eletrificados (híbridos e elétricos), a partir do boletim mensal da Fenabrave.

## Conteúdo

| Arquivo | Descrição |
|---|---|
| `app.py` | Aplicação Streamlit: página única com 6 abas — Montadoras, Modelos e Propulsão, em visão mensal e anual. |
| `tratamento_fenabrave.py` | Carga dos CSVs de `02_dados_extraidos/` e correção das falhas de extração (rankings em segmento trocado, meses ausentes, valores conferidos no PDF). Usado pelo app e pela exportação. |
| `exportar_base_tratada.py` | Gera `base_tratada/` (CSV e Excel) com os mesmos dados exibidos no painel. |
| `base_tratada/` | Base de dados tratada: `propulsao_mensal`, `segmento_mensal`, `marca_mensal`, `modelo_mensal` (CSV) e `base_tratada_fenabrave.xlsx` (mesmas tabelas + aba LEIAME com o dicionário de dados). |

## Execução local

A partir da raiz do repositório:

```bash
pip install -r requirements.txt
python -m streamlit run 04_dashboard/app.py
```

O painel abre em http://localhost:8501.

Para regenerar a base tratada após atualizar os CSVs de `02_dados_extraidos/` (requer também `openpyxl`):

```bash
python 04_dashboard/exportar_base_tratada.py
```

## Abas

1. **Montadoras (mensal)** — linhas por marca em Autos; volume absoluto ou participação; número de marcas ajustável (padrão: mínimo que cobre 80% do volume do ranking no período).
2. **Modelos (mensal)** — linhas por modelo em Autos e Com. Leves; filtros de canal de venda (Direta/Varejo/Todas), segmento e propulsão; eletrificados em verde.
3. **Propulsão (mensal)** — áreas empilhadas de combustão, híbridos e elétricos por segmento, em volume e em participação, desde jan/2024.
4. **Montadoras (anual)**, 5. **Modelos (anual)**, 6. **Propulsão (anual)** — as mesmas visões em totais anuais. O ano corrente é marcado como não consolidado (`*`). A aba 5 destaca a participação da venda direta no Top 50; a aba 6 inclui 2022–2023 apenas com o total do segmento, pois a Fenabrave só publica eletrificados desde jan/2024.

## Limitações

- Rankings de marca e de modelo são Top-N publicados pela Fenabrave, não a lista completa do mercado.
- A propulsão por modelo é uma classificação manual (proxy); a Fenabrave não publica essa informação no ranking de modelos.
- Valores estimados e corrigidos estão identificados na coluna `origem` da base tratada e no log de tratamento exibido ao final do painel.
