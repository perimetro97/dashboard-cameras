import streamlit as st
import pandas as pd
import re
import plotly.express as px

# ==============================
# Configurações da página
# ==============================
st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro", layout="wide")

# CSS customizado (animação nos cards e estética)
st.markdown("""
    <style>
    body {
        background-color: #f7f7f7;
    }
    .metric-card {
        padding: 20px;
        border-radius: 15px;
        background-color: white;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        transition: all 0.3s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 4px 4px 16px rgba(0,0,0,0.2);
    }
    .header-title {
        color: #FF6600;
    }
    .header-sub {
        color: #1E1E5E;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================
# Logo e Título
# ==============================
col1, col2 = st.columns([1, 4])

with col1:
    st.image("logo.png", width=120)
with col2:
    st.markdown("<h1 class='header-title'>📊 Dashboard de Câmeras</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='header-sub'>Grupo Perímetro</h3>", unsafe_allow_html=True)

st.markdown("---")

# ==============================
# Carregar planilha
# ==============================
try:
    df = pd.read_excel("dados.xlsx")  
except:
    st.error("⚠️ Arquivo 'dados.xlsx' não encontrado. Suba ele no repositório!")
    st.stop()

# Renomear colunas
df = df.rename(columns={df.columns[0]: "Local", df.columns[2]: "Qtd", df.columns[3]: "Status"})

# Data da última atualização (A55)
ultima_atualizacao = str(df.iloc[54, 0]) if len(df) >= 55 else "Não informada"
st.markdown(f"📅 **Atualizado em:** {ultima_atualizacao}")

st.markdown("---")

# ==============================
# Cálculos
# ==============================
cameras_online = df.loc[3:41, "Qtd"].sum(skipna=True)

cameras_offline = 0
locais_manutencao = []

for _, row in df.iterrows():
    local = str(row["Local"])
    status = str(row["Status"]).lower()
    
    if "offline" in status or "off" in status:
        cameras_offline += 1
        locais_manutencao.append(f"{local} (1 câmera offline)")
    elif "faltando" in status:
        match = re.search(r"faltando\s*(\d+)", status)
        if match:
            qtd_faltando = int(match.group(1))
            cameras_offline += qtd_faltando
            locais_manutencao.append(f"{local} ({qtd_faltando} câmeras para manutenção)")

# ==============================
# Cards estilizados
# ==============================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='metric-card'><h2>Online</h2><h1 style='color:#28a745;'>{int(cameras_online)}</h1></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h2>Offline</h2><h1 style='color:#dc3545;'>{int(cameras_offline)}</h1></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><h2>Manutenção</h2><h1 style='color:#FF6600;'>{len(locais_manutencao)}</h1></div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================
# Lista de locais em manutenção
# ==============================
st.subheader("📍 Locais que precisam de manutenção")

if locais_manutencao:
    for item in locais_manutencao:
        st.markdown(f"- <b style='color:#1E1E5E;'>{item}</b>", unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")

st.markdown("---")

# ==============================
# Gráfico de Barras (com animação de hover)
# ==============================
st.subheader("📊 Comparativo Online vs Offline")

df_grafico = pd.DataFrame({
    "Status": ["Online", "Offline"],
    "Quantidade": [cameras_online, cameras_offline]
})

fig = px.bar(
    df_grafico,
    x="Status",
    y="Quantidade",
    color="Status",
    color_discrete_map={"Online": "#28a745", "Offline": "#dc3545"},
    text="Quantidade"
)

fig.update_traces(
    hovertemplate="<b>%{x}</b>: %{y} câmeras",
    textposition="outside"
)
fig.update_layout(
    xaxis_title="",
    yaxis_title="Câmeras",
    plot_bgcolor="#f7f7f7",
    paper_bgcolor="#f7f7f7"
)

st.plotly_chart(fig, use_container_width=True)
