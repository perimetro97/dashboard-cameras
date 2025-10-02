import streamlit as st
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook

# ---------------- Configuração inicial ----------------
st.set_page_config(page_title="Dashboard de Câmeras", layout="wide")

# ---------------- Leitura do Excel ----------------
try:
    df = pd.read_excel("dados.xlsx", engine="openpyxl", header=0)
except:
    st.error("❌ Não foi possível carregar o arquivo 'dados.xlsx'.")
    st.stop()

# ---------------- Data de atualização (A55 direto) ----------------
try:
    wb = load_workbook("dados.xlsx", data_only=True)
    sheet = wb.active
    raw_date = sheet["A55"].value  # pega diretamente a célula A55

    if raw_date is None:
        ultima_atualizacao = "Não informada"
    else:
        if isinstance(raw_date, (pd.Timestamp, datetime)):
            ultima_atualizacao = raw_date.strftime("%d/%m/%Y")
        else:
            try:
                dt = pd.to_datetime(str(raw_date), dayfirst=True, errors="coerce")
                if pd.isna(dt):
                    ultima_atualizacao = str(raw_date)
                else:
                    ultima_atualizacao = dt.strftime("%d/%m/%Y")
            except:
                ultima_atualizacao = str(raw_date)
except:
    ultima_atualizacao = "Erro ao ler data"

# ---------------- Processamento dos dados ----------------
df = df.fillna("")

# Colunas principais
col_local = "A"
col_valor = "C"
col_status = "D"

# Totais
total_cameras = pd.to_numeric(df[col_valor], errors="coerce").sum()

# Câmeras online (somando valores de C4 até C42)
cameras_online = pd.to_numeric(df.loc[3:41, col_valor], errors="coerce").sum()

# Câmeras offline (contando "Offline" e "Faltando X")
offline_count = 0
faltando_count = 0

for status in df[col_status]:
    if isinstance(status, str):
        if "offline" in status.lower():
            offline_count += 1
        if "faltando" in status.lower():
            try:
                num = int(status.lower().replace("faltando", "").strip())
                faltando_count += num
            except:
                pass

# ---------------- Dashboard ----------------
st.title("📊 Dashboard de Câmeras")

st.markdown(f"📅 **Atualizado em:** {ultima_atualizacao}")

# Cards principais
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Câmeras", total_cameras)
col2.metric("Câmeras Online", cameras_online)
col3.metric("Câmeras Offline", offline_count)
col4.metric("Faltando", faltando_count)

# ---------------- Lista de Manutenção ----------------
st.subheader("🔧 Locais em Manutenção")

manutencao = []

for _, row in df.iterrows():
    local = str(row[col_local]).strip()
    status = str(row[col_status]).lower().strip()
    if any(word in status for word in ["offline", "faltando"]):
        descricao = f"{local} ({status})"
        manutencao.append(descricao)

if manutencao:
    df_manut = pd.DataFrame(manutencao, columns=["Local com problema"])
    st.dataframe(df_manut, use_container_width=True, hide_index=True)
else:
    st.success("✅ Nenhum local precisa de manutenção no momento.")
