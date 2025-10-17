# streamlit_app.py
import re
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from openpyxl import load_workbook

# ==================== CONFIG DA PÁGINA ====================
st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro",
                   page_icon="📹",
                   layout="wide")

# ==================== CORES DO TEMA ====================
AZUL = "#071E47"   # cabeçalho (site)
LARANJA = "#FF7600"
VERDE = "#27AE60"
VERMELHO = "#FF0000"
CINZA_BG = "#F5F7FB"

# ==================== CSS ====================
st.markdown(f"""
<style>
html, body, .block-container {{ background-color: white; }}
.topbar {{ height:12px; background: linear-gradient(90deg, {AZUL} 0%, {LARANJA} 100%); border-radius: 4px; margin-bottom: 20px; }}

.hdr-wrap {{ display:flex; align-items:center; gap:16px; }}
.hdr-title {{ color:{AZUL}; font-weight:800; font-size:28px; margin:0; }}
.hdr-sub {{ color:{AZUL}; opacity:.75; font-size:15px; margin:0; }}

.metric-card {{
    background: #fff; border:1px solid #eef0f5; border-radius: 12px;
    padding: 18px; text-align:center;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    transition: transform .2s ease, box-shadow .2s ease;
}}
.metric-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 28px rgba(0,0,0,0.10); }}
.metric-title {{ color:#6b6b6b; font-size:13px; margin-bottom:6px; }}
.metric-value {{ font-size:30px; font-weight:800; }}

.section-title {{ color:{AZUL}; font-weight:700; margin: 4px 0 8px; }}

.styled-table {{
    border-collapse: collapse; width: 100%; font-size: 15px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    animation: fadeIn .6s ease both;
    border-radius: 10px; overflow: hidden;
}}
.styled-table thead tr {{ background-color: {AZUL}; color: #fff; text-align: left; font-weight: 700; }}
.styled-table th, .styled-table td {{ padding: 10px 16px; }}
.styled-table tbody tr:hover {{ background-color: #faf3eb; transform: translateX(3px); transition: all .15s ease; }}

.offline-row {{ background-color: #FFE5CC; }}   /* laranja suave */
.faltando-row {{ background-color: #FFF7E6; }}  /* amarelo claro */

.status-label {{
    font-weight:700; padding:6px 10px; border-radius:8px; display:inline-block;
    animation: pulse 2s infinite;
}}
.status-offline {{ background:{VERMELHO}; color:#fff; }}
.status-faltando {{ background:#FFC107; color:#000; }}

@keyframes pulse {{ 0%{{opacity:1;}} 50%{{opacity:.85;}} 100%{{opacity:1;}} }}
@keyframes fadeIn {{ from{{opacity:0; transform:translateY(6px);}} to{{opacity:1; transform:translateY(0);}} }}
.footer {{ color:#777; font-size:13px; margin-top:20px; text-align:center; }}
</style>
""", unsafe_allow_html=True)

# ==================== TOPO ====================
st.markdown("<div class='topbar'></div>", unsafe_allow_html=True)
c_logo, c_head = st.columns([1,5])
with c_logo:
    try:
        st.image("logo.png", width=110)
    except Exception:
        st.write("")
with c_head:
    st.markdown(f"<div class='hdr-wrap'><h1 class='hdr-title'>Dashboard de Câmeras - Grupo Perímetro</h1></div>", unsafe_allow_html=True)
    st.markdown(f"<p class='hdr-sub'>Controle de câmeras</p>", unsafe_allow_html=True)
st.markdown("---")

# ==================== LEITURA DA PLANILHA ====================
EXCEL_FILE = "dados.xlsx"
try:
    df_full = pd.read_excel(EXCEL_FILE, engine="openpyxl", header=None)  # sem header para endereçar por índice
except Exception as e:
    st.error(f"❌ Erro ao carregar planilha: {e}")
    st.stop()

# Faixa útil: linhas 4..47 (índices 3..46), colunas A,B,C,D (0,1,2,3)
df = df_full.iloc[3:47, 0:4].copy()
df.columns = ["Local", "Total", "Online", "Status"]

# ==================== DATA A55 (ROBUSTA) ====================
def parse_excel_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):         # serial Excel
        base = datetime(1899, 12, 30)
        return base + timedelta(days=int(value))
    s = str(value).strip()
    for fmt in ("%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d/%m/%y","%d-%m-%y"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(d):
            return d.to_pydatetime()
    except:
        pass
    return None

try:
    wb = load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    dt = parse_excel_date(sheet["A55"].value)
    ultima_atualizacao = dt.strftime("%d/%m/%Y") if dt else "Não informada"
except Exception:
    ultima_atualizacao = "Erro ao ler data"

st.markdown(f" **Última atualização:** {ultima_atualizacao}")
st.markdown("---")

# ==================== NORMALIZAÇÃO ====================
def norm_text(x):
    return "" if pd.isna(x) else str(x).strip()

df["Local"] = df["Local"].apply(norm_text)
df["Status"] = df["Status"].apply(lambda s: norm_text(s).lower())

def is_offline_text(s: str) -> bool:
    if not s: return False
    s2 = s.lower()
    # aceita variações: offline, off-line, off line, off, off_line, sem câmeras
    return bool(re.search(r"\boff\s*-?\s*line\b|\boffline\b|\boff\b|sem\s*c[aâ]meras", s2))

def parse_int_safe(x):
    try:
        if pd.isna(x): return None
        if isinstance(x,(int,float)): return int(x)
        m = re.search(r"(\d+)", str(x).replace(".", "").replace(",", ""))
        return int(m.group(1)) if m else None
    except:
        return None

# Online: se C for número → usa; se contiver “offline” → 0
def parse_online(cell_c, status_d):
    n = parse_int_safe(cell_c)
    if n is not None:
        return max(n, 0)
    # se texto e indica offline → 0
    if is_offline_text(norm_text(cell_c)) or is_offline_text(status_d):
        return 0
    return 0  # fallback

df["Total"]  = df["Total"].apply(lambda x: parse_int_safe(x) or 0)
df["Online"] = [parse_online(c, s) for c, s in zip(df["Online"], df["Status"])]

# “Sem câmeras” → força total=0 e online=0
sem_cam_mask = df["Status"].str.contains("sem c", na=False)
df.loc[sem_cam_mask, ["Total","Online"]] = 0

# Offline calculado por linha
df["Offline_calc"] = (df["Total"] - df["Online"]).clip(lower=0)

# Badge de status para a tabela:
# - Offline (vermelho) quando total>0 e online==0
# - senão Faltando X (amarelo) quando X>0
# - linhas com X==0 não aparecem na tabela
def status_badge(total, online, status_text, offline_x):
    if total > 0 and online == 0:
        return "offline"
    if offline_x > 0:
        return f"faltando {offline_x}"
    return "ok"

df["Badge"] = [status_badge(t, o, s, x) for t, o, s, x in zip(df["Total"], df["Online"], df["Status"], df["Offline_calc"])]

# ==================== AGREGADOS ====================
total_cameras = int(df["Total"].sum())
cameras_online = int(df["Online"].sum())
cameras_offline = int(df["Offline_calc"].sum())  # é o que alimenta cards e gráfico
locais_manut = df[(df["Badge"] != "ok") & (df["Local"] != "")].copy()

# ==================== CARDS ====================
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Total de Câmeras</div>"
                f"<div class='metric-value' style='color:{AZUL}'>{total_cameras}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Online</div>"
                f"<div class='metric-value' style='color:{VERDE}'>{cameras_online}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Offline</div>"
                f"<div class='metric-value' style='color:{VERMELHO}'>{cameras_offline}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Locais em Manutenção</div>"
                f"<div class='metric-value' style='color:{LARANJA}'>{len(locais_manut)}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==================== TABELA (com busca) ====================
st.markdown(f"<h3 class='section-title'>Locais que precisam de manutenção</h3>", unsafe_allow_html=True)

if len(locais_manut):
    # ordena: offline primeiro, depois faltando maior→menor
    locais_manut["is_offline"] = locais_manut["Badge"].apply(lambda b: 1 if b == "offline" else 0)
    # extrai X de "faltando X"
    locais_manut["faltandoX"] = locais_manut["Offline_calc"]
    locais_manut = locais_manut.sort_values(by=["is_offline","faltandoX"], ascending=[False, False])

    filtro = st.text_input("🔍 Buscar local:", "").strip().lower()
    if filtro:
        locais_manut = locais_manut[locais_manut["Local"].str.lower().str.contains(filtro)]

    # monta HTML
    html = "<table class='styled-table'><thead><tr><th>Local</th><th>Status</th></tr></thead><tbody>"
    for _, r in locais_manut.iterrows():
        if r["Badge"] == "offline":
            cls = "offline-row"
            badge = "<span class='status-label status-offline'>Offline</span>"
        else:
            cls = "faltando-row"
            badge = f"<span class='status-label status-faltando'>Faltando {int(r['faltandoX'])}</span>"
        html += f"<tr class='{cls}'><td>{r['Local']}</td><td>{badge}</td></tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")

st.markdown("---")

# ==================== GRÁFICOS ====================
col_bar, col_pie = st.columns([2, 1])

with col_bar:
    st.markdown(f"<h3 class='section-title'>Online vs Offline</h3>", unsafe_allow_html=True)
    df_chart = pd.DataFrame({"Status":["Online","Offline"],
                             "Quantidade":[cameras_online, cameras_offline]})
    fig = px.bar(df_chart, x="Status", y="Quantidade", text="Quantidade",
                 color="Status",
                 color_discrete_map={"Online": VERDE, "Offline": VERMELHO},
                 height=420)
    fig.update_traces(textposition="outside",
                      hovertemplate="<b>%{x}</b><br>%{y} câmeras")
    fig.update_layout(xaxis_title="", yaxis_title="Quantidade de câmeras",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      transition={"duration":400})
    st.plotly_chart(fig, use_container_width=True)

with col_pie:
    st.markdown(f"<h3 class='section-title'>Proporção Geral</h3>", unsafe_allow_html=True)
    df_pie = pd.DataFrame({"Categoria":["Funcionando","Manutenção"],
                           "Quantidade":[cameras_online, cameras_offline]})
    pie = px.pie(df_pie, values="Quantidade", names="Categoria",
                 color="Categoria",
                 color_discrete_map={"Funcionando": VERDE, "Manutenção": LARANJA},
                 hole=0.45)
    pie.update_traces(textinfo="percent+label", pull=[0, 0.08])
    pie.update_layout(showlegend=False, height=420)
    st.plotly_chart(pie, use_container_width=True)

# ==================== RODAPÉ ====================
st.markdown("<div class='footer'>© Grupo Perímetro & Monitoramento - 2025</div>", unsafe_allow_html=True)
