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

# ---------------- CSS (cores, animação, tabela) ----------------
st.markdown("""
    <style>
    .top-gradient { height:8px; background: linear-gradient(90deg, #1E3A8A 0%, #FF0000 100%); margin-bottom: 12px; border-radius: 4px; }
    .hdr-title { color:#FF6600; font-weight:700; margin:0; }
    .hdr-sub { color:#1E1E5E; margin:0 0 6px 0; }
    .metric-card { background: #ffffff; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 6px 20px rgba(0,0,0,0.06); transition: transform 0.25s ease, box-shadow 0.25s ease; }
    .metric-card:hover { transform: translateY(-6px); box-shadow: 0 14px 40px rgba(0,0,0,0.10); }
    .metric-title { color:#6b6b6b; font-size:14px; margin-bottom:6px; }
    .metric-value { font-size:28px; font-weight:700; }
    .styled-table { border-collapse: collapse; width: 100%; border-radius: 10px; overflow: hidden; font-size: 15px; box-shadow: 0 6px 18px rgba(0,0,0,0.06); animation: fadeIn 0.9s ease both; }
    .styled-table thead tr { background-color: #1E3A8A; color: #fff; text-align: left; font-weight: 700; }
    .styled-table th, .styled-table td { padding: 10px 14px; }
    .styled-table tbody tr { border-bottom: 1px solid #f0f0f0; transition: background-color 0.18s ease, transform 0.12s ease; }
    .styled-table tbody tr:hover { background-color: #faf3eb; transform: translateX(4px); }
    .offline-row { background-color: #ffe9d6; }  /* laranja claro */
    .faltando-row { background-color: #fff7e6; } /* amarelo bem suave */
    .status-label { font-weight: 600; padding: 4px 10px; border-radius: 6px; color: #fff; display: inline-block; }
    .status-offline { background-color: #FF0000; } /* vermelho para offline */
    .status-faltando { background-color: #FFC107; color:#000; } /* amarelo */
    @keyframes fadeIn { from {opacity: 0; transform: translateY(6px);} to {opacity: 1; transform: translateY(0);} }
    .footer { color: #777; font-size: 13px; margin-top: 18px; }
    </style>
""", unsafe_allow_html=True)

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
                "<h1 class='hdr-title'>Dashboard de Câmeras - Grupo Perímetro</h1>"
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
except Exception as e:
    st.error(f"❌ Erro ao ler 'dados.xlsx': {e}")
    st.stop()

# ---------------- Ler A55 diretamente (garantia) ----------------
try:
    wb = load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    raw_date = sheet["A55"].value
    if raw_date is None or (isinstance(raw_date, str) and str(raw_date).strip() == ""):
        ultima_atualizacao = "Não informada"
    else:
        if isinstance(raw_date, datetime):
            ultima_atualizacao = raw_date.strftime("%d/%m/%Y")
        else:
            dt_try = pd.to_datetime(str(raw_date), dayfirst=True, errors="coerce")
            ultima_atualizacao = dt_try.strftime("%d/%m/%Y") if not pd.isna(dt_try) else str(raw_date)
except Exception:
    ultima_atualizacao = "Erro ao ler data"

st.markdown(f"📅 **Última atualização:** {ultima_atualizacao}")
st.markdown("---")

# ---------------- Detectar colunas ----------------
cols = list(df.columns)
col_local, col_qtd, col_status = cols[0], cols[2], cols[3]
df[col_local] = df[col_local].astype(str).fillna("").str.strip()
df[col_status] = df[col_status].astype(str).fillna("").str.strip()

# ---------------- Helpers ----------------
def parse_int_safe(x):
    try:
        if pd.isna(x):
            return None
        if isinstance(x, (int, float)):
            return int(x)
        m = re.search(r"(\d+)", str(x))
        if m:
            return int(m.group(1))
    except:
        return None
    return None

# ---------------- Somatório de câmeras online ----------------
try:
    series_online = pd.to_numeric(df[col_qtd].iloc[3:42], errors="coerce").fillna(0)
    cameras_online = int(series_online.sum())
except Exception:
    cameras_online = 0

# ---------------- Lista de manutenção ----------------
manut_records = []
for _, row in df.iterrows():
    local = str(row.get(col_local, "")).strip()
    if not local:
        continue
    status_text = str(row.get(col_status, "")).strip().lower()
    qtd_cell = row.get(col_qtd, None)

    if "faltando" in status_text:
        qtd = parse_int_safe(status_text) or parse_int_safe(qtd_cell) or 0
        manut_records.append({"Local": local, "Qtde": qtd, "Status": f"Faltando {qtd}", "Tipo": "faltando"})
    elif "offline" in status_text or status_text == "off":
        manut_records.append({"Local": local, "Qtde": 1, "Status": "Offline", "Tipo": "offline"})

cameras_offline = sum(r["Qtde"] for r in manut_records)

# ---------------- Cards ----------------
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Online</div>"
                f"<div class='metric-value' style='color:#27AE60'>{cameras_online}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Câmeras Offline</div>"
                f"<div class='metric-value' style='color:#FF0000'>{cameras_offline}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Locais em Manutenção</div>"
                f"<div class='metric-value' style='color:#FF6600'>{len(manut_records)}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------- Tabela de manutenção ----------------
st.subheader("🔧 Locais que precisam de manutenção")
if manut_records:
    df_manut = pd.DataFrame(manut_records)
    df_manut["is_offline"] = df_manut["Tipo"].apply(lambda t: 1 if t == "offline" else 0)
    df_manut = df_manut.sort_values(by=["is_offline", "Qtde"], ascending=[False, False]).reset_index(drop=True)

    html = "<table class='styled-table'><thead><tr><th>Local</th><th>Status</th></tr></thead><tbody>"
    for _, r in df_manut.iterrows():
        cls = "offline-row" if r["Tipo"] == "offline" else "faltando-row"
        if r["Tipo"] == "offline":
            status_html = f"<span class='status-label status-offline'>{r['Status']}</span>"
        else:
            status_html = f"<span class='status-label status-faltando'>{r['Status']}</span>"
        html += f"<tr class='{cls}'><td>{r['Local']}</td><td>{status_html}</td></tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")

st.markdown("---")

# ---------------- Gráfico ----------------
st.subheader("Comparativo: Online vs Offline")
df_chart = pd.DataFrame({"Status": ["Online", "Offline"], "Quantidade": [int(cameras_online), int(cameras_offline)]})
fig = px.bar(df_chart, x="Status", y="Quantidade", text="Quantidade",
             color="Status", color_discrete_map={"Online": "#27AE60", "Offline": "#FF0000"}, height=420)
fig.update_traces(textposition="outside", hovertemplate="<b>%{x}</b><br>%{y} câmeras")
fig.update_layout(xaxis_title="", yaxis_title="Quantidade de câmeras", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", transition={"duration": 400})
st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='footer'>© Grupo Perímetro - 2025</div>", unsafe_allow_html=True)
