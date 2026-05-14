
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

# Atualização controlada, sem ficar piscando.
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
        min-height: 1480px;
        border: 0;
    }

    .stSelectbox label {
        color: #003B73 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
    }

    div[data-baseweb="select"] > div {
        background-color: white !important;
        border: 1px solid #D9E4F2 !important;
        border-radius: 15px !important;
        min-height: 54px !important;
        box-shadow: 0 8px 22px rgba(10,40,80,.075) !important;
    }

    .filter-note {
        background: #FFFFFF;
        border: 1px solid #D9E4F2;
        border-radius: 15px;
        padding: 14px 18px;
        box-shadow: 0 8px 22px rgba(10,40,80,.075);
        color: #637083;
        font-weight: 700;
        font-size: 13px;
        margin-top: 26px;
    }

    .filter-wrapper {
        padding: 0 18px;
        max-width: 1740px;
        margin: 0 auto 10px auto;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LEITURA E TRATAMENTO DOS DADOS
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


def detectar_coluna_periodo(df: pd.DataFrame) -> str | None:
    possiveis = ["Periodo", "Período", "Ano", "ANO", "ano", "periodo", "período"]
    for col in possiveis:
        if col in df.columns:
            return col
    return None


def tratar_base_geral(df: pd.DataFrame) -> tuple[pd.DataFrame, dict | None, list[str]]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_periodo = detectar_coluna_periodo(df)
    if col_periodo:
        df["Periodo"] = df[col_periodo].astype(str).str.strip()
    else:
        df["Periodo"] = "2026"

    periodos = sorted([p for p in df["Periodo"].dropna().unique().tolist() if str(p).strip()])

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

    df["ordem"] = df["GRE"].str.extract(r"(\d+)").astype(int)
    df = df.sort_values(["Periodo", "ordem"]).drop(columns=["ordem"])

    df["Total"] = df["Climatizadas"] + df["Em andamento"] + df["Em rota"]
    df["Pendências"] = df["Em andamento"] + df["Em rota"]
    df["Conclusão"] = df["Climatizadas"] / df["Total"]

    return df, total_linha, periodos or ["2026"]


def tratar_setorizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Setor" not in df.columns:
        raise ValueError("A aba Setorizacao precisa ter a coluna Setor.")

    # Se futuramente existir coluna de período na setorização, o app também aceita.
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

    ordem_setores = {
        "SECRETARIA": "SECRETARIA",
        "ENERGISA": "ENERGISA",
        "SUPLAN": "SUPLAN",
    }

    df = df[df["Setor_norm"].isin(ordem_setores.keys())].copy()
    df["Setor"] = df["Setor_norm"].map(ordem_setores)

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

    df["ordem"] = df["Setor"].map({"SECRETARIA": 1, "ENERGISA": 2, "SUPLAN": 3})
    df = df.sort_values(["Periodo", "ordem"]).drop(columns=["ordem"])

    return df


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def carregar_dados():
    base_raw = pd.read_csv(BASE_GERAL_URL)
    setor_raw = pd.read_csv(SETORIZACAO_URL)

    base, total_linha, periodos = tratar_base_geral(base_raw)
    setor = tratar_setorizacao(setor_raw)

    return base, setor, total_linha, periodos


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


def gerar_panorama_horizontal(base: pd.DataFrame) -> str:
    maior_total = max(base["Total"].max(), 1)

    linhas = []
    for _, row in base.iterrows():
        total = max(float(row["Total"]), 1)
        w_clim = max(3, (float(row["Climatizadas"]) / total) * 100)
        w_and = max(3, (float(row["Em andamento"]) / total) * 100)
        w_rota = max(3, (float(row["Em rota"]) / total) * 100)
        largura_total = max(18, (total / maior_total) * 100)

        clima_label = fmt_num(row["Climatizadas"]) if row["Climatizadas"] >= 4 else ""
        and_label = fmt_num(row["Em andamento"]) if row["Em andamento"] >= 4 else ""
        rota_label = fmt_num(row["Em rota"]) if row["Em rota"] >= 4 else ""

        linhas.append(
            f"""
            <div class="gre-row">
                <div class="gre-name">{html_escape(row["GRE"])}</div>
                <div class="gre-track">
                    <div class="gre-stack" style="width:{largura_total:.2f}%;">
                        <div class="gre-seg gre-clim" style="width:{w_clim:.2f}%;">{clima_label}</div>
                        <div class="gre-seg gre-and" style="width:{w_and:.2f}%;">{and_label}</div>
                        <div class="gre-seg gre-rota" style="width:{w_rota:.2f}%;">{rota_label}</div>
                    </div>
                </div>
                <div class="gre-total">{fmt_num(row["Total"])}</div>
            </div>
            """
        )

    return "\n".join(linhas)


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


def gerar_html_dashboard(
    base: pd.DataFrame,
    setor: pd.DataFrame,
    total_linha: dict | None,
    periodo: str,
    gre: str,
    visao: str,
) -> str:
    soma_total = float(base["Total"].sum())
    soma_clim = float(base["Climatizadas"].sum())
    soma_and = float(base["Em andamento"].sum())
    soma_rota = float(base["Em rota"].sum())

    # Usa linha TOTAL apenas quando a visão é geral e nenhuma GRE específica foi filtrada.
    if gre == "Todas" and total_linha and total_linha.get("Total", 0) > 0 and str(total_linha.get("Periodo", periodo)) == str(periodo):
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

    barras_gre = gerar_panorama_horizontal(base)
    ranking = gerar_ranking(base)
    setorizacao = gerar_setorizacao(setor)

    mostra_geral = visao == "Geral"
    mostra_pendencias = visao == "Pendências"
    mostra_setorizacao = visao == "Setorização"

    # Define blocos conforme a visão selecionada.
    if mostra_pendencias:
        grid_main_style = "grid-template-columns: 1.05fr 1.55fr;"
        bloco_visao_geral = ""
    else:
        grid_main_style = "grid-template-columns: 1.35fr 1.10fr .84fr;"
        bloco_visao_geral = f"""
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
        """

    bloco_panorama = f"""
        <div class="panel panel-pad">
            <div class="chart-title">Panorama por GRE</div>
            <div class="legend-top">
                <span><span class="dot" style="background:var(--azul-escuro);"></span>Climatizadas</span>
                <span><span class="dot" style="background:var(--azul-claro);"></span>Em andamento</span>
                <span><span class="dot" style="background:var(--vermelho);"></span>Em rota</span>
            </div>
            <div class="panorama-horizontal">
                {barras_gre}
            </div>
            <div class="info-box">A GRE com maior volume de pendências é <strong>{html_escape(gre_mais_pendente["GRE"])}</strong>, com <strong>{fmt_num(gre_mais_pendente["Pendências"])}</strong> escolas em andamento ou em rota.</div>
        </div>
    """

    bloco_ranking = f"""
        <div class="panel panel-pad">
            <div class="chart-title">Ranking de Pendências</div>
            <div style="font-size:13px;color:#516174;font-weight:750;">Total em andamento + em rota</div>
            {ranking}
            <div class="alert">Priorize as GREs com maior volume de pendências para acelerar a conclusão.</div>
        </div>
    """

    if mostra_setorizacao:
        bloco_principal = ""
    elif mostra_pendencias:
        bloco_principal = bloco_panorama + bloco_ranking
    else:
        bloco_principal = bloco_visao_geral + bloco_panorama + bloco_ranking

    bloco_setorizacao = f"""
        <div class="panel">
            <div class="panel-head">Quadro de Status por Setorização</div>
            <div class="panel-body">
                <div class="sector-grid">
                    {setorizacao}
                </div>
            </div>
        </div>
    """

    if mostra_setorizacao:
        grid_bottom = f"""
        <section class="grid-bottom-only">
            {bloco_setorizacao}
        </section>
        """
    else:
        grid_bottom = f"""
        <section class="grid-bottom">
            <div class="panel panel-pad">
                <div class="chart-title">Resumo Executivo</div>
                <div class="summary-line"><span class="check"></span><span>Mais da metade das escolas já está climatizada.</span></div>
                <div class="summary-line"><span class="check"></span><span>A GRE com maior pendência é <strong>{html_escape(gre_mais_pendente["GRE"])}</strong>.</span></div>
                <div class="summary-line"><span class="check"></span><span>A maior conclusão proporcional está em <strong>{html_escape(gre_melhor["GRE"])}</strong>.</span></div>
                <div class="summary-line"><span class="check"></span><span>A setorização deve ser acompanhada separadamente do total geral.</span></div>
            </div>
            {bloco_setorizacao}
        </section>
        """

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

* {{ box-sizing: border-box; }}

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

.kpis {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin: 16px 0;
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
    {grid_main_style}
    gap: 16px;
}}

.grid-bottom {{
    display: grid;
    grid-template-columns: 1.05fr 1.45fr;
    gap: 16px;
    margin-top: 16px;
}}

.grid-bottom-only {{
    margin-top: 16px;
}}

.panel {{
    background: white;
    border: 1px solid var(--borda);
    border-radius: 20px;
    box-shadow: 0 10px 24px rgba(10,40,80,.08);
    overflow: hidden;
}}

.panel-pad {{ padding: 18px; }}

.panel-head {{
    padding: 11px 18px;
    background: linear-gradient(90deg, var(--azul-noite), #0059A8);
    color: white;
    font-size: 17px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: .2px;
}}

.panel-body {{ padding: 18px; }}

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
    margin-top: 22px;
}}

.info-box strong {{ color: var(--azul-escuro); }}

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

@media (max-width: 1200px) {{
    .kpis,
    .grid-main,
    .grid-bottom,
    .grid-bottom-only,
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

    .title {{ font-size: 24px; }}
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
                <div class="subtitle">Período: {html_escape(periodo)} · GRE: {html_escape(gre)} · Visão: {html_escape(visao)}</div>
            </div>
        </div>
        <div class="map">PB</div>
    </header>

    <section class="kpis">
        <div class="kpi" style="--accent:var(--azul-escuro);--wash:var(--azul-gelo);">
            <div class="kpi-title">Total de Escolas</div>
            <div class="kpi-value">{fmt_num(total)}</div>
            <div class="kpi-sub">Base filtrada</div>
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
        {bloco_principal}
    </section>

    {grid_bottom}

    <div class="footer">
        Sincronizado: {data_hora} · atualização controlada a cada {REFRESH_SECONDS}s.
    </div>
</div>
</body>
</html>
"""
    return html


def aplicar_filtros(base: pd.DataFrame, setor: pd.DataFrame, periodo: str, gre: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_filtrada = base.copy()
    setor_filtrado = setor.copy()

    if periodo != "Todos":
        base_filtrada = base_filtrada[base_filtrada["Periodo"].astype(str) == str(periodo)]
        setor_filtrado = setor_filtrado[setor_filtrado["Periodo"].astype(str) == str(periodo)]

    if gre != "Todas":
        base_filtrada = base_filtrada[base_filtrada["GRE"] == gre]

    if setor_filtrado.empty:
        # Se a setorização não tiver o período filtrado, mantém todos os setores disponíveis.
        setor_filtrado = setor.copy()

    return base_filtrada, setor_filtrado


def renderizar():
    try:
        base, setor, total_linha, periodos = carregar_dados()
    except Exception as erro:
        st.error("Erro ao ler a planilha publicada no Google Sheets.")
        st.exception(erro)
        return

    st.markdown('<div class="filter-wrapper">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2.2], gap="medium")

    lista_periodos = periodos
    if len(lista_periodos) > 1:
        lista_periodos = ["Todos"] + lista_periodos

    with c1:
        periodo = st.selectbox("Período", lista_periodos, index=0 if "2026" not in lista_periodos else lista_periodos.index("2026"))

    base_periodo = base if periodo == "Todos" else base[base["Periodo"].astype(str) == str(periodo)]
    gres = ["Todas"] + base_periodo["GRE"].drop_duplicates().tolist()

    with c2:
        gre = st.selectbox("GRE", gres)

    with c3:
        visao = st.selectbox("Visão", ["Geral", "Pendências", "Setorização"])

    with c4:
        st.markdown(
            f'<div class="filter-note">Filtros ativos: <b>{periodo}</b> · <b>{gre}</b> · <b>{visao}</b> · sincronização a cada {REFRESH_SECONDS}s</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    base_filtrada, setor_filtrado = aplicar_filtros(base, setor, periodo, gre)

    if base_filtrada.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # A linha total só faz sentido quando GRE = Todas e período específico.
    total_usavel = total_linha if gre == "Todas" and periodo != "Todos" else None

    html = gerar_html_dashboard(
        base=base_filtrada,
        setor=setor_filtrado,
        total_linha=total_usavel,
        periodo=periodo,
        gre=gre,
        visao=visao,
    )

    components.html(html, height=1500, scrolling=True)


if hasattr(st, "fragment"):
    @st.fragment(run_every=f"{REFRESH_SECONDS}s")
    def painel():
        renderizar()

    painel()
else:
    renderizar()
