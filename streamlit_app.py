# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.4)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="📹", layout="wide")

PLANILHA = "dados.xlsx"
ICON_PATH = Path(__file__).parent / "assets" / "icones"

LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Paleta
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
    background: rgba(255,255,255,.20);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 12px; padding: 8px;
    backdrop-filter: blur(3px);
  }}
  .title {{ font-size: 28px; font-weight: 900; letter-spacing:.2px; color:{CLR_TEXT}; margin-bottom: 2px; }}
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
  .card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER};
          border-radius:16px; padding:16px;
          box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px; }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}
  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO ------------------
def load_logo_bytes() -> bytes | None:
    for p in LOGO_FILE_CANDIDATES:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f: return f.read()
            except Exception: pass
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok: return r.content
    except Exception: pass
    return None

# ------------------ FUNÇÕES AUXILIARES ------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CAMERAS", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

# ------------------ LEITURA DE DADOS (CORRIGIDA) ------------------
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(how="all")

    # Garante 7 colunas
    if raw.shape[1] < 7:
        missing = 7 - raw.shape[1]
        raw = pd.concat([raw, pd.DataFrame(np.nan, index=raw.index,
                                           columns=range(raw.shape[1], raw.shape[1] + missing))], axis=1)
    raw = raw.iloc[:, 0:7]
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

# ------------------ DADOS ------------------
try:
    df = load_data(PLANILHA)
except Exception as e:
    st.error(f"❌ Erro ao ler a planilha `{PLANILHA}`.")
    st.exception(e)
    st.stop()

if df is None or df.empty:
    st.error("⚠️ Nenhum dado válido encontrado na planilha `dados.xlsx`.")
    st.stop()

query = (st.session_state.get("query") or "").strip()
q = st.text_input("Pesquisar local...", query, placeholder="Digite o nome do local…")
dfv = df if q == "" else df[df["Local"].astype(str).str.contains(q, case=False, na=False)]

# ------------------ GRAFICO ------------------
def bar_values(values: dict, title: str):
    dfc = pd.DataFrame({"Categoria": list(values.keys()), "Quantidade": list(values.values())})
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online": CLR_GREEN,"Offline": CLR_RED,"Locais p/ manutenção": CLR_ORANGE})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(title=title, height=360, margin=dict(l=10, r=10, t=50, b=20),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL,
                      font=dict(size=13), showlegend=False)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False,"toImageFilename": f"grafico_{title.lower().replace(' ','_')}"})

# ------------------ RENDERIZAÇÕES ------------------
def render_cameras(dfx: pd.DataFrame):
    st.markdown("<h4>📹 Câmeras</h4>", unsafe_allow_html=True)
    base = dfx[dfx["Cam_Total"] > 0]
    total = int(base["Cam_Total"].sum())
    online = int(base["Cam_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base['Cam_OfflineBool']) | (base['Cam_Falta'] > 0)).sum())

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Online", online)
    c3.metric("Offline", offline)
    c4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut}, "Resumo de Câmeras")

def render_alarms(dfx: pd.DataFrame):
    st.markdown("<h4>🚨 Alarmes</h4>", unsafe_allow_html=True)
    base = dfx[dfx["Alm_Total"] > 0]
    total = int(base["Alm_Total"].sum())
    online = int(base["Alm_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base['Alm_OfflineBool']) | (base['Alm_Falta'] > 0)).sum())

    a1,a2,a3,a4 = st.columns(4)
    a1.metric("Centrais Totais", total)
    a2.metric("Online", online)
    a3.metric("Offline", offline)
    a4.metric("Locais p/ manutenção", locais_manut)
    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut}, "Resumo de Alarmes")

def render_geral(dfx: pd.DataFrame):
    st.markdown("<h4>📊 Geral (Câmeras + Alarmes)</h4>", unsafe_allow_html=True)
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
    bar_values({"Online": cam_on+alm_on, "Offline": cam_off+alm_off, "Locais p/ manutenção": locais_manut}, "Resumo Geral")

    # ================== RELATÓRIO PDF ==================
    st.markdown("### 📄 Relatório de Locais com Problemas")
    if st.button("🖨️ Gerar Relatório PDF"):
        faltando = dfx[(dfx["Cam_Falta"] > 0) | (dfx["Alm_Falta"] > 0)]
        if faltando.empty:
            st.info("Nenhum local com falhas no momento.")
        else:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

            pdf_file = "relatorio_faltas.pdf"
            doc = SimpleDocTemplate(pdf_file, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            title = Paragraph("<b>Relatório de Locais com Falhas</b>", styles["Title"])
            elements.append(title)
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                                      styles["Normal"]))
            elements.append(Spacer(1, 12))

            data = [["Local", "Câmeras Totais", "Câmeras Online", "Faltando",
                     "Alarmes Totais", "Alarmes Online", "Faltando"]]
            for _, row in faltando.iterrows():
                data.append([
                    str(row["Local"]),
                    int(row["Cam_Total"]), int(row["Cam_Online"]), int(row["Cam_Falta"]),
                    int(row["Alm_Total"]), int(row["Alm_Online"]), int(row["Alm_Falta"])
                ])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0B66C3")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            doc.build(elements)

            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar Relatório PDF",
                    data=f,
                    file_name=pdf_file,
                    mime="application/pdf"
                )

# ------------------ DISPATCH ------------------
tab = st.radio("", ["Câmeras","Alarmes","Geral"], horizontal=True)
if tab == "Câmeras": render_cameras(dfv)
elif tab == "Alarmes": render_alarms(dfv)
else: render_geral(dfv)

st.caption("© Grupo Perímetro & Monitoramento • Dashboard Operacional")
