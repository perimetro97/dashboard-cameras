# ===============================================
# DASHBOARD CFTV & ALARMES - GRUPO PERÍMETRO
# ===============================================
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from io import BytesIO
from PIL import Image

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard Operacional - CFTV & Alarmes",
    layout="wide",
    page_icon="📊"
)

# ========================
# ESTILO VISUAL (Cores)
# ========================
st.markdown("""
    <style>
        body {
            background-color: #f2f2f2;
            color: #202020;
        }
        .title-text {
            font-size: 30px;
            font-weight: bold;
            color: #FF6600;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }
        .sub-text {
            font-size: 16px;
            color: #555;
        }
        .logo-card img {
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .search-bar input {
            border-radius: 10px;
            padding: 6px;
            border: 1px solid #ccc;
        }
    </style>
""", unsafe_allow_html=True)

# ========================
# LOGO FIXA
# ========================
try:
    st.image(
        "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo_perimetro.png",
        use_container_width=False,
        width=120
    )
except Exception as e:
    st.warning("⚠️ Logo não encontrada, mas o sistema continua funcionando.")

# ========================
# TÍTULO E DATA
# ========================
st.markdown("<div class='title-text'>Dashboard Operacional – CFTV & Alarmes</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-text'>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)

# ========================
# CAMPOS ESTRUTURAIS
# ========================
st.markdown("---")
aba = st.radio("Selecione a aba:", ["📹 Câmeras", "🚨 Alarmes", "📊 Geral"], horizontal=True)

# ========================
# LEITURA DA PLANILHA
# ========================
@st.cache_data
def load_data():
    path = "dados.xlsx"
    try:
        df = pd.read_excel(path)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Nenhum dado foi encontrado na planilha.")
else:
    st.success("✅ Dados carregados com sucesso!")

# ========================
# PLACEHOLDER DE CONTEÚDO
# ========================
if aba == "📹 Câmeras":
    st.subheader("📹 Monitoramento de Câmeras")
    st.info("Em breve: cards e gráficos de câmeras com status OK, manutenção e offline.")
elif aba == "🚨 Alarmes":
    st.subheader("🚨 Monitoramento de Alarmes")
    st.info("Em breve: cards e gráficos de alarmes com status OK, manutenção e offline.")
elif aba == "📊 Geral":
    st.subheader("📊 Resumo Geral")
    st.info("Em breve: painel consolidado com totais, porcentagens e gráficos globais.")
