# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.3-final)
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

# Logo
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Ícones (raiz do repositório)
ICON_CAMERA     = "camera.png"
ICON_ALARME     = "alarme.png"
ICON_RELATORIO  = "relatorio.png"

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
    color:{CLR_TEXT};
    margin-bottom: 2px;
  }}
  .subtitle {{ font-size: 12px; color: rgba(17,24,39,.75); }}

  .btn-row .stButton>button {{
    background: #fff;
    color: {CLR_BLUE};
    border: 1px solid {CLR_BORDER};
    border-radius: 12px;
    padding: 10px 14px;
    font-weight: 700;
    box-shadow: 0 6px 14px rgba(0,0,0,.06);
    transition: transform .08s ease, box-shadow .15s ease, background .15s ease;
    margin-right: 6px;
  }}
  .btn-row .stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 10px 22px rgba(0,0,0,.12); }}
  .btn-active {{ background: {CLR_BLUE} !important; color: #fff !important; }}
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
    return raw.reset_index(drop=True)

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
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------ ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.11,0.11,0.11,0.67], gap="small")
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

def tab_button(label_html, tab_name, key):
    active = (st.session_state.tab == tab_name)
    if st.button(label_html, key=key):
        st.session_state.tab = tab_name
    js = f"""
    <script>
      const btns = Array.from(window.parent.document.querySelectorAll('button'));
      btns.forEach(b=>{{ if(b.innerHTML.trim()==='{label_html}') {{
          if({str(active).lower()}) b.classList.add('btn-active'); else b.classList.remove('btn-active');
      }}}});
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)

# ✅ ÍCONES REAIS NOS BOTÕES
with b1:
    tab_button(f"<img src='{ICON_CAMERA}' width='16' style='vertical-align:middle;margin-right:4px;'/> Câmeras", "Câmeras", "btn_cam")
with b2:
    tab_button(f"<img src='{ICON_ALARME}' width='16' style='vertical-align:middle;margin-right:4px;'/> Alarmes", "Alarmes", "btn_alm")
with b3:
    tab_button(f"<img src='{ICON_RELATORIO}' width='16' style='vertical-align:middle;margin-right:4px;'/> Geral", "Geral", "btn_ger")

st.divider()

# ------------------ DADOS ------------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler a planilha.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ RENDER ------------------
def render_cameras(dfx):
    st.markdown(f"#### <img src='{ICON_CAMERA}' width='20' style='vertical-align:middle;margin-right:6px;'/> Câmeras", unsafe_allow_html=True)
    st.write("... conteúdo da aba Câmeras ...")

def render_alarms(dfx):
    st.markdown(f"#### <img src='{ICON_ALARME}' width='20' style='vertical-align:middle;margin-right:6px;'/> Alarmes", unsafe_allow_html=True)
    st.write("... conteúdo da aba Alarmes ...")

def render_geral(dfx):
    st.markdown(f"#### <img src='{ICON_RELATORIO}' width='20' style='vertical-align:middle;margin-right:6px;'/> Geral (Câmeras + Alarmes)", unsafe_allow_html=True)
    st.write("... conteúdo da aba Geral ...")

tab = st.session_state.tab
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro & Monitoramento • Dashboard Operacional")
