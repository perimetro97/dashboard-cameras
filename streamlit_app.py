# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3)
# Tema claro • Abas interativas • Cards (1 coluna) • Tabelas • Gráficos no final
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from PIL import Image
import os, glob
from io import BytesIO

# ---------------------------- CONFIG BÁSICA ----------------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Cores da marca
CLR_BG     = "#F4F5F7"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#2E2E2E"
CLR_SUB    = "#6A7380"
CLR_BORDER = "#E6E9EF"
CLR_BLUE   = "#0072CE"  # azul institucional
CLR_ORANGE = "#F37021"  # laranja manutenção
CLR_GREEN  = "#17C964"  # verde OK
CLR_RED    = "#E5484D"  # vermelho OFF

# ---------------------------- ESTILO ----------------------------
st.markdown(f"""
<style>
  .stApp {{ background:{CLR_BG}; color:{CLR_TEXT}; font-family:Inter, system-ui; }}
  .header {{
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 14px; margin:-16px -16px 16px -16px; position:sticky; top:0; z-index:50;
    background:rgba(244,245,247,.9); backdrop-filter:blur(8px); border-bottom:1px solid {CLR_BORDER};
  }}
  .logo-card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:12px; padding:8px;
               box-shadow:0 6px 20px rgba(0,0,0,.06); width:100%; }}
  .title {{ font-size:22px; font-weight:800; color:{CLR_BLUE}; letter-spacing:.2px; }}
  .sub   {{ font-size:12px; color:{CLR_SUB}; }}

  .pill-wrap {{ display:inline-flex; gap:6px; padding:6px; border-radius:14px; background:#EEF1F6; border:1px solid {CLR_BORDER}; }}
  .pill {{ padding:8px 14px; border-radius:12px; border:1px solid transparent; cursor:pointer;
           transition: all .15s ease; background:linear-gradient(180deg,#fff,#F7F9FC); color:#4B5563; }}
  .pill:hover {{ transform: translateY(-1px); }}
  .pill.active {{ background:linear-gradient(180deg,{CLR_BLUE},#005DB1); color:#fff; border-color:{CLR_BLUE};
                 box-shadow:0 8px 20px rgba(0,114,206,.25); }}

  .card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:14px; padding:14px;
           box-shadow:0 10px 30px rgba(0,0,0,.06); margin-bottom:10px; }}
  .metric {{ font-size:28px; font-weight:800; }}
  .tag {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px; border:1px solid transparent; }}
  .tag-ok  {{ color:{CLR_GREEN};  background:rgba(23,201,100,.12); border-color:rgba(23,201,100,.35); }}
  .tag-warn{{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12); border-color:rgba(243,112,33,.35); }}
  .tag-off {{ color:{CLR_RED};    background:rgba(229,72,77,.12);  border-color:rgba(229,72,77,.35); }}
  .table thead th {{ background:#F7F9FC; border-bottom:1px solid {CLR_BORDER}; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------- LOGO ROBUSTA ----------------------------
def load_logo():
    # Caminho absoluto (garante que funcione no Streamlit Cloud)
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
                return buf.getvalue()
            except Exception as e:
                st.write(f"Erro ao carregar logo: {e}")
    return None

# ---------------------------- LEITURA DA PLANILHA ----------------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, header=None)

    # Tenta localizar linha de cabeçalho conforme seu layout
    hdr = None
    for i, row in df.iterrows():
        s = row.astype(str).str.upper()
        if s.str.contains("POSTOS MONITORADOS").any() and s.str.contains("QUANTIDADE DE CÂMERAS").any():
            hdr = i; break
    if hdr is None: hdr = 2  # fallback (linha 3)

    data = df.iloc[hdr+1:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]
    data = data[~data["Local"].isna()]
    data["Local"] = data["Local"].astype(str).str.strip()

    # remove linhas-resumo / espelhos
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

df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha. Verifique `dados.xlsx`.")
    st.stop()

# ---------------------------- HEADER ----------------------------
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if logo_bytes:
        st.image(logo_bytes, use_container_width=True)
    else:
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
           <div></div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Pesquisar local...")

# ---------------------------- ABAS (pílulas) ----------------------------
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

tcol = st.columns([0.44, 0.28, 0.28])[0]
with tcol:
    st.markdown("<div class='pill-wrap'>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    if b1.button("📷  Câmeras"): st.session_state.tab = "Câmeras"
    if b2.button("🚨  Alarmes"): st.session_state.tab = "Alarmes"
    if b3.button("📈  Geral"):   st.session_state.tab = "Geral"
    st.markdown("</div>", unsafe_allow_html=True)

# marca ativa via CSS
active = st.session_state.tab
st.markdown(
    f"""
    <style>
      button:has(span:contains("📷  Câmeras")) {{ {'background:linear-gradient(180deg,'+CLR_BLUE+',#005DB1); color:#fff;' if active=='Câmeras' else ''} }}
      button:has(span:contains("🚨  Alarmes")) {{ {'background:linear-gradient(180deg,'+CLR_BLUE+',#005DB1); color:#fff;' if active=='Alarmes' else ''} }}
      button:has(span:contains("📈  Geral"))   {{ {'background:linear-gradient(180deg,'+CLR_BLUE+',#005DB1); color:#fff;' if active=='Geral'   else ''} }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------- BUSCA / VISÃO ----------------------------
has_query = bool(query.strip())
df_view = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

# Regras: ignorar "SEM CÂMERAS"/"SEM ALARME" quando não há busca
def _mask_sem_cam(d): return ~d["Cam_Status"].str.contains("SEM CÂMERAS", case=False, na=False)
def _mask_sem_alm(d): return (d["Alm_Total"] > 0) & ~d["Alm_Status"].str.contains("SEM ALARME", case=False, na=False)

# ---------------------------- HELPERS UI ----------------------------
def card_local(local, linha_status, info_extra, cor="ok"):
    tag = "tag-ok" if cor=="ok" else ("tag-warn" if cor=="warn" else "tag-off")
    st.markdown(
        f"<div class='card'><b>📍 {local}</b> — <span class='{tag}'>{linha_status}</span>"
        f"<div class='sub' style='margin-top:6px;'>{info_extra}</div></div>", unsafe_allow_html=True
    )

def pie_online_manutencao(total, online, title):
    manut = max(total - online, 0)
    fig = px.pie(names=["Online","Manutenção"], values=[online, manut], hole=0.55)
    fig.update_traces(textinfo="percent+label",
                      marker=dict(colors=[CLR_GREEN, CLR_ORANGE]))
    fig.update_layout(title=title, showlegend=False, margin=dict(l=10,r=10,t=40,b=10),
                      height=320, paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def bar_online_offline(df_counts, title):
    fig = px.bar(df_counts, x="Categoria", y="Quantidade", text="Quantidade")
    fig.update_traces(textposition="outside",
                      marker_color=[CLR_GREEN, CLR_ORANGE, CLR_RED])
    fig.update_layout(title=title, height=340, margin=dict(l=10,r=10,t=40,b=10),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------- ABA CÂMERAS ----------------------------
def render_cameras(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[_mask_sem_cam(dfx)]
    st.markdown("#### 📷 Câmeras")

    tot = int(base["Cam_Total"].sum())
    on  = int(base["Cam_Online"].sum())
    off = max(tot - on, 0)

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Total</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Offline / Manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{off}</div></div>", unsafe_allow_html=True)

    # Cards (coluna única): somente manutenção/offline quando não há busca
    rows = base if has_query else base[~base["Cam_Status"].str.contains("OK", case=False, na=False)]
    st.markdown("##### Locais em manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para ver locais OK.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            status = r["Cam_Status"].upper()
            cor = "ok" if "OK" in status else ("warn" if ("FALTANDO" in status or "EXCESSO" in status) else "off")
            info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
            card_local(r["Local"], status, info, cor)

    # Tabela de interpretação clara
    tb = rows.assign(Status=rows["Cam_Status"],
                     Total=rows["Cam_Total"], Online=rows["Cam_Online"])\
             [["Local","Status","Total","Online"]].reset_index(drop=True)
    st.markdown("##### Tabela resumida")
    st.dataframe(tb, use_container_width=True)

    # Gráficos (final do dashboard)
    pie_online_manutencao(tot, on, "Distribuição de dispositivos")
    df_counts = pd.DataFrame({
        "Categoria": ["Online", "Manutenção", "Offline"],
        "Quantidade": [on, max(tot-on,0), rows[rows["Cam_Status"].str.contains("OFFLINE", case=False, na=False)]["Cam_Total"].sum()]
    })
    bar_online_offline(df_counts, "Comparativo Online x Manutenção x Offline")

# ---------------------------- ABA ALARMES ----------------------------
def render_alarms(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[_mask_sem_alm(dfx)]
    st.markdown("#### 🚨 Alarmes")

    tot = int(base["Alm_Total"].sum())
    on  = int(base["Alm_Online"].sum())
    perc = 0 if tot==0 else round(100*on/tot,1)

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Centrais Totais</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Percentual Geral</div><div class='metric' style='color:{CLR_BLUE};'>{perc}%</div></div>", unsafe_allow_html=True)

    # Cards (coluna única): sem busca → mostrar quem não está 100%
    rows = base if has_query else base[base["Alm_Status"] != "100%"]
    st.markdown("##### Locais em manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para ver locais 100%.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            stt = r["Alm_Status"]
            cor = "ok" if stt=="100%" else ("off" if "OFFLINE" in stt else "warn")
            info = f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']} • {r['Alm_Percent']:.0f}%"
            card_local(r["Local"], stt, info, cor)

    # Tabela clara
    tb = rows.assign(Status=rows["Alm_Status"],
                     Total=rows["Alm_Total"], Online=rows["Alm_Online"], Percent=rows["Alm_Percent"].round(0))\
             [["Local","Status","Total","Online","Percent"]].rename(columns={"Percent":"%"}).reset_index(drop=True)
    st.markdown("##### Tabela resumida")
    st.dataframe(tb, use_container_width=True)

    # Gráficos (final do dashboard)
    pie_online_manutencao(tot, on, "Distribuição de centrais")
    df_counts = pd.DataFrame({
        "Categoria": ["Online", "Manutenção", "Offline"],
        "Quantidade": [on, max(tot-on,0), rows[rows["Alm_Status"].str.contains("OFFLINE", case=False, na=False)]["Alm_Total"].sum()]
    })
    bar_online_offline(df_counts, "Comparativo Online x Manutenção x Offline")

# ---------------------------- ABA GERAL ----------------------------
def render_geral(dfx: pd.DataFrame):
    st.markdown("#### 📈 Geral (Câmeras + Alarmes)")
    # remover sem-sistema
    cam_ok = dfx[_mask_sem_cam(dfx)]
    alm_ok = dfx[_mask_sem_alm(dfx)]

    # Totais combinados
    cam_tot, cam_on = int(cam_ok["Cam_Total"].sum()), int(cam_ok["Cam_Online"].sum())
    alm_tot, alm_on = int(alm_ok["Alm_Total"].sum()), int(alm_ok["Alm_Online"].sum())

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='card'><div class='sub'>Câmeras (total)</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='card'><div class='sub'>Câmeras online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='card'><div class='sub'>Alarmes (total)</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='card'><div class='sub'>Alarmes online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)

    # Gráficos consolidados (final da aba)
    pie_online_manutencao(cam_tot+alm_tot, cam_on+alm_on, "Geral: Online vs Manutenção")

    comb = pd.DataFrame({
        "Categoria":["Câmeras Online","Câmeras Manut.","Alarmes Online","Alarmes Manut."],
        "Quantidade":[cam_on, max(cam_tot-cam_on,0), alm_on, max(alm_tot-alm_on,0)]
    })
    fig = px.bar(comb, x="Categoria", y="Quantidade", text="Quantidade")
    fig.update_traces(textposition="outside",
                      marker_color=[CLR_GREEN, CLR_ORANGE, CLR_GREEN, CLR_ORANGE])
    fig.update_layout(title="Comparativo Geral", height=360, margin=dict(l=10,r=10,t=40,b=10),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------- DISPATCH ----------------------------
if st.session_state.tab == "Câmeras":
    render_cameras(df_view)
elif st.session_state.tab == "Alarmes":
    render_alarms(df_view)
else:
    render_geral(df_view)

st.caption("© Grupo Perímetro • Dashboard Operacional • v3.0")
