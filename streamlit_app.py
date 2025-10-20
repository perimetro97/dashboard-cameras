# =========================================================
# Dashboard Operacional – Grupo Perímetro (Tema Claro)
# CFTV & Alarmes • pizza online vs manutenção • cards lindos
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import glob, os
from PIL import Image

# ----------------- CONFIG PÁGINA -----------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Paleta / Tema Claro
CLR_BG     = "#F4F5F7"   # fundo cinza claro
CLR_PANEL  = "#FFFFFF"   # cards
CLR_TEXT   = "#2E2E2E"   # texto
CLR_SUB    = "#6A7380"   # subtítulo
CLR_BORDER = "#E6E9EF"

CLR_BLUE   = "#0072CE"   # azul institucional
CLR_ORANGE = "#F37021"   # laranja manutenção
CLR_GREEN  = "#17C964"   # verde OK
CLR_RED    = "#E5484D"   # vermelho OFF

st.markdown(f"""
<style>
  .stApp {{
    background:{CLR_BG};
    color:{CLR_TEXT};
    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  }}
  /* Header fixo translúcido */
  .header {{
    display:flex; align-items:center; justify-content:space-between;
    padding: 10px 14px; margin: -16px -16px 16px -16px;
    position: sticky; top: 0; z-index: 40;
    background: rgba(244,245,247,.9); backdrop-filter: blur(8px);
    border-bottom: 1px solid {CLR_BORDER};
  }}
  .logo-card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:12px;
    padding: 8px; box-shadow: 0 6px 20px rgba(0,0,0,.06);
    width:100%;
  }}
  .title {{ font-size: 22px; font-weight: 800; color:{CLR_BLUE}; letter-spacing:.2px; }}
  .sub {{ font-size: 12px; color:{CLR_SUB}; }}

  /* Toggle pills bonitos */
  .pill-wrap {{
    display:inline-flex; gap:6px; padding:6px; border-radius:14px;
    background:#EEF1F6; border:1px solid {CLR_BORDER};
    box-shadow: inset 0 1px 0 #fff;
  }}
  .pill {{
    padding:8px 14px; border-radius:12px; cursor:pointer; user-select:none;
    border:1px solid transparent; color:#4B5563;
    transition: all .15s ease; background: linear-gradient(180deg,#fff,#F7F9FC);
    box-shadow: 0 1px 0 rgba(0,0,0,.03);
  }}
  .pill:hover {{ transform: translateY(-1px); }}
  .pill-active {{
    color:#fff; border-color:{CLR_BLUE}; background: linear-gradient(180deg,{CLR_BLUE},#005DB1);
    box-shadow: 0 8px 20px rgba(0,114,206,.25);
  }}

  /* Cards e listas */
  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:14px;
    padding:14px; box-shadow: 0 10px 30px rgba(0,0,0,.06);
  }}
  .metric {{ font-size: 28px; font-weight:800; }}
  .item {{ display:flex; align-items:center; justify-content:space-between;
           padding:10px 0; border-top:1px dashed {CLR_BORDER}; }}
  .item:first-child {{ border-top:none; }}
  .tag {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px; border:1px solid transparent; }}
  .tag-ok  {{ color:{CLR_GREEN};  background:rgba(23,201,100,.12); border-color:rgba(23,201,100,.35); }}
  .tag-warn{{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12); border-color:rgba(243,112,33,.35); }}
  .tag-off {{ color:{CLR_RED};    background:rgba(229,72,77,.12);  border-color:rgba(229,72,77,.35); }}
</style>
""", unsafe_allow_html=True)

# ----------------- LOGO ROBUSTA -----------------
def load_logo_bytes():
    # tenta vários nomes/extensões comuns
    candidates = [
        "logo_perimetro.png", "logo_perimetro.jpg", "logo_perimetro.jpeg",
        "logo.png", "logo.jpg", "logo.jpeg"
    ]
    for pat in candidates + [*glob.glob("logo*.*")]:
        if os.path.isfile(pat):
            try:
                img = Image.open(pat)
                bb = img.tobytes()  # força load; se falhar cai no except
                return image_to_bytes(img)
            except Exception:
                pass
    return None

def image_to_bytes(img: Image.Image) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

logo_bytes = load_logo_bytes()

# ----------------- UTILS PLANILHA -----------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, header=None)

    # localizar linha de títulos do seu layout (foto que você enviou)
    hdr = None
    for i, row in df.iterrows():
        s = row.astype(str).str.upper()
        if s.str.contains("POSTOS MONITORADOS").any() and \
           s.str.contains("QUANTIDADE DE CÂMERAS").any():
            hdr = i; break
    if hdr is None: hdr = 2  # fallback (linha 3)

    data = df.iloc[hdr+1:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]
    data = data[~data["Local"].isna()]
    data["Local"] = data["Local"].astype(str).str.strip()
    # remove blocos de totais/espelhos
    data = data[~data["Local"].str.contains("TOTAL|RELATÓRIO|FUNCIONANDO|EXCESSO", case=False, na=False)]

    # números
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(_to_int)

    # status câmeras (completar)
    def cam_status(row):
        s = str(row["Cam_Status"]).strip().upper()
        tot, on = row["Cam_Total"], row["Cam_Online"]
        if any(k in s for k in ["OK","EXCESSO","FALTANDO","OFFLINE","SEM CÂMERAS"]):
            return s
        if tot == 0: return "SEM CÂMERAS"
        if on == tot: return "OK"
        if on > tot:  return "EXCESSO"
        if on == 0:   return "OFFLINE"
        return f"FALTANDO {max(tot-on,0)}"
    data["Cam_Status"] = data.apply(cam_status, axis=1)

    # % e status alarmes
    def alm_percent(row):
        tot, on = row["Alm_Total"], row["Alm_Online"]
        return 0.0 if tot<=0 else round(100.0*on/tot, 2)
    data["Alm_Percent"] = data.apply(alm_percent, axis=1)

    def alm_status(row):
        s = str(row["Alm_Status"]).strip().upper()
        if "100%" in s: return "100%"
        if "50%" in s:  return "PARCIAL (50%)"
        if "OFFLINE" in s or "SEM ALARME" in s: return "OFFLINE"
        p = row["Alm_Percent"]
        if p >= 99.9: return "100%"
        if p >= 66:   return "PARCIAL (≥66%)"
        if p >= 50:   return "PARCIAL (50%)"
        if p > 0:     return "PARCIAL (<50%)"
        return "OFFLINE"
    data["Alm_Status"] = data.apply(alm_status, axis=1)

    return data.reset_index(drop=True)

# ----------------- CARREGA DADOS -----------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha. Verifique `dados.xlsx`.")
    st.stop()

# ----------------- HEADER -----------------
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    try:
        if logo_bytes:
            st.image(logo_bytes, use_container_width=True)
        else:
            st.write(" ")  # fallback silencioso
    except Exception:
        st.write(" ")
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"""
        <div class='header'>
           <div>
             <div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>
             <div class='sub'>Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
           </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Pesquisar local...")

# ----------------- TOGGLE (pills) -----------------
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"
pill = st.columns([0.18, 0.82])[0]
with pill:
    c1, c2 = st.columns(2)
    cam_clicked = c1.button("📷  Câmeras", key="pill_cam")
    alm_clicked = c2.button("🚨  Alarmes", key="pill_alm")
    if cam_clicked: st.session_state.tab = "Câmeras"
    if alm_clicked: st.session_state.tab = "Alarmes"
st.markdown(
    f"""
    <style>
      button[kind="secondary"][data-testid="baseButton"][key="pill_cam"] {{
        {"background: linear-gradient(180deg,"+CLR_BLUE+",#005DB1); color:#fff; border:1px solid "+CLR_BLUE+";" if st.session_state.tab=="Câmeras" else ""}
        border-radius:12px;
      }}
      button[kind="secondary"][data-testid="baseButton"][key="pill_alm"] {{
        {"background: linear-gradient(180deg,"+CLR_BLUE+",#005DB1); color:#fff; border:1px solid "+CLR_BLUE+";" if st.session_state.tab=="Alarmes" else ""}
        border-radius:12px;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------- BUSCA / VIEW -----------------
has_query = bool(query.strip())
df_view = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# ----------------- UI HELPERS -----------------
def card_local(local, linha_status, info_extra, cor="ok"):
    klass = "tag-ok" if cor=="ok" else ("tag-warn" if cor=="warn" else "tag-off")
    st.markdown(
        f"<div class='card'><b>📍 {local}</b> — <span class='{klass}'>{linha_status}</span>"
        f"<div class='sub' style='margin-top:6px;'>{info_extra}</div></div>",
        unsafe_allow_html=True
    )

def pie_online_manutencao(total, online, title):
    manut = max(total - online, 0)
    fig = px.pie(
        names=["Online","Manutenção"],
        values=[online, manut],
        hole=0.55
    )
    fig.update_traces(textinfo="percent+label",
                      marker=dict(colors=[CLR_GREEN, CLR_ORANGE]))
    fig.update_layout(
        title=title, showlegend=False,
        margin=dict(l=10,r=10,t=40,b=10),
        height=280, paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ----------------- RENDER CÂMERAS -----------------
def render_cameras(dfx: pd.DataFrame):
    st.markdown("#### 📷 Câmeras")
    tot = int(dfx["Cam_Total"].sum())
    on  = int(dfx["Cam_Online"].sum())
    off = max(tot - on, 0)

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Total de Câmeras</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Em Manutenção / Offline</div><div class='metric' style='color:{CLR_ORANGE};'>{off}</div></div>", unsafe_allow_html=True)

    pie_online_manutencao(tot, on, "Distribuição de dispositivos")

    st.markdown("##### Locais")
    rows = dfx if has_query else dfx[~dfx["Cam_Status"].str.contains("OK", case=False, na=False)]
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para ver locais OK.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            status = r["Cam_Status"].upper()
            cor = "ok" if "OK" in status else ("warn" if ("FALTANDO" in status or "EXCESSO" in status) else "off")
            info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
            card_local(r["Local"], status, info, cor)

# ----------------- RENDER ALARMES -----------------
def render_alarms(dfx: pd.DataFrame):
    st.markdown("#### 🚨 Alarmes")
    tot = int(dfx["Alm_Total"].sum())
    on  = int(dfx["Alm_Online"].sum())

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Centrais Totais</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3:
        perc = 0 if tot==0 else round(100*on/tot,1)
        st.markdown(f"<div class='card'><div class='sub'>Percentual Geral</div><div class='metric' style='color:{CLR_BLUE};'>{perc}%</div></div>", unsafe_allow_html=True)

    pie_online_manutencao(tot, on, "Distribuição de centrais")

    st.markdown("##### Locais")
    rows = dfx if has_query else dfx[dfx["Alm_Status"] != "100%"]
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para ver locais 100%.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            stt = r["Alm_Status"]
            if stt == "100%": cor = "ok"
            elif "OFFLINE" in stt: cor = "off"
            else: cor = "warn"
            info = f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']} • {r['Alm_Percent']:.0f}%"
            card_local(r["Local"], stt, info, cor)

# ----------------- DISPATCH -----------------
if st.session_state.tab == "Câmeras":
    render_cameras(df_view)
else:
    render_alarms(df_view)

st.caption("© Grupo Perímetro • Dashboard Operacional • v2.1")
