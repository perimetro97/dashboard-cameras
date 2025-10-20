# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3.4)
# CFTV & Alarmes • logo.png • leitura robusta • gráficos • PDF
# =========================================================
import os
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF

# ------------- CONFIG GERAL -------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"
LOGO_URL = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Paleta
CLR_BG     = "#F4F5F7"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#2E2E2E"
CLR_SUB    = "#6A7380"
CLR_BORDER = "#E6E9EF"
CLR_BLUE   = "#0072CE"   # azul
CLR_ORANGE = "#F37021"   # manutenção
CLR_GREEN  = "#17C964"   # ok
CLR_RED    = "#E5484D"   # offline

# ------------- ESTILO -------------
st.markdown(f"""
<style>
  .stApp {{ background:{CLR_BG}; color:{CLR_TEXT}; font-family:Inter,system-ui; }}
  .logo-card {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:12px; padding:8px;
                box-shadow:0 6px 18px rgba(0,0,0,.06); }}
  .title    {{ font-size:26px; font-weight:800; color:{CLR_BLUE}; margin-bottom:2px; }}
  .sub      {{ font-size:12px; color:{CLR_SUB}; }}
  .card     {{ background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:14px; padding:14px;
               box-shadow:0 8px 24px rgba(0,0,0,.06); margin-bottom:10px; }}
  .metric   {{ font-size:28px; font-weight:800; }}
  .tag      {{ font-weight:700; padding:3px 10px; border-radius:999px; font-size:12px; }}
  .tag-ok   {{ color:{CLR_GREEN};  background:rgba(23,201,100,.12); }}
  .tag-warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12); }}
  .tag-off  {{ color:{CLR_RED};    background:rgba(229,72,77,.12); }}
  /* botões das abas mais próximos */
  .btn-row .stButton > button {{ margin-right:8px; margin-left:0; padding:8px 14px; border-radius:10px; }}
</style>
""", unsafe_allow_html=True)

# ------------- LOGO (logo.png) -------------
def get_logo_source():
    for p in ["logo.png", "./logo.png", "/app/logo.png",
              "/app/dashboard-cameras/logo.png", "/mount/src/dashboard-cameras/logo.png"]:
        if os.path.exists(p):
            return p
    return LOGO_URL  # fallback URL crua do GitHub

# ------------- HELPERS -------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS", "SEM CAMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    """Lê a planilha e mapeia as colunas A..G, ignorando cabeçalhos e linhas de total."""
    raw = pd.read_excel(xlsx_path, header=None)
    # acha primeira linha com possível dado (A com texto, pelo menos um número em B,C,E,F)
    def looks_like_row(r):
        a = str(r[0]).strip()
        if a == "" or a.lower() == "nan" or "TOTAL" in a.upper(): return False
        nums = 0
        for j in [1,2,4,5]:
            try:
                float(str(r[j]).replace(",", "."))
                nums += 1
            except:
                pass
        return nums >= 1
    start = None
    for i in range(min(25, len(raw))):
        if looks_like_row(raw.iloc[i, :]): start = i; break
    if start is None: start = 0

    df = raw.iloc[start:, 0:7].copy()
    df.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                  "Alm_Total","Alm_Online","Alm_Status"]
    df = df.dropna(subset=["Local"])
    df["Local"] = df["Local"].astype(str).str.strip()
    df = df[~df["Local"].str.contains("TOTAL|RELATÓRIO|RELATORIO", case=False, na=False)]

    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        df[c] = df[c].apply(_to_int)

    # normaliza status de câmeras
    def cam_status(row):
        s = str(row["Cam_Status"]).strip().upper()
        tot, on = row["Cam_Total"], row["Cam_Online"]
        if any(k in s for k in ["OK","EXCESSO","FALTANDO","OFFLINE","SEM CÂMERAS","SEM CAMERAS"]):
            return s.replace("CAMERAS","CÂMERAS")
        if tot == 0: return "SEM CÂMERAS"
        if on == 0: return "OFFLINE"
        if on >= tot: return "OK" if on == tot else "EXCESSO"
        return f"FALTANDO {max(tot-on,0)}"
    df["Cam_Status"] = df.apply(cam_status, axis=1)

    # percentuais e status de alarmes
    df["Alm_Percent"] = df.apply(lambda r: 0.0 if r["Alm_Total"]<=0 else round(100.0*r["Alm_Online"]/r["Alm_Total"],2), axis=1)
    def alm_status(row):
        s = str(row["Alm_Status"]).strip().upper()
        if "100%" in s: return "100%"
        if "OFFLINE" in s or "SEM ALARME" in s: return "OFFLINE"
        p = row["Alm_Percent"]
        if p >= 99.9: return "100%"
        if p > 0: return "PARCIAL"
        return "OFFLINE"
    df["Alm_Status"] = df.apply(alm_status, axis=1)

    # campos auxiliares
    df["Cam_Falta"] = (df["Cam_Total"] - df["Cam_Online"]).clip(lower=0)
    df["Alm_Falta"] = (df["Alm_Total"] - df["Alm_Online"]).clip(lower=0)
    df["Cam_OfflineBool"] = (df["Cam_Total"]>0) & (df["Cam_Online"]==0)
    df["Alm_OfflineBool"] = (df["Alm_Total"]>0) & (df["Alm_Online"]==0)
    return df.reset_index(drop=True)

# UI helpers
def card_local(local, status, info, cor="ok"):
    tag = "tag-ok" if cor=="ok" else ("tag-warn" if cor=="warn" else "tag-off")
    st.markdown(
        f"<div class='card'><b>📍 {local}</b> — <span class='{tag}'>{status}</span>"
        f"<div class='sub' style='margin-top:6px;'>{info}</div></div>", unsafe_allow_html=True
    )

def bar_single(values: dict, title: str):
    """Barra com 3 categorias (Online, Offline, Locais p/ manutenção)."""
    dfc = pd.DataFrame({
        "Categoria": list(values.keys()),
        "Quantidade": list(values.values())
    })
    fig = px.bar(dfc, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online":CLR_GREEN, "Offline":CLR_RED, "Locais p/ manutenção":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, height=340, margin=dict(l=10,r=10,t=40,b=10),
                      paper_bgcolor=CLR_PANEL, plot_bgcolor=CLR_PANEL, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# PDF simples (fpdf2)
def build_pdf_bytes(df: pd.DataFrame) -> bytes:
    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 8, "Dashboard Operacional – Grupo Perímetro", ln=True, align="C")
            self.set_font("Helvetica", "", 10)
            self.cell(0, 7, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=True, align="C")
            self.ln(3)

    cam = df[df["Cam_Total"]>0]
    alm = df[df["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = max(cam_tot-cam_on,0), max(alm_tot-alm_on,0)

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Câmeras: {cam_on}/{cam_tot} online • Offline: {cam_off}", ln=True)
    pdf.cell(0, 8, f"Alarmes: {alm_on}/{alm_tot} online • Offline: {alm_off}", ln=True)
    pdf.ln(4)

    def add_table(title, data):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 9)
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
    add_table("Câmeras em manutenção/offline", cam_rows)
    add_table("Alarmes em manutenção/offline", alm_rows)

    out = BytesIO(); pdf.output(out); out.seek(0)
    return out.read()

# ------------- HEADER -------------
import base64

with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    try:
        logo_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAoAAAAKACAYAAAC0HzYfAAA..."  # <– aqui entra a logo codificada em base64
        )
        st.image(logo_bytes, use_container_width=True)
    except Exception as e:
        st.warning("⚠️ Logo não carregada (embed falhou), mas o sistema continua funcionando.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='sub'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")

# Abas (botões mais próximos)
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([0.2,0.2,0.2])
with c1:
    if st.button("📷 Câmeras"): st.session_state['tab'] = "Câmeras"
with c2:
    if st.button("🚨 Alarmes"): st.session_state['tab'] = "Alarmes"
with c3:
    if st.button("📈 Geral"):   st.session_state['tab'] = "Geral"
st.markdown("</div>", unsafe_allow_html=True)
if 'tab' not in st.session_state: st.session_state['tab'] = "Câmeras"

# ------------- DADOS -------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha `dados.xlsx`. Verifique se está na raiz e com colunas A..G.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

def mask_sem_cam(d): return (d["Cam_Total"]>0)
def mask_sem_alm(d): return (d["Alm_Total"]>0)

# ------------- RENDER CÂMERAS -------------
def render_cameras(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[mask_sem_cam(dfx)]
    st.markdown("### 📷 Câmeras")

    tot = int(base["Cam_Total"].sum())
    on  = int(base["Cam_Online"].sum())
    off = max(tot - on, 0)
    manut_qtd_locais = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"]>0)).sum())

    # Cards (coluna única visualmente, mas métricas lado a lado)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='card'><div class='sub'>Total</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='card'><div class='sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{off}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='card'><div class='sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{manut_qtd_locais}</div></div>", unsafe_allow_html=True)

    # Ordenação: 1) offline, 2) maior faltante
    rows = base.copy()
    rows["__prio"] = np.where(rows["Cam_OfflineBool"], 2, np.where(rows["Cam_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0]
    rows = rows.sort_values(["__prio","Cam_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty and not has_query:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100% OK.")
    else:
        for _, r in rows.iterrows():
            status = "OFFLINE" if r["Cam_OfflineBool"] else (f"FALTANDO {int(r['Cam_Falta'])}" if r["Cam_Falta"]>0 else "OK")
            cor = "off" if status=="OFFLINE" else ("warn" if status.startswith("FALTANDO") else "ok")
            info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
            card_local(r["Local"], status, info, cor)

        # se houve busca, mostrar locais OK (discretos)
        if has_query:
            oks = base[(~base["Cam_OfflineBool"]) & (base["Cam_Falta"]==0)]
            for _, r in oks.sort_values("Local").iterrows():
                card_local(r["Local"], "OK", f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}", "ok")

    # Gráfico final (apenas Online, Offline, Locais p/ manutenção)
    bar_single({"Online": on, "Offline": off, "Locais p/ manutenção": manut_qtd_locais},
               "Resumo de Câmeras")

# ------------- RENDER ALARMES -------------
def render_alarms(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[mask_sem_alm(dfx)]
    st.markdown("### 🚨 Alarmes")

    tot = int(base["Alm_Total"].sum())
    on  = int(base["Alm_Online"].sum())
    off = max(tot - on, 0)
    manut_qtd_locais = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"]>0)).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='card'><div class='sub'>Centrais Totais</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='card'><div class='sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{off}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='card'><div class='sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{manut_qtd_locais}</div></div>", unsafe_allow_html=True)

    # Ordenação: 1) offline, 2) maior faltante
    rows = base.copy()
    rows["__prio"] = np.where(rows["Alm_OfflineBool"], 2, np.where(rows["Alm_Falta"]>0, 1, 0))
    rows = rows[rows["__prio"]>0]
    rows = rows.sort_values(["__prio","Alm_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty and not has_query:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100%.")
    else:
        for _, r in rows.iterrows():
            status = "OFFLINE" if r["Alm_OfflineBool"] else (f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})" if r["Alm_Falta"]>0 else "100%")
            cor = "off" if status=="OFFLINE" else ("warn" if status.startswith("PARCIAL") else "ok")
            info = f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']} • {r['Alm_Percent']:.0f}%"
            card_local(r["Local"], status, info, cor)

        if has_query:
            oks = base[(~base["Alm_OfflineBool"]) & (base["Alm_Falta"]==0)]
            for _, r in oks.sort_values("Local").iterrows():
                card_local(r["Local"], "100%", f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']} • 100%", "ok")

    bar_single({"Online": on, "Offline": off, "Locais p/ manutenção": manut_qtd_locais},
               "Resumo de Alarmes")

# ------------- RENDER GERAL -------------
def render_geral(dfx: pd.DataFrame):
    st.markdown("### 📈 Geral (Câmeras + Alarmes)")

    cam_ok = dfx[dfx["Cam_Total"]>0]
    alm_ok = dfx[dfx["Alm_Total"]>0]

    cam_tot, cam_on = int(cam_ok["Cam_Total"].sum()), int(cam_ok["Cam_Online"].sum())
    alm_tot, alm_on = int(alm_ok["Alm_Total"].sum()), int(alm_ok["Alm_Online"].sum())
    cam_off, alm_off = max(cam_tot-cam_on,0), max(alm_tot-alm_on,0)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.markdown(f"<div class='card'><div class='sub'>Câmeras Online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='sub'>Alarmes Online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='sub'>Total de Câmeras</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><div class='sub'>Total de Alarmes</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='card'><div class='sub'>Câmeras Offline</div><div class='metric' style='color:{CLR_RED};'>{cam_off}</div></div>", unsafe_allow_html=True)
    c6.markdown(f"<div class='card'><div class='sub'>Alarmes Offline</div><div class='metric' style='color:{CLR_RED};'>{alm_off}</div></div>", unsafe_allow_html=True)

    # gráfico geral (apenas barras simples)
    total_online = cam_on + alm_on
    total_off    = cam_off + alm_off
    bar_single({"Online": total_online, "Offline": total_off, "Locais p/ manutenção": 0},
               "Geral: Online x Offline")

    # PDF
    pdf_bytes = build_pdf_bytes(dfx)
    st.download_button("📄 Baixar PDF (Resumo do Dashboard)",
                       data=pdf_bytes,
                       file_name=f"relatorio_perimetro_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                       mime="application/pdf", use_container_width=True)

# ------------- DISPATCH -------------
tab = st.session_state['tab']
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro • Dashboard Operacional v3.4")
