# app.py
# Streamlit dashboard — CFTV & Alarmes (tema escuro + busca + duas seções)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO

# =========================
# CONFIG & ESTILO (Dark UI)
# =========================
st.set_page_config(
    page_title="Dashboard Operacional – CFTV & Alarmes",
    page_icon="🛡️",
    layout="wide"
)

PRIMARY_NEON = "#00E5FF"   # azul neon
SUCCESS_NEON = "#17E66E"   # verde vibrante
WARN_NEON    = "#FFD54A"   # amarelo vibrante
DANGER_NEON  = "#FF4D4D"   # vermelho vibrante
BG_DARK      = "#0D0F14"   # fundo principal
PANEL_DARK   = "#141823"   # cards
TEXT_LIGHT   = "#E6E8EE"   # texto padrão

LOGO_PATH    = "logo_perimetro.png"   # ajuste se necessário
PLANILHA     = "dados.xlsx"           # mesmo arquivo que você já usa

CUSTOM_CSS = f"""
<style>
/* Base */
.stApp {{
  background: radial-gradient(1200px 800px at 15% -5%, rgba(0,229,255,0.08), transparent 60%),
              radial-gradient(900px 600px at 100% 0%, rgba(255,77,77,0.06), transparent 40%),
              linear-gradient(180deg, {BG_DARK} 0%, #0b0d12 100%);
  color: {TEXT_LIGHT};
  font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";
}}
/* Header */
.header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; position: sticky; top: 0; z-index: 999;
  background: linear-gradient(180deg, rgba(20,24,35,0.95) 0%, rgba(20,24,35,0.85) 100%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(10px);
  margin: -1rem -1rem 1rem -1rem;
}}
.header-left {{ display: flex; align-items: center; gap: 12px; }}
.header-title {{
  font-weight: 700; letter-spacing: .2px; margin: 0;
}}
.header-sub {{
  font-size: 12px; color: #9aa3b2; margin-top: -6px;
}}
.logo {{
  width: 40px; height: 40px; object-fit: contain; filter: drop-shadow(0 0 8px rgba(0,229,255,.35));
}}
/* Search */
.search-wrap {{
  position: relative; min-width: 280px; max-width: 360px;
}}
.search-wrap input {{
  width: 100%; padding: 10px 36px 10px 36px; border-radius: 12px;
  background: rgba(255,255,255,0.06); color: {TEXT_LIGHT};
  border: 1px solid rgba(255,255,255,0.08);
}}
.search-icon {{
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  opacity: .75;
}}
.search-wrap input:focus {{
  outline: none; box-shadow: 0 0 0 3px rgba(0,229,255,0.25);
  border-color: {PRIMARY_NEON};
}}
/* Toggle buttons */
.toggle-wrap {{
  display: inline-flex; padding: 6px; gap: 6px; border-radius: 14px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
}}
.toggle-btn {{
  padding: 8px 14px; border-radius: 10px; cursor: pointer; user-select: none;
  transition: transform .15s ease, background .2s ease, color .2s ease;
  color: #c8cfda; border: 1px solid transparent;
}}
.toggle-btn.active {{
  background: linear-gradient(180deg, rgba(0,229,255,.18), rgba(0,229,255,.08));
  color: {TEXT_LIGHT}; border-color: rgba(0,229,255,.35);
  box-shadow: 0 6px 18px rgba(0,229,255,.14), inset 0 0 0 1px rgba(0,229,255,.25);
}}
.toggle-btn:hover {{ transform: translateY(-1px); }}
/* Cards */
.card {{
  background: {PANEL_DARK}; border: 1px solid rgba(255,255,255,.06);
  border-radius: 16px; padding: 16px; transition: transform .15s ease, box-shadow .2s ease, border .2s ease;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}}
.card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(0,0,0,.35);
  border-color: rgba(0,229,255,.22);
}}
.metric {{
  font-size: 28px; font-weight: 800; letter-spacing: .3px; margin: 6px 0 2px 0;
}}
.metric-sub {{
  font-size: 12px; color: #9aa3b2; margin-top: -6px;
}}
.tag {{
  display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; border: 1px solid transparent;
}}
.tag.ok {{ color: {SUCCESS_NEON}; border-color: rgba(23,230,110,.35); background: rgba(23,230,110,.12); }}
.tag.warn {{ color: {WARN_NEON};    border-color: rgba(255,213,74,.35); background: rgba(255,213,74,.12); }}
.tag.dng {{ color: {DANGER_NEON};   border-color: rgba(255,77,77,.35);  background: rgba(255,77,77,.12); }}
.row {{
  display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; width: 100%;
}}
.col-3 {{ grid-column: span 3; }}
.col-4 {{ grid-column: span 4; }}
.col-6 {{ grid-column: span 6; }}
.col-12 {{ grid-column: span 12; }}
.item {{
  display:flex; align-items:center; justify-content:space-between;
  border-top: 1px dashed rgba(255,255,255,.08); padding: 10px 0;
}}
.item:first-child {{ border-top: none; }}
.name {{ font-weight: 600; }}
.status {{ display:flex; align-items:center; gap:10px; }}
.small {{ font-size: 12px; color:#a6afbf; }}
hr.div {{ border:none; height:1px; background: linear-gradient(90deg, rgba(0,229,255,.0), rgba(0,229,255,.35), rgba(0,229,255,.0)); margin: 8px 0 14px 0; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =========================
# CARREGAMENTO DA PLANILHA
# =========================
@st.cache_data(show_spinner=False)
def load_data(planilha_path: str):
    # Lê a planilha inteira
    df_raw = pd.read_excel(planilha_path, header=None)

    # Procura a primeira linha onde há um texto parecido com "OK" ou "OFFLINE" ou "FALTANDO"
    start_index = None
    for i, row in df_raw.iterrows():
        if row.astype(str).str.contains("OK|OFFLINE|FALTANDO", case=False, na=False).any():
            start_index = max(i - 1, 0)  # sobe 1 linha (a de cabeçalho)
            break

    # Se não encontrar, assume início padrão
    if start_index is None:
        start_index = 3  # padrão (linha 4 no Excel)

    # Corta os dados a partir daí (linha de cabeçalho + dados)
    df = df_raw.iloc[start_index:, :8].copy()

    # Força 7 colunas no máximo (A até G)
    if df.shape[1] < 7:
        for _ in range(7 - df.shape[1]):
            df[df.shape[1]] = np.nan
    elif df.shape[1] > 7:
        df = df.iloc[:, :7]

    # Renomeia colunas fixas
    df.columns = ["A_Local", "B_TotalCam", "C_OnlineCam", "D_StatusCam",
                  "E_TotalAlm", "F_OnlineAlm", "G_PercentAlm"]

    # Remove linhas totalmente vazias
    df = df.dropna(how="all")

    # Remove linhas que são títulos (ex: “RELATÓRIO DE CÂMERAS...”)
    df = df[~df["A_Local"].astype(str).str.contains("RELATÓRIO|CÂMERAS|ALARMES|POSTOS", case=False, na=False)]

    # Limpa espaços
    df["A_Local"] = df["A_Local"].astype(str).str.strip()

    # Converte números
    for col in ["B_TotalCam", "C_OnlineCam", "E_TotalAlm", "F_OnlineAlm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Percentual de alarmes
    def calc_percent(row):
        if row["E_TotalAlm"] <= 0:
            return 0
        return round((row["F_OnlineAlm"] / row["E_TotalAlm"]) * 100, 2)

    df["G_PercentAlm"] = df["G_PercentAlm"].apply(lambda v: float(str(v).replace('%','').strip()) if pd.notna(v) else np.nan)
    df["G_PercentAlm"] = np.where(df["G_PercentAlm"].notna(), df["G_PercentAlm"], df.apply(calc_percent, axis=1))

    # Status de câmeras
    def status_cam(row):
        total, online = row["B_TotalCam"], row["C_OnlineCam"]
        s = str(row["D_StatusCam"]).strip().upper()
        if "OK" in s or "EXCESSO" in s or "FALTANDO" in s or "OFFLINE" in s:
            return s
        if total == 0:
            return "SEM DADOS"
        if online == total:
            return "OK"
        if online > total:
            return "EXCESSO"
        if online == 0:
            return "OFFLINE"
        return f"FALTANDO {total - online}"

    df["D_StatusCam"] = df.apply(status_cam, axis=1)

    # Status de alarmes
    def status_alm(p):
        if p >= 99.9:
            return "100%"
        if p >= 66:
            return "PARCIAL (≥66%)"
        if p >= 50:
            return "PARCIAL (50%)"
        if p > 0:
            return "PARCIAL (<50%)"
        return "OFFLINE"

    df["Alarmes_Status"] = df["G_PercentAlm"].apply(status_alm)

    return df

# =========================
# HELPERS UI / MÉTRICAS
# =========================
def metric_card(title, value, subtitle="", span_class="col-3"):
    st.markdown(
        f"""
        <div class="card {span_class}">
          <div class="small">{title}</div>
          <div class="metric">{value}</div>
          <div class="metric-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def tag(status_text):
    s = status_text.upper()
    if "OK" in s or "100%" in s:
        return '<span class="tag ok">🟢 OK</span>'
    if "EXCESSO" in s:
        return '<span class="tag warn">🟡 EXCESSO</span>'
    if "FALTANDO" in s or "PARCIAL" in s:
        return '<span class="tag warn">🟡 PARCIAL</span>'
    if "OFFLINE" in s or "SEM DADO" in s:
        return '<span class="tag dng">🔴 OFFLINE</span>'
    return '<span class="tag warn">🟡 STATUS</span>'

def camera_resume(df_):
    total_cam = df_["B_TotalCam"].sum()
    online_cam = df_["C_OnlineCam"].sum()
    offline_cam = max(total_cam - online_cam, 0)
    ok_locs = (df_["D_StatusCam"].str.upper() == "OK").sum()
    exc_locs = df_["D_StatusCam"].str.upper().str.contains("EXCESSO").sum()
    falt_locs = df_["D_StatusCam"].str.upper().str.contains("FALTANDO|OFFLINE|SEM DADO").sum()
    return total_cam, online_cam, offline_cam, ok_locs, exc_locs, falt_locs

def alarm_resume(df_):
    tot = df_["E_TotalAlm"].sum()
    on  = df_["F_OnlineAlm"].sum()
    perc_global = (on / tot * 100.0) if tot > 0 else 0.0
    full_ok = (df_["G_PercentAlm"] >= 99.99).sum()
    partial = ((df_["G_PercentAlm"] > 0) & (df_["G_PercentAlm"] < 99.99)).sum()
    off     = (df_["G_PercentAlm"] == 0).sum()
    return tot, on, perc_global, full_ok, partial, off

# =========================
# HEADER (logo + título + busca)
# =========================
col_logo, col_title, col_search = st.columns([0.12, 0.58, 0.30])
with col_logo:
    try:
        st.image(LOGO_PATH, use_container_width=False)
    except:
        st.write("")

with col_title:
    st.markdown(
        f"""
        <div class="header">
          <div class="header-left">
            <img src="app://{LOGO_PATH}" class="logo" onerror="this.style.display='none'">
            <div>
              <h3 class="header-title">Dashboard Operacional – CFTV &amp; Alarmes</h3>
              <div class="header-sub">Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
            </div>
          </div>
          <div class="search-wrap"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Como o HTML direto acima não injeta o input de busca real do Streamlit,
# criamos a busca "discreta e bonita" com um container próprio ao lado:
with col_search:
    # input de pesquisa (discreto)
    query = st.text_input(" ", placeholder="Pesquisar local...", label_visibility="collapsed")
    # estilizar o label invisível
    st.markdown(
        """
        <div class="search-icon">🔎</div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<hr class='div'/>", unsafe_allow_html=True)

# =========================
# TOGGLE: CÂMERAS | ALARMES
# =========================
left, mid, right = st.columns([0.4, 0.2, 0.4])
with mid:
    # usamos session_state para lembrar a aba selecionada
    if "tab" not in st.session_state:
        st.session_state.tab = "Câmeras"

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📷 Câmeras", use_container_width=True, type="primary" if st.session_state.tab=="Câmeras" else "secondary"):
            st.session_state.tab = "Câmeras"
    with c2:
        if st.button("🚨 Alarmes", use_container_width=True, type="primary" if st.session_state.tab=="Alarmes" else "secondary"):
            st.session_state.tab = "Alarmes"

st.markdown("<hr class='div'/>", unsafe_allow_html=True)

# =========================
# FILTRO DE BUSCA (sempre)
# =========================
if query and str(query).strip():
    mask = df["A_Local"].str.contains(query.strip(), case=False, na=False)
    dff = df[mask].copy()
else:
    dff = df.copy()

# =========================
# SEÇÃO — CÂMERAS
# =========================
def render_cameras(dbase):
    st.markdown("### 📷 Câmeras")
    total_cam, online_cam, offline_cam, ok_locs, exc_locs, falt_locs = camera_resume(dbase)

    c_a, c_b, c_c, c_d = st.columns(4)
    with c_a: metric_card("Total de Câmeras", f"{total_cam:,}".replace(",", "."), "Soma de todos os locais")
    with c_b: metric_card("Online", f"{online_cam:,}".replace(",", "."), "Câmeras operando",)
    with c_c: metric_card("Offline / Faltando", f"{offline_cam:,}".replace(",", "."), "Diferença total – online")
    with c_d: metric_card("Locais: OK / Excesso / Faltando", f"{ok_locs} / {exc_locs} / {falt_locs}", "Status por local")

    st.markdown("<div class='card col-12'>", unsafe_allow_html=True)
    st.markdown("**Locais e status (câmeras):**")
    for _, r in dbase.sort_values("A_Local").iterrows():
        st.markdown(
            f"""
            <div class="item">
              <div class="name">📍 {r['A_Local']}</div>
              <div class="status">
                <span class="small">Total: {r['B_TotalCam']} · Online: {r['C_OnlineCam']}</span>
                {tag(r['D_StatusCam'])}
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SEÇÃO — ALARMES
# =========================
def render_alarms(dbase):
    st.markdown("### 🚨 Alarmes")
    tot, on, perc_global, full_ok, partial, off = alarm_resume(dbase)

    a, b, c, d = st.columns(4)
    with a: metric_card("Centrais de Alarme (Total)", f"{tot:,}".replace(",", "."), "Soma geral")
    with b: metric_card("Centrais Online", f"{on:,}".replace(",", "."), "Operando agora")
    with c: metric_card("Percentual Médio", f"{perc_global:.1f}%", "Média ponderada geral")
    with d: metric_card("Locais: 100% / Parcial / Offline", f"{full_ok} / {partial} / {off}", "Status por local")

    st.markdown("<div class='card col-12'>", unsafe_allow_html=True)
    st.markdown("**Locais e status (alarmes):**")
    for _, r in dbase.sort_values("A_Local").iterrows():
        perc = r["G_PercentAlm"]
        status = r["Alarmes_Status"]
        st.markdown(
            f"""
            <div class="item">
              <div class="name">📍 {r['A_Local']}</div>
              <div class="status">
                <span class="small">Total: {r['E_TotalAlm']} · Online: {r['F_OnlineAlm']} · {perc:.0f}%</span>
                {tag('OK' if status=='100%' else ('OFFLINE' if status=='OFFLINE' else 'PARCIAL'))}
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RENDER DE ACORDO COM ABA
# =========================
if st.session_state.tab == "Câmeras":
    render_cameras(dff)
else:
    render_alarms(dff)

# Rodapé sutil
st.markdown("<hr class='div'/>", unsafe_allow_html=True)
st.caption("Grupo Perímetro — Painel Operacional • v1.0 (Câmeras + Alarmes + Busca)")
