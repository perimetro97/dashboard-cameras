import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- CONFIGURAÇÕES INICIAIS ----------------
st.set_page_config(page_title="Dashboard de Câmeras",
                   page_icon="📹",
                   layout="wide")

# ---------------- LINHAS COLORIDAS (TOPO) ----------------
st.markdown(
    """
    <div style='height:8px; background:linear-gradient(to right, #1E3A8A, #FF6600); margin-bottom:15px;'></div>
    """,
    unsafe_allow_html=True
)

# ---------------- CABEÇALHO ----------------
col1, col2 = st.columns([1,4])
with col1:
    st.image("logo.png", width=120)  # precisa estar no repositório
with col2:
    st.markdown("<h1 style='color:#FF6600;'>📊 Dashboard de Câmeras - Grupo Perímetro</h1>", unsafe_allow_html=True)

# ---------------- LEITURA DA PLANILHA ----------------
try:
    df = pd.read_excel("dados.xlsx")

    col_local = "A"  # nomes dos locais
    col_cameras = "C"  # quantidade de câmeras
    col_status = "D"  # status (offline, faltando X, etc.)

    # Data de atualização (célula A55 → linha 54, coluna 0)
    try:
        df_data = pd.read_excel("dados.xlsx", header=None)
        ultima_atualizacao = str(df_data.iloc[54, 0])
    except:
        ultima_atualizacao = "Não informada"

    # ---------------- MOSTRAR DATA ----------------
    st.markdown(
        f"<p style='font-size:18px; color:gray;'>📅 Última atualização: <b>{ultima_atualizacao}</b></p>",
        unsafe_allow_html=True
    )

    # ---------------- MÉTRICAS ----------------
    total_online = df[col_cameras][3:42].sum()  # soma C4 até C42
    total_offline = 0
    manutencao = []

    for _, row in df.iterrows():
        local = str(row[col_local]).strip()
        status = str(row[col_status]).lower().strip()

        if "offline" in status:
            total_offline += 1
            manutencao.append({"Local": local, "Problema": "Offline", "Qtd Faltando": 0, "Cor": "red"})
        elif "faltando" in status:
            try:
                num = int(status.replace("faltando", "").strip())
            except:
                num = 0
            total_offline += num
            manutencao.append({"Local": local, "Problema": f"Faltando {num}", "Qtd Faltando": num, "Cor": "orange"})

    total_manut = len(manutencao)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("📡 Câmeras Online", total_online)
    with c2:
        st.metric("❌ Câmeras Offline", total_offline)
    with c3:
        st.metric("🔧 Locais em Manutenção", total_manut)

    # ---------------- LISTA DE MANUTENÇÃO ----------------
    st.subheader("🔧 Locais em Manutenção")

    if manutencao:
        df_manut = pd.DataFrame(manutencao)

        # Reordenação: Offline primeiro, depois por mais câmeras faltando
        df_manut["Offline"] = df_manut["Problema"].apply(lambda x: 1 if "offline" in x.lower() else 0)
        df_manut = df_manut.sort_values(by=["Offline", "Qtd Faltando"], ascending=[False, False])

        # CSS + cores + animação
        st.markdown(
            """
            <style>
            @keyframes fadeIn {
                from {opacity: 0;}
                to {opacity: 1;}
            }
            .styled-table {
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 16px;
                width: 100%;
                animation: fadeIn 1s ease-in;
            }
            .styled-table th, .styled-table td {
                padding: 10px 15px;
                text-align: left;
            }
            .styled-table th {
                background-color: #1E3A8A;
                color: white;
            }
            .offline-row {
                background-color: #ffcccc;
            }
            .faltando-row {
                background-color: #ffe0b3;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Monta tabela HTML personalizada
        tabela_html = "<table class='styled-table'>"
        tabela_html += "<tr><th>Local</th><th>Problema</th></tr>"
        for _, row in df_manut.iterrows():
            classe = "offline-row" if row["Cor"] == "red" else "faltando-row"
            tabela_html += f"<tr class='{classe}'><td>{row['Local']}</td><td>{row['Problema']}</td></tr>"
        tabela_html += "</table>"

        st.markdown(tabela_html, unsafe_allow_html=True)

    else:
        st.success("✅ Nenhum local precisa de manutenção no momento.")

    # ---------------- GRÁFICO ----------------
    st.subheader("📊 Distribuição das Câmeras")

    fig, ax = plt.subplots()
    ax.bar(["Online", "Offline"], [total_online, total_offline], color=["#28a745", "#dc3545"])
    ax.set_ylabel("Quantidade de Câmeras")
    ax.set_title("Status Geral das Câmeras")

    st.pyplot(fig)

except FileNotFoundError:
    st.error("❌ Arquivo 'dados.xlsx' não encontrado. Suba ele no repositório junto com o app.")
