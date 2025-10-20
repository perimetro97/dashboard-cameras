# =========================================================
# Dashboard Operacional – Grupo Perímetro (v3.3)
# CFTV & Alarmes • logo.png • leitura robusta • gráficos • PDF
# =========================================================
import os, re, glob
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
from fpdf import FPDF

# ------------- CONFIG GERAL -------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="🛡️", layout="wide")

PLANILHA = "dados.xlsx"

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
</style>
""", unsafe_allow_html=True)

# ------------- LOGO (logo.png) -------------
def get_logo_source():
    # tenta localmente
    for p in ["logo.png", "./logo.png", "/app/logo.png", "/app/dashboard-cameras/logo.png",
              "/mount/src/dashboard-cameras/logo.png"]:
        if os.path.exists(p):
            return p
    # fallback URL crua do GitHub
    return "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# ------------- HELPERS -------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CÂMERAS", "SEM CAMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> pd.DataFrame:
    """
    Lê a planilha 'dados.xlsx' e tenta mapear as colunas automaticamente.
    Esperado: A Local | B Cam_Total | C Cam_Online | D Cam_Status | E Alm_Total | F Alm_Online | G Alm_Status.
    Ignora cabeçalhos, linhas de totais e linhas vazias.
    """
    # Tentativa 1: já com header=None
    xl = pd.read_excel(xlsx_path, header=None)
    # Procura primeira linha de dados onde col A tem texto e B/C/E/F são números ou vazios
    def looks_like_row(row):
        a = str(row[0]).strip()
        has_name = (a != "nan" and len(a) > 0 and "TOTAL" not in a.upper())
        # Pelo menos uma métrica numérica em B,C,E,F
        nums = 0
        for j in [1,2,4,5]:
            try:
                float(str(row[j]).replace(",", "."))
                nums += 1
            except:
                pass
        return has_name and nums >= 1

    # encontra primeira linha válida
    start_idx = None
    for i in range(min(20, len(xl))):  # procura nos 20 primeiros
        if looks_like_row(xl.iloc[i, :]):
            start_idx = i
            break
    if start_idx is None:
        start_idx = 0

    data = xl.iloc[start_idx:, 0:7].copy()
    data.columns = ["Local","Cam_Total","Cam_Online","Cam_Status",
                    "Alm_Total","Alm_Online","Alm_Status"]

    # limpeza básica
    data = data.dropna(subset=["Local"])
    data["Local"] = data["Local"].astype(str).str.strip()
    # remove linhas resumo
    data = data[~data["Local"].str.contains("TOTAL|RELATÓRIO|RELATORIO", case=False, na=False)]

    # números
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        data[c] = data[c].apply(_to_int)

    # normaliza status de câmeras
    def cam_status(row):
        s = str(row["Cam_Status"]).strip().upper()
        tot, on = row["Cam_Total"], row["Cam_Online"]
        # se já vem marcado
        if any(k in s for k in ["OK","EXCESSO","FALTANDO","OFFLINE","SEM CÂMERAS","SEM CAMERAS"]):
            return s.replace("CAMERAS","CÂMERAS")
        if tot == 0: return "SEM CÂMERAS"
        if on >= tot: return "OK" if on == tot else "EXCESSO"
        if on == 0: return "OFFLINE"
        return f"FALTANDO {max(tot-on,0)}"
    data["Cam_Status"] = data.apply(cam_status, axis=1)

    # percentuais e status de alarmes
    def alm_percent(row):
        t, o = row["Alm_Total"], row["Alm_Online"]
        return 0.0 if t <= 0 else round(100.0*o/t, 2)
    data["Alm_Percent"] = data.apply(alm_percent, axis=1)

    def alm_status(row):
        s = str(row["Alm_Status"]).strip().upper()
        if "100%" in s: return "100%"
        if "OFFLINE" in s or "SEM ALARME" in s: return "OFFLINE"
        p = row["Alm_Percent"]
        if p >= 99.9: return "100%"
        if p > 0: return "PARCIAL"
        return "OFFLINE"
    data["Alm_Status"] = data.apply(alm_status, axis=1)

    return data.reset_index(drop=True)

# UI helpers
def card_local(local, status, info, cor="ok"):
    tag = "tag-ok" if cor=="ok" else ("tag-warn" if cor=="warn" else "tag-off")
    st.markdown(
        f"<div class='card'><b>📍 {local}</b> — <span class='{tag}'>{status}</span>"
        f"<div class='sub' style='margin-top:6px;'>{info}</div></div>", unsafe_allow_html=True
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
    fig = px.bar(df_counts, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria",
                 color_discrete_map={"Online":CLR_GREEN,"Manutenção":CLR_ORANGE,"Offline":CLR_RED})
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

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Câmeras: {cam_on}/{cam_tot} online • Alarmes: {alm_on}/{alm_tot} online", ln=True)
    pdf.ln(3)

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

    cam_rows = cam[cam["Cam_Status"]!="OK"][["Local","Cam_Status","Cam_Total","Cam_Online"]]
    alm_rows = alm[alm["Alm_Status"]!="100%"][["Local","Alm_Status","Alm_Total","Alm_Online"]]
    add_table("Câmeras em manutenção/offline", cam_rows)
    add_table("Alarmes em manutenção/offline", alm_rows)

    out = BytesIO(); pdf.output(out); out.seek(0)
    return out.read()

# ------------- HEADER -------------
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    st.image(get_logo_source(), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_title:
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='sub'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

with col_search:
    query = st.text_input("Pesquisar local...", "", placeholder="Digite o nome do local…")

# Abas
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"
b1, b2, b3 = st.columns(3)
if b1.button("📷 Câmeras"): st.session_state.tab = "Câmeras"
if b2.button("🚨 Alarmes"): st.session_state.tab = "Alarmes"
if b3.button("📈 Geral"):   st.session_state.tab = "Geral"

# ------------- DADOS -------------
df = load_data(PLANILHA)
if df.empty:
    st.error("Não foi possível ler dados da planilha `dados.xlsx`. Verifique se está na raiz e com colunas A..G.")
    st.stop()

has_query = bool(query.strip())
dfv = df if not has_query else df[df["Local"].str.contains(query.strip(), case=False, na=False)]

def mask_sem_cam(d): return ~d["Cam_Status"].str.contains("SEM CÂMERAS", case=False, na=False)
def mask_sem_alm(d): return (d["Alm_Total"] > 0) & ~d["Alm_Status"].str.contains("SEM ALARME", case=False, na=False)

# ------------- RENDER CÂMERAS -------------
def render_cameras(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[mask_sem_cam(dfx)]
    st.markdown("### 📷 Câmeras")

    tot = int(base["Cam_Total"].sum()); on = int(base["Cam_Online"].sum()); off = max(tot - on, 0)
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Total</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Offline/Manut.</div><div class='metric' style='color:{CLR_ORANGE};'>{off}</div></div>", unsafe_allow_html=True)

    rows = base if has_query else base[~base["Cam_Status"].str.contains("OK", case=False, na=False)]
    st.markdown("#### Locais em manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100% OK.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            status = r["Cam_Status"].upper()
            cor = "ok" if "OK" in status else ("warn" if ("FALTANDO" in status or "EXCESSO" in status) else "off")
            info = f"Total: {r['Cam_Total']} • Online: {r['Cam_Online']}"
            card_local(r["Local"], status, info, cor)

    tb = rows.assign(Status=rows["Cam_Status"], Total=rows["Cam_Total"], Online=rows["Cam_Online"])\
             [["Local","Status","Total","Online"]].reset_index(drop=True)
    st.markdown("#### Tabela resumida")
    st.dataframe(tb, use_container_width=True)

    # Gráficos (final)
    pie_online_manutencao(tot, on, "Distribuição de câmeras")
    dfc = pd.DataFrame({"Categoria":["Online","Manutenção","Offline"],
                        "Quantidade":[on, max(tot-on,0), rows[rows["Cam_Status"].str.contains("OFFLINE", case=False, na=False)]["Cam_Total"].sum()]})
    bar_online_offline(dfc, "Comparativo Online x Manutenção x Offline")

# ------------- RENDER ALARMES -------------
def render_alarms(dfx: pd.DataFrame):
    base = dfx if has_query else dfx[mask_sem_alm(dfx)]
    st.markdown("### 🚨 Alarmes")

    tot = int(base["Alm_Total"].sum()); on = int(base["Alm_Online"].sum()); perc = 0 if tot==0 else round(100*on/tot,1)
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='card'><div class='sub'>Centrais Totais</div><div class='metric'>{tot}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='card'><div class='sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{on}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='card'><div class='sub'>Percentual Geral</div><div class='metric' style='color:{CLR_BLUE};'>{perc}%</div></div>", unsafe_allow_html=True)

    rows = base if has_query else base[base["Alm_Status"]!="100%"]
    st.markdown("#### Locais em manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100%.")
    else:
        for _, r in rows.sort_values("Local").iterrows():
            stt = r["Alm_Status"]
            cor = "ok" if stt=="100%" else ("off" if "OFFLINE" in stt else "warn")
            info = f"Total: {r['Alm_Total']} • Online: {r['Alm_Online']} • {r['Alm_Percent']:.0f}%"
            card_local(r["Local"], stt, info, cor)

    tb = rows.assign(Status=rows["Alm_Status"], Total=rows["Alm_Total"], Online=rows["Alm_Online"], Percent=rows["Alm_Percent"].round(0))\
             [["Local","Status","Total","Online","Percent"]].rename(columns={"Percent":"%"}).reset_index(drop=True)
    st.markdown("#### Tabela resumida")
    st.dataframe(tb, use_container_width=True)

    # Gráficos (final)
    pie_online_manutencao(tot, on, "Distribuição de alarmes")
    dfa = pd.DataFrame({"Categoria":["Online","Manutenção","Offline"],
                        "Quantidade":[on, max(tot-on,0), rows[rows["Alm_Status"].str.contains("OFFLINE", case=False, na=False)]["Alm_Total"].sum()]})
    bar_online_offline(dfa, "Comparativo Online x Manutenção x Offline")

# ------------- RENDER GERAL -------------
def render_geral(dfx: pd.DataFrame):
    st.markdown("### 📈 Geral (Câmeras + Alarmes)")
    cam_ok = dfx[mask_sem_cam(dfx)]
    alm_ok = dfx[mask_sem_alm(dfx)]

    cam_tot, cam_on = int(cam_ok["Cam_Total"].sum()), int(cam_ok["Cam_Online"].sum())
    alm_tot, alm_on = int(alm_ok["Alm_Total"].sum()), int(alm_ok["Alm_Online"].sum())

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='card'><div class='sub'>Câmeras (total)</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='card'><div class='sub'>Câmeras online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='card'><div class='sub'>Alarmes (total)</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='card'><div class='sub'>Alarmes online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)

    pie_online_manutencao(cam_tot+alm_tot, cam_on+alm_on, "Geral: Online vs Manutenção")

    comb = pd.DataFrame({
        "Categoria":["Câmeras Online","Câmeras Manut.","Alarmes Online","Alarmes Manut."],
        "Quantidade":[cam_on, max(cam_tot-cam_on,0), alm_on, max(alm_tot-alm_on,0)]
    })
    fig = px.bar(comb, x="Categoria", y="Quantidade", text="Quantidade",
                 color="Categoria", color_discrete_map={
                    "Câmeras Online":CLR_GREEN, "Câmeras Manut.":CLR_ORANGE,
                    "Alarmes Online":CLR_GREEN, "Alarmes Manut.":CLR_ORANGE})
    fig.update_traces(textposition="outside")
    fig.update_layout(height=360, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    pdf_bytes = build_pdf_bytes(dfx)
    st.download_button("📄 Baixar PDF (Resumo do Dashboard)",
                       data=pdf_bytes,
                       file_name=f"relatorio_perimetro_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                       mime="application/pdf", use_container_width=True)

# ------------- DISPATCH -------------
if st.session_state.tab == "Câmeras":
    render_cameras(dfv)
elif st.session_state.tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro • Dashboard Operacional v3.3")
