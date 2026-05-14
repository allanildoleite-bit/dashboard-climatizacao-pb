
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================

BASE_GERAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=2023176344&single=true&output=csv"
SETORIZACAO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=1839503437&single=true&output=csv"

# Tempo de sincronização.
# A versão anterior atualizava a página inteira a cada 10s, causando o "pisca".
# Agora só o bloco do dashboard é reexecutado, e com intervalo maior.
REFRESH_SECONDS = 60


# ============================================================
# PALETA
# ============================================================

AZUL_NOITE = "#001F49"
AZUL_ESCURO = "#003B73"
AZUL_MEDIO = "#1F77D0"
AZUL_CLARO = "#5DA7F2"
AZUL_GELO = "#EAF4FF"
VERMELHO = "#EF4444"
VERMELHO_ESCURO = "#B91C1C"
FUNDO = "#F3F7FB"
BRANCO = "#FFFFFF"
BORDA = "#D9E4F2"
TEXTO = "#1E2F47"
TEXTO_SUAVE = "#637083"
CINZA_BARRA = "#E8EEF6"


# ============================================================
# CONFIGURAÇÃO STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Painel de Climatização Escolar PB",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
<style>
.stApp {{
    background: {FUNDO};
    color: {TEXTO};
}}

.block-container {{
    max-width: 1780px;
    padding-top: 0.55rem;
    padding-left: 1.15rem;
    padding-right: 1.15rem;
    padding-bottom: 1.2rem;
}}

[data-testid="stSidebar"] {{
    background: {BRANCO};
}}

[data-testid="stToolbar"] {{
    visibility: hidden;
    height: 0%;
    position: fixed;
}}

div[data-testid="stDecoration"] {{
    visibility: hidden;
    height: 0%;
}}

.header {{
    background:
      radial-gradient(circle at 0% 0%, rgba(93,167,242,.28), transparent 28%),
      linear-gradient(90deg, {AZUL_NOITE} 0%, {AZUL_ESCURO} 52%, #0059A8 100%);
    color: {BRANCO};
    min-height: 124px;
    padding: 23px 34px;
    border-radius: 0 0 22px 22px;
    margin: -0.55rem -0.25rem 18px -0.25rem;
    box-shadow: 0 15px 36px rgba(0, 31, 73, .23);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.header-left {{
    display: flex;
    align-items: center;
    gap: 24px;
}}

.logo-card {{
    width: 92px;
    height: 92px;
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,.38);
    background: rgba(255,255,255,.08);
    display: grid;
    place-items: center;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
}}

.logo-school {{
    font-size: 35px;
    font-weight: 900;
    letter-spacing: -1px;
}}

.header-title {{
    font-size: 35px;
    font-weight: 950;
    line-height: 1.04;
    letter-spacing: -0.9px;
    text-transform: uppercase;
}}

.header-subtitle {{
    margin-top: 10px;
    font-size: 16px;
    opacity: .94;
    font-weight: 650;
}}

.map-card {{
    width: 155px;
    height: 72px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,.40);
    background: rgba(255,255,255,.07);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 3px;
}}

.map-card .pb {{
    font-size: 30px;
    font-weight: 950;
    line-height: 1;
}}

.map-card .txt {{
    font-size: 12px;
    opacity: .88;
    font-weight: 700;
}}

.filters {{
    display: grid;
    grid-template-columns: 220px 220px 220px 1fr;
    gap: 14px;
    margin-bottom: 16px;
}}

.filter-card {{
    background: {BRANCO};
    border: 1px solid {BORDA};
    border-radius: 15px;
    padding: 12px 18px;
    box-shadow: 0 8px 22px rgba(10,40,80,.075);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.filter-card .info small {{
    color: {TEXTO_SUAVE};
    font-size: 12px;
    font-weight: 750;
    display: block;
}}

.filter-card .info b {{
    color: {AZUL_ESCURO};
    font-size: 19px;
    font-weight: 900;
}}

.update-card {{
    background: linear-gradient(90deg, #FFFFFF, #F6FAFF);
    border: 1px solid {BORDA};
    border-radius: 15px;
    padding: 12px 18px;
    box-shadow: 0 8px 22px rgba(10,40,80,.075);
    display: flex;
    justify-content: flex-end;
    align-items: center;
    color: {TEXTO_SUAVE};
    font-size: 13px;
    font-weight: 750;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 16px;
}}

.kpi {{
    background: {BRANCO};
    border: 1px solid {BORDA};
    border-radius: 20px;
    min-height: 136px;
    padding: 20px 22px;
    box-shadow: 0 10px 24px rgba(10,40,80,.08);
    position: relative;
    overflow: hidden;
}}

.kpi:before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 7px;
    background: var(--accent);
}}

.kpi:after {{
    content: "";
    position: absolute;
    right: -25px;
    bottom: -42px;
    width: 150px;
    height: 90px;
    border-radius: 50%;
    background: var(--wash);
}}

.kpi-label {{
    color: #25364F;
    font-size: 15px;
    font-weight: 850;
    margin-left: 8px;
    position: relative;
    z-index: 2;
}}

.kpi-value {{
    color: var(--accent);
    font-size: 51px;
    line-height: 1;
    letter-spacing: -1.6px;
    font-weight: 950;
    margin: 10px 0 0 8px;
    position: relative;
    z-index: 2;
}}

.kpi-sub {{
    color: {TEXTO_SUAVE};
    font-size: 15px;
    font-weight: 750;
    margin: 9px 0 0 8px;
    position: relative;
    z-index: 2;
}}

.main-grid {{
    display: grid;
    grid-template-columns: 1.36fr 1.10fr .82fr;
    gap: 16px;
    align-items: stretch;
}}

.bottom-grid {{
    display: grid;
    grid-template-columns: 1.05fr 1.45fr;
    gap: 16px;
    margin-top: 16px;
}}

.panel {{
    background: {BRANCO};
    border: 1px solid {BORDA};
    border-radius: 20px;
    box-shadow: 0 10px 24px rgba(10,40,80,.08);
    height: 100%;
}}

.panel-padding {{
    padding: 18px;
}}

.section-title {{
    background: linear-gradient(90deg, {AZUL_NOITE}, #0059A8);
    color: {BRANCO};
    padding: 11px 18px;
    border-radius: 20px 20px 0 0;
    font-size: 17px;
    font-weight: 950;
    letter-spacing: .2px;
    text-transform: uppercase;
}}

.panel-body {{
    padding: 18px;
}}

.chart-title {{
    color: {AZUL_ESCURO};
    font-size: 18px;
    font-weight: 950;
    margin-bottom: 6px;
}}

.big-progress {{
    color: {AZUL_ESCURO};
    font-size: 46px;
    font-weight: 950;
    line-height: 1;
    letter-spacing: -1.2px;
    margin-top: 8px;
}}

.big-progress span {{
    color: {TEXTO_SUAVE};
    font-size: 18px;
    font-weight: 650;
    letter-spacing: 0;
}}

.progress-track {{
    margin-top: 17px;
    width: 100%;
    height: 38px;
    background: {CINZA_BARRA};
    border: 1px solid #D6E2EF;
    border-radius: 999px;
    overflow: hidden;
}}

.progress-fill {{
    height: 100%;
    width: var(--progress);
    border-radius: 999px;
    background: linear-gradient(90deg, {AZUL_NOITE}, #005FB8);
}}

.progress-labels {{
    display: flex;
    justify-content: space-between;
    margin-top: 7px;
    color: #516174;
    font-size: 13px;
    font-weight: 800;
}}

.info-box {{
    background: #F2F7FD;
    border: 1px solid #D9E8FA;
    border-radius: 15px;
    padding: 14px 16px;
    color: #1D3557;
    font-size: 15px;
    font-weight: 750;
    margin-top: 28px;
}}

.info-box strong {{
    color: {AZUL_ESCURO};
}}

.alert-box {{
    background: #FFF0F0;
    border: 1px solid #FECACA;
    color: {VERMELHO_ESCURO};
    border-radius: 15px;
    padding: 14px 15px;
    font-size: 14px;
    font-weight: 800;
    margin-top: 14px;
}}

.summary-line {{
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 12px;
    align-items: center;
    padding: 11px 0;
    border-bottom: 1px dashed #C7D6E8;
    color: #1C3556;
    font-size: 15px;
    font-weight: 750;
}}

.check-dot {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: {AZUL_MEDIO};
}}

.sector-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-top: 4px;
}}

.sector-card {{
    border: 1px solid {BORDA};
    border-radius: 15px;
    overflow: hidden;
    background: {BRANCO};
    box-shadow: 0 6px 16px rgba(10,40,80,.07);
}}

.sector-head {{
    background: linear-gradient(90deg, {AZUL_NOITE}, {AZUL_MEDIO});
    color: white;
    padding: 11px 14px;
    text-align: center;
    font-weight: 950;
    text-transform: uppercase;
}}

.sector-row {{
    display: flex;
    justify-content: space-between;
    padding: 11px 16px;
    border-top: 1px solid #EBF1F8;
    font-size: 15px;
    font-weight: 850;
}}

.footer {{
    text-align: center;
    color: #40516A;
    margin-top: 16px;
    font-size: 13px;
    font-weight: 650;
}}

@media(max-width: 1200px) {{
    .header {{
        display: block;
    }}
    .map-card {{
        margin-top: 15px;
    }}
    .filters, .kpi-grid, .main-grid, .bottom-grid, .visao-grid, .sector-grid {{
        grid-template-columns: 1fr;
    }}
    .header-title {{
        font-size: 25px;
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
def carregar_csv(url: str) -> pd.DataFrame:
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
    df["Conclusão"] = df["Climatizadas"] / df["Total"]
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


def renderizar_dashboard():
    try:
        base_geral = tratar_base_geral(carregar_csv(BASE_GERAL_URL))
        setorizacao = tratar_setorizacao(carregar_csv(SETORIZACAO_URL))
    except Exception as erro:
        st.error("Não consegui ler os dados publicados no Google Sheets. Verifique se as abas continuam publicadas.")
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

    gre_mais_pendente = base_geral.sort_values("Pendências", ascending=False).iloc[0]
    gre_melhor_conclusao = base_geral.sort_values("Conclusão", ascending=False).iloc[0]
    ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Filtros e status de atualização
    st.markdown(
        f"""
    <div class="filters">
        <div class="filter-card"><div class="info"><small>Período</small><b>2026</b></div><span>▾</span></div>
        <div class="filter-card"><div class="info"><small>GRE</small><b>Todas</b></div><span>▾</span></div>
        <div class="filter-card"><div class="info"><small>Visão</small><b>Geral</b></div><span>▾</span></div>
        <div class="update-card">Sincronizado: {ultima_atualizacao} · Verificação a cada {REFRESH_SECONDS}s</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # KPIs
    st.markdown(
        f"""
    <div class="kpi-grid">
        <div class="kpi" style="--accent:{AZUL_ESCURO};--wash:{AZUL_GELO};">
            <div class="kpi-label">Total de Escolas</div>
            <div class="kpi-value">{fmt_num(total)}</div>
            <div class="kpi-sub">Base consolidada das GREs</div>
        </div>
        <div class="kpi" style="--accent:{AZUL_ESCURO};--wash:{AZUL_GELO};">
            <div class="kpi-label">Climatizadas</div>
            <div class="kpi-value">{fmt_num(climatizadas)}</div>
            <div class="kpi-sub">{fmt_pct(pct_climatizadas)} do total</div>
        </div>
        <div class="kpi" style="--accent:{AZUL_CLARO};--wash:#EDF6FF;">
            <div class="kpi-label">Em Andamento</div>
            <div class="kpi-value">{fmt_num(andamento)}</div>
            <div class="kpi-sub">{fmt_pct(pct_andamento)} do total</div>
        </div>
        <div class="kpi" style="--accent:{VERMELHO};--wash:#FFF1F1;">
            <div class="kpi-label">Em Rota</div>
            <div class="kpi-value">{fmt_num(rota)}</div>
            <div class="kpi-sub">{fmt_pct(pct_rota)} do total</div>
        </div>
        <div class="kpi" style="--accent:{AZUL_ESCURO};--wash:{AZUL_GELO};">
            <div class="kpi-label">Conclusão</div>
            <div class="kpi-value">{fmt_pct(pct_climatizadas)}</div>
            <div class="kpi-sub">Progresso geral</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Gráficos
    fig_donut = go.Figure(
        data=[
            go.Pie(
                labels=["Climatizadas", "Em andamento", "Em rota"],
                values=[climatizadas, andamento, rota],
                hole=0.62,
                sort=False,
                marker=dict(colors=[AZUL_ESCURO, AZUL_CLARO, VERMELHO], line=dict(color="white", width=3)),
                textinfo="percent",
                textfont=dict(color="white", size=14, family="Arial"),
            )
        ]
    )

    fig_donut.update_layout(
        height=312,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, x=0.02, font=dict(size=12, color="#24364F")),
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
        text=base_geral["Climatizadas"].astype(int),
        textposition="inside",
        insidetextfont=dict(color="white", size=12),
    )
    fig_gre.add_bar(
        name="Em andamento",
        x=base_geral["GRE"],
        y=base_geral["Em andamento"],
        marker_color=AZUL_CLARO,
        text=base_geral["Em andamento"].astype(int),
        textposition="inside",
        insidetextfont=dict(color="white", size=12),
    )
    fig_gre.add_bar(
        name="Em rota",
        x=base_geral["GRE"],
        y=base_geral["Em rota"],
        marker_color=VERMELHO,
        text=base_geral["Em rota"].astype(int),
        textposition="inside",
        insidetextfont=dict(color="white", size=12),
    )

    fig_gre.update_layout(
        barmode="stack",
        height=390,
        margin=dict(l=10, r=10, t=35, b=20),
        legend=dict(orientation="h", y=1.08, x=0.08, font=dict(size=12)),
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

    # Bloco principal com colunas nativas do Streamlit para evitar problemas de HTML aninhado
    col1, col2, col3 = st.columns([1.36, 1.10, .82], gap="medium")

    with col1:
        st.markdown('<div class="panel"><div class="section-title">Visão Geral da Climatização</div><div class="panel-body">', unsafe_allow_html=True)
        a, b = st.columns([0.95, 1.05])
        with a:
            st.markdown('<div class="chart-title">Status Geral</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                f"""
                <div style="font-size:13px;font-weight:850;color:#24364F;text-align:center;margin-top:-8px;">
                Total de Escolas: {fmt_num(total)}
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b:
            st.markdown('<div class="chart-title">Progresso Geral</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="big-progress">{fmt_pct(pct_climatizadas)} <span>concluído</span></div>
                <div class="progress-track"><div class="progress-fill" style="--progress:{pct_climatizadas*100:.1f}%;"></div></div>
                <div class="progress-labels"><span>0%</span><span>100%</span></div>
                <div class="info-box"><strong>{fmt_num(climatizadas)}</strong> escolas já foram climatizadas. Restam <strong>{fmt_num(pendencias)}</strong> em andamento ou em rota.</div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="panel panel-padding"><div class="chart-title">Panorama por GRE</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_gre, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"""
            <div class="info-box">
            A GRE com maior volume de pendências é <strong>{gre_mais_pendente["GRE"]}</strong>, com <strong>{fmt_num(gre_mais_pendente["Pendências"])}</strong> escolas em andamento ou em rota.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown('<div class="panel panel-padding"><div class="chart-title">Ranking de Pendências</div><div style="font-size:13px;color:#516174;font-weight:750;">Total em andamento + em rota</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            """
            <div class="alert-box">
            Priorize as GREs com maior volume de pendências para acelerar a conclusão.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    bottom1, bottom2 = st.columns([1.05, 1.45], gap="medium")

    with bottom1:
        st.markdown('<div class="panel panel-padding"><div class="chart-title">Resumo Executivo</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="summary-line"><span class="check-dot"></span><span>Mais da metade das escolas já está climatizada.</span></div>
            <div class="summary-line"><span class="check-dot"></span><span>A GRE com maior pendência é <strong>{gre_mais_pendente["GRE"]}</strong>.</span></div>
            <div class="summary-line"><span class="check-dot"></span><span>A maior conclusão proporcional está em <strong>{gre_melhor_conclusao["GRE"]}</strong>.</span></div>
            <div class="summary-line"><span class="check-dot"></span><span>A setorização deve ser acompanhada separadamente do total geral.</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with bottom2:
        st.markdown('<div class="panel"><div class="section-title">Quadro de Status por Setorização</div><div class="panel-body">', unsafe_allow_html=True)
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
        st.markdown('</div></div>', unsafe_allow_html=True)

    with st.expander("Ver tabela detalhada por GRE"):
        tabela = base_geral.copy()
        tabela["Conclusão"] = tabela["Conclusão"].apply(fmt_pct)
        tabela = tabela[["GRE", "Total", "Climatizadas", "Em andamento", "Em rota", "Pendências", "Conclusão"]]
        st.dataframe(tabela, use_container_width=True, hide_index=True)


# ============================================================
# CABEÇALHO FIXO
# ============================================================

st.markdown(
    """
<div class="header">
    <div class="header-left">
        <div class="logo-card"><div class="logo-school">PB</div></div>
        <div>
            <div class="header-title">Painel de Monitoramento da Climatização Escolar na Paraíba</div>
            <div class="header-subtitle">Acompanhamento consolidado por GRE e setorização</div>
        </div>
    </div>
    <div class="map-card">
        <div class="pb">PB</div>
        <div class="txt">Paraíba</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# ATUALIZAÇÃO SEM PISCAR A PÁGINA INTEIRA
# ============================================================

# st.fragment faz apenas esta área do painel ser reexecutada periodicamente.
# Assim evita a sensação de "pisca" causada pelo refresh da página inteira.
if hasattr(st, "fragment"):
    @st.fragment(run_every=f"{REFRESH_SECONDS}s")
    def dashboard_fragment():
        renderizar_dashboard()

    dashboard_fragment()
else:
    # Fallback para versões antigas do Streamlit.
    renderizar_dashboard()

st.markdown(
    """
<div class="footer">
Os dados apresentados são consolidados com base nas informações enviadas pelas GREs e órgãos executores.
</div>
""",
    unsafe_allow_html=True,
)
