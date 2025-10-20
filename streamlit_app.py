# =========================================================
# Dashboard Operacional – Grupo Perímetro
# Tema claro • Botões bonitos • Gráficos pizza • Cards
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

# ----------------- CONFIG PÁGINA -----------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

# Arquivos
PLANILHA = "dados.xlsx"
LOGO_PATH = "logo_perimetro.png"

# Paleta / Tema
CLR_BG     = "#F4F5F7"   # fundo cinza claro
CLR_PANEL  = "#FFFFFF"   # cards / painéis
CLR_TEXT   = "#2E2E2E"   # texto
CLR_SUB    = "#6A7380"   # subtítulos

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
  /* Cabeçalho */
  .header {{
    display:flex; align-items:center; justify-content:space-between;
    padding: 10px 14px; margin: -16px -16px 16px -16px;
    position: sticky; top: 0; z-index: 50;
    background: rgba(244,245,247,0.8); backdrop-filter: blur(8px);
    border-bottom: 1px solid #E6E9EF;
  }}
  .logo-card {{
    background: {CLR_PANEL}; border: 1px solid #E6E9EF; border-radius: 12px;
    padding: 8px; box-shadow: 0 6px 20px rgba(0,0,0,.06);
  }}
  .title {{
    font-size: 22px; font-weight: 800; color: {CLR_BLUE}; letter-spacing:.2px;
  }}
  .sub {{
    font-size: 12px; color: {CLR_SUB};
  }}

  /* Toggle bonito */
  .toggle {{
    display:inline-flex; gap:6px; padding:6px; border-radius: 14px;
    background: #EEF1F6; border: 1px solid #E0E6EF;
    box-shadow: inset 0 1px 0 #fff;
  }}
  .tbtn {{
    padding: 8px 14px; border-radius:12px; cursor:pointer; user-select:none;
    border: 1px solid transparent; color: #4B5563;
    transition: all .15s ease;
    background: linear-gradient(180deg,#fff,#F7F9FC);
    box-shadow: 0 1px 0 rgba(0,0,0,.03);
  }}
  .tbtn:hover {{ transform: translateY(-1px); }}
  .tbtn.active {{
    color:#fff; border-color:{CLR_BLUE};
    background: linear-gradient(180deg,{CLR_BLUE},#005DB1);
    box-shadow: 0 8px 20px rgba(0,114,206,.25);
  }}

  /* Cards */
  .card {{
    background:{CLR_PANEL}; border:1px solid #E6E9EF; border-radius:14px;
    padding:14px; box-shadow: 0 10px 30px rgba(0,0,0,.06);
  }}
  .metric {{
    font-size: 28px; font-weight:800; color:{CLR_TEXT};
  }}
  .tag {{ font-weight: 700; padding: 3px 10px; border-radius: 999px; font-size:12px; }}
  .tag-ok  {{ background:rgba(23,201,100,.12); color:{CLR_GREEN}; border:1px solid rgba(23,201,100,.35); }}
  .tag-warn{{ background:rgba(243,112,33,.12); color:{CLR_ORANGE}; border:1px solid rgba(243,112,33,.35); }}
  .tag-off {{ background:rgba(229,72,77,.12);  color:{CLR_RED};    border:1px solid rgba(229,72,77,.35); }}

  .item {{ display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-top:1px dashed #E6E9EF; }}
  .item:first-child {{ border-top:none; }}
</style>
""", unsafe_allow_html=True)

# ----------------- LOAD DATA (compatível com sua planilha) -----------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, header=None)

    # localizar linha de títulos do seu layout
    hdr = None
    for i, row in df.iterrows():
        s = row.astype(str).str.upper()
        if s.str.contains("POSTOS MONITORADOS").any() and \
           s.str.contains("QUANTIDADE DE CÂMERAS").any():
            hdr = i; break
    if hdr is None: hdr = 2  # fallback

    data = df.iloc[hdr+1:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]
    data = data[~data["Local"].isna()]
    data["Local"] = data["Local"].astype(str).str.strip()

    # remover linhas-resumo / totais
    data = data[~data["Local"].str.contains("TOTAL|RELATÓRIO|FUNCIONANDO|EXCESSO", case=False, na=False)]

    # números
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(_to_int)

    # status câmeras
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

df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha. Verifique `dados.xlsx`.")
    st.stop()

# ----------------- HEADER -----------------
hdr_l, hdr_r = st.columns([0.18, 0.82])
with hdr_l:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    st.image(LOGO_PATH, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with hdr_r:
    st.markdown(f"""
    <div class='header'>
      <div>
        <div class='title'>Dashboard Operacional – CFTV & Alarmes</div>
        <div class='sub'>Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
      </div>
      <div style="min-width:320px;">
        {''}
      </div>
    </div>
    """, unsafe_allow_html=True)

# ----------------- BUSCA + TOGGLE -----------------
top_l, top_m, top_r = st.columns([0.40, 0.28, 0.32])

with top_l:
    # Toggle customizado com session_state
    if "tab" not in st.session_state: st.session_state.tab = "Câmeras"
    st.markdown("<div class='toggle'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📷  Câmeras", use_container_width=True, key="b_cam"):
            st.session_state.tab = "Câmeras"
    with c2:
        if st.button("🚨  Alarmes", use_container_width=True, key="b_alm"):
            st.session_state.tab = "Alarmes"
    st.markdown("</div>", unsafe_allow_html=True)

    # aplicar classe active
    st.markdown(f"""
    <script>
      let cam = window.parent.document.querySelector('button[kind="secondary"]#b_cam');
      let alm = window.parent.document.querySelector('button[kind="secondary"]#b_alm');
    </script>
    """, unsafe_allow_html=True)

with top_r:
    query = st.text_input("Pesquisar local...", "", placeholder="Pesquisar local...")

# filtrar por busca
df_view = df.copy()
has_query = bool(query.strip())
if has_query:
    df_view = df_view[df_view["Local"].str.contains(query.strip(), case=False, na=False)]

# ----------------- FUNÇÕES DE UI -----------------
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
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(
        title=title,
        showlegend=False,
        margin=dict(l=10,r=10,t=40,b=10),
        height=280,
        paper_bgcolor=CLR_PANEL,
        plot_bgcolor=CLR_PANEL
    )
    # cores: verde (ok) e laranja (manutenção)
    fig.update_traces(marker=dict(colors=[CLR_GREEN, CLR_ORANGE]))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ----------------- CÂMERAS -----------------
def render_cameras(dfx: pd.DataFrame):
    st.markdown("#### 📷 Câmeras")

    tot = int(dfx["Cam_Total"].sum())
    on  = int(dfx["Cam_Online"].sum())
    off = max(tot - on, 0)

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Total de Câmeras</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Em Manutenção / Offline</div><div class='metric' style='color:{CLR_ORANGE};'>{off}</div></div>", unsafe_allow_html=True)

    # Gráfico pizza Online vs Manutenção
    pie_online_manutencao(tot, on, "Distribuição de dispositivos")

    # Linhas por local
    st.markdown("##### Locais")
    # sem busca → mostrar apenas problemáticos; com busca → mostrar todos
    if not has_query:
        rows = dfx[~dfx["Cam_Status"].str.contains("OK", case=False, na=False)]
    else:
        rows = dfx

    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para ver locais OK.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            status = r["Cam_Status"].upper()
            cor = "ok" if "OK" in status else ("warn" if ("FALTANDO" in status or "EXCESSO" in status) else "off")
            info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
            card_local(r["Local"], status, info, cor)

# ----------------- ALARMES -----------------
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

    # Gráfico pizza Online vs Manutenção
    pie_online_manutencao(tot, on, "Distribuição de centrais")

    # Linhas por local
    st.markdown("##### Locais")
    # sem busca → mostrar apenas não-100%; com busca → todos
    if not has_query:
        rows = dfx[dfx["Alm_Status"] != "100%"]
    else:
        rows = dfx

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

# Render conforme aba
if st.session_state.tab == "Câmeras":
    render_cameras(df_view)
else:
    render_alarms(df_view)

st.caption("© Grupo Perímetro • Dashboard Operacional • v2.0")
