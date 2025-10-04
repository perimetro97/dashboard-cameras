# streamlit_app.py
import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro", layout="wide")

# ---------------- CSS (estética + animações) ----------------
st.markdown("""
    <style>
    /* Página */
    body { background-color: #f6f7f9; }

    /* Header */
    .header-title { color: #FF6600; margin: 0; font-weight: 700; }
    .header-sub { color: #1E1E5E; margin: 0; font-weight: 600; }

    /* Cards */
    .metric-card {
        padding: 18px;
        border-radius: 12px;
        background-color: #ffffff;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        text-align: center;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .metric-card:hover {
        transform: translateY(-6px) scale(1.01);
        box-shadow: 0 12px 30px rgba(0,0,0,0.12);
    }
    .metric-title { font-size: 14px; color: #6b6b6b; margin-bottom: 6px; }
    .metric-value { font-size: 28px; font-weight: 700; }

    /* Tabela estilizada */
    .styled-table {
        border-collapse: collapse;
        margin: 14px 0;
        font-size: 15px;
        width: 100%;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    }
    .styled-table thead tr {
        background-color: #1E1E5E;
        color: #ffffff;
        text-align: left;
        font-weight: bold;
    }
    .styled-table th, .styled-table td {
        padding: 12px 14px;
    }
    .styled-table tbody tr {
        border-bottom: 1px solid #eeeeee;
        transition: background-color 0.2s ease, transform 0.15s ease;
    }
    .styled-table tbody tr:hover {
        background-color: #fff7e6;
        transform: translateX(4px);
    }
    .status-offline { color: #dc3545; font-weight: 600; }
    .status-faltando { color: #F39C12; font-weight: 600; }
    .status-online { color: #27AE60; font-weight: 600; }

    /* Pequeno ajuste de responsividade para cards */
    @media (max-width: 640px) {
        .metric-value { font-size: 22px; }
    }
    </style>
""", unsafe_allow_html=True)


# ---------------- Header (logo + título + data) ----------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo.png", width=110)
    except Exception:
        # não trava se o logo não existir
        st.write("")

with col_title:
    st.markdown("<h1 class='header-title'>📊 Dashboard de Câmeras</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='header-sub'>Grupo Perímetro</h3>", unsafe_allow_html=True)

st.markdown("---")


# ---------------- Ler planilha ----------------
try:
    df = pd.read_excel("dados.xlsx", engine="openpyxl")
except Exception as e:
    st.error("⚠️ Arquivo 'dados.xlsx' não encontrado ou erro ao ler: " + str(e))
    st.stop()

# Normalizar: pegar as colunas esperadas (A=Local, C=Qtd, D=Status)
if df.shape[1] >= 4:
    local_col_name = df.columns[0]
    qtd_col_name = df.columns[2]
    status_col_name = df.columns[3]
else:
    st.error("A planilha precisa conter pelo menos 4 colunas (A..D). Verifique o arquivo.")
    st.stop()

df = df.rename(columns={local_col_name: "Local", qtd_col_name: "Qtd", status_col_name: "Status"})

from openpyxl import load_workbook

# ---------------- Data de atualização (pega diretamente A55) ----------------
try:
    wb = load_workbook("dados.xlsx", data_only=True)
    sheet = wb.active
    raw_date = sheet["A55"].value  # pega diretamente a célula A55

    if raw_date is None:
        ultima_atualizacao = "Não informada"
    else:
        # se for data verdadeira
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
except Exception as e:
    ultima_atualizacao = "Erro ao ler data"


# ---------------- Cálculo: Câmeras Online (somar C4:C42) ----------------
try:
    # linhas 4..42 -> índices 3..41
    online_series = pd.to_numeric(df.loc[3:41, "Qtd"], errors="coerce").fillna(0)
    cameras_online = int(online_series.sum())
except Exception:
    cameras_online = 0


# ---------------- Cálculo: Offline e lista de manutenção (Local, Qtde, Status) ----------------
manut_records = []  # lista de dicts: {'Local':..., 'Qtde': int, 'Status': 'Offline'/'Faltando X'}

def parse_int_safe(x):
    try:
        return int(float(x))
    except Exception:
        return None

for _, row in df.iterrows():
    local = str(row.get("Local", "")).strip()
    status = str(row.get("Status", "")).strip().lower()
    qtd_cell = row.get("Qtd", None)

    if not local:
        continue  # pular linhas sem local

    # caso 'faltando X'
    if "faltando" in status:
        m = re.search(r"faltando\s*[:\-]?\s*(\d+)", status)
        if not m:
            # tentar pegar qualquer número na string
            m2 = re.search(r"(\d+)", status)
            if m2:
                qtd_falt = parse_int_safe(m2.group(1))
            else:
                qtd_falt = None
        else:
            qtd_falt = parse_int_safe(m.group(1))

        if qtd_falt is None:
            # fallback: se coluna Qtd tem número, usar
            qtd_falt = parse_int_safe(qtd_cell) or 0

        manut_records.append({"Local": local, "Qtde": int(qtd_falt), "Status": f"Faltando {qtd_falt}"})
    # caso 'offline' ou 'off'
    elif "offline" in status or status == "off":
        # Preferir valor em coluna Qtd (se numérico), senão 1
        qtd_off = parse_int_safe(qtd_cell)
        if qtd_off is None:
            qtd_off = 1
        manut_records.append({"Local": local, "Qtde": int(qtd_off), "Status": "Offline"})
    else:
        # Não marca como manutenção
        pass

# Somar câmeras offline total
cameras_offline = sum(rec["Qtde"] for rec in manut_records)

# ---------------- Resultado: Cards ----------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"<div class='metric-card'><div class='metric-title'>Câmeras Online</div>"
        f"<div class='metric-value' style='color:#27AE60'>{int(cameras_online)}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(
        f"<div class='metric-card'><div class='metric-title'>Câmeras Offline</div>"
        f"<div class='metric-value' style='color:#dc3545'>{int(cameras_offline)}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(
        f"<div class='metric-card'><div class='metric-title'>Locais em Manutenção</div>"
        f"<div class='metric-value' style='color:#FF6600'>{len(manut_records)}</div></div>", unsafe_allow_html=True)

st.markdown("---")


# ---------------- Tabela de manutenção (bonita) ----------------
st.subheader("📍 Locais que precisam de manutenção")

if manut_records:
    df_manut = pd.DataFrame(manut_records)
    # Organizar: ordenar por Qtde desc
    df_manut = df_manut.sort_values(by="Qtde", ascending=False).reset_index(drop=True)

    # Ajustar coluna Status com classes para cor via HTML
    def status_html(s):
        s_low = s.lower()
        if "faltando" in s_low:
            return f"<span class='status-faltando'>{s}</span>"
        elif "offline" in s_low:
            return f"<span class='status-offline'>{s}</span>"
        else:
            return f"<span class='status-online'>{s}</span>"

    # Construir HTML da tabela manualmente para aplicar classes e animação
    html = "<table class='styled-table'><thead><tr><th>Local</th><th>Qtde de câmeras</th><th>Status</th></tr></thead><tbody>"
    for _, r in df_manut.iterrows():
        local = str(r["Local"])
        qtd = int(r["Qtde"])
        stat = str(r["Status"])
        html += f"<tr><td>{local}</td><td>{qtd}</td><td>{status_html(stat)}</td></tr>"
    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")


st.markdown("---")


# ---------------- Gráfico de barras (final) ----------------
st.subheader("📊 Comparativo Online vs Offline")

df_chart = pd.DataFrame({
    "Status": ["Online", "Offline"],
    "Quantidade": [int(cameras_online), int(cameras_offline)]
})

fig = px.bar(
    df_chart,
    x="Status",
    y="Quantidade",
    color="Status",
    color_discrete_map={"Online": "#27AE60", "Offline": "#dc3545"},
    text="Quantidade",
    height=380
)
fig.update_traces(hovertemplate="<b>%{x}</b>: %{y} câmeras", textposition="outside", marker_line_width=0)
fig.update_layout(
    xaxis_title="",
    yaxis_title="Câmeras",
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    transition={"duration": 400}
)

st.plotly_chart(fig, use_container_width=True)



atualização bug data:

linas 109 a 129


# ---------------- Data de atualização (A55 -> índice 54, coluna 0) ----------------
try:
    raw_date = df.iloc[54, 0]  # A55
    if pd.isna(raw_date):
        ultima_atualizacao = "Não informada"
    else:
        # tratar se for datetime ou string
        try:
            if isinstance(raw_date, (pd.Timestamp, datetime)):
                ultima_atualizacao = raw_date.strftime("%d/%m/%Y")
            else:
                # tenta converter string para datetime
                dt = pd.to_datetime(str(raw_date), dayfirst=True, errors="coerce")
                if pd.isna(dt):
                    ultima_atualizacao = str(raw_date)
                else:
                    ultima_atualizacao = dt.strftime("%d/%m/%Y")
        except Exception:
            ultima_atualizacao = str(raw_date)
except Exception:
    ultima_atualizacao = "Não informada"
