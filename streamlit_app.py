# =========================================================
# Dashboard Operacional – Grupo Perímetro (v4.0)
# CFTV & Alarmes • Visual Pro • PDF • Logo robusta
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

# Se quiser EMBUTIR a logo (recomendado), cole aqui o base64 da imagem (sem quebras):
LOGO_BASE64 = ""  # <- COLE AQUI (opcional). Se vazio, usa arquivo local/URL.

# URL raw (fallback)
LOGO_URL = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Paleta
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#1E293B"
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#0B66C3"   # Azul institucional
CLR_ORANGE = "#F37021"   # Manutenção
CLR_GREEN  = "#16A34A"   # OK
CLR_RED    = "#E11D48"   # Offline
CLR_GRAD_1 = "#0B66C3"
CLR_GRAD_2 = "#053B82"

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

  /* Top bar gradiente */
  .top-wrap {{
    background: linear-gradient(90deg, {CLR_GRAD_1}, {CLR_GRAD_2});
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 14px 28px rgba(0,0,0,.12);
    color: #fff;
  }}
  .logo-card {{
    background: rgba(255,255,255,.18);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 12px;
    padding: 8px;
    backdrop-filter: blur(4px);
  }}
  .title {{
    font-size: 28px; font-weight: 900; letter-spacing:.2px;
    text-shadow: 0 2px 10px rgba(0,0,0,.25);
    margin-bottom: 4px;
  }}
  .subtitle {{ font-size: 12px; color: rgba(255,255,255,.85); }}

  /* Botões das abas */
  .btn-row .stButton>button {{
    background: #fff;
    color: {CLR_BLUE};
    border: 1px solid {CLR_BORDER};
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 700;
    box-shadow: 0 6px 14px rgba(0,0,0,.06);
    transition: transform .08s ease, box-shadow .15s ease, background .15s ease;
    margin-right: 8px;
  }}
  .btn-row .stButton>button:hover {{
    transform: translateY(-1px) scale(1.02);
    box-shadow: 0 10px 22px rgba(0,0,0,.12);
  }}
  .btn-active {{ background: {CLR_BLUE} !important; color: #fff !important; }}

  /* Cards */
  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:16px; padding:16px;
    box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px;
    transition: transform .08s ease, box-shadow .15s ease;
  }}
  .card:hover {{ transform: translateY(-1px); box-shadow:0 14px 30px rgba(2,12,27,.12); }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}

  /* Chips de status */
  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}

  /* Lista de locais */
  .local-card {{
    background:#FAFBFF; border:1px solid {CLR_BORDER}; border-left:6px solid {CLR_ORANGE};
    border-radius:14px; padding:12px 14px; margin-bottom:10px;
  }}
  .local-card.offline {{ border-left-color:{CLR_RED}; }}
  .local-title {{ font-weight:900; font-size:16px; }}
  .local-info  {{ color:{CLR_SUB}; font-size:12px; margin-top:2px; }}

  /* Espaçamento fino dos botões */
  .tight-row .stColumn {{ padding-right:2px; padding-left:0px; }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO ROBUSTA ------------------
def load_logo_bytes() -> bytes | None:
    # 1) Base64 embutido (se fornecido)
    if LOGO_BASE64 and len(LOGO_BASE64) > 100:
        try:
            return base64.b64decode(LOGO_BASE64)
        except Exception:
            pass
    # 2) Arquivo local
    for p in ["logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png"]:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f: return f.read()
            except Exception:
                pass
    # 3) URL raw do GitHub
    try:
        r = requests.get(LOGO_URL, timeout=6)
        if r.ok: return r.content
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
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(how="all").iloc[:, 0:7]  # A..G
    raw.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                   "Alm_Total","Alm_Online","Alm_Status"]
    raw = raw.dropna(subset=["Local"])
    # remove linhas de total/relatorio
    raw = raw[~raw["Local"].astype(str).str.contains("TOTAL|RELATÓRIO|RELATORIO", case=False, na=False)]

    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        raw[c] = raw[c].apply(_to_int)

    # Auxiliares
    raw["Cam_Falta"] = (raw["Cam_Total"] - raw["Cam_Online"]).clip(lower=0)
    raw["Alm_Falta"] = (raw["Alm_Total"] - raw["Alm_Online"]).clip(lower=0)
    raw["Cam_OfflineBool"] = (raw["Cam_Total"]>0) & (raw["Cam_Online"]==0)
    raw["Alm_OfflineBool"] = (raw["Alm_Total"]>0) & (raw["Alm_Online"]==0)

    # Status amigáveis
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

def bar_values(values: dict, title: str):
    dfc = pd.DataFrame({"Categoria": list(values.keys()),
                        "Quantidade": list(values.values())})
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online":CLR_GREEN, "Offline":CLR_RED, "Locais p/ manutenção":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, height=360,
                      margin=dict(l=10,r=10,t=50,b=20),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL,
                      font=dict(size=13), showlegend=False)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displaylogo": False,
                "toImageFilename": f"grafico_{title.lower().replace(' ','_')}",
                "modeBarButtonsToAdd":["toImage"]}
    )

# ------------------ PDF ------------------
def build_pdf_bytes(df: pd.DataFrame) -> bytes:
    class PDF(FPDF):
        def header(self):
            self.set_auto_page_break(auto=True, margin=15)
            self.set_font("helvetica", "B", 14)
            self.set_text_color(11,102,195)  # azul
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

    cam = df[df["Cam_Total"]>0]
    alm = df[df["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    pdf.cell(0, 8, f"Câmeras: {cam_on}/{cam_tot} online • Offline: {cam_off}", ln=True)
    pdf.cell(0, 8, f"Alarmes: {alm_on}/{alm_tot} online • Offline: {alm_off}", ln=True)
    pdf.ln(4)

    def table_block(title, data):
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(11,102,195)
        pdf.cell(0, 7, title, ln=True)
        pdf.set_text_color(30,41,59)
        pdf.set_font("helvetica", "", 9)
        if data.empty:
            pdf.cell(0, 6, "Sem ocorrências", ln=True)
            pdf.ln(2); return
        headers = list(data.columns)
        pdf.cell(0, 6, " | ".join(headers), ln=True)
        for _, r in data.iterrows():
            pdf.cell(0, 6, " | ".join(str(v) for v in r), ln=True)
        pdf.ln(2)

    cam_rows = cam[(cam["Cam_OfflineBool"]) | (cam["Cam_Falta"]>0)][["Local","Cam_Status","Cam_Total","Cam_Online"]]
    alm_rows = alm[(alm["Alm_OfflineBool"]) | (alm["Alm_Falta"]>0)][["Local","Alm_Status","Alm_Total","Alm_Online"]]

    table_block("Câmeras – Manutenção/Offline", cam_rows)
    table_block("Alarmes – Manutenção/Offline", alm_rows)

    out = BytesIO(); pdf.output(out); out.seek(0)
    return out.read()

# ------------------ HEADER ------------------
logo_bytes = load_logo_bytes()

st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if logo_bytes:
        st.image(logo_bytes, use_container_width=True)
    else:
        st.warning("⚠️ Logo não carregada,\nmas o sistema continua funcionando.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='subtitle'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------ ABAS (botões com animação) ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.12,0.12,0.12,0.64], gap="small")
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

def make_btn(label, tab_name, key):
    active = (st.session_state.tab == tab_name)
    clicked = st.button(label, key=key)
    if clicked: st.session_state.tab = tab_name
    # aplica classe ativa via HTML pós-render
    st.markdown(f"""
    <script>
      const btns = window.parent.document.querySelectorAll('button[k="{key}"]');
      if(btns && btns.length>0) {{
        const b=btns[0];
        if({str(active).lower()}) b.classList.add('btn-active'); else b.classList.remove('btn-active');
      }}
    </script>
    """, unsafe_allow_html=True)

with b1: make_btn("📷 Câmeras", "Câmeras", "btn_cam")
with b2: make_btn("🚨 Alarmes", "Alarmes", "btn_alm")
with b3: make_btn("📊 Geral",   "Geral",   "btn_ger")

st.divider()

# ------------------ DADOS ------------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha `dados.xlsx`. Verifique se está na raiz.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ RENDER: CÂMERAS ------------------
def render_cameras(dfx: pd.DataFrame):
    base = dfx[dfx["Cam_Total"]>0]
    st.markdown("#### 📷 Câmeras")

    total = int(base["Cam_Total"].sum())
    online = int(base["Cam_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)).sum())

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card'><div class='metric-sub'>Total</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    # Ordenação: offline primeiro, depois maior faltante
    rows = base.copy()
    rows["__prio"] = np.where(rows["Cam_OfflineBool"], 2, np.where(rows["Cam_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Cam_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty and not has_query:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100% OK.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Cam_OfflineBool"] else f"FALTANDO {int(r['Cam_Falta'])}"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'>"
            f"<div class='local-title'>📍 {r['Local']} — "
            f"{chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Cam_Total']} • Online: {r['Cam_Online']}</div>"
            f"</div>", unsafe_allow_html=True
        )

    # Gráfico final (baixável)
    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut},
               "Resumo de Câmeras")

# ------------------ RENDER: ALARMES ------------------
def render_alarms(dfx: pd.DataFrame):
    base = dfx[dfx["Alm_Total"]>0]
    st.markdown("#### 🚨 Alarmes")

    total = int(base["Alm_Total"].sum())
    online = int(base["Alm_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)).sum())

    a1,a2,a3,a4 = st.columns(4)
    a1.markdown(f"<div class='card'><div class='metric-sub'>Centrais Totais</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    a2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    a3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    a4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    rows = base.copy()
    rows["__prio"] = np.where(rows["Alm_OfflineBool"], 2, np.where(rows["Alm_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0].sort_values(["__prio","Alm_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty and not has_query:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100%.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Alm_OfflineBool"] else f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'>"
            f"<div class='local-title'>📍 {r['Local']} — "
            f"{chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Alm_Total']} • Online: {r['Alm_Online']}</div>"
            f"</div>", unsafe_allow_html=True
        )

    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut},
               "Resumo de Alarmes")

# ------------------ RENDER: GERAL ------------------
def render_geral(dfx: pd.DataFrame):
    st.markdown("#### 📊 Geral (Câmeras + Alarmes)")

    cam = dfx[dfx["Cam_Total"]>0]; alm = dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='card'><div class='metric-sub'>Total de Câmeras</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    g4.markdown(f"<div class='card'><div class='metric-sub'>Total de Alarmes</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    g5.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Offline</div><div class='metric' style='color:{CLR_RED};'>{cam_off}</div></div>", unsafe_allow_html=True)
    g6.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Offline</div><div class='metric' style='color:{CLR_RED};'>{alm_off}</div></div>", unsafe_allow_html=True)

    bar_values({"Online": cam_on+alm_on, "Offline": cam_off+alm_off, "Locais p/ manutenção": 0},
               "Resumo Geral")

    # PDF
    pdf = build_pdf_bytes(dfx)
    st.download_button("📄 Baixar PDF (Resumo do Dashboard)",
                       data=pdf,
                       file_name=f"relatorio_perimetro_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                       mime="application/pdf", use_container_width=True)

# ------------------ DISPATCH ------------------
tab = st.session_state.tab
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro • Dashboard Operacional v4.0")
