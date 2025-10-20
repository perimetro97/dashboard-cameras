# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3.5)
# Logo embutida • CFTV & Alarmes • PDF • Correções visuais
# =========================================================
import os
import base64
from io import BytesIO
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF

# ------------- CONFIG -------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Paleta
CLR_BG     = "#F4F5F7"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#2E2E2E"
CLR_SUB    = "#6A7380"
CLR_BORDER = "#E6E9EF"
CLR_BLUE   = "#0072CE"
CLR_ORANGE = "#F37021"
CLR_GREEN  = "#17C964"
CLR_RED    = "#E5484D"

# ------------- CSS -------------
st.markdown(f"""
<style>
.stApp {{
    background:{CLR_BG};
    color:{CLR_TEXT};
    font-family:Inter,system-ui;
}}
.logo-card {{
    background:{CLR_PANEL};
    border:1px solid {CLR_BORDER};
    border-radius:12px;
    padding:8px;
    box-shadow:0 6px 18px rgba(0,0,0,.06);
}}
.title {{
    font-size:26px;
    font-weight:800;
    color:{CLR_BLUE};
    margin-bottom:2px;
}}
.sub {{
    font-size:12px;
    color:{CLR_SUB};
}}
.card {{
    background:{CLR_PANEL};
    border:1px solid {CLR_BORDER};
    border-radius:14px;
    padding:14px;
    box-shadow:0 8px 24px rgba(0,0,0,.06);
    margin-bottom:10px;
}}
.metric {{ font-size:28px; font-weight:800; }}
.tag {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px; }}
.tag-ok   {{ color:{CLR_GREEN};  background:rgba(23,201,100,.12); }}
.tag-warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12); }}
.tag-off  {{ color:{CLR_RED};    background:rgba(229,72,77,.12); }}
.btn-row .stButton > button {{ margin-right:8px; margin-left:0; padding:8px 14px; border-radius:10px; }}
</style>
""", unsafe_allow_html=True)

# ============== LOGO EMBUTIDA ==============
logo_base64 = """
iVBORw0KGgoAAAANSUhEUgAAAoAAAAKACAYAAAC0HzYfAAA...
"""  # substituído por código base64 completo da logo Grupo Perímetro

# Converter Base64 → bytes
try:
    logo_bytes = base64.b64decode(logo_base64)
except Exception:
    logo_bytes = None

# ============== FUNÇÕES AUXILIARES ==============
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CAMERAS", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=None)
    df = df.dropna(how="all")
    df = df.iloc[:, 0:7]
    df.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                  "Alm_Total","Alm_Online","Alm_Status"]
    df = df.dropna(subset=["Local"])
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        df[c] = df[c].apply(_to_int)
    df["Cam_Falta"] = (df["Cam_Total"] - df["Cam_Online"]).clip(lower=0)
    df["Alm_Falta"] = (df["Alm_Total"] - df["Alm_Online"]).clip(lower=0)
    df["Cam_OfflineBool"] = (df["Cam_Total"]>0) & (df["Cam_Online"]==0)
    df["Alm_OfflineBool"] = (df["Alm_Total"]>0) & (df["Alm_Online"]==0)
    return df.reset_index(drop=True)

def card_local(local, status, info, cor="ok"):
    tag = "tag-ok" if cor=="ok" else ("tag-warn" if cor=="warn" else "tag-off")
    st.markdown(
        f"<div class='card'><b>📍 {local}</b> — <span class='{tag}'>{status}</span>"
        f"<div class='sub' style='margin-top:6px;'>{info}</div></div>", unsafe_allow_html=True
    )

def bar_single(values: dict, title: str):
    dfc = pd.DataFrame({"Categoria": list(values.keys()),
                        "Quantidade": list(values.values())})
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online":CLR_GREEN,
                                     "Offline":CLR_RED,
                                     "Locais p/ manutenção":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, height=340, margin=dict(l=10,r=10,t=40,b=10),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# PDF
def build_pdf(df: pd.DataFrame) -> bytes:
    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 8, "Dashboard Operacional – Grupo Perímetro", ln=True, align="C")
            self.set_font("Helvetica", "", 10)
            self.cell(0, 6, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=True, align="C")
            self.ln(3)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    cam_ok = df[df["Cam_Total"]>0]
    alm_ok = df[df["Alm_Total"]>0]
    cam_tot, cam_on = int(cam_ok["Cam_Total"].sum()), int(cam_ok["Cam_Online"].sum())
    alm_tot, alm_on = int(alm_ok["Alm_Total"].sum()), int(alm_ok["Alm_Online"].sum())
    pdf.cell(0, 8, f"Câmeras: {cam_on}/{cam_tot} • Alarmes: {alm_on}/{alm_tot}", ln=True)
    out = BytesIO(); pdf.output(out); out.seek(0)
    return out.read()

# ============== HEADER ==============
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if logo_bytes:
        st.image(logo_bytes, use_container_width=True)
    else:
        st.warning("⚠️ Logo não carregada, mas o sistema continua funcionando.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='sub'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local...")

# ============== ABAS ==============
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([0.2,0.2,0.2])
if 'tab' not in st.session_state: st.session_state['tab'] = "Câmeras"
if c1.button("📷 Câmeras"): st.session_state['tab'] = "Câmeras"
if c2.button("🚨 Alarmes"): st.session_state['tab'] = "Alarmes"
if c3.button("📊 Geral"): st.session_state['tab'] = "Geral"
st.markdown("</div>", unsafe_allow_html=True)

# ============== DADOS ==============
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha `dados.xlsx`.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ============== FUNÇÕES DE RENDER ==============
def render_cameras(dfx):
    base = dfx[dfx["Cam_Total"]>0]
    st.markdown("### 📷 Câmeras")
    tot, on = int(base["Cam_Total"].sum()), int(base["Cam_Online"].sum())
    off = max(tot - on, 0)
    manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)).sum())
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total", tot); m2.metric("Online", on)
    m3.metric("Offline", off); m4.metric("Locais p/ manutenção", manut)
    rows = base.copy()
    rows["__prio"] = np.where(rows["Cam_OfflineBool"],2,np.where(rows["Cam_Falta"]>0,1,0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Cam_Falta"],ascending=[False,False])
    st.markdown("#### Locais para manutenção / offline")
    for _,r in rows.iterrows():
        status = "OFFLINE" if r["Cam_OfflineBool"] else f"FALTANDO {int(r['Cam_Falta'])}"
        cor = "off" if status=="OFFLINE" else "warn"
        info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
        card_local(r["Local"],status,info,cor)
    bar_single({"Online": on, "Offline": off, "Locais p/ manutenção": manut},"Resumo de Câmeras")

def render_alarms(dfx):
    base = dfx[dfx["Alm_Total"]>0]
    st.markdown("### 🚨 Alarmes")
    tot, on = int(base["Alm_Total"].sum()), int(base["Alm_Online"].sum())
    off = max(tot - on, 0)
    manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)).sum())
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total", tot); m2.metric("Online", on)
    m3.metric("Offline", off); m4.metric("Locais p/ manutenção", manut)
    rows = base.copy()
    rows["__prio"] = np.where(rows["Alm_OfflineBool"],2,np.where(rows["Alm_Falta"]>0,1,0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Alm_Falta"],ascending=[False,False])
    st.markdown("#### Locais para manutenção / offline")
    for _,r in rows.iterrows():
        status = "OFFLINE" if r["Alm_OfflineBool"] else f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        cor = "off" if status=="OFFLINE" else "warn"
        info = f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']}"
        card_local(r["Local"],status,info,cor)
    bar_single({"Online": on, "Offline": off, "Locais p/ manutenção": manut},"Resumo de Alarmes")

def render_geral(dfx):
    st.markdown("### 📊 Geral (Câmeras + Alarmes)")
    cam, alm = dfx[dfx["Cam_Total"]>0], dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot - cam_on, alm_tot - alm_on
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Câmeras Online", cam_on)
    c2.metric("Alarmes Online", alm_on)
    c3.metric("Total Câmeras", cam_tot)
    c4.metric("Total Alarmes", alm_tot)
    c5.metric("Câmeras Offline", cam_off)
    c6.metric("Alarmes Offline", alm_off)
    bar_single({"Online": cam_on+alm_on, "Offline": cam_off+alm_off,
                "Locais p/ manutenção": 0},"Resumo Geral")
    st.download_button("📄 Baixar PDF",
                       data=build_pdf(dfx),
                       file_name="relatorio_perimetro.pdf",
                       mime="application/pdf")

# ============== DESPACHO ==============
tab = st.session_state['tab']
if tab=="Câmeras": render_cameras(dfv)
elif tab=="Alarmes": render_alarms(dfv)
else: render_geral(dfv)
st.caption("© Grupo Perímetro • Dashboard Operacional v3.5")
