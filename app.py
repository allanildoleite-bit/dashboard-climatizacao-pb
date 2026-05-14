
from __future__ import annotations

import json
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

REFRESH_SECONDS = 60


# ============================================================
# CONFIGURAÇÃO STREAMLIT
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
    padding: 0;
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
    min-height: 1500px;
    border: 0;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# TRATAMENTO DA BASE
# ============================================================

def numero_para_float(valor) -> float:
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
    if pd.isna(valor):
        return None

    texto = str(valor).strip().upper().replace("º", "ª")

    if not texto or "TOTAL" in texto or "GERAL" in texto or "STATUS" in texto:
        return None

    match = re.search(r"(\d+)", texto)
    if not match:
        return None

    numero = int(match.group(1))
    if numero <= 0 or numero > 30:
        return None

    return f"{numero}ª GRE"


def detectar_coluna_periodo(df: pd.DataFrame) -> str | None:
    for col in ["Periodo", "Período", "Ano", "ANO", "ano", "periodo", "período"]:
        if col in df.columns:
            return col
    return None


def tratar_base_geral(df: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_periodo = detectar_coluna_periodo(df)
    if col_periodo:
        df["Periodo"] = df[col_periodo].astype(str).str.strip()
    else:
        df["Periodo"] = "2026"

    colunas_obrigatorias = ["GRE", "Climatizadas", "Em andamento", "Em rota"]
    faltando = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError("A aba Base_Geral precisa ter as colunas: GRE, Climatizadas, Em andamento e Em rota.")

    total_linha = None
    linhas_total = df[df["GRE"].astype(str).str.upper().str.contains("TOTAL", na=False)].copy()

    if not linhas_total.empty:
        ultima_total = linhas_total.iloc[-1]
        total_linha = {
            "Periodo": str(ultima_total.get("Periodo", "2026")),
            "Climatizadas": numero_para_float(ultima_total["Climatizadas"]),
            "Em andamento": numero_para_float(ultima_total["Em andamento"]),
            "Em rota": numero_para_float(ultima_total["Em rota"]),
        }
        total_linha["Total"] = total_linha["Climatizadas"] + total_linha["Em andamento"] + total_linha["Em rota"]

    for col in ["Climatizadas", "Em andamento", "Em rota"]:
        df[col] = df[col].apply(numero_para_float)

    df["GRE"] = df["GRE"].apply(padronizar_gre)
    df = df[df["GRE"].notna()].copy()
    df = df[df[["Climatizadas", "Em andamento", "Em rota"]].sum(axis=1) > 0].copy()
    df = df.drop_duplicates(subset=["Periodo", "GRE", "Climatizadas", "Em andamento", "Em rota"])

    df = (
        df.groupby(["Periodo", "GRE"], as_index=False)
        .agg({
            "Climatizadas": "max",
            "Em andamento": "max",
            "Em rota": "max",
        })
    )

    df["Ordem"] = df["GRE"].str.extract(r"(\d+)").astype(int)
    df = df.sort_values(["Periodo", "Ordem"])
    df["Total"] = df["Climatizadas"] + df["Em andamento"] + df["Em rota"]
    df["Pendências"] = df["Em andamento"] + df["Em rota"]
    df["Conclusão"] = df["Climatizadas"] / df["Total"]

    return df, total_linha


def tratar_setorizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_periodo = detectar_coluna_periodo(df)
    if col_periodo:
        df["Periodo"] = df[col_periodo].astype(str).str.strip()
    else:
        df["Periodo"] = "2026"

    colunas_obrigatorias = ["Setor", "Em andamento", "Rota de climatização", "Total"]
    faltando = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError("A aba Setorizacao precisa ter as colunas: Setor, Em andamento, Rota de climatização e Total.")

    df["Setor"] = df["Setor"].astype(str).str.strip()
    df["Setor_norm"] = df["Setor"].str.upper()

    setores_validos = {
        "SECRETARIA": "SECRETARIA",
        "ENERGISA": "ENERGISA",
        "SUPLAN": "SUPLAN",
    }

    df = df[df["Setor_norm"].isin(setores_validos.keys())].copy()
    df["Setor"] = df["Setor_norm"].map(setores_validos)

    for col in ["Em andamento", "Rota de climatização", "Total"]:
        df[col] = df[col].apply(numero_para_float)

    df = (
        df.groupby(["Periodo", "Setor"], as_index=False)
        .agg({
            "Em andamento": "max",
            "Rota de climatização": "max",
            "Total": "max",
        })
    )

    df["Ordem"] = df["Setor"].map({"SECRETARIA": 1, "ENERGISA": 2, "SUPLAN": 3})
    df = df.sort_values(["Periodo", "Ordem"])

    return df


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def carregar_dados():
    base_raw = pd.read_csv(BASE_GERAL_URL)
    setor_raw = pd.read_csv(SETORIZACAO_URL)

    base, total_linha = tratar_base_geral(base_raw)
    setor = tratar_setorizacao(setor_raw)

    return base, setor, total_linha


def montar_html(base: pd.DataFrame, setor: pd.DataFrame, total_linha: dict | None) -> str:
    dados_base = base[[
        "Periodo", "GRE", "Ordem", "Climatizadas", "Em andamento", "Em rota",
        "Total", "Pendências", "Conclusão"
    ]].to_dict(orient="records")

    dados_setor = setor[[
        "Periodo", "Setor", "Ordem", "Em andamento", "Rota de climatização", "Total"
    ]].to_dict(orient="records")

    json_base = json.dumps(dados_base, ensure_ascii=False)
    json_setor = json.dumps(dados_setor, ensure_ascii=False)
    json_total = json.dumps(total_linha or {}, ensure_ascii=False)

    sincronizado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

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
    padding: 0 18px 56px 18px;
}}

.header {{
    min-height: 132px;
    padding: 20px 30px;
    border-radius: 0 0 22px 22px;
    color: white;
    background:
        radial-gradient(circle at 0% 0%, rgba(93,167,242,.35), transparent 28%),
        linear-gradient(90deg, var(--azul-noite), var(--azul-escuro) 55%, #0059A8);
    box-shadow: 0 14px 34px rgba(0,31,73,.22);
    display: grid;
    grid-template-columns: 440px 1fr 120px;
    align-items: center;
    gap: 22px;
}}

.institutional-card {{
    height: 92px;
    background: rgba(255,255,255,.96);
    border: 1px solid rgba(255,255,255,.72);
    border-radius: 20px;
    padding: 10px 14px;
    display: grid;
    grid-template-columns: 1fr 86px;
    align-items: center;
    gap: 13px;
    box-shadow: 0 10px 24px rgba(0,31,73,.20);
}}

.logo-gov {{
    width: 100%;
    max-height: 72px;
    object-fit: contain;
    object-position: left center;
}}

.logo-geobs {{
    width: 86px;
    max-height: 76px;
    object-fit: contain;
}}

.header-text {{
    min-width: 0;
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
    font-size: 31px;
    line-height: 1.06;
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

.filter {{
    background: white;
    border: 1px solid var(--borda);
    border-radius: 15px;
    box-shadow: 0 8px 22px rgba(10,40,80,.075);
    padding: 10px 14px;
}}

.filter label {{
    display:block;
    color: var(--texto-suave);
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 3px;
}}

.filter select {{
    width: 100%;
    border: 0;
    outline: 0;
    background: white;
    color: var(--azul-escuro);
    font-size: 19px;
    font-weight: 900;
    cursor: pointer;
}}

.sync {{
    background: white;
    border: 1px solid var(--borda);
    border-radius: 15px;
    box-shadow: 0 8px 22px rgba(10,40,80,.075);
    padding: 12px 18px;
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
    grid-template-columns: 1.20fr 1.22fr .78fr;
    gap: 16px;
}}

.grid-main.pendencias {{
    grid-template-columns: 1.45fr .90fr;
}}

.grid-main.setorizacao {{
    grid-template-columns: 1fr;
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
        var(--azul-escuro) 0deg var(--deg-clim),
        var(--azul-claro) var(--deg-clim) var(--deg-and),
        var(--vermelho) var(--deg-and) 360deg
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
    width: 0%;
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
    margin-top: 22px;
}}

.info-box strong {{
    color: var(--azul-escuro);
}}

.panorama-horizontal {{
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}}

.gre-row {{
    display: grid;
    grid-template-columns: 58px 1fr 42px;
    align-items: center;
    gap: 10px;
    min-height: 24px;
}}

.gre-name {{
    color: #18365C;
    font-size: 12px;
    font-weight: 900;
    text-align: right;
}}

.gre-track {{
    background: #ECF1F7;
    height: 24px;
    border-radius: 7px;
    overflow: hidden;
    position: relative;
}}

.gre-stack {{
    height: 100%;
    display: flex;
    border-radius: 7px;
    overflow: hidden;
}}

.gre-seg {{
    height: 100%;
    display: grid;
    place-items: center;
    color: white;
    font-size: 11px;
    font-weight: 900;
    white-space: nowrap;
    min-width: 12px;
}}

.gre-clim {{ background: var(--azul-escuro); }}
.gre-and {{ background: var(--azul-claro); }}
.gre-rota {{ background: var(--vermelho); }}

.gre-total {{
    color: #25364F;
    font-size: 12px;
    font-weight: 900;
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

.sector-line b {{ color: var(--azul-escuro); }}
.sector-line b.blue {{ color: var(--azul-medio); }}
.sector-line b.red {{ color: var(--vermelho); }}

.footer {{
    margin-top: 16px;
    text-align: center;
    color: #40516A;
    font-size: 13px;
    font-weight: 650;
}}

.hidden {{
    display: none !important;
}}

@media (max-width: 1200px) {{
    .filters,
    .kpis,
    .grid-main,
    .grid-main.pendencias,
    .grid-main.setorizacao,
    .grid-bottom,
    .visao-grid,
    .sector-grid {{
        grid-template-columns: 1fr;
    }}

    .header {{
        height: auto;
        display: grid;
        grid-template-columns: 1fr;
    }}

    .institutional-card {{
        width: 100%;
        grid-template-columns: 1fr 80px;
    }}

    .map {{
        margin-top: 0;
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
        <div class="institutional-card">
            <img class="logo-gov" src="data:image/png;base64,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" alt="Governo da Paraíba">
            <img class="logo-geobs" src="data:image/png;base64,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" alt="GEOBS - Gerência de Obras">
        </div>

        <div class="header-text">
            <div class="title">Painel de Monitoramento da Climatização Escolar na Paraíba</div>
            <div class="subtitle" id="subtitle">Filtros aplicados diretamente no painel</div>
        </div>

        <div class="map">PB</div>
    </header>

    <section class="filters">
        <div class="filter">
            <label for="periodFilter">Período</label>
            <select id="periodFilter"></select>
        </div>
        <div class="filter">
            <label for="greFilter">GRE</label>
            <select id="greFilter"></select>
        </div>
        <div class="filter">
            <label for="viewFilter">Visão</label>
            <select id="viewFilter">
                <option value="Geral">Geral</option>
                <option value="Pendências">Pendências</option>
                <option value="Setorização">Setorização</option>
            </select>
        </div>
        <div class="sync">Sincronizado: {sincronizado} · verificação a cada {REFRESH_SECONDS}s</div>
    </section>

    <section class="kpis">
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Total de Escolas</div>
            <div class="kpi-value" id="kpiTotal">0</div>
            <div class="kpi-sub">Base filtrada</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Climatizadas</div>
            <div class="kpi-value" id="kpiClimatizadas">0</div>
            <div class="kpi-sub" id="subClimatizadas">0,0% do total</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-claro);--wash:#EDF6FF;">
            <div class="kpi-title">Em Andamento</div>
            <div class="kpi-value" id="kpiAndamento">0</div>
            <div class="kpi-sub" id="subAndamento">0,0% do total</div>
        </div>
        <div class="kpi" style="--accent:var(--vermelho);--wash:#FFF1F1;">
            <div class="kpi-title">Em Rota</div>
            <div class="kpi-value" id="kpiRota">0</div>
            <div class="kpi-sub" id="subRota">0,0% do total</div>
        </div>
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Conclusão</div>
            <div class="kpi-value" id="kpiConclusao">0,0%</div>
            <div class="kpi-sub">Progresso geral</div>
        </div>
    </section>

    <section class="grid-main" id="mainGrid">
        <div class="panel" id="generalPanel">
            <div class="panel-head">Visão Geral da Climatização</div>
            <div class="panel-body">
                <div class="visao-grid">
                    <div>
                        <div class="chart-title">Status Geral</div>
                        <div class="donut" id="donut">
                            <div class="donut-center">
                                <div id="donutCenter">0,0%<span>Conclusão</span></div>
                            </div>
                        </div>
                        <div class="legend">
                            <div class="legend-row"><span><span class="dot" style="background:var(--azul-escuro);"></span>Climatizadas</span><b id="legClim">0</b></div>
                            <div class="legend-row"><span><span class="dot" style="background:var(--azul-claro);"></span>Em andamento</span><b id="legAnd">0</b></div>
                            <div class="legend-row"><span><span class="dot" style="background:var(--vermelho);"></span>Em rota</span><b id="legRota">0</b></div>
                            <div class="legend-row" style="justify-content:center;margin-top:6px;"><b>Total de Escolas: <span id="legTotal">0</span></b></div>
                        </div>
                    </div>

                    <div>
                        <div class="chart-title">Progresso Geral</div>
                        <div class="big-progress"><span id="progressPct" style="font-size:46px;color:var(--azul-escuro);font-weight:950;">0,0%</span> <span>concluído</span></div>
                        <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
                        <div class="progress-labels"><span>0%</span><span>100%</span></div>
                        <div class="info-box" id="progressInfo">Dados filtrados serão exibidos aqui.</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="panel panel-pad" id="panoramaPanel">
            <div class="chart-title">Panorama por GRE</div>
            <div class="legend-top">
                <span><span class="dot" style="background:var(--azul-escuro);"></span>Climatizadas</span>
                <span><span class="dot" style="background:var(--azul-claro);"></span>Em andamento</span>
                <span><span class="dot" style="background:var(--vermelho);"></span>Em rota</span>
            </div>
            <div class="panorama-horizontal" id="panorama"></div>
            <div class="info-box" id="panoramaInfo">Informação principal será exibida aqui.</div>
        </div>

        <div class="panel panel-pad" id="rankingPanel">
            <div class="chart-title">Ranking de Pendências</div>
            <div style="font-size:13px;color:#516174;font-weight:750;">Total em andamento + em rota</div>
            <div id="ranking"></div>
            <div class="alert">Priorize as GREs com maior volume de pendências para acelerar a conclusão.</div>
        </div>
    </section>

    <section class="grid-bottom" id="bottomGrid">
        <div class="panel panel-pad" id="summaryPanel">
            <div class="chart-title">Resumo Executivo</div>
            <div id="summary"></div>
        </div>

        <div class="panel" id="sectorPanel">
            <div class="panel-head">Quadro de Status por Setorização</div>
            <div class="panel-body">
                <div class="sector-grid" id="sectorGrid"></div>
            </div>
        </div>
    </section>

    <div class="footer">
        Os dados apresentados são consolidados com base nas informações enviadas pelas GREs e órgãos executores.
    </div>
</div>

<script>
const baseData = {json_base};
const setorData = {json_setor};
const totalLine = {json_total};

const LS_PERIOD = "climatizacao_periodo";
const LS_GRE = "climatizacao_gre";
const LS_VIEW = "climatizacao_visao";

function fmtNum(value) {{
    return Math.round(Number(value || 0)).toLocaleString("pt-BR");
}}

function fmtPct(value) {{
    return (Number(value || 0) * 100).toLocaleString("pt-BR", {{
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
    }}) + "%";
}}

function escapeHtml(text) {{
    return String(text ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}}

function uniqueValues(arr) {{
    return [...new Set(arr)];
}}

function getSelectedFilters() {{
    return {{
        periodo: document.getElementById("periodFilter").value,
        gre: document.getElementById("greFilter").value,
        visao: document.getElementById("viewFilter").value
    }};
}}

function setOptions(select, values, selectedValue) {{
    select.innerHTML = "";
    values.forEach(value => {{
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        if (value === selectedValue) option.selected = true;
        select.appendChild(option);
    }});
}}

function initializeFilters() {{
    const periodFilter = document.getElementById("periodFilter");
    const greFilter = document.getElementById("greFilter");
    const viewFilter = document.getElementById("viewFilter");

    let periodos = uniqueValues(baseData.map(d => String(d.Periodo || "2026"))).filter(Boolean);
    periodos.sort();
    if (periodos.length > 1) periodos = ["Todos", ...periodos];

    const savedPeriod = localStorage.getItem(LS_PERIOD);
    const defaultPeriod = periodos.includes(savedPeriod) ? savedPeriod : (periodos.includes("2026") ? "2026" : periodos[0]);
    setOptions(periodFilter, periodos, defaultPeriod);

    const savedView = localStorage.getItem(LS_VIEW);
    if (savedView && ["Geral", "Pendências", "Setorização"].includes(savedView)) {{
        viewFilter.value = savedView;
    }}

    updateGreOptions();

    periodFilter.addEventListener("change", () => {{
        localStorage.setItem(LS_PERIOD, periodFilter.value);
        updateGreOptions();
        renderDashboard();
    }});

    greFilter.addEventListener("change", () => {{
        localStorage.setItem(LS_GRE, greFilter.value);
        renderDashboard();
    }});

    viewFilter.addEventListener("change", () => {{
        localStorage.setItem(LS_VIEW, viewFilter.value);
        renderDashboard();
    }});
}}

function updateGreOptions() {{
    const period = document.getElementById("periodFilter").value;
    const greFilter = document.getElementById("greFilter");
    const savedGre = localStorage.getItem(LS_GRE);

    let filtered = baseData;
    if (period !== "Todos") {{
        filtered = filtered.filter(d => String(d.Periodo) === String(period));
    }}

    const gres = ["Todas", ...filtered
        .slice()
        .sort((a, b) => Number(a.Ordem || 0) - Number(b.Ordem || 0))
        .map(d => d.GRE)
        .filter((v, i, a) => a.indexOf(v) === i)];

    const selectedGre = gres.includes(savedGre) ? savedGre : "Todas";
    setOptions(greFilter, gres, selectedGre);
}}

function filterBase() {{
    const {{ periodo, gre }} = getSelectedFilters();
    let filtered = baseData.slice();

    if (periodo !== "Todos") {{
        filtered = filtered.filter(d => String(d.Periodo) === String(periodo));
    }}

    if (gre !== "Todas") {{
        filtered = filtered.filter(d => d.GRE === gre);
    }}

    return filtered.sort((a, b) => Number(a.Ordem || 0) - Number(b.Ordem || 0));
}}

function filterSetor() {{
    const {{ periodo }} = getSelectedFilters();
    let filtered = setorData.slice();

    if (periodo !== "Todos") {{
        const byPeriod = filtered.filter(d => String(d.Periodo) === String(periodo));
        if (byPeriod.length > 0) filtered = byPeriod;
    }}

    return filtered.sort((a, b) => Number(a.Ordem || 0) - Number(b.Ordem || 0));
}}

function getTotals(filtered) {{
    const {{ periodo, gre }} = getSelectedFilters();

    if (
        gre === "Todas" &&
        periodo !== "Todos" &&
        totalLine &&
        Number(totalLine.Total || 0) > 0 &&
        String(totalLine.Periodo || periodo) === String(periodo)
    ) {{
        return {{
            total: Number(totalLine.Total || 0),
            climatizadas: Number(totalLine.Climatizadas || 0),
            andamento: Number(totalLine["Em andamento"] || 0),
            rota: Number(totalLine["Em rota"] || 0)
        }};
    }}

    const climatizadas = filtered.reduce((sum, d) => sum + Number(d.Climatizadas || 0), 0);
    const andamento = filtered.reduce((sum, d) => sum + Number(d["Em andamento"] || 0), 0);
    const rota = filtered.reduce((sum, d) => sum + Number(d["Em rota"] || 0), 0);
    const total = climatizadas + andamento + rota;

    return {{ total, climatizadas, andamento, rota }};
}}

function renderKpis(totals) {{
    const pctClim = totals.total ? totals.climatizadas / totals.total : 0;
    const pctAnd = totals.total ? totals.andamento / totals.total : 0;
    const pctRota = totals.total ? totals.rota / totals.total : 0;

    document.getElementById("kpiTotal").textContent = fmtNum(totals.total);
    document.getElementById("kpiClimatizadas").textContent = fmtNum(totals.climatizadas);
    document.getElementById("kpiAndamento").textContent = fmtNum(totals.andamento);
    document.getElementById("kpiRota").textContent = fmtNum(totals.rota);
    document.getElementById("kpiConclusao").textContent = fmtPct(pctClim);

    document.getElementById("subClimatizadas").textContent = fmtPct(pctClim) + " do total";
    document.getElementById("subAndamento").textContent = fmtPct(pctAnd) + " do total";
    document.getElementById("subRota").textContent = fmtPct(pctRota) + " do total";

    const donut = document.getElementById("donut");
    const degClim = pctClim * 360;
    const degAnd = degClim + pctAnd * 360;
    donut.style.setProperty("--deg-clim", degClim + "deg");
    donut.style.setProperty("--deg-and", degAnd + "deg");

    document.getElementById("donutCenter").innerHTML = fmtPct(pctClim) + "<span>Conclusão</span>";
    document.getElementById("legClim").textContent = fmtNum(totals.climatizadas);
    document.getElementById("legAnd").textContent = fmtNum(totals.andamento);
    document.getElementById("legRota").textContent = fmtNum(totals.rota);
    document.getElementById("legTotal").textContent = fmtNum(totals.total);

    document.getElementById("progressPct").textContent = fmtPct(pctClim);
    document.getElementById("progressFill").style.width = Math.max(0, Math.min(100, pctClim * 100)) + "%";
    document.getElementById("progressInfo").innerHTML =
        `<strong>${{fmtNum(totals.climatizadas)}}</strong> escolas já foram climatizadas. Restam <strong>${{fmtNum(totals.andamento + totals.rota)}}</strong> em andamento ou em rota.`;
}}

function renderPanorama(filtered) {{
    const panel = document.getElementById("panorama");
    const info = document.getElementById("panoramaInfo");

    if (filtered.length === 0) {{
        panel.innerHTML = "";
        info.textContent = "Nenhum dado encontrado para o filtro selecionado.";
        return;
    }}

    const maxTotal = Math.max(...filtered.map(d => Number(d.Total || 0)), 1);
    let rows = "";

    filtered.forEach(d => {{
        const total = Math.max(Number(d.Total || 0), 1);
        const widthTotal = Math.max(18, (total / maxTotal) * 100);
        const wClim = Math.max(3, (Number(d.Climatizadas || 0) / total) * 100);
        const wAnd = Math.max(3, (Number(d["Em andamento"] || 0) / total) * 100);
        const wRota = Math.max(3, (Number(d["Em rota"] || 0) / total) * 100);

        const climLabel = Number(d.Climatizadas || 0) >= 4 ? fmtNum(d.Climatizadas) : "";
        const andLabel = Number(d["Em andamento"] || 0) >= 4 ? fmtNum(d["Em andamento"]) : "";
        const rotaLabel = Number(d["Em rota"] || 0) >= 4 ? fmtNum(d["Em rota"]) : "";

        rows += `
            <div class="gre-row">
                <div class="gre-name">${{escapeHtml(d.GRE)}}</div>
                <div class="gre-track">
                    <div class="gre-stack" style="width:${{widthTotal}}%;">
                        <div class="gre-seg gre-clim" style="width:${{wClim}}%;">${{climLabel}}</div>
                        <div class="gre-seg gre-and" style="width:${{wAnd}}%;">${{andLabel}}</div>
                        <div class="gre-seg gre-rota" style="width:${{wRota}}%;">${{rotaLabel}}</div>
                    </div>
                </div>
                <div class="gre-total">${{fmtNum(d.Total)}}</div>
            </div>`;
    }});

    panel.innerHTML = rows;

    const maior = filtered.slice().sort((a, b) => Number(b.Pendências || 0) - Number(a.Pendências || 0))[0];
    info.innerHTML = `A GRE com maior volume de pendências é <strong>${{escapeHtml(maior.GRE)}}</strong>, com <strong>${{fmtNum(maior.Pendências)}}</strong> escolas em andamento ou em rota.`;
}}

function renderRanking(filtered) {{
    const panel = document.getElementById("ranking");

    const ranking = filtered
        .slice()
        .sort((a, b) => Number(b.Pendências || 0) - Number(a.Pendências || 0))
        .slice(0, 8);

    const maxPend = Math.max(...ranking.map(d => Number(d.Pendências || 0)), 1);

    let html = "";
    ranking.forEach(d => {{
        const width = Math.max(3, (Number(d.Pendências || 0) / maxPend) * 100);
        html += `
            <div class="rank-row">
                <div class="rank-label">${{escapeHtml(d.GRE)}}</div>
                <div class="rank-track"><div class="rank-fill" style="width:${{width}}%;"></div></div>
                <div class="rank-value">${{fmtNum(d.Pendências)}}</div>
            </div>`;
    }});

    panel.innerHTML = html;
}}

function renderSetores(setores) {{
    const panel = document.getElementById("sectorGrid");

    let html = "";
    setores.forEach(s => {{
        html += `
            <div class="sector-card">
                <div class="sector-head">${{escapeHtml(s.Setor)}}</div>
                <div class="sector-line"><span>Em andamento</span><b class="blue">${{fmtNum(s["Em andamento"])}}</b></div>
                <div class="sector-line"><span>Rota de climatização</span><b class="red">${{fmtNum(s["Rota de climatização"])}}</b></div>
                <div class="sector-line"><span>Total</span><b>${{fmtNum(s.Total)}}</b></div>
            </div>`;
    }});

    panel.innerHTML = html;
}}

function renderSummary(filtered) {{
    const panel = document.getElementById("summary");

    if (filtered.length === 0) {{
        panel.innerHTML = "";
        return;
    }}

    const maiorPend = filtered.slice().sort((a, b) => Number(b.Pendências || 0) - Number(a.Pendências || 0))[0];
    const melhor = filtered.slice().sort((a, b) => Number(b.Conclusão || 0) - Number(a.Conclusão || 0))[0];

    panel.innerHTML = `
        <div class="summary-line"><span class="check"></span><span>Mais da metade das escolas já está climatizada.</span></div>
        <div class="summary-line"><span class="check"></span><span>A GRE com maior pendência é <strong>${{escapeHtml(maiorPend.GRE)}}</strong>.</span></div>
        <div class="summary-line"><span class="check"></span><span>A maior conclusão proporcional está em <strong>${{escapeHtml(melhor.GRE)}}</strong>.</span></div>
        <div class="summary-line"><span class="check"></span><span>A setorização deve ser acompanhada separadamente do total geral.</span></div>`;
}}

function applyViewMode() {{
    const visao = document.getElementById("viewFilter").value;
    const mainGrid = document.getElementById("mainGrid");
    const generalPanel = document.getElementById("generalPanel");
    const panoramaPanel = document.getElementById("panoramaPanel");
    const rankingPanel = document.getElementById("rankingPanel");
    const bottomGrid = document.getElementById("bottomGrid");
    const summaryPanel = document.getElementById("summaryPanel");
    const sectorPanel = document.getElementById("sectorPanel");

    mainGrid.className = "grid-main";
    generalPanel.classList.remove("hidden");
    panoramaPanel.classList.remove("hidden");
    rankingPanel.classList.remove("hidden");
    bottomGrid.className = "grid-bottom";
    summaryPanel.classList.remove("hidden");
    sectorPanel.classList.remove("hidden");

    if (visao === "Pendências") {{
        generalPanel.classList.add("hidden");
        mainGrid.classList.add("pendencias");
    }}

    if (visao === "Setorização") {{
        mainGrid.classList.add("setorizacao");
        generalPanel.classList.add("hidden");
        panoramaPanel.classList.add("hidden");
        rankingPanel.classList.add("hidden");
        summaryPanel.classList.add("hidden");
        bottomGrid.className = "grid-bottom";
    }}
}}

function renderDashboard() {{
    const filtered = filterBase();
    const setores = filterSetor();
    const totals = getTotals(filtered);

    renderKpis(totals);
    renderPanorama(filtered);
    renderRanking(filtered);
    renderSetores(setores);
    renderSummary(filtered);
    applyViewMode();

    const f = getSelectedFilters();
    document.getElementById("subtitle").textContent = `Período: ${{f.periodo}} · GRE: ${{f.gre}} · Visão: ${{f.visao}}`;
}}

initializeFilters();
renderDashboard();
</script>
</body>
</html>
"""
    return html


def renderizar():
    try:
        base, setor, total_linha = carregar_dados()
        html = montar_html(base, setor, total_linha)
        components.html(html, height=1500, scrolling=True)
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
