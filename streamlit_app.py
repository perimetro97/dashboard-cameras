# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.2)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Logo somente do repositório / arquivo (sem Base64)
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Paleta
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#111827"  # preto suave
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#0B66C3"   # Azul institucional
CLR_ORANGE = "#F37021"   # Laranja institucional
CLR_GREEN  = "#16A34A"   # OK
CLR_RED    = "#E11D48"   # Offline

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

  /* Barra superior com gradiente azul->laranja (modelo 18) */
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
  /* Título preto, sem sombra */
  .title {{
    font-size: 28px; font-weight: 900; letter-spacing:.2px;
    color:{CLR_TEXT};
    margin-bottom: 2px;
  }}
  .subtitle {{ font-size: 12px; color: rgba(17,24,39,.75); }}

  /* Botões das abas – mais próximos e com hover */
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

  /* Cards */
  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:16px; padding:16px;
    box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px;
    transition: transform .08s ease, box-shadow .15s ease;
  }}
  .card:hover {{ transform: translateY(-1px); box-shadow:0 14px 30px rgba(2,12,27,.12); }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}

  /* Chips */
  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}

  /* Cartões de locais */
  .local-card {{
    background:#FAFBFF; border:1px solid {CLR_BORDER}; border-left:6px solid {CLR_ORANGE};
    border-radius:14px; padding:12px 14px; margin-bottom:10px;
  }}
  .local-card.offline {{ border-left-color:{CLR_RED}; }}
  .local-title {{ font-weight:900; font-size:16px; }}
  .local-info  {{ color:{CLR_SUB}; font-size:12px; margin-top:2px; }}

  /* Destaque discreto no campo de busca */
  .search-box .stTextInput>div>div>input {{
    border:1px solid {CLR_BORDER};
    box-shadow: 0 2px 8px rgba(11,102,195,.07);
  }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO (repositório/arquivo) ------------------
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
        dfc,
        x="Categoria",
        y="Quantidade",
        text="Quantidade",
        color="Categoria",
        color_discrete_map={
            "Online": CLR_GREEN,
            "Offline": CLR_RED,
            "Locais p/ manutenção": CLR_ORANGE
        }
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=10, r=10, t=50, b=20),
        paper_bgcolor=CLR_PANEL,
        plot_bgcolor=CLR_PANEL,
        font=dict(size=13),
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Quantidade"
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "toImageFilename": f"grafico_{title.lower().replace(' ','_')}",
            "modeBarButtonsToAdd": ["toImage"]
        },
        key=f"chart_{title.replace(' ','_')}"
    )

# ------------------ HEADER ------------------
_logo_bytes = load_logo_bytes()

st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
c_logo, c_title, c_search = st.columns([0.12, 0.58, 0.30])
with c_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo_bytes:
        try:
            st.image(_logo_bytes, use_container_width=True)
        except Exception:
            st.warning("⚠️ Erro ao carregar logo. O sistema continua funcionando.")
    else:
        st.warning("⚠️ Logo não carregada, mas o sistema continua funcionando.")
    st.markdown("</div>", unsafe_allow_html=True)

with c_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='subtitle'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with c_search:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.12,0.12,0.12,0.64], gap="small")
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
    st.error("Não foi possível ler dados da planilha `dados.xlsx`. Verifique se está na raiz.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ------------------ RENDER: GERAL ------------------
def render_geral(dfx: pd.DataFrame):
    st.markdown("#### 📊 Geral (Câmeras + Alarmes)")

    cam = dfx[dfx["Cam_Total"]>0]; alm = dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    # Novo: contar locais em manutenção (câmeras ou alarmes)
    locais_manut = int(((dfx["Cam_OfflineBool"]) | (dfx["Cam_Falta"]>0) |
                        (dfx["Alm_OfflineBool"]) | (dfx["Alm_Falta"]>0)).sum())

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='card'><div class='metric-sub'>Total de Câmeras</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    g4.markdown(f"<div class='card'><div class='metric-sub'>Total de Alarmes</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    g5.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Offline</div><div class='metric' style='color:{CLR_RED};'>{cam_off}</div></div>", unsafe_allow_html=True)
    g6.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Offline</div><div class='metric' style='color:{CLR_RED};'>{alm_off}</div></div>", unsafe_allow_html=True)

    bar_values(
        {"Online": cam_on+alm_on, "Offline": cam_off+alm_off, "Locais p/ manutenção": locais_manut},
        "Resumo Geral"
    )

# ------------------ DISPATCH ------------------
tab = st.session_state.tab
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro • Dashboard Operacional v5.6.2")
