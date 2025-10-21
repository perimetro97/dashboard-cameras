# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.3)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
import pytz  # horário de Brasília

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

# Logo somente do repositório / arquivo (sem Base64)
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# ------------------ ÍCONES ------------------
ICON_DIR = Path(__file__).parent

def icon_src(local_path, github_filename):
    if os.path.exists(local_path):
        return local_path
    return f"https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/{github_filename}"

ICON_CAMERA_SRC     = icon_src(str(ICON_DIR / "camera.png"), "camera.png")
ICON_ALARME_SRC     = icon_src(str(ICON_DIR / "alarme.png"), "alarme.png")
ICON_RELATORIO_SRC  = icon_src(str(ICON_DIR / "relatorio.png"), "relatorio.png")

# ------------------ CORES ------------------
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
    border-radius: 18px;
    padding: 14px 16px;
    box-shadow: 0 10px 22px rgba(0,0,0,.10);
    color: #fff;
  }}
  .logo-card {{
    background: rgba(255,255,255,.20);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 12px;
    padding: 8px;
    backdrop-filter: blur(3px);
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
  .btn-row .stButton>button:hover {{
    transform: translateY(-1px); box-shadow: 0 10px 22px rgba(0,0,0,.12);
  }}
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
    border-left:6px solid {CLR_ORANGE};
    border-radius:14px; padding:12px 14px; margin-bottom:10px;
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
            try:
                with open(p, "rb") as f:
                    return f.read()
            except Exception:
                pass
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None

# ------------------ HELPERS ------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CAMERAS", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        p = PLANILHA_PATH
    raw = pd.read_excel(p, header=None)
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
    def cam_status(r):
        if r["Cam_Total"]==0: return "SEM CÂMERAS"
        if r["Cam_Online"]==0: return "OFFLINE"
        if r["Cam_Online"]<r["Cam_Total"]: return f"FALTANDO {int(r['Cam_Falta'])}"
        return "OK"
    raw["Cam_Status"] = raw.apply(cam_status, axis=1)
    def alm_status(r):
        if r["Alm_Total"]==0: return "SEM ALARME"
        if r["Alm_Online"]==0: return "OFFLINE"
        if r["Alm_Online"]<r["Alm_Total"]: return f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        return "100%"
    raw["Alm_Status"] = raw.apply(alm_status, axis=1)
    return raw.reset_index(drop=True)

def chip(texto, tipo):
    cls = "ok" if tipo=="ok" else ("warn" if tipo=="warn" else "off")
    return f"<span class='chip {cls}'>{texto}</span>"

# ------------------ GRAFICO ------------------
def bar_values(values: dict, title: str):
    dfc = pd.DataFrame({
        "Categoria": list(values.keys()),
        "Quantidade": list(values.values())
    })
    fig = px.bar(
        dfc, x="Categoria", y="Quantidade", text="Quantidade",
        color="Categoria",
        color_discrete_map={
            "Online": CLR_GREEN,
            "Offline": CLR_RED,
            "Locais p/ manutenção": CLR_ORANGE
        }
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title, height=360, margin=dict(l=10, r=10, t=50, b=20),
        paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL,
        font=dict(size=13), showlegend=False,
        xaxis_title=None, yaxis_title="Quantidade"
    )
    st.plotly_chart(
        fig, use_container_width=True,
        config={"displaylogo": False,
                "toImageFilename": f"grafico_{title.lower().replace(' ','_')}",
                "modeBarButtonsToAdd": ["toImage"]}
    )

# ------------------ HEADER ------------------
_logo_bytes = load_logo_bytes()
st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
c_logo, c_title, c_search = st.columns([0.12, 0.58, 0.30])

with c_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo_bytes:
        st.image(_logo_bytes, use_container_width=True)
    else:
        st.warning("⚠️ Logo não carregada.")
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

# ------------------ ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.11,0.11,0.11,0.67], gap="small")
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

def tab_button(label, tab_name, key):
    active = (st.session_state.tab == tab_name)
    if st.button(label, key=key):
        st.session_state.tab = tab_name
    js = f"""
    <script>
      const btns = Array.from(window.parent.document.querySelectorAll('button'));
      btns.forEach(b=>{{ if(b.innerText.trim()==='{label}') {{
          if({str(active).lower()}) b.classList.add('btn-active'); else b.classList.remove('btn-active');
      }}}});
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)

with b1: tab_button("📷 Câmeras", "Câmeras", "btn_cam")
with b2: tab_button("🚨 Alarmes", "Alarmes", "btn_alm")
with b3: tab_button("📊 Geral",   "Geral",   "btn_ger")
st.divider()

# ------------------ DADOS ------------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha `dados.xlsx`.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ RENDER CÂMERAS ------------------
def render_cameras(dfx: pd.DataFrame):
    st.markdown(f"#### <img src='{ICON_CAMERA_SRC}' width='22' style='vertical-align:middle;margin-right:6px;'/> Câmeras", unsafe_allow_html=True)
    base = dfx[dfx["Cam_Total"] > 0]
    total = int(base["Cam_Total"].sum())
    online = int(base["Cam_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"] > 0)).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Online", online)
    c3.metric("Offline", offline)
    c4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online,"Offline": offline,"Locais p/ manutenção": locais_manut}, "Resumo de Câmeras")

# ------------------ RENDER ALARMES ------------------
def render_alarms(dfx: pd.DataFrame):
    st.markdown(f"#### <img src='{ICON_ALARME_SRC}' width='22' style='vertical-align:middle;margin-right:6px;'/> Alarmes", unsafe_allow_html=True)
    base = dfx[dfx["Alm_Total"] > 0]
    total = int(base["Alm_Total"].sum())
    online = int(base["Alm_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"] > 0)).sum())

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Centrais Totais", total)
    a2.metric("Online", online)
    a3.metric("Offline", offline)
    a4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online,"Offline": offline,"Locais p/ manutenção": locais_manut}, "Resumo de Alarmes")

# ------------------ RENDER GERAL ------------------
def render_geral(dfx: pd.DataFrame):
    st.markdown(f"#### <img src='{ICON_RELATORIO_SRC}' width='22' style='vertical-align:middle;margin-right:6px;'/> Geral (Câmeras + Alarmes)", unsafe_allow_html=True)
    cam = dfx[dfx["Cam_Total"]>0]; alm = dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on
    locais_manut = int(((dfx["Cam_OfflineBool"]) | (dfx["Cam_Falta"]>0) |
                        (dfx["Alm_OfflineBool"]) | (dfx["Alm_Falta"]>0)).sum())

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.metric("Câmeras Online", cam_on)
    g2.metric("Alarmes Online", alm_on)
    g3.metric("Total de Câmeras", cam_tot)
    g4.metric("Total de Alarmes", alm_tot)
    g5.metric("Câmeras Offline", cam_off)
    g6.metric("Alarmes Offline", alm_off)
    bar_values({"Online": cam_on+alm_on,"Offline": cam_off+alm_off,"Locais p/ manutenção": locais_manut},"Resumo Geral")

    # Relatório PDF
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
            elements=[]
            elements.append(Paragraph("<b>Relatório de Locais com Falhas</b>",styles["Title"]))
            elements.append(Spacer(1,10))
            data=[["Local","Câmeras Faltantes","
