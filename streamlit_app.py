# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3.2)
# Tema cinza/azul/laranja + PDF + busca de logo automática
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from io import BytesIO
from PIL import Image
import os, glob
from pathlib import Path

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

# Cores institucionais
CLR_BG     = "#F4F5F7"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#2E2E2E"
CLR_SUB    = "#6A7380"
CLR_BORDER = "#E6E9EF"
CLR_BLUE   = "#0072CE"
CLR_ORANGE = "#F37021"
CLR_GREEN  = "#17C964"
CLR_RED    = "#E5484D"

# ---------------- ESTILO ----------------
st.markdown(f"""
<style>
  .stApp {{ background:{CLR_BG}; color:{CLR_TEXT}; font-family:Inter, system-ui; }}
  .card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:14px;
           padding:14px; box-shadow:0 8px 22px rgba(0,0,0,.05); margin-bottom:10px; }}
  .metric {{ font-size:28px; font-weight:800; }}
  .tag {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px; }}
  .tag-ok  {{ color:{CLR_GREEN}; background:rgba(23,201,100,.12); }}
  .tag-warn{{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12); }}
  .tag-off {{ color:{CLR_RED}; background:rgba(229,72,77,.12); }}
  .pill {{ padding:10px 18px; border-radius:10px; background:#E9EDF2; 
           cursor:pointer; margin:4px; font-weight:600; }}
  .pill:hover {{ background:{CLR_BLUE}; color:white; }}
  .pill.active {{ background:{CLR_BLUE}; color:white; }}
  .logo-card {{ background:{CLR_PANEL}; border-radius:12px; padding:6px;
                box-shadow:0 3px 10px rgba(0,0,0,.08); }}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGO ROBUSTA ----------------
def load_logo_bytes():
    paths = [
        "logo_perimetro.png",
        "./logo_perimetro.png",
        "/app/dashboard-cameras/logo_perimetro.png",
        "/mount/src/dashboard-cameras/logo_perimetro.png"
    ]
    for p in paths + glob.glob("**/logo_perimetro.*", recursive=True):
        if os.path.exists(p):
            try:
                img = Image.open(p).convert("RGBA")
                buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
                st.sidebar.success(f"✅ Logo carregada: {os.path.basename(p)}")
                return buf.read()
            except Exception as e:
                st.sidebar.warning(f"Erro: {e}")
    st.sidebar.warning("⚠️ Nenhum arquivo de logo encontrado.")
    return None

logo_bytes = load_logo_bytes()

# ---------------- LEITURA DA PLANILHA ----------------
def to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE","SEM ALARME","SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data
def load_data():
    df = pd.read_excel(PLANILHA, header=None)
    data = df.iloc[3:,:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]
    data = data.dropna(subset=["Local"])
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(to_int)
    data["Cam_Status"] = data.apply(
        lambda r: "OK" if r.Cam_Total and r.Cam_Online==r.Cam_Total else
                  "FALTANDO" if r.Cam_Online<r.Cam_Total and r.Cam_Online>0 else
                  "OFFLINE", axis=1)
    data["Alm_Percent"] = data.apply(
        lambda r: 0 if r.Alm_Total==0 else round((r.Alm_Online/r.Alm_Total)*100,1), axis=1)
    data["Alm_Status"] = data["Alm_Percent"].apply(
        lambda p: "100%" if p==100 else "PARCIAL" if p>0 else "OFFLINE")
    return data

df = load_data()

# ---------------- HEADER ----------------
col_logo, col_title, col_search = st.columns([0.12,0.58,0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if logo_bytes: st.image(logo_bytes, use_container_width=True)
    else: st.write("**Grupo Perímetro**")
    st.markdown("</div>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"<h3 style='color:{CLR_BLUE};margin-bottom:-4px'>Dashboard Operacional – CFTV & Alarmes</h3>"
                f"<p style='color:{CLR_SUB};font-size:12px;'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
                unsafe_allow_html=True)
with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local...")

# ---------------- FUNÇÕES ----------------
def card(local, status, info, cor="ok"):
    tag = "tag-ok" if cor=="ok" else "tag-warn" if cor=="warn" else "tag-off"
    st.markdown(f"<div class='card'><b>{local}</b> — <span class='{tag}'>{status}</span><br><span>{info}</span></div>",
                unsafe_allow_html=True)

def graf_pizza(total, online, titulo):
    off = max(total-online,0)
    fig = px.pie(names=["Online","Manutenção"], values=[online,off], hole=0.55)
    fig.update_traces(marker=dict(colors=[CLR_GREEN, CLR_ORANGE]))
    fig.update_layout(title=titulo,height=320)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

def graf_bar(df,titulo):
    fig = px.bar(df,x="Categoria",y="Qtd",text="Qtd",
                 color="Categoria",color_discrete_map={
                     "Online":CLR_GREEN,"Manutenção":CLR_ORANGE,"Offline":CLR_RED})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=titulo,height=340)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

# PDF gerador
def build_pdf_bytes(df):
    cam = df[df["Cam_Total"]>0]
    alm = df[df["Alm_Total"]>0]
    buf = BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.6*cm,rightMargin=1.6*cm)
    styles=getSampleStyleSheet()
    story=[]
    story+=[Paragraph("Dashboard Operacional – Grupo Perímetro",styles["Title"]),
            Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"),styles["Normal"]),Spacer(1,8)]
    cam_tot,cam_on=cam["Cam_Total"].sum(),cam["Cam_Online"].sum()
    alm_tot,alm_on=alm["Alm_Total"].sum(),alm["Alm_Online"].sum()
    t=Table([
        ["Sistema","Total","Online","Offline/Manut."],
        ["Câmeras",cam_tot,cam_on,cam_tot-cam_on],
        ["Alarmes",alm_tot,alm_on,alm_tot-alm_on],
    ])
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),
                           ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
    story+=[t,Spacer(1,12)]
    story+=[Paragraph("<b>Locais com câmeras em manutenção/offline</b>",styles["Heading3"])]
    cams=cam[cam["Cam_Status"]!="OK"][["Local","Cam_Status","Cam_Total","Cam_Online"]]
    camrows=[["Local","Status","Total","Online"]]+cams.values.tolist() if not cams.empty else [["Sem ocorrências"]]
    tc=Table(camrows,colWidths=[7*cm,4*cm,2.5*cm,2.5*cm])
    tc.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),
                            ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
    story+=[tc,Spacer(1,12)]
    story+=[Paragraph("<b>Locais com alarmes em manutenção/offline</b>",styles["Heading3"])]
    alms=alm[alm["Alm_Status"]!="100%"][["Local","Alm_Status","Alm_Total","Alm_Online"]]
    almrows=[["Local","Status","Total","Online"]]+alms.values.tolist() if not alms.empty else [["Sem ocorrências"]]
    ta=Table(almrows,colWidths=[7*cm,4*cm,2.5*cm,2.5*cm])
    ta.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),
                            ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
    story+=[ta]
    doc.build(story);buf.seek(0)
    return buf.read()

# ---------------- ABAS ----------------
if "tab" not in st.session_state: st.session_state.tab="Câmeras"
cols=st.columns(3)
if cols[0].button("📷 Câmeras"): st.session_state.tab="Câmeras"
if cols[1].button("🚨 Alarmes"): st.session_state.tab="Alarmes"
if cols[2].button("📊 Geral"):   st.session_state.tab="Geral"

has_query=bool(query.strip())
df_view=df if not has_query else df[df["Local"].str.contains(query,case=False,na=False)]

# --- render
def render_cameras(df):
    st.subheader("📷 Câmeras")
    base=df if has_query else df[df["Cam_Total"]>0]
    total,online=base["Cam_Total"].sum(),base["Cam_Online"].sum()
    show=base if has_query else base[base["Cam_Status"]!="OK"]
    for _,r in show.iterrows():
        cor="ok" if r.Cam_Status=="OK" else "warn" if "FALTANDO" in r.Cam_Status else "off"
        card(r.Local,r.Cam_Status,f"{r.Cam_Online}/{r.Cam_Total}",cor)
    graf_pizza(total,online,"Câmeras Online vs Manutenção")
    graf_bar(pd.DataFrame({"Categoria":["Online","Manutenção"],
                           "Qtd":[online,total-online]}),"Resumo Câmeras")

def render_alarms(df):
    st.subheader("🚨 Alarmes")
    base=df if has_query else df[df["Alm_Total"]>0]
    total,online=base["Alm_Total"].sum(),base["Alm_Online"].sum()
    show=base if has_query else base[base["Alm_Status"]!="100%"]
    for _,r in show.iterrows():
        cor="ok" if r.Alm_Status=="100%" else "warn" if "PARCIAL" in r.Alm_Status else "off"
        card(r.Local,r.Alm_Status,f"{r.Alm_Online}/{r.Alm_Total} ({r.Alm_Percent}%)",cor)
    graf_pizza(total,online,"Alarmes Online vs Manutenção")
    graf_bar(pd.DataFrame({"Categoria":["Online","Manutenção"],
                           "Qtd":[online,total-online]}),"Resumo Alarmes")

def render_geral(df):
    st.subheader("📊 Geral (Câmeras + Alarmes)")
    cam_tot,cam_on=df["Cam_Total"].sum(),df["Cam_Online"].sum()
    alm_tot,alm_on=df["Alm_Total"].sum(),df["Alm_Online"].sum()
    total,online=cam_tot+alm_tot,cam_on+alm_on
    graf_pizza(total,online,"Dispositivos Online vs Manutenção (Geral)")
    comb=pd.DataFrame({"Categoria":["Câmeras","Alarmes"],"Qtd":[cam_on,alm_on]})
    fig=px.bar(comb,x="Categoria",y="Qtd",text="Qtd",
               color="Categoria",color_discrete_map={"Câmeras":CLR_BLUE,"Alarmes":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    pdf_bytes=build_pdf_bytes(df)
    st.download_button("📄 Baixar PDF (Resumo do Dashboard)",pdf_bytes,
                       file_name=f"relatorio_perimetro_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                       mime="application/pdf",use_container_width=True)

if st.session_state.tab=="Câmeras": render_cameras(df_view)
elif st.session_state.tab=="Alarmes": render_alarms(df_view)
else: render_geral(df_view)

st.caption("© Grupo Perímetro • Dashboard v3.2")
