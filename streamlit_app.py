# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.3)
# CFTV & Alarmes • Visual Pro • PDF • Base64 + Gradiente
# =========================================================
import os, base64, requests
from io import BytesIO
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# 1) COLE AQUI O BASE64 DA SUA LOGO
LOGO_BASE64 = r"""
"""  # <- COLE aqui sua Base64 e deixe as aspas triplas fechando logo abaixo

# 2) Alternativas de fallback
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Paleta
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#1E293B"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#004AAD"   # Azul institucional
CLR_ORANGE = "#FF6600"   # Laranja da empresa
CLR_GREEN  = "#16A34A"
CLR_RED    = "#E11D48"

# ------------------ CSS ------------------
st.markdown(f"""
<style>
.stApp {{
  background:{CLR_BG};
  color:{CLR_TEXT};
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif;
  animation: fadein .3s ease;
}}
@keyframes fadein {{ from {{ opacity:0 }} to {{ opacity:1 }} }}

.top-wrap {{
  background: linear-gradient(90deg, {CLR_BLUE}, {CLR_ORANGE});
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 10px 25px rgba(0,0,0,.12);
  color: #fff;
}}

.logo-card {{
  background: rgba(255,255,255,.18);
  border: 1px solid rgba(255,255,255,.35);
  border-radius: 12px;
  padding: 6px;
  backdrop-filter: blur(4px);
}}

.title {{
  font-size: 26px; font-weight: 800; color: black; text-align:center;
}}
.subtitle {{ font-size: 12px; color: {CLR_SUB}; text-align:center; margin-top:-8px; }}

.btn-row .stButton>button {{
  background: #fff;
  color: {CLR_BLUE};
  border: 1px solid {CLR_BORDER};
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 600;
  transition: 0.2s ease;
  margin-right: 5px;
}}
.btn-row .stButton>button:hover {{
  transform: scale(1.05);
  background: {CLR_ORANGE};
  color: #fff;
}}
.btn-active {{
  background: {CLR_BLUE} !important;
  color: #fff !important;
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
.card:hover {{ transform: translateY(-2px); box-shadow:0 12px 28px rgba(2,12,27,.12); }}
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

# ------------------ LOGO (robusta) ------------------
def load_logo_bytes():
    if LOGO_BASE64.strip():
        try: return base64.b64decode(LOGO_BASE64.strip())
        except Exception: pass
    for p in LOGO_FILE_CANDIDATES:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f: return f.read()
            except Exception: pass
    try:
        r = requests.get(LOGO_URL_RAW, timeout=5)
        if r.ok: return r.content
    except Exception: pass
    return None

# ------------------ LEITURA DE DADOS ------------------
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(how="all").iloc[:, 0:7]
    raw.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                   "Alm_Total","Alm_Online","Alm_Status"]
    raw = raw.dropna(subset=["Local"])
    raw = raw[~raw["Local"].astype(str).str.contains("TOTAL|RELATORIO", case=False, na=False)]

    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce").fillna(0).astype(int)

    raw["Cam_Falta"] = (raw["Cam_Total"] - raw["Cam_Online"]).clip(lower=0)
    raw["Alm_Falta"] = (raw["Alm_Total"] - raw["Alm_Online"]).clip(lower=0)
    raw["Cam_OfflineBool"] = (raw["Cam_Total"]>0) & (raw["Cam_Online"]==0)
    raw["Alm_OfflineBool"] = (raw["Alm_Total"]>0) & (raw["Alm_Online"]==0)

    return raw.reset_index(drop=True)

# ------------------ FUNÇÕES VISUAIS ------------------
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
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False, "toImageFilename": f"grafico_{title.lower().replace(' ','_')}",
                            "modeBarButtonsToAdd":["toImage"]})

def chip(txt, cor):
    css = {"ok":CLR_GREEN, "warn":CLR_ORANGE, "off":CLR_RED}[cor]
    return f"<span style='color:{css}; font-weight:700;'>{txt}</span>"

# ------------------ PDF ------------------
def build_pdf_bytes(df: pd.DataFrame) -> bytes:
    class PDF(FPDF):
        def header(self):
            self.set_auto_page_break(auto=True, margin=15)
            self.set_font("helvetica", "B", 14)
            self.set_text_color(11,102,195)
            self.cell(0, 8, "Dashboard Operacional – Grupo Perímetro", ln=True, align="C")
            self.set_draw_color(230,231,235)
            self.set_line_width(0.4); self.line(10, 24, 200, 24)
            self.ln(2)
            self.set_font("helvetica", "", 9)
            self.set_text_color(90, 98, 110)
            self.cell(0, 6, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=True, align="C")
            self.ln(2)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(30,41,59)

    cam = df[df["Cam_Total"]>0]; alm = df[df["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    pdf.cell(0, 8, f"Câmeras: {cam_on}/{cam_tot} online • Offline: {cam_off}", ln=True)
    pdf.cell(0, 8, f"Alarmes: {alm_on}/{alm_tot} online • Offline: {alm_off}", ln=True)
    pdf.ln(4)
    out = BytesIO(); pdf.output(out); out.seek(0)
    return out.read()

# ------------------ TOPO ------------------
_logo = load_logo_bytes()
st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([0.15, 0.55, 0.30])
with col1:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo: st.image(_logo, use_container_width=True)
    else: st.warning("⚠️ Logo não carregada, mas o sistema continua funcionando.")
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
    total = int(base["Cam_Total"].sum()); online = int(base["Cam_Online"].sum())
    offline = total - online; locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)).sum())

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card'><div class='metric-sub'>Total</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    rows = base.copy()
    rows["__prio"] = np.where(rows["Cam_OfflineBool"], 2, np.where(rows["Cam_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Cam_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Cam_OfflineBool"] else f"FALTANDO {int(r['Cam_Falta'])}"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'><div class='local-title'>📍 {r['Local']} — {chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Cam_Total']} • Online: {r['Cam_Online']}</div></div>", unsafe_allow_html=True)

    bar_values({"Online": online, "Offline": offline, "Manutenção": locais_manut}, "Resumo de Câmeras")

# ------------------ ALARMES ------------------
def render_alarms(dfv):
    base = dfv[dfv["Alm_Total"]>0]
    st.markdown("#### 🚨 Alarmes")
    total = int(base["Alm_Total"].sum()); online = int(base["Alm_Online"].sum())
    offline = total - online; locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)).sum())

    a1,a2,a3,a4 = st.columns(4)
    a1.markdown(f"<div class='card'><div class='metric-sub'>Centrais Totais</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    a2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    a3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    a4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    rows = base.copy()
    rows["__prio"] = np.where(rows["Alm_OfflineBool"], 2, np.where(rows["Alm_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Alm_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Alm_OfflineBool"] else f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'><div class='local-title'>📍 {r['Local']} — {chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Alm_Total']} • Online: {r['Alm_Online']}</div></div>", unsafe_allow_html=True)

    bar_values({"Online": online, "Offline": offline, "Manutenção": locais_manut}, "Resumo de Alarmes")

# ------------------ GERAL ------------------
def render_geral(dfv):
    st.markdown("#### 📊 Geral (Câmeras + Alarmes)")
    cam = dfv[dfv["Cam_Total"]>0]; alm = dfv[dfv["Alm_Total"]>0]
    cam
