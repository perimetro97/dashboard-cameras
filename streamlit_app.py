# streamlit_app.py
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from openpyxl import load_workbook

# ---------------- Configuração da página ----------------
st.set_page_config(page_title="Dashboard de Câmeras - Grupo Perímetro",
                   page_icon="📹",
                   layout="wide")

# ---------------- CSS ----------------
st.markdown(
    """
    <style>
    /* Top gradient */
    .top-gradient {
        height:8px;
        background: linear-gradient(90deg, #1E3A8A 0%, #FF6600 100%);
        margin-bottom: 12px;
        border-radius: 4px;
    }

    .hdr-title { color:#FF6600; font-weight:700; margin:0; }
    .hdr-sub { color:#1E1E5E; margin:0 0 6px 0; }

    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 14px 40px rgba(0,0,0,0.10);
    }
    .metric-title { color:#6b6b6b; font-size:14px; margin-bottom:6px; }
    .metric-value { font-size:28px; font-weight:700; }

    /* Tabela */
    .styled-table {
        border-collapse: collapse;
        width: 100%;
        border-radius: 10px;
        overflow: hidden;
        font-size: 15px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        animation: fadeIn 0.9s ease both;
    }
    .styled-table thead tr {
        background-color: #1E3A8A;
        color: #fff;
        text-align: left;
        font-weight: 700;
    }
    .styled-table th, .styled-table td {
        padding: 10px 14px;
    }
    .styled-table tbody tr {
        border-bottom: 1px solid #f0f0f0;
        transition: background-color 0.18s ease, transform 0.12s ease;
    }
    .styled-table tbody tr:hover {
        background-color: #f9f9f9;
        transform: translateX(4px);
    }

    /* Cores de fundo */
    .offline-row { background-color: #ffecec; }  /* vermelho claro */
    .faltando-row { background-color: #fff7e6; } /* laranja bem clara */

    /* Barra de status */
    .status-label {
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        color: #fff;
        display: inline-block;
    }
    .status-offline { background-color: #DC3545; } /* vermelho */
    .status-faltando { background-color: #FFC107; color:#000; } /* amarelo */

    @keyframes fadeIn {
        from {opacity: 0; transform: translateY(6px);}
        to {opacity: 1; transform: translateY(0);}
    }

    .footer {
        color: #777;
        font-size: 13px;
        margin-top: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Top gradient + header ----------------
st.markdown("<div class='top-gradient'></div>", unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo.png", width=110)
    except Exception:
        st.write("")
with col_title:
    st.markdown("<div style='line-height:1.0'>"
                "<h1 class='hdr-title'>📊 Dashboard de Câmeras - Grupo Perímetro</h1>"
                "<div class='hdr-sub'>Painel de status das câmeras</div>"
                "</div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------- Ler planilha ----------------
EXCEL_FILE = "dados.xlsx"

try:
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl", header=0)
except FileNotFoundError:
    st.error("❌ Arquivo 'dados.xlsx' não encontrado.")
    st.stop()

# pegar data de A55
try:
    wb = load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    raw_date = sheet["A55"].value
    if isinstance(raw_date, datetime):
        ultima_atualizacao = raw_date.strftime("%d/%m/%Y")
    elif raw_date:
        dt_try = pd.to_datetime(str(raw_date), dayfirst=True, errors="coerce")
        ultima_atualizacao = dt_try.strftime("%d/%m/%Y") if not pd.isna(dt_try) else str(raw_date)
    else:
        ultima_atualizacao = "Não informada"
except Exception:
    ultima_atualizacao = "Erro ao ler data"

st.markdown(f"📅 **Última atualização:** {ultima_atualizacao}")
st.markdown("---")

# ---------------- Detectar colunas ----------------
cols = list(df.columns)

def find_col_by_keywords(keywords):
    for c in cols:
        if any(k in str(c).lower() for k in keywords):
            return c
    return None

col_local = find_col_by_keywords(["local", "site"]) or cols[0]
col_qtd = find_col_by_keywords(["qtd", "quant"]) or (cols[1] if len(cols) > 1 else cols[0])
col_status = find_col_by_keywords(["status", "obs", "situação"]) or cols[-1]

# ---------------- Cálculos ----------------
try:
    q_series = pd.to_numeric(df[col_qtd].iloc[3:42], errors="coerce").fillna(0)
    cameras_online = int(q_series.sum())
except Exception:
    cameras_online = 0

manut_records = []
for _, row in df.iterrows():
    local = str(row.get(col_local, "")).strip()
    status_text = str(row.get(col_status, "")).strip().lower()
    if not local: continue

    if "faltando" in status_text:
        manut_records.append({"Local": local, "Status": f"Faltando"})
    elif "offline" in status_text or status_text == "off":
        manut_records.append({"Local": local, "Status": "Offline"})

cameras_offline = len([r for r in manut_records if r["Status"] == "Offline"])

# ---------------- Cards ----------------
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Online</div>"
                f"<div class='metric-value' style='color:#27AE60'>{cameras_online}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Offline</div>"
                f"<div class='metric-value' style='color:#DC3545'>{cameras_offline}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Locais em Manutenção</div>"
                f"<div class='metric-value' style='color:#FF6600'>{len(manut_records)}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------- Tabela de manutenção ----------------
st.subheader("🔧 Locais que precisam de manutenção")

if manut_records:
    html = "<table class='styled-table'><thead><tr><th>Local</th><th>Status</th></tr></thead><tbody>"
    for r in manut_records:
        status = r["Status"]
        if status.lower() == "offline":
            cls = "offline-row"
            status_html = "<span class='status-label status-offline'>Offline</span>"
        else:
            cls = "faltando-row"
            status_html = "<span class='status-label status-faltando'>Faltando</span>"
        html += f"<tr class='{cls}'><td>{r['Local']}</td><td>{status_html}</td></tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")

st.markdown("---")

# ---------------- Gráfico ----------------
st.subheader("📊 Comparativo: Online vs Offline")

df_chart = pd.DataFrame({
    "Status": ["Online", "Offline"],
    "Quantidade": [int(cameras_online), int(cameras_offline)]
})

fig = px.bar(df_chart, x="Status", y="Quantidade", text="Quantidade",
             color="Status",
             color_discrete_map={"Online": "#27AE60", "Offline": "#DC3545"},
             height=420)

fig.update_traces(textposition="outside")
fig.update_layout(xaxis_title="", yaxis_title="Quantidade de câmeras",
                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

# ---------------- Footer ----------------
st.markdown("<div class='footer'>© Grupo Perímetro - 2025</div>", unsafe_allow_html=True)
