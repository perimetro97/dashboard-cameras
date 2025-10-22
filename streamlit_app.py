# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.7.1 FINAL)
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

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="📹", layout="wide")

# === LEITURA DO EXCEL DIRETO DO GOOGLE DRIVE (OPÇÃO B) ===
DRIVE_FILE_ID = "1LofqwV9_fXfKAGbqjk2LEfgSQmJvUiuA"
DRIVE_URL = f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}"

PLANILHA = "dados.xlsx"
ROOT_PATH = Path(__file__).parent
PLANILHA_PATH = ROOT_PATH / PLANILHA

# LOGO E ÍCONES
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

ICON_CAMERA     = "camera.png"
ICON_ALARME     = "alarme.png"
ICON_RELATORIO  = "relatorio.png"

# CORES INSTITUCIONAIS
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#111827"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#1B1F3B"
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
    font-size: 28px; font-weight: 900;
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

  .local-card {{
    background:#FAFBFF; border:1px solid {CLR_BORDER}; border-left:6px solid {CLR_ORANGE};
    border-radius:14px; padding:12px 14px; margin-bottom:10px;
  }}
  .local-card.offline {{ border-left-color:{CLR_RED}; }}
  .local-title {{ font-weight:900; font-size:16px; }}
  .local-info  {{ color:{CLR_SUB}; font-size:12px; margin-top:2px; }}

  .search-box .stTextInput>div>div>input {{
    border:1px solid {CLR_BORDER};
    box-shadow: 0 2px 8px rgba(27,31,59,.07);
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
            except:
                pass
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok:
            return r.content
    except:
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
    try:
        if path.startswith("http"):
            raw = pd.read_excel(path, header=None)
        else:
            p = Path(path)
            if not p.exists():
                p = PLANILHA_PATH
            raw = pd.read_excel(p, header=None)
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return pd.DataFrame()

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

def chip(txt, tipo):
    cls = "ok" if tipo=="ok" else "warn" if tipo=="warn" else "off"
    return f"<span class='chip {cls}'>{txt}</span>"

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
st.divider()

# ------------------ DADOS ------------------
df = load_data(DRIVE_URL)
if df.empty:
    st.error("❌ Não foi possível ler dados do Google Drive. Verifique o link e permissões.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ RENDER ------------------
def render_cameras(dfx):
    base = dfx[dfx["Cam_Total"] > 0]
    st.markdown(f"#### <img src='{ICON_CAMERA}' width='22' style='vertical-align:middle;margin-right:6px;'/> Câmeras", unsafe_allow_html=True)

    total, online = int(base["Cam_Total"].sum()), int(base["Cam_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"] > 0)).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Online", online)
    c3.metric("Offline", offline)
    c4.metric("Locais p/ manutenção", locais_manut)

    rows = base[(base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)]
    st.markdown("#### Locais para manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Cam_OfflineBool"] else f"FALTANDO {int(r['Cam_Falta'])}"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(f"<div class='local-card {cls}'><div class='local-title'>📍 {r['Local']} — {chip(status,'off' if 'OFFLINE' in status else 'warn')}</div><div class='local-info'>Total: {r['Cam_Total']} • Online: {r['Cam_Online']}</div></div>", unsafe_allow_html=True)

def render_alarms(dfx):
    base = dfx[dfx["Alm_Total"] > 0]
    st.markdown(f"#### <img src='{ICON_ALARME}' width='22' style='vertical-align:middle;margin-right:6px;'/> Alarmes", unsafe_allow_html=True)

    total, online = int(base["Alm_Total"].sum()), int(base["Alm_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"] > 0)).sum())

    a1,a2,a3,a4 = st.columns(4)
    a1.metric("Totais", total)
    a2.metric("Online", online)
    a3.metric("Offline", offline)
    a4.metric("Locais p/ manutenção", locais_manut)

    rows = base[(base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)]
    st.markdown("#### Locais para manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Alm_OfflineBool"] else f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(f"<div class='local-card {cls}'><div class='local-title'>🚨 {r['Local']} — {chip(status,'off' if 'OFFLINE' in status else 'warn')}</div><div class='local-info'>Total: {r['Alm_Total']} • Online: {r['Alm_Online']}</div></div>", unsafe_allow_html=True)

def render_geral(dfx):
    st.markdown(f"#### <img src='{ICON_RELATORIO}' width='22' style='vertical-align:middle;margin-right:6px;'/> Geral (Câmeras + Alarmes)", unsafe_allow_html=True)

    cam = dfx[dfx["Cam_Total"]>0]
    alm = dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    st.columns(6)
    st.metric("Câmeras Online", cam_on)
    st.metric("Alarmes Online", alm_on)
    st.metric("Total Câmeras", cam_tot)
    st.metric("Total Alarmes", alm_tot)
    st.metric("Câmeras Offline", cam_off)
    st.metric("Alarmes Offline", alm_off)

    # -------- Relatório PDF com logo --------
    st.markdown("### 📄 Relatório de Locais com Problemas")
    if st.button("🖨️ Gerar Relatório PDF"):
        faltando = dfx[(dfx["Cam_Falta"] > 0) | (dfx["Alm_Falta"] > 0)].copy()
        if faltando.empty:
            st.info("Nenhum local com falhas no momento.")
        else:
            table_df = faltando[["Local", "Cam_Falta", "Alm_Falta"]].rename(columns={
                "Cam_Falta": "Câmeras Faltantes", "Alm_Falta": "Alarmes Faltantes"
            })

            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

            pdf_name = "Relatório_Cftv&alarmes.pdf"
            doc = SimpleDocTemplate(pdf_name, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            # LOGO NO TOPO
            logo_path = next((p for p in LOGO_FILE_CANDIDATES if os.path.exists(p)), None)
            if logo_path:
                elements.append(Image(logo_path, width=120, height=40))
                elements.append(Spacer(1, 8))

            title = Paragraph("<b>Relatório de Locais com Falhas</b>", styles["Title"])
            elements.append(title)
            elements.append(Spacer(1, 8))
            subtitle = Paragraph(f"Gerado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')}", styles["Normal"])
            elements.append(subtitle)
            elements.append(Spacer(1, 12))

            data = [list(table_df.columns)] + table_df.values.tolist()
            table = Table(data, repeatRows=1)
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

# ------------------ DISPATCH ------------------
tab = st.session_state.get("tab", "Câmeras")
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro & Monitoramento • Dashboard Operacional v5.7.1")
