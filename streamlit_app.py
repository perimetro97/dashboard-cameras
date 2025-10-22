# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.7 FINAL)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
import pytz

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="📹", layout="wide")

# --- PLANILHA (Google Drive link)
FILE_ID = "1LofqwV9_fXfKAGbqjk2LEfgSQmJvUiuA"
PLANILHA_URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"

# Logo e ícones
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

ICON_CAMERA     = "camera.png"
ICON_ALARME     = "alarme.png"
ICON_RELATORIO  = "relatorio.png"

# Paleta atualizada (azul institucional puxado da logo)
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#111827"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#1B1F3B"   # Azul exato da logo
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
  .title {{ font-size: 28px; font-weight: 900; color:{CLR_TEXT}; margin-bottom: 2px; }}
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

  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:16px; padding:16px;
    box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px;
  }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}

  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO ------------------
def load_logo_bytes():
    for p in LOGO_FILE_CANDIDATES:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok: return r.content
    except Exception:
        pass
    return None

# ------------------ LOAD DATA (Drive) ------------------
@st.cache_data(show_spinner=False)
def load_data_online() -> pd.DataFrame:
    try:
        df = pd.read_excel(PLANILHA_URL, header=None)
        df = df.dropna(how="all").iloc[:, 0:7]
        df.columns = ["Local","Cam_Total","Cam_Online","Cam_Status","Alm_Total","Alm_Online","Alm_Status"]
        df = df.dropna(subset=["Local"])
        for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar planilha do Drive: {e}")
        return pd.DataFrame()

df = load_data_online()
if df.empty:
    st.stop()

# ------------------ CABEÇALHO ------------------
_logo_bytes = load_logo_bytes()
st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
c_logo, c_title, c_search = st.columns([0.12, 0.58, 0.30])

with c_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo_bytes: st.image(_logo_bytes, use_container_width=True)
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

# ------------------ BOTÕES / ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.11,0.11,0.11,0.67], gap="small")

if "tab" not in st.session_state:
    st.session_state.tab = "Câmeras"

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

# ------------------ SEÇÕES ------------------
tab = st.session_state.tab

if tab == "Câmeras":
    st.markdown(f"#### <img src='{ICON_CAMERA}' width='22' style='vertical-align:middle;margin-right:6px;'/> Câmeras", unsafe_allow_html=True)
    # conteúdo original permanece...

elif tab == "Alarmes":
    st.markdown(f"#### <img src='{ICON_ALARME}' width='22' style='vertical-align:middle;margin-right:6px;'/> Alarmes", unsafe_allow_html=True)
    # conteúdo original permanece...

else:
    st.markdown(f"#### <img src='{ICON_RELATORIO}' width='22' style='vertical-align:middle;margin-right:6px;'/> Relatório Geral", unsafe_allow_html=True)
    # ----------- LOGO NO PDF -----------
    if st.button("🖨️ Gerar Relatório PDF"):
        pdf_name = "Relatorio_CFTV_Alarmes.pdf"
        doc = SimpleDocTemplate(pdf_name, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        logo_path = next((p for p in LOGO_FILE_CANDIDATES if os.path.exists(p)), None)
        if logo_path:
            elements.append(Image(logo_path, width=120, height=40))
            elements.append(Spacer(1, 8))

        title = Paragraph("<b>Relatório de Locais com Falhas</b>", styles["Title"])
        elements.append(title)
        elements.append(Spacer(1, 12))

        table = Table([["Local", "Câmeras Faltantes", "Alarmes Faltantes"]],
                      repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B1F3B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)
        doc.build(elements)

        with open(pdf_name, "rb") as f:
            st.download_button("⬇️ Baixar Relatório PDF", f, pdf_name, "application/pdf")
