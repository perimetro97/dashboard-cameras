# streamlit_app.py
import re
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from openpyxl import load_workbook

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro",
                   page_icon="📹",
                   layout="wide")

# ==================== CSS / ESTILO ====================
st.markdown("""
<style>
.top-gradient {
    height:10px;
    background: linear-gradient(90deg, #1E3A8A 0%, #FF6600 100%);
    border-radius: 4px;
    margin-bottom: 20px;
}
.hdr-title { color:#FF6600; font-weight:800; font-size:28px; margin-bottom:4px; }
.hdr-sub { color:#1E1E5E; font-size:16px; margin-bottom:0; }
.metric-card {
    background: #fff;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.metric-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
.metric-title { color:#6b6b6b; font-size:14px; margin-bottom:4px; }
.metric-value { font-size:30px; font-weight:700; }

.styled-table {
    border-collapse: collapse;
    width: 100%;
    font-size: 15px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    animation: fadeIn 0.8s ease both;
    border-radius: 10px;
    overflow: hidden;
}
.styled-table thead tr {
    background-color: #1E3A8A;
    color: #fff;
    text-align: left;
    font-weight: 700;
}
.styled-table th, .styled-table td { padding: 10px 16px; }
.styled-table tbody tr:hover { background-color: #faf3eb; transform: translateX(3px); }
.offline-row { background-color: #FFE5CC; }
.faltando-row { background-color: #FFF7E6; }

.status-label {
    font-weight:600;
    padding:5px 10px;
    border-radius:6px;
    display:inline-block;
    animation: pulse 2s infinite;
}
.status-offline { background:#FF0000; color:#fff; }
.status-faltando { background:#FFC107; color:#000; }
@keyframes pulse {
    0% {opacity:1;}
    50% {opacity:0.85;}
    100% {opacity:1;}
}
@keyframes fadeIn { from {opacity:0; transform:translateY(6px);} to {opacity:1; transform:translateY(0);} }
.footer { color:#777; font-size:13px; margin-top:20px; text-align:center; }
</style>
""", unsafe_allow_html=True)

# ==================== CABEÇALHO ====================
st.markdown("<div class='top-gradient'></div>", unsafe_allow_html=True)
col_logo, col_title = st.columns([1,5])
with col_logo:
    try:
        st.image("logo.png", width=110)
    except Exception:
        st.write("")
with col_title:
    st.markdown("<h1 class='hdr-title'>Dashboard de Câmeras - Grupo Perímetro</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hdr-sub'>Painel de status e desempenho das câmeras</p>", unsafe_allow_html=True)
st.markdown("---")

# ==================== LEITURA DO EXCEL ====================
EXCEL_FILE = "dados.xlsx"
try:
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl", header=0)
except Exception as e:
    st.error(f"❌ Erro ao carregar planilha: {e}")
    st.stop()

# -------- Função para interpretar data (A55) --------
def parse_excel_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        base = datetime(1899,12,30)
        return base + timedelta(days=int(value))
    s = str(value).strip()
    for fmt in ("%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d/%m/%y","%d-%m-%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(d): return d.to_pydatetime()
    except: pass
    return None

try:
    wb = load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    dt = parse_excel_date(sheet["A55"].value)
    ultima_atualizacao = dt.strftime("%d/%m/%Y") if dt else "Não informada"
except Exception:
    ultima_atualizacao = "Erro ao ler data"

st.markdown(f"📅 **Última atualização:** {ultima_atualizacao}")
st.markdown("---")

# ==================== COLUNAS PRINCIPAIS ====================
cols = list(df.columns)
col_local, col_qtd, col_status = cols[0], cols[2], cols[3]
df[col_local] = df[col_local].astype(str).fillna("").str.strip()
df[col_status] = df[col_status].astype(str).fillna("").str.strip()

# ==================== FUNÇÕES AUXILIARES ====================
def parse_int_safe(x):
    try:
        if pd.isna(x): return None
        if isinstance(x,(int,float)): return int(x)
        m = re.search(r"(\d+)", str(x))
        return int(m.group(1)) if m else None
    except: return None

# ==================== CÁLCULOS ====================
try:
    series_online = pd.to_numeric(df[col_qtd].iloc[3:42], errors="coerce").fillna(0)
    cameras_online = int(series_online.sum())
except: cameras_online = 0

manut_records=[]
for _, row in df.iterrows():
    local=str(row.get(col_local,"")).strip()
    if not local: continue
    status=str(row.get(col_status,"")).lower().strip()
    qtd=row.get(col_qtd,None)
    if "faltando" in status:
        q=parse_int_safe(status) or parse_int_safe(qtd) or 0
        manut_records.append({"Local":local,"Qtde":q,"Status":f"Faltando {q}","Tipo":"faltando"})
    elif "offline" in status or status=="off":
        manut_records.append({"Local":local,"Qtde":1,"Status":"Offline","Tipo":"offline"})
cameras_offline=sum(r["Qtde"] for r in manut_records)
total_cameras = cameras_online + cameras_offline

# ==================== CARDS ====================
c1,c2,c3=st.columns(3)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Online</div>"
                f"<div class='metric-value' style='color:#27AE60'>{cameras_online}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Offline</div>"
                f"<div class='metric-value' style='color:#FF0000'>{cameras_offline}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Locais em Manutenção</div>"
                f"<div class='metric-value' style='color:#FF6600'>{len(manut_records)}</div></div>", unsafe_allow_html=True)
st.markdown("---")

# ==================== TABELA DE MANUTENÇÃO ====================
st.subheader("🔧 Locais que precisam de manutenção")
if manut_records:
    df_manut=pd.DataFrame(manut_records)
    df_manut["is_offline"]=df_manut["Tipo"].apply(lambda t:1 if t=="offline" else 0)
    df_manut=df_manut.sort_values(by=["is_offline","Qtde"],ascending=[False,False]).reset_index(drop=True)

    filtro=st.text_input("🔍 Buscar local:", "").strip().lower()
    if filtro:
        df_manut=df_manut[df_manut["Local"].str.lower().str.contains(filtro)]

    html="<table class='styled-table'><thead><tr><th>Local</th><th>Status</th></tr></thead><tbody>"
    for _,r in df_manut.iterrows():
        cls="offline-row" if r["Tipo"]=="offline" else "faltando-row"
        badge=("<span class='status-label status-offline'>Offline</span>"
               if r["Tipo"]=="offline"
               else f"<span class='status-label status-faltando'>Faltando {r['Qtde']}</span>")
        html+=f"<tr class='{cls}'><td>{r['Local']}</td><td>{badge}</td></tr>"
    html+="</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")
st.markdown("---")

# ==================== GRÁFICOS ====================
col1, col2 = st.columns([2,1])
with col1:
    st.subheader("Comparativo: Online vs Offline")
    df_chart=pd.DataFrame({"Status":["Online","Offline"],
                           "Quantidade":[int(cameras_online),int(cameras_offline)]})
    fig=px.bar(df_chart,x="Status",y="Quantidade",text="Quantidade",
               color="Status",
               color_discrete_map={"Online":"#27AE60","Offline":"#FF0000"},
               height=420)
    fig.update_traces(textposition="outside",
                      hovertemplate="<b>%{x}</b><br>%{y} câmeras")
    fig.update_layout(xaxis_title="",yaxis_title="Quantidade de câmeras",
                      plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                      transition={"duration":400})
    st.plotly_chart(fig,use_container_width=True)

with col2:
    st.subheader("📈 Proporção Geral")
    df_pie=pd.DataFrame({
        "Categoria":["Funcionando","Manutenção"],
        "Quantidade":[cameras_online, cameras_offline]
    })
    pie=px.pie(df_pie,values="Quantidade",names="Categoria",
               color="Categoria",
               color_discrete_map={"Funcionando":"#27AE60","Manutenção":"#FF6600"},
               hole=0.45)
    pie.update_traces(textinfo="percent+label",pull=[0,0.08])
    pie.update_layout(showlegend=False, height=420)
    st.plotly_chart(pie,use_container_width=True)

# ==================== RODAPÉ ====================
st.markdown("<div class='footer'>© Grupo Perímetro & Monitoramento - 2025</div>", unsafe_allow_html=True)
