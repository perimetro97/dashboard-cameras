# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.5)
# CFTV & Alarmes • Visual Pro • Logo via GitHub
# =========================================================
import requests
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"
LOGO_URL = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# ------------------ PALETA DE CORES ------------------
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#1E293B"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#004AAD"
CLR_ORANGE = "#FF6600"
CLR_GREEN  = "#16A34A"
CLR_RED    = "#E11D48"

# ------------------ CSS ------------------
st.markdown(f"""
<style>
.stApp {{
  background:{CLR_BG};
  color:{CLR_TEXT};
  font-family: 'Inter', system-ui, Segoe UI, Roboto, sans-serif;
  animation: fadein .3s ease;
}}
@keyframes fadein {{ from {{ opacity:0 }} to {{ opacity:1 }} }}
.top-wrap {{
  background: linear-gradient(90deg, {CLR_BLUE}, {CLR_ORANGE});
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 10px 25px rgba(0,0,0,.12);
}}
.logo-card {{
  background: rgba(255,255,255,.18);
  border: 1px solid rgba(255,255,255,.35);
  border-radius: 12px;
  padding: 6px;
  text-align: center;
  transition: transform .3s ease;
}}
.logo-card:hover {{ transform: scale(1.05); }}
.title {{
  font-size: 26px;
  font-weight: 800;
  color: black;
  text-align:center;
  margin-bottom: -4px;
}}
.subtitle {{
  font-size: 12px;
  color: {CLR_SUB};
  text-align:center;
}}
.btn-row .stButton>button {{
  background: #fff;
  color: {CLR_BLUE};
  border: 1px solid {CLR_BORDER};
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 600;
  transition: 0.25s ease;
  margin-right: 6px;
}}
.btn-row .stButton>button:hover {{
  transform: scale(1.06);
  background: {CLR_ORANGE};
  color: #fff;
  box-shadow: 0 6px 16px rgba(255,102,0,.25);
}}
input[type="text"] {{
  border: 2px solid {CLR_BLUE} !important;
  border-radius: 8px !important;
  box-shadow: 0px 0px 6px rgba(0,74,173,0.25);
}}
.card {{
  background:{CLR_PANEL};
  border:1px solid {CLR_BORDER};
  border-radius:14px;
  padding:14px;
  box-shadow: 0 8px 20px rgba(2,12,27,.06);
  margin-bottom: 10px;
  transition: transform .08s ease, box-shadow .15s ease;
}}
.card:hover {{
  transform: translateY(-2px);
  box-shadow:0 12px 28px rgba(2,12,27,.12);
}}
.metric {{ font-size:30px; font-weight:900; }}
.metric-sub {{ font-size:12px; color:{CLR_SUB}; }}
.local-card {{
  background:#FAFBFF;
  border:1px solid {CLR_BORDER};
  border-left:6px solid {CLR_ORANGE};
  border-radius:14px;
  padding:12px 14px;
  margin-bottom:8px;
}}
.local-card.offline {{ border-left-color:{CLR_RED}; }}
.local-title {{ font-weight:900; font-size:15px; }}
.local-info  {{ color:{CLR_SUB}; font-size:12px; }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO ------------------
def load_logo_bytes():
    try:
        r = requests.get(LOGO_URL, timeout=6)
        if r.ok:
            return r.content
    except Exception:
        return None
    return None

# ------------------ DADOS ------------------
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=None)
    df = df.dropna(how="all").iloc[:, 0:7]
    df.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                  "Alm_Total","Alm_Online","Alm_Status"]
    df = df.dropna(subset=["Local"])
    df = df[~df["Local"].astype(str).str.contains("TOTAL|RELATORIO", case=False, na=False)]

    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Cam_Falta"] = (df["Cam_Total"] - df["Cam_Online"]).clip(lower=0)
    df["Alm_Falta"] = (df["Alm_Total"] - df["Alm_Online"]).clip(lower=0)
    df["Cam_OfflineBool"] = (df["Cam_Total"]>0) & (df["Cam_Online"]==0)
    df["Alm_OfflineBool"] = (df["Alm_Total"]>0) & (df["Alm_Online"]==0)
    return df.reset_index(drop=True)

# ------------------ GRÁFICO ------------------
def bar_values(values, title):
    dfc = pd.DataFrame({"Categoria": list(values.keys()), "Quantidade": list(values.values())})
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online":CLR_GREEN, "Offline":CLR_RED, "Manutenção":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, height=360,
                      margin=dict(l=10,r=10,t=50,b=20),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL,
                      font=dict(size=13), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ------------------ TOPO ------------------
_logo = load_logo_bytes()
st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([0.15, 0.55, 0.30])
with col1:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo:
        st.image(_logo, use_container_width=True)
    else:
        st.warning("⚠️ Logo não carregada (verifique o link do repositório).")
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='title'>Dashboard Operacional – CFTV & Alarmes</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)
with col3:
    query = st.text_input("🔎 Pesquisar local...", "", placeholder="Digite o nome do local…")
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.12,0.12,0.12,0.64], gap="small")
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

def tab_button(label, tab_name, key):
    active = (st.session_state.tab == tab_name)
    if st.button(label, key=key):
        st.session_state.tab = tab_name
    if active:
        st.markdown(f"<style>button[kind='primary'][key='{key}']{{background:{CLR_BLUE};color:white;}}</style>", unsafe_allow_html=True)

with b1: tab_button("📷 Câmeras", "Câmeras", "btn_cam")
with b2: tab_button("🚨 Alarmes", "Alarmes", "btn_alm")
with b3: tab_button("📊 Geral",   "Geral",   "btn_ger")
st.divider()

# ------------------ DADOS ------------------
df = load_data(PLANILHA)
dfv = df if not query.strip() else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ CÂMERAS ------------------
def render_cameras(dfv):
    base = dfv[dfv["Cam_Total"]>0]
    st.markdown("#### 📷 Câmeras")
    total = int(base["Cam_Total"].sum())
    online = int(base["Cam_Online"].sum())
    offline = total - online
    locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)).sum())

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Online", online)
    c3.metric("Offline", offline)
    c4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online, "Offline": offline, "Manutenção": locais_manut}, "Resumo de Câmeras")

# ------------------ ALARMES ------------------
def render_alarms(dfv):
    base = dfv[dfv["Alm_Total"]>0]
    st.markdown("#### 🚨 Alarmes")
    total = int(base["Alm_Total"].sum())
    online = int(base["Alm_Online"].sum())
    offline = total - online
    locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)).sum())

    a1,a2,a3,a4 = st.columns(4)
    a1.metric("Centrais Totais", total)
    a2.metric("Online", online)
    a3.metric("Offline", offline)
    a4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online, "Offline": offline, "Manutenção": locais_manut}, "Resumo de Alarmes")

# ------------------ GERAL ------------------
def render_geral(dfv):
    st.markdown("#### 📊 Geral (Câmeras + Alarmes)")
    cam = dfv[dfv["Cam_Total"]>0]
    alm = dfv[dfv["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.metric("Câmeras Online", cam_on)
    g2.metric("Alarmes Online", alm_on)
    g3.metric("Total de Câmeras", cam_tot)
    g4.metric("Total de Alarmes", alm_tot)
    g5.metric("Câmeras Offline", cam_off)
    g6.metric("Alarmes Offline", alm_off)
    bar_values({"Online": cam_on+alm_on, "Offline": cam_off+alm_off, "Manutenção": 0}, "Resumo Geral")

# ------------------ DISPATCH ------------------
tab = st.session_state.tab
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro • Dashboard Operacional v5.5")
