# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.7)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
import pytz  # <── adicionado para horário de Brasília

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="📹", layout="wide")

PLANILHA = "dados.xlsx"
ROOT_PATH = Path(__file__).parent
PLANILHA_PATH = ROOT_PATH / PLANILHA

# Logo
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Ícones na raiz do repositório
ICON_CAMERA     = "camera.png"
ICON_ALARME     = "alarme.png"
ICON_ENGRENAGEM = "engrenagem.png"
ICON_RELATORIO  = "relatorio.png"

# Paleta de cores
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#111827"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#0B66C3"
CLR_ORANGE = "#F37021"
CLR_GREEN  = "#16A34A"
CLR_RED    = "#E11D48"

# ------------------ CSS ------------------
st.markdown(f"""
<style>
  .stApp {{
    background:{CLR_BG};
    color:{CLR_TEXT};
    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif;
    animation: fadein .25s ease;
  }}
  @keyframes fadein {{ from {{ opacity:0 }} to {{ opacity:1 }} }}

  .top-wrap {{
    background: linear-gradient(90deg, {CLR_BLUE} 0%, {CLR_ORANGE} 100%);
    border-radius: 18px; padding: 14px 16px;
    box-shadow: 0 10px 22px rgba(0,0,0,.10); color: #fff;
  }}
  .logo-card {{
    background: rgba(255,255,255,.20); border: 1px solid rgba(255,255,255,.35);
    border-radius: 12px; padding: 8px; backdrop-filter: blur(3px);
  }}
  .title {{
    font-size: 28px; font-weight: 900; letter-spacing:.2px;
    color:{CLR_TEXT}; margin-bottom: 2px;
  }}
  .subtitle {{ font-size: 12px; color: rgba(17,24,39,.75); }}

  .btn-row .stButton>button {{
    background: #fff; color: {CLR_BLUE}; border: 1px solid {CLR_BORDER};
    border-radius: 12px; padding: 10px 14px; font-weight: 700;
    box-shadow: 0 6px 14px rgba(0,0,0,.06);
    transition: transform .08s ease, box-shadow .15s ease, background .15s ease;
    margin-right: 6px;
  }}
  .btn-row .stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 10px 22px rgba(0,0,0,.12); }}
  .btn-active {{ background: {CLR_BLUE} !important; color: #fff !important; }}

  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER};
    border-radius:16px; padding:16px;
    box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px;
  }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}
  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}
  .local-card {{
    background:#FAFBFF; border:1px solid {CLR_BORDER};
    border-left:6px solid {CLR_ORANGE}; border-radius:14px;
    padding:12px 14px; margin-bottom:10px;
  }}
  .local-card.offline {{ border-left-color:{CLR_RED}; }}
  .local-title {{ font-weight:900; font-size:16px; }}
  .local-info  {{ color:{CLR_SUB}; font-size:12px; margin-top:2px; }}
  .search-box .stTextInput>div>div>input {{
    border:1px solid {CLR_BORDER};
    box-shadow: 0 2px 8px rgba(11,102,195,.07);
  }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO ------------------
def load_logo_bytes() -> bytes | None:
    for p in LOGO_FILE_CANDIDATES:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok:
            return r.content
    except:
        pass
    return None

# ------------------ LEITURA DE DADOS ------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE","SEM ALARME","SEM CAMERAS","SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(how="all").iloc[:, 0:7]
    raw.columns = ["Local","Cam_Total","Cam_Online","Cam_Status","Alm_Total","Alm_Online","Alm_Status"]
    raw = raw.dropna(subset=["Local"])
    raw = raw[~raw["Local"].astype(str).str.contains("TOTAL|RELATÓRIO|RELATORIO", case=False, na=False)]
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        raw[c] = raw[c].apply(_to_int)
    raw["Cam_Falta"] = (raw["Cam_Total"] - raw["Cam_Online"]).clip(lower=0)
    raw["Alm_Falta"] = (raw["Alm_Total"] - raw["Alm_Online"]).clip(lower=0)
    raw["Cam_OfflineBool"] = (raw["Cam_Total"]>0) & (raw["Cam_Online"]==0)
    raw["Alm_OfflineBool"] = (raw["Alm_Total"]>0) & (raw["Alm_Online"]==0)
    return raw.reset_index(drop=True)

# ------------------ HEADER ------------------
_logo_bytes = load_logo_bytes()

st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
c_logo, c_title, c_search = st.columns([0.12, 0.58, 0.30])
with c_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo_bytes: st.image(_logo_bytes, use_container_width=True)
    else: st.warning("⚠️ Logo não carregada.")
    st.markdown("</div>", unsafe_allow_html=True)
with c_title:
    hora_brasilia = datetime.now(pytz.timezone("America/Sao_Paulo"))
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='subtitle'>Atualizado em {hora_brasilia.strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with c_search:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ DADOS ------------------
try:
    df = load_data(PLANILHA_PATH)
except Exception as e:
    st.error("Erro ao ler a planilha `dados.xlsx`. Verifique se está na raiz do repositório.")
    st.exception(e)
    st.stop()

if df.empty:
    st.error("Planilha sem dados válidos.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].astype(str).str.contains(query.strip(), case=False, na=False)]

# ------------------ FUNÇÕES ------------------
def chip(texto, tipo):
    cls = "ok" if tipo=="ok" else ("warn" if tipo=="warn" else "off")
    return f"<span class='chip {cls}'>{texto}</span>"

def bar_values(values, title):
    dfc = pd.DataFrame({"Categoria": list(values.keys()), "Quantidade": list(values.values())})
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online": CLR_GREEN,"Offline": CLR_RED,"Locais p/ manutenção": CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, height=360, paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL,
                      margin=dict(l=10,r=10,t=50,b=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

# ---- RENDER: CÂMERAS ----
def render_cameras(dfx):
    st.markdown(f"<h4 style='display:flex;align-items:center;gap:8px;'><img src='{ICON_CAMERA}' width='24'/> Câmeras</h4>", unsafe_allow_html=True)
    base = dfx[dfx["Cam_Total"] > 0]
    total, online = int(base["Cam_Total"].sum()), int(base["Cam_Online"].sum())
    offline, locais_manut = max(total-online,0), int(((base["Cam_OfflineBool"])|(base["Cam_Falta"]>0)).sum())
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Online", online)
    c3.metric("Offline", offline)
    c4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online,"Offline": offline,"Locais p/ manutenção": locais_manut}, "Resumo de Câmeras")

# ---- RENDER: ALARMES ----
def render_alarms(dfx):
    st.markdown(f"<h4 style='display:flex;align-items:center;gap:8px;'><img src='{ICON_ALARME}' width='24'/> Alarmes</h4>", unsafe_allow_html=True)
    base = dfx[dfx["Alm_Total"] > 0]
    total, online = int(base["Alm_Total"].sum()), int(base["Alm_Online"].sum())
    offline, locais_manut = max(total-online,0), int(((base["Alm_OfflineBool"])|(base["Alm_Falta"]>0)).sum())
    a1,a2,a3,a4 = st.columns(4)
    a1.metric("Centrais Totais", total)
    a2.metric("Online", online)
    a3.metric("Offline", offline)
    a4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online,"Offline": offline,"Locais p/ manutenção": locais_manut}, "Resumo de Alarmes")

# ---- RENDER: GERAL + RELATÓRIO ----
def render_geral(dfx):
    st.markdown(f"<h4 style='display:flex;align-items:center;gap:8px;'><img src='{ICON_RELATORIO}' width='24'/> Geral (Câmeras + Alarmes)</h4>", unsafe_allow_html=True)
    cam, alm = dfx[dfx["Cam_Total"]>0], dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on
    locais_manut = int(((dfx["Cam_OfflineBool"])|(dfx["Cam_Falta"]>0)|(dfx["Alm_OfflineBool"])|(dfx["Alm_Falta"]>0)).sum())
    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.metric("Câmeras Online", cam_on)
    g2.metric("Alarmes Online", alm_on)
    g3.metric("Total de Câmeras", cam_tot)
    g4.metric("Total de Alarmes", alm_tot)
    g5.metric("Câmeras Offline", cam_off)
    g6.metric("Alarmes Offline", alm_off)
    bar_values({"Online": cam_on+alm_on,"Offline": cam_off+alm_off,"Locais p/ manutenção": locais_manut}, "Resumo Geral")

    st.markdown("### 📄 Relatório de Locais com Problemas")
    if st.button("🖨️ Gerar Relatório PDF"):
        faltando = dfx[(dfx["Cam_Falta"]>0)|(dfx["Alm_Falta"]>0)].copy()
        if faltando.empty:
            st.info("Nenhum local com falhas no momento.")
        else:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            pdf_name = "Relatório_Cftv&alarmes.pdf"
            doc = SimpleDocTemplate(pdf_name, pagesize=A4)
            styles = getSampleStyleSheet()
            data = [["Local","Câmeras Faltantes","Alarmes Faltantes"]]
            for _,r in faltando.iterrows():
                data.append([str(r["Local"]), int(r["Cam_Falta"]), int(r["Alm_Falta"])])
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0B66C3")),
                ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ]))
            elements=[Paragraph("<b>Relatório de Locais com Falhas</b>",styles["Title"]),Spacer(1,10),table]
            doc.build(elements)
            with open(pdf_name,"rb") as f:
                st.download_button("⬇️ Baixar Relatório PDF",f,file_name=pdf_name,mime="application/pdf")

# ------------------ DISPATCH ------------------
tab = st.radio("", ["Câmeras","Alarmes","Geral"], horizontal=True)
if tab == "Câmeras": render_cameras(dfv)
elif tab == "Alarmes": render_alarms(dfv)
else: render_geral(dfv)

st.caption("© Grupo Perímetro & Monitoramento • Dashboard Operacional")
