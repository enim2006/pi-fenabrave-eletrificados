"""Painel Fenabrave — Eletrificados no Brasil (2022–2026).

Dashboard Streamlit do PI Desenvolvimento Low Code em Ciência de Dados (Senac EAD ADS, Grupo 08).
Seis abas independentes: montadoras, modelos e propulsão, em visão mensal e anual.
Fonte: Fenabrave, Informativo – Emplacamentos (CSVs em 02_dados_extraidos/, tratados por
tratamento_fenabrave.py).

Execução local:  python -m streamlit run 04_dashboard/app.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DADOS = BASE.parent / "02_dados_extraidos"
sys.path.insert(0, str(BASE))
from tratamento_fenabrave import carregar  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes de apresentação
# ---------------------------------------------------------------------------
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
COR_TIPO = {"Elétricos": "#2a78d6", "Híbridos": "#eb6834", "Combustão": "#898781"}
COR_SEM_DIVISAO = "#d9d7cf"
COR_ELETRIFICADO = "#1baf7a"
COR_COMBUSTAO_MODELO = "#eb6834"
PALETA_MARCAS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#7a7860", "#0d366b"]
PALETA_EXTRA = ["#5b9bd5", "#c55a11", "#70ad47", "#bf9000", "#a5a5a5", "#7030a0", "#264478", "#9e480e",
                "#43682b", "#997300", "#636363", "#255e91"]
SEGMENTOS_PROPULSAO = ["Autos", "Com. Leves", "Caminhões", "Ônibus", "Motos"]
TIPOS = ["Combustão", "Híbridos", "Elétricos"]  # ordem de empilhamento (base → topo)
CANAL = {"Diretas": "Direta", "Varejo": "Varejo", "Todas": "Total"}

# Proxy de modelo eletrificado (a Fenabrave não publica a propulsão por modelo).
RX_ELETRIFICADO = r"^(?:BYD/|GWM/ORA|GWM/HAVAL H6|GEELY/EX|LEAPMOTOR/|VOLVO/EX|JAC/(?:EJV|IEV))"
RX_HIBRIDO = r"^(?:BYD/(?:KING|SHARK|SONG)|GWM/HAVAL H6|GEELY/EX5 EM-I)"

FONTE = "Fonte: Fenabrave, Informativo – Emplacamentos."

st.set_page_config(page_title="Painel Fenabrave — Eletrificados", page_icon="🚗", layout="wide")


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------
def fmt_int(v):
    return f"{v:,.0f}".replace(",", ".") if pd.notna(v) else "—"


def fmt_pct(v, casas=1):
    return f"{v:.{casas}f}%".replace(".", ",") if pd.notna(v) else "—"


def rot_mes(d):
    return f"{MESES[d.month - 1]}/{d.year}"


def rot_mes_curto(d):
    return f"{MESES[d.month - 1]}/{str(d.year)[2:]}"


def nome_modelo(m):
    marca, _, modelo = m.partition("/")
    marca = marca if len(marca) <= 3 else marca.title()
    return f"{marca} · {modelo.title()}" if modelo else marca


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando e tratando a base Fenabrave…")
def dados():
    D = carregar(str(DADOS))
    res = D["resumo"]
    tot = (res[res.segmento.isin(SEGMENTOS_PROPULSAO)]
           .pivot_table(index="data", columns="segmento", values="quantidade_mes", aggfunc="sum")
           .sort_index())

    mar = D["marca"]
    mar_autos = (mar[mar.segmento == "Autos"]
                 .pivot_table(index="data", columns="fabricante", values="quantidade_mes", aggfunc="sum")
                 .sort_index())
    ordem = mar_autos.sum().sort_values(ascending=False).index
    cores_marca = {m: (PALETA_MARCAS + PALETA_EXTRA)[i % (len(PALETA_MARCAS) + len(PALETA_EXTRA))]
                   for i, m in enumerate(ordem)}

    mod = D["modelo"].copy()
    mod["modelo"] = mod.modelo.astype(str).str.replace(r"\s*/\s*", "/", regex=True).str.strip()
    mod["eletrificado"] = mod.modelo.str.contains(RX_ELETRIFICADO, regex=True)
    mod["propulsao"] = np.where(~mod.eletrificado, "Combustão",
                                np.where(mod.modelo.str.contains(RX_HIBRIDO, regex=True), "Híbrido", "Elétrico"))
    mod = (mod.groupby(["data", "ano", "segmento", "tipo_venda", "modelo", "eletrificado", "propulsao"], as_index=False)
              .agg(quantidade_mes=("quantidade_mes", "sum"), estimado=("estimado", "max")))

    elr = D["eletrificados_resumo"]
    elr = (elr[elr.tipo_eletrificacao.isin(["Híbridos", "Elétricos"])]
           .pivot_table(index=["data", "segmento"], columns="tipo_eletrificacao", values="quantidade_mes", aggfunc="sum"))
    return dict(tot=tot, mar_autos=mar_autos, cores_marca=cores_marca, mod=mod, elr=elr, log=D["log"])


def propulsao_mensal(B, seg):
    """Combustão/Híbridos/Elétricos por mês desde jan/2024. Combustão = total do segmento − H − E."""
    e = B["elr"].xs(seg, level="segmento")[["Híbridos", "Elétricos"]]
    t = B["tot"][seg]
    df = e.join(t.rename("Total"), how="inner")
    df["Combustão"] = df["Total"] - df["Híbridos"] - df["Elétricos"]
    return df[TIPOS + ["Total"]]


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
def _anticolisao(itens, gap, piso):
    """itens: lista (chave, y) — devolve {chave: y ajustado}, ordem preservada e espaçamento mínimo `gap`."""
    itens = sorted(itens, key=lambda kv: -kv[1])
    ys = [y for _, y in itens]
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - gap)
    if ys and ys[-1] < piso:
        ys[-1] = piso
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = max(ys[i], ys[i + 1] + gap)
    return {k: y for (k, _), y in zip(itens, ys)}


def _eixo_x(fig, xs, anual, parcial):
    if anual:
        fig.update_xaxes(tickmode="array", tickvals=list(xs),
                         ticktext=[f"{x}*" if x == parcial else str(x) for x in xs])
    else:
        n = len(xs)
        passo = 1 if n <= 8 else 2 if n <= 18 else 6
        ticks = [d for d in xs if (d.month - 1) % passo == 0] if passo > 1 else list(xs)
        fig.update_xaxes(tickmode="array", tickvals=ticks, ticktext=[rot_mes_curto(d) for d in ticks])


def _layout(fig, altura, pct, titulo_y):
    fig.update_layout(
        height=altura, template="plotly_white", separators=",.", showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10), hovermode="x unified",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12),
    )
    fig.update_yaxes(title_text=titulo_y, ticksuffix="%" if pct else "", rangemode="tozero",
                     tickformat=".0f" if pct else ",.0f",
                     gridcolor="#e9e8e4", zeroline=True, zerolinecolor="#c9c7bf")
    fig.update_xaxes(showgrid=False)


def _rotulos(fig, pontos, x_ult, x_rot, y_max, pct):
    """Rótulos em lista vertical à direita, ligados ao último ponto por um traço fino."""
    pos = _anticolisao([(n, y) for n, (y, _, _) in pontos.items()], gap=y_max * 0.072, piso=y_max * 0.02)
    for n, (y, valor, cor) in pontos.items():
        yy = pos[n]
        fig.add_trace(go.Scatter(x=[x_ult, x_rot], y=[y, yy], mode="lines", hoverinfo="skip",
                                 line=dict(color=cor, width=0.7), opacity=0.6))
        fig.add_annotation(x=x_rot, y=yy, xanchor="left", yanchor="middle", showarrow=False, align="left",
                           text=f"<span style='color:{cor}'><b>{n}</b></span><br>"
                                f"<span style='color:#77756e;font-size:10px'>{fmt_pct(valor) if pct else fmt_int(valor)}</span>")


def fig_linhas(W, cores, pct=False, anual=False, parcial=None, altura=560):
    """W: índice = datas (mensal) ou anos (anual); colunas = séries, já na ordem desejada."""
    W = W.dropna(how="all")
    fig = go.Figure()
    xs = list(W.index)
    hover = "%{y:.1f}%" if pct else "%{y:,.0f}"
    for n in W.columns:
        s = W[n]
        cor = cores[n]
        if anual and parcial in xs and len(xs) > 1:
            fechados = s[s.index < parcial]
            fig.add_trace(go.Scatter(x=fechados.index, y=fechados.values, name=n, mode="lines+markers",
                                     line=dict(color=cor, width=2.2), marker=dict(size=7),
                                     hovertemplate=f"{n}: {hover}<extra></extra>"))
            trecho = s.loc[[x for x in xs if x >= xs[-2]]]
            fig.add_trace(go.Scatter(x=trecho.index, y=trecho.values, mode="lines", hoverinfo="skip",
                                     line=dict(color=cor, width=2.2, dash="dash")))
            fig.add_trace(go.Scatter(x=[parcial], y=[s.loc[parcial]], name=f"{n}*", mode="markers",
                                     marker=dict(size=11, symbol="circle-open", color=cor, line=dict(width=2.5, color=cor)),
                                     hovertemplate=f"{n} (parcial): {hover}<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=s.index, y=s.values, name=n, mode="lines+markers" if anual else "lines",
                                     line=dict(color=cor, width=2.2), marker=dict(size=7),
                                     hovertemplate=f"{n}: {hover}<extra></extra>"))
    ult = W.ffill().iloc[-1]
    y_max = float(np.nanmax(W.values)) if W.size else 1.0
    if anual:
        x_ult = xs[-1]
        x_rot = xs[-1] + max(0.12 * (xs[-1] - xs[0]), 0.25)
        x_fim = xs[-1] + max(0.42 * (xs[-1] - xs[0]), 0.9)
        x_ini = xs[0] - max(0.04 * (xs[-1] - xs[0]), 0.2)
    else:
        span = xs[-1] - xs[0]
        x_ult = xs[-1]
        x_rot = xs[-1] + span * 0.025
        x_fim = xs[-1] + span * 0.15
        x_ini = xs[0]
    pontos = {n: (float(ult[n]), float(ult[n]), cores[n]) for n in W.columns if pd.notna(ult[n])}
    _rotulos(fig, pontos, x_ult, x_rot, y_max, pct)
    _layout(fig, altura, pct, "Participação (%)" if pct else ("Emplacamentos/ano (unidades)" if anual
                                                                 else "Emplacamentos/mês (unidades)"))
    fig.update_xaxes(range=[x_ini, x_fim])
    _eixo_x(fig, xs, anual, parcial)
    return fig


def fig_area(W, series, pct=False, anual=False, parcial=None, sem_divisao=None, altura=420):
    """Áreas empilhadas. W: colunas Combustão/Híbridos/Elétricos (+ Total). Em pct, W já está em %.
    sem_divisao: Series {ano: total} de anos sem série de eletrificados (hachurado)."""
    fig = go.Figure()
    hover = "%{y:.1f}%" if pct else "%{y:,.0f}"
    xs_div = list(W.index)
    if sem_divisao is not None and len(sem_divisao):
        xs_h = list(sem_divisao.index) + ([xs_div[0]] if xs_div else [])
        ys_h = [100.0] * len(xs_h) if pct else list(sem_divisao.values) + ([float(W["Total"].iloc[0])] if xs_div else [])
        fig.add_trace(go.Scatter(
            x=xs_h, y=ys_h, mode="lines+markers" if not pct else "lines", fill="tozeroy", name="Total sem divisão",
            line=dict(color="#a9a79f", width=1), marker=dict(size=6, color="#55534d"),
            fillcolor=COR_SEM_DIVISAO, fillpattern=dict(shape="/", fgcolor="#b9b7af", bgcolor=COR_SEM_DIVISAO, size=8),
            hovertemplate="Total do segmento: %{y:,.0f}<extra></extra>" if not pct else None,
            hoverinfo="skip" if pct else None))
        xm = (xs_h[0] + xs_h[-1]) / 2
        ym = (max(ys_h) * 0.45) if not pct else 50
        fig.add_annotation(x=xm, y=ym, showarrow=False, bgcolor="rgba(255,255,255,0.85)",
                           text="sem série oficial<br>de eletrificados" if pct else "total do segmento<br>(sem divisão)")
        if xs_div:
            fig.add_vline(x=xs_div[0], line=dict(color="#55534d", width=1))
    for n in [t for t in TIPOS if t in series]:
        fig.add_trace(go.Scatter(x=W.index, y=W[n], name=n, mode="lines", stackgroup="um",
                                 line=dict(color="white", width=0.8), fillcolor=COR_TIPO[n],
                                 hovertemplate=f"{n}: {hover}<extra></extra>"))
    sel = [t for t in TIPOS if t in series]
    if anual and parcial in xs_div and sel:
        topo = W[sel].cumsum(axis=1)
        for n in sel:
            fig.add_trace(go.Scatter(x=[parcial], y=[topo.loc[parcial, n]], mode="markers", hoverinfo="skip",
                                     marker=dict(size=10, symbol="circle-open", color="#3d3b36", line=dict(width=2))))
    if sel and xs_div:
        acum = W[sel].cumsum(axis=1).iloc[-1]
        base = acum.shift(1, fill_value=0)
        y_max = float(acum.max()) if not pct else 100.0
        pontos = {n: ((base[n] + acum[n]) / 2, float(W[n].iloc[-1]), COR_TIPO[n]) for n in sel}
        xs_all = (list(sem_divisao.index) if sem_divisao is not None else []) + xs_div
        if anual:
            span = xs_all[-1] - xs_all[0]
            x_rot = xs_all[-1] + max(0.08 * span, 0.2)
            x_fim = xs_all[-1] + max(0.38 * span, 0.8)
            x_ini = xs_all[0] - max(0.03 * span, 0.15)
        else:
            span = xs_all[-1] - xs_all[0]
            x_rot = xs_all[-1] + span * 0.02
            x_fim = xs_all[-1] + span * 0.13
            x_ini = xs_all[0]
        _rotulos(fig, pontos, xs_div[-1], x_rot, y_max, pct)
        fig.update_xaxes(range=[x_ini, x_fim])
        _eixo_x(fig, xs_all, anual, parcial)
    _layout(fig, altura, pct, "Participação (%)" if pct else ("Emplacamentos/ano" if anual else "Emplacamentos/mês"))
    if pct:
        fig.update_yaxes(range=[0, 101])
    return fig


# ---------------------------------------------------------------------------
# Controles comuns
# ---------------------------------------------------------------------------
def controle_periodo(datas, chave, padrao_meses=None, ajuda=None):
    rotulos = [rot_mes(d) for d in datas]
    ini = rotulos[-padrao_meses] if padrao_meses else rotulos[0]
    a, b = st.select_slider("Período (mm/aaaa a mm/aaaa)", options=rotulos, value=(ini, rotulos[-1]),
                            key=chave, help=ajuda)
    return datas[rotulos.index(a)], datas[rotulos.index(b)]


def controle_anos(anos, parcial, chave, ajuda=None):
    rot = [f"{a}*" if a == parcial else str(a) for a in anos]
    a, b = st.select_slider("Anos (mínimo e máximo)", options=rot, value=(rot[0], rot[-1]), key=chave, help=ajuda)
    return anos[rot.index(a)], anos[rot.index(b)]


def escolha(rotulo, opcoes, padrao, chave, desabilitado=False, ajuda=None):
    v = st.segmented_control(rotulo, opcoes, default=padrao, key=chave, disabled=desabilitado, help=ajuda)
    return v if v is not None else padrao


def aviso_parcial(B, extra=""):
    dmax = B["tot"].index.max()
    if dmax.month == 12:
        return None
    st.warning(f"{dmax.year} não consolidado: dados até {rot_mes(dmax)} ({dmax.month} de 12 meses). "
               f"Em volume absoluto, {dmax.year} não é comparável aos anos fechados; no modo Percentual "
               f"a comparação é válida.{extra}", icon="⚠️")
    return dmax.year


def n_para_80(volumes, total):
    acum = volumes.sort_values(ascending=False).cumsum() / total
    return int((acum < 0.8).sum() + 1) if total > 0 else len(volumes)


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
def aba_montadoras(B, anual):
    M = B["mar_autos"]
    tot = B["tot"]["Autos"]
    parcial = None
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([3.2, 1.6, 1.6, 0.9, 1.5])
        with c1:
            if anual:
                dmax = tot.index.max()
                parcial = dmax.year if dmax.month < 12 else None
                anos = sorted(M.index.year.unique())
                a0, a1 = controle_anos(anos, parcial, "m_anos_a")
                d0, d1 = pd.Timestamp(a0, 1, 1), pd.Timestamp(a1, 12, 1)
            else:
                d0, d1 = controle_periodo(list(M.index), "m_per_m")
        with c2:
            vol = escolha("Volume", ["Absoluto", "Percentual (%)"], "Absoluto", f"m_vol_{anual}")
        with c3:
            escolha("Vendas", ["Diretas", "Varejo", "Todas"], "Todas", f"m_vnd_{anual}", desabilitado=True,
                    ajuda="O ranking de marcas da Fenabrave só publica o total (sem canal de venda).")
        with c4:
            st.segmented_control("Segmento", ["Autos"], default="Autos", key=f"m_seg_{anual}", disabled=True)
        Mp = M.loc[d0:d1]
        vols = Mp.sum().loc[lambda s: s > 0]
        total_periodo = tot.loc[d0:d1].sum()
        a_pad = n_para_80(vols, vols.sum())
        with c5:
            a = st.number_input(f"Montadoras (a) — de {len(vols)}", min_value=1, max_value=len(vols), value=a_pad,
                                step=1, key=f"m_a_{anual}_{d0:%Y%m}_{d1:%Y%m}",
                                help="Padrão: mínimo de montadoras que cobre ≥80% do volume do ranking no período.")
        st.caption("Vendas Diretas/Varejo não existem no nível de marca (fato_marca só publica o total); "
                   "o filtro fica inativo nesta aba — ver abas 2 e 5.")
    if anual:
        aviso_parcial(B)
    top = vols.sort_values(ascending=False).head(a).index
    cobertura = vols[top].sum() / vols.sum() * 100
    if anual:
        W = Mp[top].groupby(Mp.index.year).sum(min_count=1)
        T = tot.loc[d0:d1].groupby(tot.loc[d0:d1].index.year).sum()
    else:
        W, T = Mp[top], tot.loc[d0:d1]
    if vol.startswith("Percentual"):
        W = W.div(T, axis=0) * 100
    pct = vol.startswith("Percentual")
    with st.container(border=True):
        h1, h2 = st.columns([4, 1.4])
        h1.markdown(f"**Ranking de montadoras — Autos{' (totais anuais)' if anual else ''}**")
        periodo = (f"{W.index.min()}–{W.index.max()}{'*' if W.index.max() == parcial else ''}" if anual
                   else f"{rot_mes(d0)}–{rot_mes(d1)}")
        h1.caption(f"{'participação no total do segmento' if pct else 'emplacamentos'} "
                   f"{'por ano' if anual else 'por mês'}, {'%' if pct else 'unidades'} · {periodo}")
        h2.caption(f"a = {a} · cobre {fmt_pct(cobertura)} do volume do período")
        st.plotly_chart(fig_linhas(W, B["cores_marca"], pct=pct, anual=anual, parcial=parcial),
                        width="stretch", config={"displayModeBar": False})
    st.caption(f"{FONTE} Ranking de marcas tratado (fato_marca): rankings de Com. Leves e de Autos + Com. Leves "
               "rotulados como Autos foram separados; jan/2022 e alguns marca-mês ausentes foram estimados pela soma "
               "dos modelos da marca. O ranking mensal é Top-N (a lista de marcas varia mês a mês).")


def _filtra_modelos(mod, seg, canal, motor, d0, d1):
    s = mod[(mod.tipo_venda == CANAL[canal]) & (mod.data >= d0) & (mod.data <= d1)]
    if seg != "Ambos":
        s = s[s.segmento == seg]
    if motor != "Todas":
        s = s[s.propulsao == {"Combustão": "Combustão", "Híbrido (proxy)": "Híbrido",
                              "Elétrico (proxy)": "Elétrico"}[motor]]
    return s


def destaque_venda_direta(mod):
    """Venda direta em % do Total no Top 50 (Direta ÷ Total), por ano, sem meses estimados."""
    ok = mod[~mod.estimado]
    anos = sorted(ok.ano.unique())[-2:]
    out = []
    for ano in reversed(anos):
        s = ok[ok.ano == ano]
        g = s.groupby(["eletrificado", "tipo_venda"]).quantidade_mes.sum().unstack()
        for ele in (False, True):
            out.append((ano, ele, g.loc[ele, "Direta"] / g.loc[ele, "Total"] * 100))
    return out


def aba_modelos(B, anual):
    mod = B["mod"]
    tot = B["tot"]
    datas = sorted(mod.data.unique())
    parcial = None
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3.2, 1.6, 1.8, 1.4])
        with c1:
            if anual:
                dmax = tot.index.max()
                parcial = dmax.year if dmax.month < 12 else None
                anos = sorted(pd.DatetimeIndex(datas).year.unique())
                a0, a1 = controle_anos(anos, parcial, "mo_anos_a")
                d0, d1 = pd.Timestamp(a0, 1, 1), pd.Timestamp(a1, 12, 1)
            else:
                d0, d1 = controle_periodo([pd.Timestamp(d) for d in datas], "mo_per_m", padrao_meses=12,
                                          ajuda="Padrão: últimos 12 meses; pode voltar até jan/2022.")
        with c2:
            vol = escolha("Volume", ["Absoluto", "Percentual (%)"], "Absoluto", f"mo_vol_{anual}")
        with c3:
            canal = escolha("Vendas", ["Diretas", "Varejo", "Todas"], "Todas", f"mo_vnd_{anual}")
        with c4:
            b = st.number_input("Modelos (b)", min_value=1, max_value=50, value=10, step=1, key=f"mo_b_{anual}",
                                help="Padrão fixo: b = 10.")
        c5, c6, _ = st.columns([2.2, 3.4, 2.3])
        with c5:
            seg = escolha("Categoria (segmento)", ["Autos", "Com. Leves", "Ambos"], "Ambos", f"mo_seg_{anual}")
        with c6:
            motor = escolha("Motorização", ["Combustão", "Híbrido (proxy)", "Elétrico (proxy)", "Todas"], "Todas",
                            f"mo_mot_{anual}", ajuda="Classificação por modelo é estimativa (proxy): a Fenabrave "
                                                     "não publica a propulsão por modelo.")
        st.caption("Categoria/segmento e vendas Direta·Varejo·Total só coexistem em fato_modelo (Autos + Com. Leves). "
                   "Caminhões, Ônibus e Motos não têm ranking de modelo.")
    if anual:
        aviso_parcial(B)
        with st.container(border=True):
            d1c, *cols = st.columns([2.6, 1, 1, 1, 1])
            d1c.markdown("**Destaque · venda direta (frotistas, locadoras, PcD etc.) em % do total do Top 50**")
            d1c.caption("Eletrificados dependem muito menos da venda direta do que os modelos a combustão. "
                        "Proxy: modelos eletrificados mapeados manualmente; 2024 omitido (meses estimados sem "
                        "Direta/Varejo).")
            for col, (ano, ele, v) in zip(cols, destaque_venda_direta(mod)):
                cor = COR_ELETRIFICADO if ele else COR_COMBUSTAO_MODELO
                rot = f"{ano}{'*' if ano == parcial else ''} · {'Eletrificados (proxy)' if ele else 'Combustão'}"
                col.markdown(f"<span style='color:{cor}'>■</span> <span style='font-size:0.85em'>{rot}</span><br>"
                             f"<span style='font-size:1.9em;font-weight:700'>{fmt_pct(v, 0)}</span>",
                             unsafe_allow_html=True)
    s = _filtra_modelos(mod, seg, canal, motor, d0, d1)
    if s.empty:
        st.info("Nenhum modelo para a combinação de filtros escolhida.")
        return
    P = s.pivot_table(index="data", columns="modelo", values="quantidade_mes", aggfunc="sum").sort_index()
    top = P.sum().sort_values(ascending=False).head(b).index
    segs = ["Autos", "Com. Leves"] if seg == "Ambos" else [seg]
    T = tot.loc[d0:d1, segs].sum(axis=1)
    if anual:
        W = P[top].groupby(P.index.year).sum(min_count=1)
        T = T.groupby(T.index.year).sum()
    else:
        W = P[top]
    pct = vol.startswith("Percentual")
    if pct:
        W = W.div(T, axis=0) * 100
    ele = s.drop_duplicates("modelo").set_index("modelo").eletrificado
    W.columns = [nome_modelo(m) for m in W.columns]
    cores = {nome_modelo(m): (COR_ELETRIFICADO if ele[m] else COR_COMBUSTAO_MODELO) for m in top}
    with st.container(border=True):
        h1, h2 = st.columns([4, 1])
        seg_txt = "Autos + Com. Leves" if seg == "Ambos" else seg
        h1.markdown(f"**Ranking de modelos — {seg_txt}{' (totais anuais)' if anual else ''}**")
        periodo = (f"{W.index.min()}–{W.index.max()}{'*' if W.index.max() == parcial else ''}" if anual
                   else f"{rot_mes(d0)}–{rot_mes(d1)}")
        h1.caption(f"{'participação no total do segmento' if pct else 'emplacamentos'} "
                   f"{'por ano' if anual else 'por mês'} · vendas: {canal.lower()} · {periodo}")
        h1.markdown(f"<span style='color:{COR_ELETRIFICADO}'>■</span> Eletrificado (proxy) &nbsp; "
                    f"<span style='color:{COR_COMBUSTAO_MODELO}'>■</span> Combustão", unsafe_allow_html=True)
        h2.caption(f"b = {b}")
        if anual and motor == "Todas" and not any(ele[m] for m in top):
            todos = (_filtra_modelos(mod, seg, canal, "Todas", d0, d1).groupby("modelo").quantidade_mes.sum()
                     .sort_values(ascending=False))
            pos = [i + 1 for i, m in enumerate(todos.index) if ele.get(m, False)]
            if pos:
                h1.caption(f"Nenhum eletrificado no Top {b} do período; o 1º é "
                           f"{nome_modelo(todos.index[pos[0] - 1])} ({pos[0]}º). Com período mais recente ou b maior, "
                           f"ele aparece em verde.")
        st.plotly_chart(fig_linhas(W, cores, pct=pct, anual=anual, parcial=parcial),
                        width="stretch", config={"displayModeBar": False})
    st.caption(f"{FONTE} Ranking de modelos tratado (fato_modelo, Top 50). Estimados: set/2023 e jan/2024 (só havia "
               "ranking de Varejo; Total = Varejo × razão Total/Varejo do modelo) e abr/2024 (média de mar e mai), "
               "calibrados pela cobertura típica do Top 50. Nesses meses não há Direta/Varejo. Classificação "
               "eletrificado/combustão por modelo é proxy manual (BYD, GWM Ora/Haval H6, Geely EX, Leapmotor, "
               "Volvo EX, JAC EJV/IEV); nameplates mistos (ex.: Toyota Corolla Cross) ficam como combustão.")


def aba_propulsao_mensal(B):
    with st.container(border=True):
        c1, c2 = st.columns([3, 3])
        with c1:
            seg = escolha("Categoria (segmento)", SEGMENTOS_PROPULSAO, "Autos", "p_seg_m")
        df = propulsao_mensal(B, seg)
        with c1:
            d0, d1 = controle_periodo(list(df.index), "p_per_m",
                                      ajuda="A série oficial de eletrificados só existe a partir de jan/2024.")
        with c2:
            series = st.pills("Séries de motorização (selecionáveis)", TIPOS, selection_mode="multi",
                              default=TIPOS, key="p_ser_m") or TIPOS
        st.caption("Sem subdivisão de híbridos (mild/plug-in): a Fenabrave publica só 'Híbridos' e 'Elétricos'. "
                   "Combustão = total do segmento − híbridos − elétricos.")
    df = df.loc[d0:d1]
    P = df[TIPOS].div(df["Total"], axis=0) * 100
    with st.container(border=True):
        st.markdown(f"**Emplacamentos por tipo de motorização — {seg}**")
        st.caption(f"volume mensal, unidades · áreas empilhadas · {rot_mes(d0)}–{rot_mes(d1)}")
        st.plotly_chart(fig_area(df, series), width="stretch", config={"displayModeBar": False})
    c1, c2 = st.columns([1.4, 1])
    with c1, st.container(border=True):
        st.markdown(f"**Participação (%) por tipo de motorização — {seg}**")
        st.caption("% do total mensal do segmento · área 100% empilhada")
        st.plotly_chart(fig_area(P, series, pct=True, altura=330), width="stretch", config={"displayModeBar": False})
    with c2, st.container(border=True):
        u = P.iloc[-1]
        p0 = P.iloc[0]
        st.markdown("**Como ler esta aba**")
        st.markdown(
            f"- Áreas empilhadas com as 3 séries de motorização; qualquer uma pode ser desmarcada "
            f"(ex.: comparar só Híbridos × Elétricos).\n"
            f"- O seletor de categoria troca o segmento (Autos, Com. Leves, Caminhões, Ônibus, Motos), todos "
            f"disponíveis em fato_eletrificados_resumo.\n"
            f"- Combustão é residual (total − híbridos − elétricos).\n"
            f"- {rot_mes(df.index[-1])} ({seg}): Elétricos {fmt_pct(u['Elétricos'])}, Híbridos "
            f"{fmt_pct(u['Híbridos'])}, Combustão {fmt_pct(u['Combustão'])} do mercado "
            f"(em {rot_mes(df.index[0])}: eletrificados {fmt_pct(p0['Híbridos'] + p0['Elétricos'])}).")
    st.caption(f"{FONTE} Tabelas fato_resumo_segmento e fato_eletrificados_resumo (publicado desde jan/2024).")


def aba_propulsao_anual(B):
    tot = B["tot"]
    dmax = tot.index.max()
    parcial = dmax.year if dmax.month < 12 else None
    anos = sorted(tot.index.year.unique())
    with st.container(border=True):
        c1, c2 = st.columns([3, 3])
        with c1:
            a0, a1 = controle_anos(anos, parcial, "p_anos_a",
                                   ajuda="2022–2023: só o total do segmento (sem divisão por propulsão na fonte).")
        with c2:
            seg = escolha("Categoria (segmento)", SEGMENTOS_PROPULSAO, "Autos", "p_seg_a")
        c3, c4 = st.columns([3, 3])
        with c3:
            series = st.pills("Séries de motorização (selecionáveis)", TIPOS, selection_mode="multi",
                              default=TIPOS, key="p_ser_a") or TIPOS
        with c4:
            escolha("Vendas", ["Diretas", "Varejo", "Todas"], "Todas", "p_vnd_a", desabilitado=True,
                    ajuda="Desabilitado: a fonte não separa eletrificados por canal de venda.")
        st.caption("Sem subdivisão de híbridos (mild/plug-in) na fonte. Combustão = total do segmento − híbridos − "
                   "elétricos.")
    aviso_parcial(B, extra=" · 2022–2023: a Fenabrave não publicava eletrificados (seção criada em jan/2024).")
    df = propulsao_mensal(B, seg)
    A = df.groupby(df.index.year).sum()
    A = A.loc[a0:a1]
    total_seg = tot[seg].groupby(tot.index.year).sum().loc[a0:a1]
    sem = total_seg[total_seg.index < (A.index.min() if len(A) else a1 + 1)]
    P = A[TIPOS].div(A["Total"], axis=0) * 100
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown(f"**Emplacamentos por motorização — {seg} (totais anuais)**")
        st.caption(f"unidades por ano · áreas empilhadas{f' · {parcial}* = jan–{MESES[dmax.month - 1]}' if parcial else ''}")
        st.plotly_chart(fig_area(A, series, anual=True, parcial=parcial, sem_divisao=sem, altura=430),
                        width="stretch", config={"displayModeBar": False})
    with c2, st.container(border=True):
        st.markdown(f"**Participação por motorização — {seg} (anual)**")
        st.caption(f"% do total do ano · área 100% empilhada{f' · {parcial}* = jan–{MESES[dmax.month - 1]}' if parcial else ''}")
        st.plotly_chart(fig_area(P, series, pct=True, anual=True, parcial=parcial, sem_divisao=sem, altura=430),
                        width="stretch", config={"displayModeBar": False})
    linhas = []
    for ano, t in total_seg.items():
        r = A.loc[ano] if ano in A.index else None
        linhas.append({
            "Ano": f"{ano}*" if ano == parcial else str(ano),
            "Combustão": fmt_int(r["Combustão"]) if r is not None else "—",
            "Híbridos": fmt_int(r["Híbridos"]) if r is not None else "—",
            "Elétricos": fmt_int(r["Elétricos"]) if r is not None else "—",
            "Total": fmt_int(t),
            "Eletrificados (%)": fmt_pct((r["Híbridos"] + r["Elétricos"]) / r["Total"] * 100) if r is not None
            else "sem série oficial",
        })
    with st.container(border=True):
        st.markdown("**Totais do período**")
        st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    st.caption(f"{FONTE} fato_resumo_segmento (tratado) e fato_eletrificados_resumo (publicado desde jan/2024)."
               f"{f' {parcial}* = jan–{MESES[dmax.month - 1]}.' if parcial else ''}")


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
B = dados()
st.title("Painel Fenabrave — Eletrificados no Brasil (2022–2026)")
st.caption(f"Emplacamentos Fenabrave (Informativo) · dados até {rot_mes(B['tot'].index.max())} · Grupo 08 · "
           "PI Desenvolvimento Low Code em Ciência de Dados · Senac EAD ADS")

abas = st.tabs(["1 · Montadoras (mensal)", "2 · Modelos (mensal)", "3 · Propulsão (mensal)",
                "4 · Montadoras (anual)", "5 · Modelos (anual)", "6 · Propulsão (anual)"])
with abas[0]:
    aba_montadoras(B, anual=False)
with abas[1]:
    aba_modelos(B, anual=False)
with abas[2]:
    aba_propulsao_mensal(B)
with abas[3]:
    aba_montadoras(B, anual=True)
with abas[4]:
    aba_modelos(B, anual=True)
with abas[5]:
    aba_propulsao_anual(B)

with st.expander("Tratamento aplicado à base (log)"):
    st.markdown("\n".join(f"- {linha}" for linha in B["log"]))
