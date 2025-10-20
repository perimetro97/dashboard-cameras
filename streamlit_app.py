# ============================================================
# Dashboard Operacional – Grupo Perímetro (v5.2)
# CFTV & Alarmes • Visual Pro • PDF desativado temporariamente
# ============================================================

import os
import requests
from io import BytesIO
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image
import streamlit as st

# ------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Operacional – CFTV & Alarmes",
    page_icon="🛡️",
    layout="wide"
)

PLANILHA = "dados.xlsx"

# ------------------------------------------------------------
# TOPO COM LOGO (versão estável 18/10)
# ------------------------------------------------------------
LOGO_FILE_CANDIDATES = [
    "logo.png",
    "./logo.png",
    "app/logo.png",
    "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png",
    "./logo_perimetro.png"
]

LOGO_URL = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

def carregar_logo():
    logo = None
    for caminho in LOGO_FILE_CANDIDATES:
        if os.path.exists(caminho):
            logo = Image.open(caminho)
            break
    if logo is None:
        try:
            response = requests.get(LOGO_URL)
            logo = Image.open(BytesIO(response.content))
        except Exception:
            st.warning("⚠️ Erro ao carregar logo. O sistema continua funcionando.")
    if logo:
        st.image(logo, width=180)

# Barra superior (gradiente azul → laranja)
st.markdown("""
    <div style="
        background: linear-gradient(90deg, #004AAD, #FF6600);
        padding: 10px 0;
        border-radius: 8px;
        margin-bottom: 12px;">
    </div>
""", unsafe_allow_html=True)

# Exibir logo e título
carregar_logo()
st.markdown(
    "<h1 style='text-align:center; color:black; font-weight:600; margin-top:-10px;'>Dashboard Operacional – CFTV & Alarmes</h1>",
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# ESTILOS (botões, pesquisa e layout)
# ------------------------------------------------------------
st.markdown("""
<style>
/* Botões */
.stButton>button {
    background-color: #f5f5f5;
    color: #333;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 6px 18px;
    transition: 0.3s;
    font-weight: 500;
    margin-right: 8px;
}
.stButton>button:hover {
    transform: scale(1.05);
    background-color: #ff6600;
    color: white;
    border-color: #ff6600;
}

/* Campo de busca */
input[type="text"] {
    border: 2px solid #004AAD !important;
    border-radius: 8px !important;
    box-shadow: 0px 0px 6px rgba(0, 74, 173, 0.3);
}

/* Centralizar conteúdo */
.block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# BARRA DE CONTROLE
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns([1,1,1,3])
with col1:
    if st.button("📷 Câmeras"):
        aba = "cameras"
with col2:
    if st.button("🔔 Alarmes"):
        aba = "alarmes"
with col3:
    if st.button("📊 Geral"):
        aba = "geral"
with col4:
    st.text_input("🔎 Pesquisar local:", placeholder="Digite o nome do local")

# ------------------------------------------------------------
# LEITURA DOS DADOS E AJUSTE AUTOMÁTICO
# ------------------------------------------------------------
try:
    df = pd.read_excel(PLANILHA)
    st.success("✅ Dados carregados com sucesso!")
except Exception as e:
    st.error(f"Erro ao carregar planilha: {e}")
    st.stop()

# Normaliza nomes de colunas
df.columns = (
    df.columns.str.lower()
    .str.replace(" ", "_")
    .str.replace("ç", "c")
    .str.replace("ã", "a")
    .str.replace("á", "a")
    .str.replace("â", "a")
    .str.replace("é", "e")
    .str.replace("ê", "e")
    .str.replace("í", "i")
    .str.replace("ó", "o")
    .str.replace("ô", "o")
    .str.replace("õ", "o")
    .str.replace("ú", "u")
)

# Detecta automaticamente colunas
col_total_cam = next((c for c in df.columns if "total" in c and "camera" in c), None)
col_online_cam = next((c for c in df.columns if "online" in c and "camera" in c), None)
col_total_alarm = next((c for c in df.columns if "total" in c and "alarme" in c), None)
col_online_alarm = next((c for c in df.columns if "online" in c and "alarme" in c), None)

if not all([col_total_cam, col_online_cam, col_total_alarm, col_online_alarm]):
    st.warning("⚠️ Não foi possível identificar todas as colunas. Verifique os nomes na planilha.")
else:
    total_cameras = int(df[col_total_cam].sum())
    cameras_online = int(df[col_online_cam].sum())
    cameras_offline = total_cameras - cameras_online
    total_alarmes = int(df[col_total_alarm].sum())
    alarmes_online = int(df[col_online_alarm].sum())
    alarmes_offline = total_alarmes - alarmes_online

# ------------------------------------------------------------
# FUNÇÃO DE GRÁFICO
# ------------------------------------------------------------
def gerar_grafico(titulo, dados):
    fig = px.bar(
        dados,
        x='Status',
        y='Quantidade',
        color='Status',
        color_discrete_map={'Online':'#00C49F','Offline':'#FF4C61','Manutenção':'#FFA500'},
        text='Quantidade'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        title=titulo,
        xaxis_title=None,
        yaxis_title="Quantidade",
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=14),
        bargap=0.3
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# ABA GERAL
# ------------------------------------------------------------
if 'aba' not in locals():
    aba = "geral"

if aba == "geral":
    st.subheader("📊 Geral (Câmeras + Alarmes)")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Câmeras Online", cameras_online)
    col2.metric("Câmeras Offline", cameras_offline)
    col3.metric("Total de Câmeras", total_cameras)
    col4.metric("Alarmes Online", alarmes_online)
    col5.metric("Alarmes Offline", alarmes_offline)
    col6.metric("Total de Alarmes", total_alarmes)

    st.markdown("### Resumo Geral")
    dados_gerais = pd.DataFrame({
        'Status': ['Online', 'Offline'],
        'Quantidade': [cameras_online + alarmes_online, cameras_offline + alarmes_offline]
    })
    gerar_grafico("Resumo de Operação", dados_gerais)

# ------------------------------------------------------------
# ABA CÂMERAS
# ------------------------------------------------------------
elif aba == "cameras":
    st.subheader("📷 Monitoramento de Câmeras")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total_cameras)
    col2.metric("Online", cameras_online)
    col3.metric("Offline", cameras_offline)
    dados = pd.DataFrame({
        'Status': ['Online', 'Offline'],
        'Quantidade': [cameras_online, cameras_offline]
    })
    gerar_grafico("Gráfico de Câmeras", dados)

# ------------------------------------------------------------
# ABA ALARMES
# ------------------------------------------------------------
elif aba == "alarmes":
    st.subheader("🔔 Monitoramento de Alarmes")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total_alarmes)
    col2.metric("Online", alarmes_online)
    col3.metric("Offline", alarmes_offline)
    dados = pd.DataFrame({
        'Status': ['Online', 'Offline'],
        'Quantidade': [alarmes_online, alarmes_offline]
    })
    gerar_grafico("Gráfico de Alarmes", dados)
