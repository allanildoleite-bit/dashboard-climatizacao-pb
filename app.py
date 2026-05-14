
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

.logo {
    width: 86px;
    height: 86px;
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,.38);
    background: rgba(255,255,255,.08);
    display: grid;
    place-items: center;
    font-size: 34px;
    font-weight: 950;
}

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
