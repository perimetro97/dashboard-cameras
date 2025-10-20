# =========================================================
# Dashboard Operacional – Grupo Perímetro
# CFTV & Alarmes | Tema Escuro | Streamlit 1.38 (Py 3.12)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --------- CONFIG ---------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"
LOGO_PATH = "logo_perimetro.png"

PRIMARY = "#00E5FF"; OKC="#17E66E"; WARN="#FFD54A"; DNG="#FF4D4D"
BG="#0D0F14"; PANEL="#141823"; TEXT="#E6E8EE"

st.markdown(f"""
<style>
.stApp {{ background:{BG}; color:{TEXT}; font-family:Inter, system-ui; }}
h1,h2,h3 {{ color:{PRIMARY}; }}
.card {{ background:{PANEL}; border:1px solid rgba(255,255,255,.06);
        padding:16px; border-radius:12px; box-shadow:0 0 18px rgba(0,229,255,.08); }}
.small {{ color:#9aa3b2; font-size:12px; }}
.tag-ok {{ color:{OKC}; }} .tag-warn {{ color:{WARN}; }} .tag-off {{ color:{DNG}; }}
</style>
""", unsafe_allow_html=True)

# --------- HELPERS ---------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s == "OFFLINE": return 0
    try:
        return int(float(s))
    except:
        return 0

# --------- LOAD DATA (ajustado para sua planilha) ---------
@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, header=None)     # 55 x 15 na planilha enviada

    # localizar a linha de cabeçalho (onde aparecem os títulos)
    hdr = None
    for i, row in df.iterrows():
        s = row.astype(str).str.upper()
        if s.str.contains("POSTOS MONITORADOS").any() and \
           s.str.contains("QUANTIDADE DE CÂMERAS FIXA").any():
            hdr = i; break
    if hdr is None: hdr = 2   # fallback (linha 3 da planilha)

    # recorte apenas do bloco da esquerda (colunas 0..6), dados começam na linha seguinte ao cabeçalho
    data = df.iloc[hdr+1:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]

    # remover linhas vazias e o "espelho" / totais do fim
    data = data[~data["Local"].isna()]
    data = data[~data["Local"].astype(str).str.contains("TOTAL|FUNCIONANDO|OFFLINE|EXCESSO|202", case=False, na=False)]

    # números
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(_to_int)

    # status câmeras (preenche se vier vazio)
    def cam_status(row):
        s = str(row["Cam_Status"]).strip().upper()
        tot, on = row["Cam_Total"], row["Cam_Online"]
        if s and s != "NAN":
            return s
        if tot == 0: return "SEM CÂMERAS"
        if on == tot: return "OK"
        if on > tot:  return "EXCESSO"
        if on == 0:   return "OFFLINE"
        return f"FALTANDO {max(tot-on,0)}"

    data["Cam_Status"] = data.apply(cam_status, axis=1)

    # % alarmes
    def alm_percent(row):
        tot, on = row["Alm_Total"], row["Alm_Online"]
        if tot <= 0: return 0.0
        return round(100.0 * on / tot, 2)
    data["Alm_Percent"] = data.apply(alm_percent, axis=1)

    # status alarmes (prioriza texto; senão classifica pela %)
    def alm_status(row):
        s = str(row["Alm_Status"]).strip().upper()
        if "100%" in s:   return "100%"
        if "50%" in s:    return "PARCIAL (50%)"
        if "OFFLINE" in s or "SEM ALARME" in s: return "OFFLINE"
        p = row["Alm_Percent"]
        if p >= 99.9: return "100%"
        if p >= 66:   return "PARCIAL (≥66%)"
        if p >= 50:   return "PARCIAL (50%)"
        if p > 0:     return "PARCIAL (<50%)"
        return "OFFLINE"

    data["Alm_Status"] = data.apply(alm_status, axis=1)

    # normalizações finais
    data["Local"] = data["Local"].astype(str).str.strip()
    return data.reset_index(drop=True)

# --------- CARREGA ---------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha. Verifique o arquivo `dados.xlsx`.")
    st.stop()

# --------- HEADER ---------
c1, c2 = st.columns([0.12, 0.88])
with c1: st.image(LOGO_PATH, width=80)
with c2:
    st.markdown(f"### Dashboard Operacional – CFTV & Alarmes")
    st.markdown(f"<span class='small'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>",
                unsafe_allow_html=True)

# --------- BUSCA + TOGGLE ---------
col_a, col_b = st.columns([0.6,0.4])
with col_a:
    tab = st.radio(" ", ["📷 Câmeras", "🚨 Alarmes"], horizontal=True, label_visibility="collapsed")
with col_b:
    query = st.text_input("Pesquisar local...", "", placeholder="Pesquisar local...")

dff = df.copy()
if query.strip():
    dff = dff[dff["Local"].str.contains(query.strip(), case=False, na=False)]

# --------- CÂMERAS ---------
if "Câmeras" in tab:
    st.subheader("📷 Câmeras")
    tot = int(dff["Cam_Total"].sum())
    on  = int(dff["Cam_Online"].sum())
    off = max(tot - on, 0)

    m1,m2,m3 = st.columns(3)
    m1.metric("Total de Câmeras", tot)
    m2.metric("Online", on)
    m3.metric("Offline / Faltando", off)

    for _, r in dff.sort_values("Local").iterrows():
        css = "tag-ok" if "OK" in r["Cam_Status"] else "tag-off" if "OFFLINE" in r["Cam_Status"] else "tag-warn"
        st.markdown(
            f"<div class='card'>📍 <b>{r['Local']}</b> — "
            f"<span class='{css}'>{r['Cam_Status']}</span> "
            f"<span class='small'>&nbsp;• Total: {r['Cam_Total']} · Online: {r['Cam_Online']}</span></div>",
            unsafe_allow_html=True
        )

# --------- ALARMES ---------
else:
    st.subheader("🚨 Alarmes")
    tot = int(dff["Alm_Total"].sum())
    on  = int(dff["Alm_Online"].sum())
    perc = round((on/tot*100),1) if tot>0 else 0.0

    m1,m2,m3 = st.columns(3)
    m1.metric("Centrais Totais", tot)
    m2.metric("Online", on)
    m3.metric("Percentual Geral", f"{perc}%")

    for _, r in dff.sort_values("Local").iterrows():
        cor = "tag-ok" if r["Alm_Status"]=="100%" else ("tag-warn" if "PARCIAL" in r["Alm_Status"] else "tag-off")
        st.markdown(
            f"<div class='card'>📍 <b>{r['Local']}</b> — "
            f"<span class='{cor}'>{r['Alm_Status']}</span> "
            f"<span class='small'>&nbsp;• Total: {r['Alm_Total']} · Online: {r['Alm_Online']} · {r['Alm_Percent']:.0f}%</span></div>",
            unsafe_allow_html=True
        )

st.caption("© Grupo Perímetro • Dashboard Operacional • v1.3")
