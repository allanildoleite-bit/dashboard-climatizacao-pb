
from __future__ import annotations

from datetime import datetime
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


# ============================================================
# LINKS DA SUA PLANILHA PUBLICADA
# ============================================================

BASE_GERAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=2023176344&single=true&output=csv"
SETORIZACAO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=1839503437&single=true&output=csv"

# Atualiza a cada 10 segundos.
REFRESH_SECONDS = 10


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Climatização Escolar PB",
    layout="wide",
    initial_sidebar_state="collapsed",
)

AZUL_ESCURO = "#003B73"
AZUL_PROFUNDO = "#002B5C"
AZUL_MEDIO = "#1F77D0"
AZUL_CLARO = "#5DA7F2"
VERMELHO = "#EF4444"
FUNDO = "#F3F7FB"
TEXTO = "#1E2F47"
BORDA = "#DDE7F2"

if st_autorefresh is not None:
    st_autorefresh(interval=REFRESH_SECONDS * 1000, key="atualizacao_automatica")


# ============================================================
# VISUAL / CSS
# ============================================================

st.markdown(
    f"""
<style>
.stApp {{
    background: {FUNDO};
    color: {TEXTO};
}}

.block-container {{
    max-width: 1760px;
    padding-top: 0.6rem;
    padding-bottom: 1.2rem;
}}

[data-testid="stSidebar"] {{
    background: #FFFFFF;
    border-right: 1px solid #E5EDF6;
}}

.header {{
    background: linear-gradient(90deg, {AZUL_PROFUNDO} 0%, {AZUL_ESCURO} 55%, #00539D 100%);
    color: white;
    padding: 26px 34px;
    border-radius: 0 0 20px 20px;
    margin: -0.6rem -0.3rem 18px -0.3rem;
    box-shadow: 0 12px 30px rgba(0, 43, 92, .18);
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.header-title {{
    font-size: 35px;
    line-height: 1.06;
    font-weight: 900;
    letter-spacing: -0.8px;
    text-transform: uppercase;
}}

.header-sub {{
    margin-top: 10px;
    font-size: 16px;
    font-weight: 600;
    opacity: .94;
}}

.pb-map {{
    width: 150px;
    height: 72px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(255,255,255,.38);
    border-radius: 18px;
    font-size: 28px;
    font-weight: 900;
    opacity: .86;
}}

.filters {{
    display: grid;
    grid-template-columns: 220px 220px 220px;
    gap: 14px;
    margin-bottom: 16px;
}}

.filter-card {{
    background: white;
    border: 1px solid {BORDA};
    border-radius: 14px;
    padding: 12px 18px;
    box-shadow: 0 8px 22px rgba(10, 40, 80, .08);
}}

.filter-label {{
    color: #667085;
    font-size: 12px;
    font-weight: 700;
}}

.filter-value {{
    color: {AZUL_ESCURO};
    font-size: 19px;
    font-weight: 850;
    margin-top: 2px;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 16px;
}}

.kpi {{
    background: #FFFFFF;
    border: 1px solid {BORDA};
    border-radius: 18px;
    padding: 20px 22px;
    min-height: 128px;
    box-shadow: 0 8px 22px rgba(10, 40, 80, .08);
    position: relative;
    overflow: hidden;
}}

.kpi::before {{
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 7px;
    background: var(--accent);
}}

.kpi-title {{
    font-size: 15px;
    font-weight: 800;
    color: #24364F;
    margin-left: 8px;
}}

.kpi-value {{
    font-size: 50px;
    font-weight: 950;
    color: var(--accent);
    letter-spacing: -1.3px;
    line-height: 1.05;
    margin: 8px 0 0 8px;
}}

.kpi-sub {{
    color: #667085;
    font-size: 15px;
    font-weight: 750;
    margin: 8px 0 0 8px;
}}

.panel {{
    background: #FFFFFF;
    border: 1px solid {BORDA};
    border-radius: 18px;
    box-shadow: 0 8px 22px rgba(10, 40, 80, .08);
    padding: 18px;
    height: 100%;
}}

.panel-tight {{
    padding: 0;
    overflow: hidden;
}}

.section-title {{
    background: linear-gradient(90deg, {AZUL_PROFUNDO}, #00539D);
    color: white;
    border-radius: 18px 18px 0 0;
    padding: 11px 18px;
    font-size: 17px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .2px;
}}

.panel-body {{
    padding: 18px;
}}

.chart-title {{
    color: {AZUL_ESCURO};
    font-size: 18px;
    font-weight: 900;
    margin-bottom: 6px;
}}

.big-progress {{
    color: {AZUL_ESCURO};
    font-size: 46px;
    font-weight: 950;
    letter-spacing: -1px;
    line-height: 1;
    margin-top: 10px;
}}

.big-progress span {{
    color: #5A687B;
    font-size: 18px;
    font-weight: 650;
}}

.progress-track {{
    background: #E8EEF6;
    border: 1px solid #D6E2EF;
    height: 38px;
    border-radius: 999px;
    margin-top: 17px;
    overflow: hidden;
}}

.progress-fill {{
    width: var(--progress);
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, {AZUL_PROFUNDO}, #005FB8);
}}

.progress-labels {{
    display: flex;
    justify-content: space-between;
    color: #516174;
    font-size: 13px;
    font-weight: 800;
    margin-top: 6px;
}}

.info-box {{
    background: #F2F7FD;
    border: 1px solid #D9E8FA;
    color: #1D3557;
    border-radius: 14px;
    padding: 14px 16px;
    font-weight: 750;
    font-size: 15px;
    margin-top: 28px;
}}

.alert-box {{
    background: #FFF0F0;
    color: #B91C1C;
    border: 1px solid #FECACA;
    border-radius: 14px;
    padding: 14px;
    font-size: 14px;
    font-weight: 750;
    margin-top: 14px;
}}

.summary-line {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px dashed #C7D6E8;
    font-weight: 750;
    color: #1C3556;
    font-size: 15px;
}}

.check-dot {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: {AZUL_MEDIO};
    flex: 0 0 auto;
}}

.sector-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-top: 6px;
}}

.sector-card {{
    border: 1px solid {BORDA};
    border-radius: 14px;
    overflow: hidden;
    background: #FFFFFF;
    box-shadow: 0 6px 16px rgba(10, 40, 80, .07);
}}

.sector-head {{
    background: linear-gradient(90deg, {AZUL_PROFUNDO}, {AZUL_MEDIO});
    color: white;
    padding: 11px 14px;
    text-align: center;
    font-weight: 900;
    text-transform: uppercase;
}}

.sector-row {{
    display: flex;
    justify-content: space-between;
    padding: 11px 16px;
    border-top: 1px solid #EBF1F8;
    font-size: 15px;
    font-weight: 800;
}}

.footer {{
    text-align: center;
    color: #40516A;
    margin-top: 16px;
    font-size: 13px;
    font-weight: 650;
}}

@media (max-width: 1200px) {{
    .kpi-grid, .filters {{
        grid-template-columns: 1fr;
    }}
    .header {{
        display: block;
    }}
    .header-title {{
        font-size: 25px;
    }}
    .pb-map {{
        margin-top: 18px;
    }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNÇÕES
# ============================================================

def fmt_num(valor: float | int) -> str:
    return f"{int(round(float(valor))):,}".replace(",", ".")


def fmt_pct(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def carregar_dados_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


def tratar_base_geral(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    colunas = ["GRE", "Climatizadas", "Em andamento", "Em rota"]
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        st.error("A aba Base_Geral precisa ter as colunas: GRE, Climatizadas, Em andamento e Em rota.")
        st.stop()

    for col in ["Climatizadas", "Em andamento", "Em rota"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[df[["Climatizadas", "Em andamento", "Em rota"]].sum(axis=1) > 0].copy()
    df["Total"] = df["Climatizadas"] + df["Em andamento"] + df["Em rota"]
    df["Pendências"] = df["Em andamento"] + df["Em rota"]
    return df


def tratar_setorizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    colunas = ["Setor", "Em andamento", "Rota de climatização", "Total"]
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        st.error("A aba Setorizacao precisa ter as colunas: Setor, Em andamento, Rota de climatização e Total.")
        st.stop()

    for col in ["Em andamento", "Rota de climatização", "Total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ============================================================
# LEITURA DOS DADOS
# ============================================================

try:
    base_geral = tratar_base_geral(carregar_dados_csv(BASE_GERAL_URL))
    setorizacao = tratar_setorizacao(carregar_dados_csv(SETORIZACAO_URL))
except Exception as erro:
    st.error("Não consegui ler os dados do Google Sheets. Confira se as abas continuam publicadas como CSV.")
    st.exception(erro)
    st.stop()

total = float(base_geral["Total"].sum())
climatizadas = float(base_geral["Climatizadas"].sum())
andamento = float(base_geral["Em andamento"].sum())
rota = float(base_geral["Em rota"].sum())
pendencias = andamento + rota

pct_climatizadas = climatizadas / total if total else 0
pct_andamento = andamento / total if total else 0
pct_rota = rota / total if total else 0

ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")


# ============================================================
# LAYOUT
# ============================================================

st.markdown(
    f"""
<div class="header">
    <div>
        <div class="header-title">Painel de Monitoramento da Climatização Escolar na Paraíba</div>
        <div class="header-sub">Última atualização do painel: {ultima_atualizacao}</div>
    </div>
    <div class="pb-map">PB</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="filters">
    <div class="filter-card"><div class="filter-label">Período</div><div class="filter-value">2026</div></div>
    <div class="filter-card"><div class="filter-label">GRE</div><div class="filter-value">Todas</div></div>
    <div class="filter-card"><div class="filter-label">Visão</div><div class="filter-value">Geral</div></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="kpi-grid">
    <div class="kpi" style="--accent:{AZUL_ESCURO};">
        <div class="kpi-title">Total de Escolas</div>
        <div class="kpi-value">{fmt_num(total)}</div>
        <div class="kpi-sub">Base consolidada</div>
    </div>
    <div class="kpi" style="--accent:{AZUL_ESCURO};">
        <div class="kpi-title">Climatizadas</div>
        <div class="kpi-value">{fmt_num(climatizadas)}</div>
        <div class="kpi-sub">{fmt_pct(pct_climatizadas)} do total</div>
    </div>
    <div class="kpi" style="--accent:{AZUL_CLARO};">
        <div class="kpi-title">Em Andamento</div>
        <div class="kpi-value">{fmt_num(andamento)}</div>
        <div class="kpi-sub">{fmt_pct(pct_andamento)} do total</div>
    </div>
    <div class="kpi" style="--accent:{VERMELHO};">
        <div class="kpi-title">Em Rota</div>
        <div class="kpi-value">{fmt_num(rota)}</div>
        <div class="kpi-sub">{fmt_pct(pct_rota)} do total</div>
    </div>
    <div class="kpi" style="--accent:{AZUL_ESCURO};">
        <div class="kpi-title">Conclusão</div>
        <div class="kpi-value">{fmt_pct(pct_climatizadas)}</div>
        <div class="kpi-sub">Progresso Geral</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# GRÁFICOS
# ============================================================

fig_donut = go.Figure(
    data=[
        go.Pie(
            labels=["Climatizadas", "Em andamento", "Em rota"],
            values=[climatizadas, andamento, rota],
            hole=0.62,
            sort=False,
            marker=dict(
                colors=[AZUL_ESCURO, AZUL_CLARO, VERMELHO],
                line=dict(color="white", width=3),
            ),
            textinfo="percent",
            textfont=dict(color="white", size=14),
        )
    ]
)
fig_donut.update_layout(
    height=310,
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=True,
    legend=dict(orientation="h", y=-0.04, x=0.02, font=dict(size=12)),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    annotations=[
        dict(
            text=f"<b>{fmt_pct(pct_climatizadas)}</b><br>Conclusão",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=22, color=AZUL_ESCURO),
        )
    ],
)

fig_gre = go.Figure()
fig_gre.add_bar(
    name="Climatizadas",
    x=base_geral["GRE"],
    y=base_geral["Climatizadas"],
    marker_color=AZUL_ESCURO,
    text=base_geral["Climatizadas"],
    textposition="inside",
)
fig_gre.add_bar(
    name="Em andamento",
    x=base_geral["GRE"],
    y=base_geral["Em andamento"],
    marker_color=AZUL_CLARO,
    text=base_geral["Em andamento"],
    textposition="inside",
)
fig_gre.add_bar(
    name="Em rota",
    x=base_geral["GRE"],
    y=base_geral["Em rota"],
    marker_color=VERMELHO,
    text=base_geral["Em rota"],
    textposition="inside",
)
fig_gre.update_layout(
    barmode="stack",
    height=375,
    margin=dict(l=10, r=10, t=35, b=20),
    legend=dict(orientation="h", y=1.08, x=0.1),
    yaxis=dict(gridcolor="#E4ECF5", zeroline=False),
    xaxis=dict(tickangle=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#24364F"),
)

ranking = base_geral.sort_values("Pendências", ascending=True).tail(8)
fig_rank = go.Figure(
    data=[
        go.Bar(
            x=ranking["Pendências"],
            y=ranking["GRE"],
            orientation="h",
            marker_color=AZUL_ESCURO,
            text=ranking["Pendências"].astype(int),
            textposition="outside",
            textfont=dict(color=VERMELHO, size=14),
        )
    ]
)
fig_rank.update_layout(
    height=330,
    margin=dict(l=10, r=35, t=10, b=10),
    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    yaxis=dict(showgrid=False),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#24364F"),
)


col1, col2, col3 = st.columns([1.35, 1.12, 0.82], gap="medium")

with col1:
    st.markdown(
        '<div class="panel panel-tight"><div class="section-title">Visão Geral da Climatização</div><div class="panel-body">',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([0.95, 1.05])
    with c1:
        st.markdown('<div class="chart-title">Status Geral</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"""
<div style="font-size:13px;font-weight:800;color:#24364F;text-align:center;margin-top:-8px;">
Total de Escolas: {fmt_num(total)}
</div>
""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown('<div class="chart-title">Progresso Geral</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="big-progress">{fmt_pct(pct_climatizadas)} <span>concluído</span></div>
<div class="progress-track"><div class="progress-fill" style="--progress:{pct_climatizadas*100:.1f}%;"></div></div>
<div class="progress-labels"><span>0%</span><span>100%</span></div>
<div class="info-box">Mais da metade das escolas já está climatizada.</div>
""",
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="panel"><div class="chart-title">Panorama por GRE</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_gre, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="info-box">As GREs com maior volume de pendências devem receber prioridade no acompanhamento.</div></div>', unsafe_allow_html=True)

with col3:
    st.markdown(
        '<div class="panel"><div class="chart-title">Ranking de Pendências</div><div style="font-size:13px;color:#516174;font-weight:750;">Total em andamento + em rota</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="alert-box">Priorize as GREs com maior volume de pendências para acelerar a conclusão.</div></div>', unsafe_allow_html=True)


bottom1, bottom2 = st.columns([1.05, 1.45], gap="medium")

with bottom1:
    st.markdown('<div class="panel"><div class="chart-title">Resumo Executivo</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="summary-line"><span class="check-dot"></span>Mais da metade das escolas já está climatizada.</div>
<div class="summary-line"><span class="check-dot"></span>A prioridade está nas GREs com maior volume em andamento e em rota.</div>
<div class="summary-line"><span class="check-dot"></span>A setorização deve ser acompanhada separadamente do total geral.</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with bottom2:
    st.markdown(
        '<div class="panel panel-tight"><div class="section-title">Quadro de Status por Setorização</div><div class="panel-body">',
        unsafe_allow_html=True,
    )
    cards = '<div class="sector-grid">'
    for _, row in setorizacao.iterrows():
        cards += f"""
<div class="sector-card">
    <div class="sector-head">{str(row["Setor"]).upper()}</div>
    <div class="sector-row"><span>Em andamento</span><span style="color:{AZUL_MEDIO};">{fmt_num(row["Em andamento"])}</span></div>
    <div class="sector-row"><span>Rota de climatização</span><span style="color:{VERMELHO};">{fmt_num(row["Rota de climatização"])}</span></div>
    <div class="sector-row"><span>Total</span><span style="color:{AZUL_ESCURO};">{fmt_num(row["Total"])}</span></div>
</div>
"""
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown(
    """
<div class="footer">
Os dados apresentados são consolidados com base nas informações enviadas pelas GREs e órgãos executores.
</div>
""",
    unsafe_allow_html=True,
)
