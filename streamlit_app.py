# =========================================================
# Dashboard Operacional – Grupo Perímetro
# CFTV & Alarmes | Tema Escuro Tecnológico | Streamlit 1.38
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ---------- CONFIGURAÇÃO DE PÁGINA ----------
st.set_page_config(
    page_title="Dashboard Operacional – CFTV & Alarmes",
    page_icon="🛡️",
    layout="wide"
)

# ---------- CORES E ESTILOS ----------
PRIMARY_NEON = "#00E5FF"
SUCCESS_NEON = "#17E66E"
WARN_NEON    = "#FFD54A"
DANGER_NEON  = "#FF4D4D"
BG_DARK      = "#0D0F14"
PANEL_DARK   = "#141823"
TEXT_LIGHT   = "#E6E8EE"

PLANILHA = "dados.xlsx"
LOGO_PATH = "logo_perimetro.png"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG_DARK};
        color: {TEXT_LIGHT};
        font-family: 'Inter', sans-serif;
    }}
    .big-title {{
        font-size: 22px; font-weight: 700;
        color: {PRIMARY_NEON};
    }}
    .card {{
        background: {PANEL_DARK};
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 0 18px rgba(0,229,255,.08);
        border: 1px solid rgba(255,255,255,0.06);
    }}
    .tag-ok {{color:{SUCCESS_NEON};}}
    .tag-warn {{color:{WARN_NEON};}}
    .tag-off {{color:{DANGER_NEON};}}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# FUNÇÃO PRINCIPAL DE LEITURA DA PLANILHA
# =========================================================
@st.cache_data(show_spinner=False)
def load_data(planilha_path: str):
    try:
        df_raw = pd.read_excel(planilha_path, header=None)

        # Localiza a primeira linha com "OK", "OFFLINE" ou "FALTANDO"
        start_index = None
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains("OK|OFFLINE|FALTANDO", case=False, na=False).any():
                start_index = max(i - 1, 0)
                break
        if start_index is None:
            start_index = 3

        df = df_raw.iloc[start_index:, :8].copy()

        # Garante 7 colunas
        if df.shape[1] < 7:
            for _ in range(7 - df.shape[1]):
                df[df.shape[1]] = np.nan
        elif df.shape[1] > 7:
            df = df.iloc[:, :7]

        df.columns = [
            "A_Local", "B_TotalCam", "C_OnlineCam", "D_StatusCam",
            "E_TotalAlm", "F_OnlineAlm", "G_PercentAlm"
        ]

        df = df.dropna(how="all")
        df["A_Local"] = df["A_Local"].astype(str).str.strip()

        # Converte números
        for col in ["B_TotalCam", "C_OnlineCam", "E_TotalAlm", "F_OnlineAlm"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Percentual de alarmes
        def calc_percent(row):
            if row["E_TotalAlm"] <= 0:
                return 0.0
            return round((row["F_OnlineAlm"] / row["E_TotalAlm"]) * 100, 2)

        df["G_PercentAlm"] = df["G_PercentAlm"].apply(
            lambda v: float(str(v).replace("%", "").strip()) if pd.notna(v) else np.nan
        )
        df["G_PercentAlm"] = np.where(
            df["G_PercentAlm"].notna(),
            df["G_PercentAlm"],
            df.apply(calc_percent, axis=1)
        )

        # Status de câmeras
        def status_cam(row):
            total, online = row["B_TotalCam"], row["C_OnlineCam"]
            s = str(row["D_StatusCam"]).strip().upper()
            if "OK" in s or "EXCESSO" in s or "FALTANDO" in s or "OFFLINE" in s:
                return s
            if total == 0:
                return "SEM DADOS"
            if online == total:
                return "OK"
            if online > total:
                return "EXCESSO"
            if online == 0:
                return "OFFLINE"
            return f"FALTANDO {total - online}"

        df["D_StatusCam"] = df.apply(status_cam, axis=1)

        # Status de alarmes
        def status_alm(p):
            if p >= 99.9:
                return "100%"
            if p >= 66:
                return "PARCIAL (≥66%)"
            if p >= 50:
                return "PARCIAL (50%)"
            if p > 0:
                return "PARCIAL (<50%)"
            return "OFFLINE"

        df["Alarmes_Status"] = df["G_PercentAlm"].apply(status_alm)
        return df

    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return pd.DataFrame(columns=[
            "A_Local", "B_TotalCam", "C_OnlineCam", "D_StatusCam",
            "E_TotalAlm", "F_OnlineAlm", "G_PercentAlm", "Alarmes_Status"
        ])

# =========================================================
# CARREGAR OS DADOS
# =========================================================
df = load_data(PLANILHA)

if df.empty:
    st.warning("⚠️ Não foi possível ler os dados. Verifique a planilha.")
    st.stop()

# =========================================================
# CABEÇALHO
# =========================================================
col_logo, col_title = st.columns([0.12, 0.88])
with col_logo:
    st.image(LOGO_PATH, width=80)
with col_title:
    st.markdown(
        f"<div class='big-title'>Dashboard Operacional – CFTV & Alarmes</div>"
        f"<div style='color:#9aa3b2;font-size:12px;'>Atualizado em "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

# =========================================================
# MENU DE NAVEGAÇÃO
# =========================================================
tab = st.radio("Escolha a visualização:", ["📷 Câmeras", "🚨 Alarmes"], horizontal=True)
pesquisa = st.text_input("Pesquisar local...", "")

if pesquisa:
    df = df[df["A_Local"].str.contains(pesquisa, case=False, na=False)]

# =========================================================
# VISUAL CÂMERAS
# =========================================================
if "Câmeras" in tab:
    st.subheader("📷 Status das Câmeras")

    total_cam = int(df["B_TotalCam"].sum())
    online_cam = int(df["C_OnlineCam"].sum())
    offline_cam = max(total_cam - online_cam, 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Câmeras", total_cam)
    with col2:
        st.metric("Online", online_cam)
    with col3:
        st.metric("Offline / Faltando", offline_cam)

    for _, row in df.iterrows():
        st.markdown(
            f"<div class='card'>📍 <b>{row['A_Local']}</b> — "
            f"<span class='tag-{ 'ok' if 'OK' in row['D_StatusCam'] else 'off' if 'OFFLINE' in row['D_StatusCam'] else 'warn'}'>"
            f"{row['D_StatusCam']}</span></div>",
            unsafe_allow_html=True
        )

# =========================================================
# VISUAL ALARMES
# =========================================================
else:
    st.subheader("🚨 Status dos Alarmes")

    total_alm = int(df["E_TotalAlm"].sum())
    online_alm = int(df["F_OnlineAlm"].sum())
    perc = round((online_alm / total_alm * 100), 1) if total_alm > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Centrais Totais", total_alm)
    with c2:
        st.metric("Online", online_alm)
    with c3:
        st.metric("Percentual Geral", f"{perc}%")

    for _, row in df.iterrows():
        cor = "ok" if row["Alarmes_Status"] == "100%" else "warn" if "PARCIAL" in row["Alarmes_Status"] else "off"
        st.markdown(
            f"<div class='card'>📍 <b>{row['A_Local']}</b> — "
            f"<span class='tag-{cor}'>{row['Alarmes_Status']}</span> "
            f"<small>({row['G_PercentAlm']:.0f}% online)</small></div>",
            unsafe_allow_html=True
        )

# =========================================================
st.caption("© Grupo Perímetro • Dashboard Operacional • v1.2 (2025)")
