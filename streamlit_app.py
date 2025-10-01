import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt

# ==============================
# Configurações da página
# ==============================
st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro", layout="wide")

# ==============================
# Logo e Título
# ==============================
col1, col2 = st.columns([1, 4])

with col1:
    st.image("logo.png", width=120)  # certifique-se de subir o arquivo logo.png no repositório
with col2:
    st.markdown("<h1 style='color:#FF6600;'>📊 Dashboard de Câmeras</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#1E1E5E;'>Grupo Perímetro</h3>", unsafe_allow_html=True)

st.markdown("---")

# ==============================
# Carregar planilha
# ==============================
try:
    df = pd.read_excel("dados.xlsx")  
except:
    st.error("⚠️ Arquivo 'dados.xlsx' não encontrado. Suba ele no repositório!")
    st.stop()

# Renomear colunas para facilitar
df = df.rename(columns={df.columns[0]: "Local", df.columns[2]: "Qtd", df.columns[3]: "Status"})

# ==============================
# Câmeras Online (somar coluna C)
# ==============================
cameras_online = df.loc[3:41, "Qtd"].sum(skipna=True)  # linhas 4 até 42

# ==============================
# Câmeras Offline e Locais em Manutenção
# ==============================
cameras_offline = 0
locais_manutencao = []

for _, row in df.iterrows():
    local = str(row["Local"])
    status = str(row["Status"]).lower()
    
    if "offline" in status or "off" in status:
        cameras_offline += 1
        locais_manutencao.append(f"{local} (câmeras offline)")
    elif "faltando" in status:
        match = re.search(r"faltando\s*(\d+)", status)
        if match:
            qtd_faltando = int(match.group(1))
            cameras_offline += qtd_faltando
            locais_manutencao.append(f"{local} ({qtd_faltando} câmeras para manutenção)")

# ==============================
# Métricas em cards
# ==============================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Câmeras Online", int(cameras_online))
with col2:
    st.metric("Câmeras Offline", int(cameras_offline))
with col3:
    st.metric("Locais em Manutenção", len(locais_manutencao))

st.markdown("---")

# ==============================
# Gráfico de Pizza
# ==============================
st.subheader("📊 Distribuição Online vs Offline")

fig, ax = plt.subplots()
ax.pie(
    [cameras_online, cameras_offline],
    labels=["Online", "Offline"],
    autopct="%1.1f%%",
    startangle=90,
    colors=["#28a745", "#dc3545"]  # verde online, vermelho offline
)
ax.axis("equal")
st.pyplot(fig)

st.markdown("---")

# ==============================
# Lista de locais em manutenção
# ==============================
st.subheader("📍 Locais que precisam de manutenção")

if locais_manutencao:
    for item in locais_manutencao:
        st.write("- " + item)
else:
    st.success("✅ Nenhum local em manutenção no momento.")
