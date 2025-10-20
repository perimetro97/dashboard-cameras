# ============================================================
# Dashboard Operacional – Grupo Perímetro (v5.0)
# CFTV & Alarmes • Visual Pro • PDF desativado temporariamente
# ============================================================

import os
import requests
from io import BytesIO
from datetime import datetime
import pandas as pd
import numpy as np
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
        padding: 12px 0;
        border-radius: 8px;
        margin-bottom: 10px;">
    </div>
""", unsafe_allow_html=True)

# Exibir logo e título
carregar_logo()
st.markdown(
    "<h1 style='text-align:center; color:black; font-weight:600; margin-top:-5px;'>Dashboard Operacional – CFTV & Alarmes</h1>",
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# ESTILOS (botões e campo de busca)
# ------------------------------------------------------------
st.markdown("""
<style>
/* Botões */
.stButton>button {
    background-color: #f2f2f2;
    color: #333;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 6px 18px;
    transition: 0.3s;
    font-weight: 500;
    margin-right: 6px;
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
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# CONTROLE DE ABAS
# ------------------------------------------------------------
col1, col2, col3 = st.columns([1,1,1])
with col1:
    if st.button("📷 Câmeras"):
        aba = "cameras"
with col2:
    if st.button("🔔 Alarmes"):
        aba = "alarmes"
with col3:
    if st.button("📊 Geral"):
        aba = "geral"

# ------------------------------------------------------------
# LEITURA DOS DADOS
# ------------------------------------------------------------
try:
    df = pd.read_excel(PLANILHA)
    st.success("✅ Dados carregados com sucesso!")
except Exception as e:
    st.error(f"Erro ao carregar planilha: {e}")
    st.stop()

# ------------------------------------------------------------
# FUNÇÕES AUXILIARES
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

    total_cameras = int(df['Total_Cameras'].sum()) if 'Total_Cameras' in df.columns else 0
    cameras_online = int(df['Online_Cameras'].sum()) if 'Online_Cameras' in df.columns else 0
    cameras_offline = total_cameras - cameras_online
    total_alarmes = int(df['Total_Alarmes'].sum()) if 'Total_Alarmes' in df.columns else 0
    alarmes_online = int(df['Online_Alarmes'].sum()) if 'Online_Alarmes' in df.columns else 0
    alarmes_offline = total_alarmes - alarmes_online

    col1, col2, col3 = st.columns(3)
    col1.metric("Câmeras Online", cameras_online)
    col2.metric("Alarmes Online", alarmes_online)
    col3.metric("Total de Câmeras", total_cameras)

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
    total = int(df['Total_Cameras'].sum()) if 'Total_Cameras' in df.columns else 0
    online = int(df['Online_Cameras'].sum()) if 'Online_Cameras' in df.columns else 0
    offline = total - online

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total)
    col2.metric("Online", online)
    col3.metric("Offline", offline)

    dados = pd.DataFrame({
        'Status': ['Online', 'Offline'],
        'Quantidade': [online, offline]
    })
    gerar_grafico("Gráfico de Câmeras", dados)

# ------------------------------------------------------------
# ABA ALARMES
# ------------------------------------------------------------
elif aba == "alarmes":
    st.subheader("🔔 Monitoramento de Alarmes")
    total = int(df['Total_Alarmes'].sum()) if 'Total_Alarmes' in df.columns else 0
    online = int(df['Online_Alarmes'].sum()) if 'Online_Alarmes' in df.columns else 0
    offline = total - online

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total)
    col2.metric("Online", online)
    col3.metric("Offline", offline)

    dados = pd.DataFrame({
        'Status': ['Online', 'Offline'],
        'Quantidade': [online, offline]
    })
    gerar_grafico("Gráfico de Alarmes", dados)
