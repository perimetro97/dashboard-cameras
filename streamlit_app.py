# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3.1)
# Tema cinza • Abas interativas • Cards em coluna única • Gráficos no final
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from PIL import Image
from io import BytesIO
import os, glob

# ---------------------------- CONFIGURAÇÃO BÁSICA ----------------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Paleta Grupo Perímetro
CLR_BG     = "#F4F5F7"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#2E2E2E"
CLR_SUB    = "#6A7380"
CLR_BORDER = "#E6E9EF"
CLR_BLUE   = "#0072CE"
CLR_ORANGE = "#F37021"
CLR_GREEN  = "#17C964"
CLR_RED    = "#E5484D"

# ---------------------------- ESTILOS ----------------------------
st.markdown(f"""
<style>
  .stApp {{ background:{CLR_BG}; color:{CLR_TEXT}; font-family:Inter, system-ui; }}
  .logo-card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:12px;
                padding:8px; box-shadow:0 6px 20px rgba(0,0,0,.06); width:100%; }}
  .title {{ font-size:22px; font-weight:800; color:{CLR_BLUE}; }}
  .sub   {{ font-size:12px; color:{CLR_SUB}; }}
  .pill-wrap {{ display:inline-flex; gap:6px; padding:6px; border-radius:14px;
                background:#EEF1F6; border:1px solid {CLR_BORDER}; }}
  .pill {{ padding:8px 14px; border-radius:12px; border:1px solid transparent;
           cursor:pointer; background:linear-gradient(180deg,#fff,#F7F9FC);
           color:#4B5563; transition:all .15s ease; }}
  .pill:hover {{ transform: translateY(-1px); }}
  .pill.active {{ background:linear-gradient(180deg,{CLR_BLUE},#005DB1); color:#fff;
                  border-color:{CLR_BLUE}; box-shadow:0 8px 20px rgba(0,114,206,.25); }}
  .card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:14px;
           padding:14px; box-shadow:0 10px 30px rgba(0,0,0,.06); margin-bottom:10px; }}
  .metric {{ font-size:28px; font-weight:800; }}
  .tag {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px;
          border:1px solid transparent; }}
  .tag-ok  {{ color:{CLR_GREEN};  background:rgba(23,201,100,.12);
              border-color:rgba(23,201,100,.35); }}
  .tag-warn{{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12);
              border-color:rgba(243,112,33,.35); }}
  .tag-off {{ color:{CLR_RED};    background:rgba(229,72,77,.12);
              border-color:rgba(229,72,77,.35); }}
</style>
""", unsafe_allow_html=True)

# ---------------------------- LOGO ROBUSTA ----------------------------
def load_logo():
    """Procura a logo em múltiplos caminhos possíveis (local e cloud)."""
    paths = [
        "/mount/src/dashboard-cameras/logo_perimetro.png",
        "logo_perimetro.png",
        "./logo_perimetro.png",
        os.path.join(os.getcwd(), "logo_perimetro.png")
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                buf = BytesIO(); img.save(buf, format="PNG")
                st.sidebar.success(f"✅ Logo carregada: {os.path.basename(path)}")
                return buf.getvalue()
            except Exception as e:
                st.sidebar.warning(f"Erro ao carregar logo: {e}")
    st.sidebar.warning("⚠️ Nenhum arquivo de logo encontrado.")
    return None

logo_bytes = load_logo()

# ---------------------------- LEITURA DA PLANILHA ----------------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path):
    df = pd.read_excel(xlsx_path, header=None)
    hdr = 2
    data = df.iloc[hdr+1:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status","Alm_Total","Alm_Online","Alm_Status"]
    data = data.dropna(subset=["Local"])
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(_to_int)
    data["Cam_Status"] = data.apply(lambda r:
        "OK" if r.Cam_Total and r.Cam_Online == r.Cam_Total else
        "FALTANDO" if r.Cam_Online < r.Cam_Total and r.Cam_Online > 0 else
        "OFFLINE", axis=1)
    data["Alm_Percent"] = data.apply(lambda r:
        0 if r.Alm_Total==0 else round((r.Alm_Online/r.Alm_Total)*100,1), axis=1)
    data["Alm_Status"] = data["Alm_Percent"].apply(
        lambda p: "100%" if p==100 else "PARCIAL" if p>0 else "OFFLINE"
    )
    return data

df = load_data(PLANILHA)

# ---------------------------- HEADER ----------------------------
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if logo_bytes:
        st.image(logo_bytes, use_container_width=True)
    else:
        st.write("**Grupo Perímetro**")
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='sub'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Pesquisar local...")

# ---------------------------- ABAS ----------------------------
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"
cols = st.columns(3)
if cols[0].button("📷  Câmeras"): st.session_state.tab = "Câmeras"
if cols[1].button("🚨  Alarmes"): st.session_state.tab = "Alarmes"
if cols[2].button("📊  Geral"):   st.session_state.tab = "Geral"

has_query = bool(query.strip())
df_view = df if not has_query else df[df["Local"].str.contains(query, case=False, na=False)]

# ---------------------------- FUNÇÕES DE INTERFACE ----------------------------
def card(local, status, info, cor="ok"):
    tag = "tag-ok" if cor=="ok" else "tag-warn" if cor=="warn" else "tag-off"
    st.markdown(f"<div class='card'><b>{local}</b> — <span class='{tag}'>{status}</span>"
                f"<div class='sub'>{info}</div></div>", unsafe_allow_html=True)

def graf_pizza(total, online, titulo):
    offline = max(total - online, 0)
    fig = px.pie(names=["Online","Manutenção"], values=[online, offline], hole=0.55)
    fig.update_traces(marker=dict(colors=[CLR_GREEN, CLR_ORANGE]))
    fig.update_layout(title=titulo, height=320)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def graf_bar(df, titulo):
    fig = px.bar(df, x="Categoria", y="Qtd", text="Qtd",
                 color="Categoria", color_discrete_map={
                     "Online": CLR_GREEN, "Manutenção": CLR_ORANGE, "Offline": CLR_RED
                 })
    fig.update_traces(textposition="outside")
    fig.update_layout(title=titulo, height=340)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------- ABA CÂMERAS ----------------------------
def render_cameras(df):
    st.subheader("📷 Câmeras")
    base = df if has_query else df[df["Cam_Total"] > 0]
    total, online = base["Cam_Total"].sum(), base["Cam_Online"].sum()
    off = total - online
    st.metric("Total", total)
    st.metric("Online", online)
    st.metric("Offline", off)

    show = base if has_query else base[base["Cam_Status"]!="OK"]
    for _, r in show.iterrows():
        cor = "ok" if r.Cam_Status=="OK" else "warn" if "FALTANDO" in r.Cam_Status else "off"
        card(r.Local, r.Cam_Status, f"{r.Cam_Online}/{r.Cam_Total}", cor)

    graf_pizza(total, online, "Distribuição Câmeras")
    dfb = pd.DataFrame({"Categoria":["Online","Manutenção","Offline"],
                        "Qtd":[online, total-online, show[show.Cam_Status=='OFFLINE']["Cam_Total"].sum()]})
    graf_bar(dfb, "Comparativo Online x Manutenção x Offline")

# ---------------------------- ABA ALARMES ----------------------------
def render_alarms(df):
    st.subheader("🚨 Alarmes")
    base = df if has_query else df[df["Alm_Total"] > 0]
    total, online = base["Alm_Total"].sum(), base["Alm_Online"].sum()
    perc = 0 if total==0 else round((online/total)*100,1)
    st.metric("Total", total)
    st.metric("Online", online)
    st.metric("Percentual Geral", f"{perc}%")

    show = base if has_query else base[base["Alm_Status"]!="100%"]
    for _, r in show.iterrows():
        cor = "ok" if r.Alm_Status=="100%" else "warn" if "PARCIAL" in r.Alm_Status else "off"
        card(r.Local, r.Alm_Status, f"{r.Alm_Online}/{r.Alm_Total} ({r.Alm_Percent}%)", cor)

    graf_pizza(total, online, "Distribuição Alarmes")
    dfb = pd.DataFrame({"Categoria":["Online","Manutenção","Offline"],
                        "Qtd":[online, total-online, show[show.Alm_Status=='OFFLINE']["Alm_Total"].sum()]})
    graf_bar(dfb, "Comparativo Online x Manutenção x Offline")

# ---------------------------- ABA GERAL ----------------------------
def render_geral(df):
    st.subheader("📊 Geral (Câmeras + Alarmes)")
    cam_tot, cam_on = df["Cam_Total"].sum(), df["Cam_Online"].sum()
    alm_tot, alm_on = df["Alm_Total"].sum(), df["Alm_Online"].sum()
    total = cam_tot + alm_tot
    online = cam_on + alm_on

    st.metric("Total Dispositivos", total)
    st.metric("Online", online)
    st.metric("Manutenção", total - online)

    graf_pizza(total, online, "Visão Geral Online vs Manutenção")
    comb = pd.DataFrame({"Categoria":["Câmeras","Alarmes"], "Qtd":[cam_on, alm_on]})
    fig = px.bar(comb, x="Categoria", y="Qtd", text="Qtd",
                 color="Categoria", color_discrete_map={"Câmeras":CLR_BLUE,"Alarmes":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------- RENDERIZAÇÃO ----------------------------
if st.session_state.tab == "Câmeras":
    render_cameras(df_view)
elif st.session_state.tab == "Alarmes":
    render_alarms(df_view)
else:
    render_geral(df_view)

st.caption("© Grupo Perímetro • Dashboard Operacional v3.1")
