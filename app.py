
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# LINKS DA PLANILHA PUBLICADA
# ============================================================

BASE_GERAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=2023176344&single=true&output=csv"
SETORIZACAO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRd-tfclRRvEh9FKgC3IZUpZCRyJ5EnaTyqL40UbOHALao4BZanA0uD056YnXFbxw/pub?gid=1839503437&single=true&output=csv"

# Atualização sem "piscar" a página toda.
REFRESH_SECONDS = 60


# ============================================================
# CONFIGURAÇÃO DO STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Climatização Escolar PB",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .stApp {
        background: #F3F7FB;
    }

    .block-container {
        max-width: 1800px;
        padding-top: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
        padding-bottom: 0rem;
    }

    [data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    footer {
        visibility: hidden;
        height: 0;
    }

    iframe {
        display: block;
        width: 100%;
        border: 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LEITURA E TRATAMENTO DOS DADOS
# ============================================================

def numero_para_float(valor) -> float:
    """Converte números vindos do Google Sheets para float."""
    if pd.isna(valor):
        return 0.0

    texto = str(valor).strip()
    texto = texto.replace(" escolas", "").replace("ESCOLAS", "")
    texto = texto.replace(".", "").replace(",", ".")
    texto = re.sub(r"[^0-9.\-]", "", texto)

    if texto in ("", "-", "."):
        return 0.0

    try:
        return float(texto)
    except Exception:
        return 0.0


def padronizar_gre(valor: str) -> str | None:
    """Mantém apenas linhas de GRE real. Remove TOTAL, cabeçalhos e linhas duplicadas de resumo."""
    if pd.isna(valor):
        return None

    texto = str(valor).strip().upper()
    texto = texto.replace("º", "ª")

    if not texto or "TOTAL" in texto or "GERAL" in texto or "STATUS" in texto:
        return None

    match = re.search(r"(\d+)", texto)
    if not match:
        return None

    numero = int(match.group(1))
    if numero <= 0 or numero > 30:
        return None

    return f"{numero}ª GRE"


def tratar_base_geral(df: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    colunas_obrigatorias = ["GRE", "Climatizadas", "Em andamento", "Em rota"]
    faltando = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError("A aba Base_Geral precisa ter as colunas: GRE, Climatizadas, Em andamento e Em rota.")

    # Guarda a linha TOTAL, se existir, apenas para conferência dos KPIs.
    total_linha = None
    linhas_total = df[df["GRE"].astype(str).str.upper().str.contains("TOTAL", na=False)].copy()

    if not linhas_total.empty:
        ultima_total = linhas_total.iloc[-1]
        total_linha = {
            "Climatizadas": numero_para_float(ultima_total["Climatizadas"]),
            "Em andamento": numero_para_float(ultima_total["Em andamento"]),
            "Em rota": numero_para_float(ultima_total["Em rota"]),
        }
        total_linha["Total"] = total_linha["Climatizadas"] + total_linha["Em andamento"] + total_linha["Em rota"]

    for col in ["Climatizadas", "Em andamento", "Em rota"]:
        df[col] = df[col].apply(numero_para_float)

    df["GRE"] = df["GRE"].apply(padronizar_gre)
    df = df[df["GRE"].notna()].copy()

    # Remove linhas vazias e duplicadas exatas.
    df = df[df[["Climatizadas", "Em andamento", "Em rota"]].sum(axis=1) > 0].copy()
    df = df.drop_duplicates(subset=["GRE", "Climatizadas", "Em andamento", "Em rota"])

    # Se a mesma GRE aparecer mais de uma vez por causa da publicação do Google Sheets,
    # usa o maior valor de cada coluna, evitando somar duplicatas.
    df = (
        df.groupby("GRE", as_index=False)
        .agg({
            "Climatizadas": "max",
            "Em andamento": "max",
            "Em rota": "max",
        })
    )

    df["ordem"] = df["GRE"].str.extract(r"(\d+)").astype(int)
    df = df.sort_values("ordem").drop(columns=["ordem"])

    df["Total"] = df["Climatizadas"] + df["Em andamento"] + df["Em rota"]
    df["Pendências"] = df["Em andamento"] + df["Em rota"]
    df["Conclusão"] = df["Climatizadas"] / df["Total"]

    return df, total_linha


def tratar_setorizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    colunas_obrigatorias = ["Setor", "Em andamento", "Rota de climatização", "Total"]
    faltando = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError("A aba Setorizacao precisa ter as colunas: Setor, Em andamento, Rota de climatização e Total.")

    df["Setor"] = df["Setor"].astype(str).str.strip()
    df["Setor_norm"] = df["Setor"].str.upper()

    # Mantém apenas os 3 setores reais. Remove linha TOTAL.
    ordem_setores = {
        "SECRETARIA": "SECRETARIA",
        "ENERGISA": "ENERGISA",
        "SUPLAN": "SUPLAN",
    }

    df = df[df["Setor_norm"].isin(ordem_setores.keys())].copy()
    df["Setor"] = df["Setor_norm"].map(ordem_setores)

    for col in ["Em andamento", "Rota de climatização", "Total"]:
        df[col] = df[col].apply(numero_para_float)

    # Remove duplicatas e evita somar linhas repetidas.
    df = (
        df.groupby("Setor", as_index=False)
        .agg({
            "Em andamento": "max",
            "Rota de climatização": "max",
            "Total": "max",
        })
    )

    df["ordem"] = df["Setor"].map({"SECRETARIA": 1, "ENERGISA": 2, "SUPLAN": 3})
    df = df.sort_values("ordem").drop(columns=["ordem"])

    return df


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def carregar_dados():
    base_raw = pd.read_csv(BASE_GERAL_URL)
    setor_raw = pd.read_csv(SETORIZACAO_URL)

    base, total_linha = tratar_base_geral(base_raw)
    setor = tratar_setorizacao(setor_raw)

    return base, setor, total_linha


def fmt_num(valor: float | int) -> str:
    return f"{int(round(float(valor))):,}".replace(",", ".")


def fmt_pct(valor: float) -> str:
    return f"{float(valor) * 100:.1f}%".replace(".", ",")


def html_escape(texto) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def gerar_stacked_bars(base: pd.DataFrame, max_height: int = 210) -> str:
    maior_total = max(base["Total"].max(), 1)

    partes = []
    for _, row in base.iterrows():
        total = max(row["Total"], 1)
        altura_total = max(28, int((total / maior_total) * max_height))

        h_clim = max(8, int((row["Climatizadas"] / total) * altura_total))
        h_and = max(8, int((row["Em andamento"] / total) * altura_total))
        h_rota = max(8, int((row["Em rota"] / total) * altura_total))

        partes.append(
            f"""
            <div class="bar-col">
                <div class="stack" style="height:{altura_total}px;">
                    <div class="seg seg-rota" style="height:{h_rota}px;">{fmt_num(row["Em rota"])}</div>
                    <div class="seg seg-and" style="height:{h_and}px;">{fmt_num(row["Em andamento"])}</div>
                    <div class="seg seg-clim" style="height:{h_clim}px;">{fmt_num(row["Climatizadas"])}</div>
                </div>
                <div class="x-label">{html_escape(row["GRE"])}</div>
            </div>
            """
        )

    return "\n".join(partes)


def gerar_ranking(base: pd.DataFrame) -> str:
    ranking = base.sort_values("Pendências", ascending=False).head(8).copy()
    max_pend = max(ranking["Pendências"].max(), 1)

    linhas = []
    for _, row in ranking.iterrows():
        largura = int((row["Pendências"] / max_pend) * 100)
        linhas.append(
            f"""
            <div class="rank-row">
                <div class="rank-label">{html_escape(row["GRE"])}</div>
                <div class="rank-track"><div class="rank-fill" style="width:{largura}%"></div></div>
                <div class="rank-value">{fmt_num(row["Pendências"])}</div>
            </div>
            """
        )

    return "\n".join(linhas)


def gerar_setorizacao(setor: pd.DataFrame) -> str:
    cards = []
    for _, row in setor.iterrows():
        cards.append(
            f"""
            <div class="sector-card">
                <div class="sector-head">{html_escape(row["Setor"])}</div>
                <div class="sector-line"><span>Em andamento</span><b class="blue">{fmt_num(row["Em andamento"])}</b></div>
                <div class="sector-line"><span>Rota de climatização</span><b class="red">{fmt_num(row["Rota de climatização"])}</b></div>
                <div class="sector-line"><span>Total</span><b>{fmt_num(row["Total"])}</b></div>
            </div>
            """
        )

    return "\n".join(cards)


def gerar_html_dashboard(base: pd.DataFrame, setor: pd.DataFrame, total_linha: dict | None) -> str:
    soma_total = float(base["Total"].sum())
    soma_clim = float(base["Climatizadas"].sum())
    soma_and = float(base["Em andamento"].sum())
    soma_rota = float(base["Em rota"].sum())

    # Se a planilha tiver uma linha TOTAL válida, usa ela nos cards.
    # Se não tiver, usa a soma das GREs limpas.
    if total_linha and total_linha.get("Total", 0) > 0:
        total = float(total_linha["Total"])
        climatizadas = float(total_linha["Climatizadas"])
        andamento = float(total_linha["Em andamento"])
        rota = float(total_linha["Em rota"])
    else:
        total = soma_total
        climatizadas = soma_clim
        andamento = soma_and
        rota = soma_rota

    pendencias = andamento + rota
    pct_clim = climatizadas / total if total else 0
    pct_and = andamento / total if total else 0
    pct_rota = rota / total if total else 0

    deg_clim = pct_clim * 360
    deg_and = deg_clim + pct_and * 360

    gre_mais_pendente = base.sort_values("Pendências", ascending=False).iloc[0]
    gre_melhor = base.sort_values("Conclusão", ascending=False).iloc[0]

    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    barras_gre = gerar_stacked_bars(base)
    ranking = gerar_ranking(base)
    setorizacao = gerar_setorizacao(setor)

    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
:root {{
    --azul-noite:#001F49;
    --azul-escuro:#003B73;
    --azul-medio:#1F77D0;
    --azul-claro:#5DA7F2;
    --azul-gelo:#EAF4FF;
    --vermelho:#EF4444;
    --vermelho-escuro:#B91C1C;
    --fundo:#F3F7FB;
    --branco:#FFFFFF;
    --borda:#D9E4F2;
    --texto:#1E2F47;
    --texto-suave:#637083;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background: var(--fundo);
    color: var(--texto);
}}

.dashboard {{
    width: 100%;
    max-width: 1740px;
    margin: 0 auto;
    padding: 0 18px 24px 18px;
}}

.header {{
    height: 118px;
    padding: 22px 32px;
    border-radius: 0 0 22px 22px;
    color: white;
    background:
        radial-gradient(circle at 0% 0%, rgba(93,167,242,.35), transparent 28%),
        linear-gradient(90deg, var(--azul-noite), var(--azul-escuro) 55%, #0059A8);
    box-shadow: 0 14px 34px rgba(0,31,73,.22);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.header-left {{
    display: flex;
    align-items: center;
    gap: 22px;
}}

.logo {{
    width: 86px;
    height: 86px;
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,.38);
    background: rgba(255,255,255,.08);
    display: grid;
    place-items: center;
    font-size: 34px;
    font-weight: 950;
}}

.title {{
    font-size: 34px;
    line-height: 1.04;
    font-weight: 950;
    letter-spacing: -0.9px;
    text-transform: uppercase;
}}

.subtitle {{
    margin-top: 10px;
    font-size: 16px;
    font-weight: 650;
    opacity: .94;
}}

.map {{
    width: 150px;
    height: 70px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,.38);
    background: rgba(255,255,255,.07);
    display: grid;
    place-items: center;
    font-size: 30px;
    font-weight: 950;
}}

.filters {{
    display: grid;
    grid-template-columns: 220px 220px 220px 1fr;
    gap: 14px;
    margin: 16px 0;
}}

.filter,
.sync {{
    background: white;
    border: 1px solid var(--borda);
    border-radius: 15px;
    box-shadow: 0 8px 22px rgba(10,40,80,.075);
    padding: 12px 18px;
}}

.filter {{
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.filter small {{
    display: block;
    color: var(--texto-suave);
    font-size: 12px;
    font-weight: 750;
}}

.filter b {{
    color: var(--azul-escuro);
    font-size: 19px;
    font-weight: 900;
}}

.sync {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    color: var(--texto-suave);
    font-size: 13px;
    font-weight: 750;
}}

.kpis {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-bottom: 16px;
}}

.kpi {{
    min-height: 132px;
    background: white;
    border: 1px solid var(--borda);
    border-radius: 20px;
    box-shadow: 0 10px 24px rgba(10,40,80,.08);
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
}}

.kpi::before {{
    content: "";
    position: absolute;
    width: 7px;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--accent);
}}

.kpi::after {{
    content: "";
    position: absolute;
    right: -35px;
    bottom: -48px;
    width: 160px;
    height: 100px;
    border-radius: 50%;
    background: var(--wash);
}}

.kpi-title {{
    position: relative;
    z-index: 1;
    margin-left: 8px;
    font-size: 15px;
    font-weight: 850;
    color: #25364F;
}}

.kpi-value {{
    position: relative;
    z-index: 1;
    margin: 10px 0 0 8px;
    font-size: 50px;
    line-height: 1;
    font-weight: 950;
    letter-spacing: -1.5px;
    color: var(--accent);
}}

.kpi-sub {{
    position: relative;
    z-index: 1;
    margin: 9px 0 0 8px;
    color: var(--texto-suave);
    font-size: 15px;
    font-weight: 750;
}}

.grid-main {{
    display: grid;
    grid-template-columns: 1.35fr 1.10fr .84fr;
    gap: 16px;
}}

.grid-bottom {{
    display: grid;
    grid-template-columns: 1.05fr 1.45fr;
    gap: 16px;
    margin-top: 16px;
}}

.panel {{
    background: white;
    border: 1px solid var(--borda);
    border-radius: 20px;
    box-shadow: 0 10px 24px rgba(10,40,80,.08);
    overflow: hidden;
}}

.panel-pad {{
    padding: 18px;
}}

.panel-head {{
    padding: 11px 18px;
    background: linear-gradient(90deg, var(--azul-noite), #0059A8);
    color: white;
    font-size: 17px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: .2px;
}}

.panel-body {{
    padding: 18px;
}}

.visao-grid {{
    display: grid;
    grid-template-columns: .93fr 1.07fr;
    gap: 18px;
}}

.chart-title {{
    color: var(--azul-escuro);
    font-size: 18px;
    font-weight: 950;
    margin-bottom: 8px;
}}

.donut {{
    width: 285px;
    height: 285px;
    margin: 0 auto;
    border-radius: 50%;
    background: conic-gradient(
        var(--azul-escuro) 0deg {deg_clim:.2f}deg,
        var(--azul-claro) {deg_clim:.2f}deg {deg_and:.2f}deg,
        var(--vermelho) {deg_and:.2f}deg 360deg
    );
    position: relative;
}}

.donut::after {{
    content: "";
    position: absolute;
    inset: 76px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 0 0 1px #E7EEF7;
}}

.donut-center {{
    position: absolute;
    inset: 0;
    z-index: 2;
    display: grid;
    place-items: center;
    text-align: center;
    color: var(--azul-escuro);
    font-size: 31px;
    font-weight: 950;
}}

.donut-center span {{
    display: block;
    margin-top: 6px;
    color: #40516A;
    font-size: 14px;
    font-weight: 700;
}}

.legend {{
    margin-top: 13px;
    font-size: 13px;
    font-weight: 750;
}}

.legend-row {{
    display: flex;
    justify-content: space-between;
    padding: 4px 2px;
}}

.dot {{
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
}}

.big-progress {{
    margin-top: 8px;
    color: var(--azul-escuro);
    font-size: 46px;
    line-height: 1;
    font-weight: 950;
    letter-spacing: -1.2px;
}}

.big-progress span {{
    color: var(--texto-suave);
    font-size: 18px;
    font-weight: 650;
}}

.progress-track {{
    height: 38px;
    background: #E8EEF6;
    border: 1px solid #D6E2EF;
    border-radius: 999px;
    margin-top: 17px;
    overflow: hidden;
}}

.progress-fill {{
    height: 100%;
    width: {pct_clim * 100:.2f}%;
    background: linear-gradient(90deg, var(--azul-noite), #005FB8);
    border-radius: 999px;
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
    color: #1D3557;
    border-radius: 15px;
    padding: 14px 16px;
    font-size: 15px;
    font-weight: 750;
    margin-top: 28px;
}}

.info-box strong {{
    color: var(--azul-escuro);
}}

.stack-wrap {{
    height: 315px;
    padding: 24px 4px 0 4px;
    border-bottom: 1px solid #C9D5E2;
    display: flex;
    align-items: flex-end;
    gap: 11px;
    position: relative;
}}

.stack-wrap::before {{
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: 22px;
    bottom: 0;
    background: repeating-linear-gradient(to top, transparent 0 51px, #E4ECF5 52px);
    pointer-events: none;
}}

.bar-col {{
    position: relative;
    z-index: 2;
    flex: 1;
    min-width: 28px;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-end;
}}

.stack {{
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
}}

.seg {{
    display: grid;
    place-items: center;
    color: white;
    font-size: 11px;
    font-weight: 850;
}}

.seg-clim {{
    background: var(--azul-escuro);
}}

.seg-and {{
    background: var(--azul-claro);
}}

.seg-rota {{
    background: var(--vermelho);
}}

.x-label {{
    height: 30px;
    margin-top: 8px;
    font-size: 11px;
    font-weight: 850;
    text-align: center;
    color: #25364F;
}}

.legend-top {{
    display: flex;
    justify-content: center;
    gap: 20px;
    font-size: 12px;
    font-weight: 750;
    color: #4A5A70;
}}

.rank-row {{
    display: grid;
    grid-template-columns: 70px 1fr 42px;
    align-items: center;
    gap: 12px;
    margin: 16px 0;
    font-weight: 850;
    color: #18365C;
    font-size: 14px;
}}

.rank-track {{
    height: 23px;
    background: #ECF1F7;
    border-radius: 5px;
    overflow: hidden;
}}

.rank-fill {{
    height: 100%;
    background: linear-gradient(90deg, var(--azul-noite), #005FB8);
    border-radius: 5px;
}}

.rank-value {{
    color: var(--vermelho);
    font-size: 16px;
}}

.alert {{
    margin-top: 18px;
    background: #FFF0F0;
    color: var(--vermelho-escuro);
    border: 1px solid #FECACA;
    border-radius: 15px;
    padding: 14px;
    font-size: 14px;
    font-weight: 800;
}}

.summary-line {{
    display: grid;
    grid-template-columns: 20px 1fr;
    align-items: center;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px dashed #C7D6E8;
    color: #1C3556;
    font-size: 15px;
    font-weight: 750;
}}

.check {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--azul-medio);
}}

.sector-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
}}

.sector-card {{
    border: 1px solid var(--borda);
    border-radius: 15px;
    overflow: hidden;
    box-shadow: 0 6px 16px rgba(10,40,80,.07);
}}

.sector-head {{
    background: linear-gradient(90deg, var(--azul-noite), var(--azul-medio));
    color: white;
    padding: 11px;
    text-align: center;
    font-weight: 950;
}}

.sector-line {{
    display: flex;
    justify-content: space-between;
    padding: 11px 16px;
    border-top: 1px solid #EBF1F8;
    font-size: 15px;
    font-weight: 850;
}}

.sector-line b {{
    color: var(--azul-escuro);
}}

.sector-line b.blue {{
    color: var(--azul-medio);
}}

.sector-line b.red {{
    color: var(--vermelho);
}}

.footer {{
    margin-top: 16px;
    text-align: center;
    color: #40516A;
    font-size: 13px;
    font-weight: 650;
}}

@media (max-width: 1200px) {{
    .filters,
    .kpis,
    .grid-main,
    .grid-bottom,
    .visao-grid,
    .sector-grid {{
        grid-template-columns: 1fr;
    }}

    .header {{
        height: auto;
        display: block;
    }}

    .map {{
        margin-top: 16px;
    }}

    .title {{
        font-size: 24px;
    }}
}}
</style>
</head>
<body>
<div class="dashboard">

    <header class="header">
        <div class="header-left">
            <div class="logo">PB</div>
            <div>
                <div class="title">Painel de Monitoramento da Climatização Escolar na Paraíba</div>
                <div class="subtitle">Acompanhamento consolidado por GRE e setorização</div>
            </div>
        </div>
        <div class="map">PB</div>
    </header>

    <section class="filters">
        <div class="filter"><div><small>Período</small><b>2026</b></div><span>▾</span></div>
        <div class="filter"><div><small>GRE</small><b>Todas</b></div><span>▾</span></div>
        <div class="filter"><div><small>Visão</small><b>Geral</b></div><span>▾</span></div>
        <div class="sync">Sincronizado: {data_hora} · verificação a cada {REFRESH_SECONDS}s</div>
    </section>

    <section class="kpis">
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Total de Escolas</div>
            <div class="kpi-value">{fmt_num(total)}</div>
            <div class="kpi-sub">Base consolidada</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Climatizadas</div>
            <div class="kpi-value">{fmt_num(climatizadas)}</div>
            <div class="kpi-sub">{fmt_pct(pct_clim)} do total</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-claro);--wash:#EDF6FF;">
            <div class="kpi-title">Em Andamento</div>
            <div class="kpi-value">{fmt_num(andamento)}</div>
            <div class="kpi-sub">{fmt_pct(pct_and)} do total</div>
        </div>
        <div class="kpi" style="--accent:var(--vermelho);--wash:#FFF1F1;">
            <div class="kpi-title">Em Rota</div>
            <div class="kpi-value">{fmt_num(rota)}</div>
            <div class="kpi-sub">{fmt_pct(pct_rota)} do total</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Conclusão</div>
            <div class="kpi-value">{fmt_pct(pct_clim)}</div>
            <div class="kpi-sub">Progresso geral</div>
        </div>
    </section>

    <section class="grid-main">
        <div class="panel">
            <div class="panel-head">Visão Geral da Climatização</div>
            <div class="panel-body">
                <div class="visao-grid">
                    <div>
                        <div class="chart-title">Status Geral</div>
                        <div class="donut">
                            <div class="donut-center">
                                <div>{fmt_pct(pct_clim)}<span>Conclusão</span></div>
                            </div>
                        </div>
                        <div class="legend">
                            <div class="legend-row"><span><span class="dot" style="background:var(--azul-escuro);"></span>Climatizadas</span><b>{fmt_num(climatizadas)}</b></div>
                            <div class="legend-row"><span><span class="dot" style="background:var(--azul-claro);"></span>Em andamento</span><b>{fmt_num(andamento)}</b></div>
                            <div class="legend-row"><span><span class="dot" style="background:var(--vermelho);"></span>Em rota</span><b>{fmt_num(rota)}</b></div>
                            <div class="legend-row" style="justify-content:center;margin-top:6px;"><b>Total de Escolas: {fmt_num(total)}</b></div>
                        </div>
                    </div>

                    <div>
                        <div class="chart-title">Progresso Geral</div>
                        <div class="big-progress">{fmt_pct(pct_clim)} <span>concluído</span></div>
                        <div class="progress-track"><div class="progress-fill"></div></div>
                        <div class="progress-labels"><span>0%</span><span>100%</span></div>
                        <div class="info-box"><strong>{fmt_num(climatizadas)}</strong> escolas já foram climatizadas. Restam <strong>{fmt_num(pendencias)}</strong> em andamento ou em rota.</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="panel panel-pad">
            <div class="chart-title">Panorama por GRE</div>
            <div class="legend-top">
                <span><span class="dot" style="background:var(--azul-escuro);"></span>Climatizadas</span>
                <span><span class="dot" style="background:var(--azul-claro);"></span>Em andamento</span>
                <span><span class="dot" style="background:var(--vermelho);"></span>Em rota</span>
            </div>
            <div class="stack-wrap">
                {barras_gre}
            </div>
            <div class="info-box">A GRE com maior volume de pendências é <strong>{html_escape(gre_mais_pendente["GRE"])}</strong>, com <strong>{fmt_num(gre_mais_pendente["Pendências"])}</strong> escolas em andamento ou em rota.</div>
        </div>

        <div class="panel panel-pad">
            <div class="chart-title">Ranking de Pendências</div>
            <div style="font-size:13px;color:#516174;font-weight:750;">Total em andamento + em rota</div>
            {ranking}
            <div class="alert">Priorize as GREs com maior volume de pendências para acelerar a conclusão.</div>
        </div>
    </section>

    <section class="grid-bottom">
        <div class="panel panel-pad">
            <div class="chart-title">Resumo Executivo</div>
            <div class="summary-line"><span class="check"></span><span>Mais da metade das escolas já está climatizada.</span></div>
            <div class="summary-line"><span class="check"></span><span>A GRE com maior pendência é <strong>{html_escape(gre_mais_pendente["GRE"])}</strong>.</span></div>
            <div class="summary-line"><span class="check"></span><span>A maior conclusão proporcional está em <strong>{html_escape(gre_melhor["GRE"])}</strong>.</span></div>
            <div class="summary-line"><span class="check"></span><span>A setorização deve ser acompanhada separadamente do total geral.</span></div>
        </div>

        <div class="panel">
            <div class="panel-head">Quadro de Status por Setorização</div>
            <div class="panel-body">
                <div class="sector-grid">
                    {setorizacao}
                </div>
            </div>
        </div>
    </section>

    <div class="footer">
        Os dados apresentados são consolidados com base nas informações enviadas pelas GREs e órgãos executores.
    </div>
</div>
</body>
</html>
"""
    return html


# ============================================================
# RENDERIZAÇÃO COM ATUALIZAÇÃO CONTROLADA
# ============================================================

def renderizar():
    try:
        base, setor, total_linha = carregar_dados()
        html = gerar_html_dashboard(base, setor, total_linha)
        components.html(html, height=1010, scrolling=False)
    except Exception as erro:
        st.error("Erro ao montar o dashboard. Verifique a publicação das abas do Google Sheets.")
        st.exception(erro)


if hasattr(st, "fragment"):
    @st.fragment(run_every=f"{REFRESH_SECONDS}s")
    def painel():
        renderizar()

    painel()
else:
    renderizar()
