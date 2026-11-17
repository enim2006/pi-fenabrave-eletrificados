"""Exporta a base tratada usada pelo dashboard para 04_dashboard/base_tratada/.

Gera quatro CSVs (UTF-8, separador vírgula, decimal ponto) e um arquivo Excel com as mesmas
tabelas e uma aba LEIAME com o dicionário de dados. Os números são os mesmos exibidos pelo
app, pois ambos usam tratamento_fenabrave.carregar().

Uso (a partir da raiz do repositório):
    python 04_dashboard/exportar_base_tratada.py
Requer openpyxl para o arquivo Excel.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from tratamento_fenabrave import carregar, classificar_modelos

BASE = Path(__file__).resolve().parent
ORIGEM = BASE.parent / "02_dados_extraidos"
DESTINO = BASE / "base_tratada"
MESES = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho",
         8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
SEGMENTOS_BASE = ["Autos", "Com. Leves", "Caminhões", "Ônibus", "Motos", "Implementos Rodoviários", "Outros"]
SEGMENTOS_PROPULSAO = ["Autos", "Com. Leves", "Caminhões", "Ônibus", "Motos"]


def _cabecalho(df):
    df = df.copy()
    df["ano"] = df.ano.astype(int)
    df["mes_num"] = df.mes_num.astype(int)
    df["mes_nome"] = df.mes_num.map(MESES)
    df["periodo"] = df.ano.astype(str) + "-" + df.mes_num.astype(str).str.zfill(2)
    return df


def tabela_segmento(D):
    r = _cabecalho(D["resumo"])
    if "origem" not in r:
        r["origem"] = "extraido"
    r["origem"] = r.origem.fillna("calculado")
    r["agregado"] = ~r.segmento.isin(SEGMENTOS_BASE)
    r = r.rename(columns={"quantidade_mes": "emplacamentos"})
    r["emplacamentos"] = r.emplacamentos.astype(int)
    cols = ["periodo", "ano", "mes_num", "mes_nome", "segmento", "agregado", "emplacamentos", "origem"]
    return r[cols].sort_values(["periodo", "agregado", "segmento"]).reset_index(drop=True)


def tabela_propulsao(D):
    res = D["resumo"]
    tot = res[res.segmento.isin(SEGMENTOS_PROPULSAO)].pivot_table(
        index=["ano", "mes_num", "segmento"], values="quantidade_mes", aggfunc="sum").quantidade_mes
    e = D["eletrificados_resumo"]
    e = e[e.tipo_eletrificacao.isin(["Híbridos", "Elétricos"])].pivot_table(
        index=["ano", "mes_num", "segmento"], columns="tipo_eletrificacao", values="quantidade_mes", aggfunc="sum")
    df = e.join(tot.rename("total_segmento"), how="inner").reset_index()
    df = df.rename(columns={"Híbridos": "hibridos", "Elétricos": "eletricos"})
    df["combustao"] = df.total_segmento - df.hibridos - df.eletricos
    df["eletrificados"] = df.hibridos + df.eletricos
    df["pct_eletrificados"] = (df.eletrificados / df.total_segmento * 100).round(2)
    df = _cabecalho(df)
    for c in ["combustao", "hibridos", "eletricos", "eletrificados", "total_segmento"]:
        df[c] = df[c].astype(int)
    cols = ["periodo", "ano", "mes_num", "mes_nome", "segmento", "combustao", "hibridos", "eletricos",
            "eletrificados", "total_segmento", "pct_eletrificados"]
    return df[cols].sort_values(["periodo", "segmento"]).reset_index(drop=True)


def tabela_marca(D):
    m = _cabecalho(D["marca"])
    for c in ["recuperado", "estimado", "conferido_pdf"]:
        m[c] = m[c].astype("boolean").fillna(False).astype(bool) if c in m else False
    reclass = m.seg_orig.notna() & (m.seg_orig != m.segmento)
    m["origem"] = np.select(
        [m.conferido_pdf, m.estimado, m.recuperado, reclass],
        ["conferido_pdf", "estimado", "recuperado", "reclassificado"], default="extraido")
    seg_tot = D["resumo"].pivot_table(index=["ano", "mes_num", "segmento"], values="quantidade_mes",
                                      aggfunc="sum").quantidade_mes
    tot = pd.Series([seg_tot.get((a, mm, s), np.nan) for a, mm, s in zip(m.ano, m.mes_num, m.segmento)], index=m.index)
    m["participacao_pct"] = m.participacao_pct.fillna((m.quantidade_mes / tot * 100).round(2))
    m = m.rename(columns={"quantidade_mes": "emplacamentos"})
    m["emplacamentos"] = m.emplacamentos.round().astype(int)
    cols = ["periodo", "ano", "mes_num", "mes_nome", "segmento", "fabricante", "emplacamentos", "participacao_pct",
            "origem"]
    return (m[cols].sort_values(["periodo", "segmento", "emplacamentos"], ascending=[True, True, False])
            .reset_index(drop=True))


def tabela_modelo(D):
    m = _cabecalho(classificar_modelos(D["modelo"]))
    m["estimado"] = m.estimado.astype("boolean").fillna(False).astype(bool)
    m = (m.groupby(["periodo", "ano", "mes_num", "mes_nome", "segmento", "tipo_venda", "modelo", "eletrificado",
                    "propulsao"], as_index=False)
          .agg(emplacamentos=("quantidade_mes", "sum"), estimado=("estimado", "max")))
    m["fabricante"] = m.modelo.str.split("/").str[0]
    m["emplacamentos"] = m.emplacamentos.round().astype(int)
    m["origem"] = np.where(m.estimado, "estimado", "extraido")
    m = m.rename(columns={"eletrificado": "eletrificado_proxy", "propulsao": "propulsao_proxy"})
    cols = ["periodo", "ano", "mes_num", "mes_nome", "segmento", "tipo_venda", "fabricante", "modelo", "emplacamentos",
            "eletrificado_proxy", "propulsao_proxy", "origem"]
    return (m[cols].sort_values(["periodo", "segmento", "tipo_venda", "emplacamentos"],
                                ascending=[True, True, True, False]).reset_index(drop=True))


LEIAME = [
    ("Fonte", "Fenabrave, Informativo – Emplacamentos (boletim mensal), PDFs em 01_dados_brutos/."),
    ("Cobertura", "{cobertura}"),
    ("Tratamento", "02_dados_extraidos/ (extração dos PDFs) + 04_dashboard/tratamento_fenabrave.py (correção das "
                   "falhas de extração). Detalhes em 03_exploracao/scripts/notas_extracao_fatos.md."),
    ("", ""),
    ("Tabela", "Conteúdo"),
    ("propulsao_mensal", "Emplacamentos por segmento e tipo de propulsão (combustão, híbridos, elétricos), desde "
                         "jan/2024. Combustão = total do segmento − híbridos − elétricos."),
    ("segmento_mensal", "Total mensal de emplacamentos por segmento, desde jan/2022. agregado=True indica linhas de "
                        "soma (Autos + Com. Leves, Caminhões + Ônibus, Subtotal (A a D), Total Geral)."),
    ("marca_mensal", "Ranking mensal de marcas (Top-N publicado pela Fenabrave) por segmento. Não é a lista "
                     "completa do mercado."),
    ("modelo_mensal", "Ranking mensal dos 50 modelos mais emplacados em Autos e Com. Leves, por canal de venda "
                      "(Total, Direta, Varejo)."),
    ("", ""),
    ("Coluna", "Significado"),
    ("periodo", "Mês de referência dos dados, AAAA-MM."),
    ("emplacamentos", "Quantidade de veículos emplacados no mês (unidades)."),
    ("participacao_pct", "Participação da marca no total do segmento no mês (%)."),
    ("pct_eletrificados", "(híbridos + elétricos) ÷ total do segmento × 100."),
    ("tipo_venda", "Total = todas as vendas; Direta = vendas diretas da montadora (frotistas, locadoras, PcD etc.); "
                   "Varejo = vendas pelas concessionárias."),
    ("eletrificado_proxy / propulsao_proxy", "Classificação do modelo por lista manual de nameplates eletrificados "
                                             "(a Fenabrave não publica a propulsão por modelo). Nameplates com versões "
                                             "a combustão e híbridas ficam como combustão."),
    ("origem", "extraido = lido do PDF pelo parser; calculado = derivado por identidade contábil do próprio "
               "informativo (ex.: Total = soma dos segmentos); reclassificado = linha que o parser atribuiu ao "
               "segmento errado, corrigida pelo total implícito (quantidade ÷ participação); recuperado = (Autos + "
               "Com. Leves) − Com. Leves; estimado = valor estimado a partir de meses vizinhos ou da soma dos modelos; "
               "conferido_pdf = valor lido manualmente no PDF."),
]


def main():
    D = carregar(str(ORIGEM))
    tabelas = {
        "propulsao_mensal": tabela_propulsao(D),
        "segmento_mensal": tabela_segmento(D),
        "marca_mensal": tabela_marca(D),
        "modelo_mensal": tabela_modelo(D),
    }
    DESTINO.mkdir(exist_ok=True)
    for nome, df in tabelas.items():
        df.to_csv(DESTINO / f"{nome}.csv", index=False, encoding="utf-8")
        print(f"{nome}.csv: {len(df)} linhas")
    p = tabelas["segmento_mensal"].periodo
    cobertura = (f"{p.min()} a {p.max()} (eletrificados desde 2024-01, quando a Fenabrave passou a publicar a "
                 f"seção 'Mercado de Eletrificados').")
    leiame = pd.DataFrame([(a, b.format(cobertura=cobertura)) for a, b in LEIAME], columns=["item", "descricao"])
    with pd.ExcelWriter(DESTINO / "base_tratada_fenabrave.xlsx", engine="openpyxl") as xw:
        leiame.to_excel(xw, sheet_name="LEIAME", index=False, header=False)
        for nome, df in tabelas.items():
            df.to_excel(xw, sheet_name=nome, index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2" if ws.title != "LEIAME" else None
            for col in ws.columns:
                largura = max(len(str(c.value)) if c.value is not None else 0 for c in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largura + 2), 90)
    print("base_tratada_fenabrave.xlsx gerado")


if __name__ == "__main__":
    main()
