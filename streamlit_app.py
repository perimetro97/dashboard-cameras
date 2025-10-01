import streamlit as st
import pandas as pd

# Título
st.title("📊 Dashboard de Câmeras")

# Carregar a planilha (aqui vamos trocar depois pelo caminho real do seu arquivo)
# Exemplo: se você subir a planilha para o mesmo repositório, basta colocar o nome dela.
try:
    df = pd.read_excel("dados.xlsx")  
except:
    st.error("⚠️ Arquivo 'dados.xlsx' não encontrado. Suba ele no repositório!")

# Exibir dados brutos
st.subheader("Tabela de Dados")
st.write(df.head())

# Exemplo de resumo
st.subheader("Resumo")
st.metric("Câmeras Online", 10)
st.metric("Câmeras Offline", 2)
st.metric("Manutenções Pendentes", 1)
