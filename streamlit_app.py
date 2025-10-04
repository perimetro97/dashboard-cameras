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
st.markdown(
    """
    <style>
    /* Top gradient (linha azul -> laranja) */
    .top-gradient {
        height:8px;
        background: linear-gradient(90deg, #1E3A8A 0%, #FF6600 100%);
        margin-bottom: 12px;
        border-radius: 4px;
    }

    /* Header */
    .hdr-title { color:#FF6600; font-weight:700; margin:0; }
    .hdr-sub { color:#1E1E5E; margin:0 0 6px 0; }

    /* Cards */
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

    /* Tabela estilizada */
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

    .offline-row { background-color: #ffecec; }  /* vermelho claro */
    .faltando-row { background-color: #fff4e6; } /* laranja claro */

    @keyframes fadeIn {
        from {opacity: 0; transform: translateY(6px);}
        to {opacity: 1; transform: translateY(0);}
    }

    /* footer */
    .footer {
        color: #777;
        font-size: 13px;
        margin-top: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Top gradient + header (logo + title) ----------------
st.markdown("<div class='top-gradient'></div>", unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 5])
with col_logo:
    # tenta exibir logo (se existir no repo)
    try:
        st.image("logo.png", width=110)
    except Exception:
        st.write("")  # não trava se não existir
with col_title:
    st.markdown("<div style='line-height:1.0'>"
                "<h1 class='hdr-title'>📊 Dashboard de Câmeras - Grupo Perímetro</h1>"
                "<div class='hdr-sub'>Painel de status das câmeras</div>"
                "</div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------- Ler planilha (pandas) ----------------
EXCEL_FILE = "dados.xlsx"

try:
    # Lê a planilha com pandas (usar header=0 para colunas se houver)
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl", header=0)
except FileNotFoundError:
    st.error("❌ Arquivo 'dados.xlsx' não encontrado. Suba o arquivo no repositório e redeploy.")
    st.stop()
except Exception as e:
    st.error("❌ Erro ao ler 'dados.xlsx': " + str(e))
    st.stop()

# ---------------- Ler A55 diretamente com openpyxl para garantir ----------------
try:
    wb = load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    raw_date = sheet["A55"].value  # pega a célula A55
    if raw_date is None or (isinstance(raw_date, str) and str(raw_date).strip() == ""):
        ultima_atualizacao = "Não informada"
    else:
        # formatar datas se necessário
        if isinstance(raw_date, datetime):
            ultima_atualizacao = raw_date.strftime("%d/%m/%Y")
        else:
            # tentar converter string para data (dia/mês/ano)
            dt_try = pd.to_datetime(str(raw_date), dayfirst=True, errors="coerce")
            if pd.isna(dt_try):
                ultima_atualizacao = str(raw_date)
            else:
                ultima_atualizacao = dt_try.strftime("%d/%m/%Y")
except Exception:
    ultima_atualizacao = "Erro ao ler data"

# exibir data no topo
st.markdown(f"📅 **Última atualização:** {ultima_atualizacao}")
st.markdown("---")

# ---------------- Detectar colunas (robusto) ----------------
cols = list(df.columns)

def find_col_by_keywords(keywords):
    for c in cols:
        lname = str(c).lower()
        for k in keywords:
            if k in lname:
                return c
    return None

# Preferência: se tiver >=4 colunas, assumimos A=cols[0], C=cols[2], D=cols[3]
if len(cols) >= 4:
    col_local = cols[0]
    col_qtd = cols[2]
    col_status = cols[3]
else:
    # tenter localizar por nome
    col_local = find_col_by_keywords(["local", "nome", "site"]) or cols[0]
    col_qtd = find_col_by_keywords(["qtd", "quant", "cameras", "câmeras", "qtd."]) or (cols[1] if len(cols) > 1 else cols[0])
    col_status = find_col_by_keywords(["status", "estado", "situacao", "situação", "obs", "observação"]) or cols[-1]

# normalizar coluna pra evitar problemas
df[col_local] = df[col_local].astype(str).fillna("").str.strip()
df[col_status] = df[col_status].astype(str).fillna("").str.strip()
# qtd pode ser numérico ou texto; manter original e tentar parse quando necessário

# ---------------- Cálculo: Câmeras Online ----------------
# soma da coluna C (linhas 4..42 => índices 3..41)
try:
    q_series = pd.to_numeric(df[col_qtd].iloc[3:42], errors="coerce").fillna(0)
    cameras_online = int(q_series.sum())
except Exception:
    cameras_online = 0

# ---------------- Construir lista de manutenção ----------------
manut_records = []  # dicts: {'Local', 'Qtde', 'Status'}

def parse_int_safe(x):
    try:
        return int(float(x))
    except Exception:
        return None

for idx, row in df.iterrows():
    local = str(row.get(col_local, "")).strip()
    if not local:
        continue  # pular linhas sem nome
    status_text = str(row.get(col_status, "")).strip().lower()
    qtd_cell = row.get(col_qtd, None)

    # se contiver "faltando"
    if "faltando" in status_text:
        m = re.search(r"faltando\s*[:\-]?\s*(\d+)", status_text)
        if m:
            qtd = parse_int_safe(m.group(1)) or 0
        else:
            # tentar pegar qualquer número na string
            m2 = re.search(r"(\d+)", status_text)
            if m2:
                qtd = parse_int_safe(m2.group(1)) or 0
            else:
                # fallback: usar valor na coluna qtd, se numérico
                qtd = parse_int_safe(qtd_cell) or 0
        manut_records.append({"Local": local, "Qtde": int(qtd), "Status": f"Faltando {int(qtd)}"})
    # se contiver offline / off
    elif "offline" in status_text or status_text == "off":
        # preferir o número em coluna qtd; senão 1
        q = parse_int_safe(qtd_cell)
        if q is None:
            q = 1
        manut_records.append({"Local": local, "Qtde": int(q), "Status": "Offline"})
    else:
        # não considera manutenção
        pass

# somatório de offline total (soma Qtde dos registros)
cameras_offline = sum(r["Qtde"] for r in manut_records)

# ---------------- Cards (métricas) ----------------
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

# ---------------- Tabela de manutenção (ordenada + animada + cores) ----------------
st.subheader("🔧 Locais que precisam de manutenção")

if manut_records:
    df_manut = pd.DataFrame(manut_records)

    # marcar offline e ordenar: Offline primeiro, depois por Qtde desc
    df_manut["is_offline"] = df_manut["Status"].apply(lambda s: 1 if "offline" in str(s).lower() else 0)
    df_manut = df_manut.sort_values(by=["is_offline", "Qtde"], ascending=[False, False]).reset_index(drop=True)

    # construir HTML da tabela com classes para cor de linha
    html = "<table class='styled-table'><thead><tr><th>Local</th><th>Qtde de câmeras</th><th>Status</th></tr></thead><tbody>"
    for _, r in df_manut.iterrows():
        cls = "offline-row" if "offline" in str(r["Status"]).lower() else "faltando-row"
        local = str(r["Local"])
        qtd = int(r["Qtde"])
        status = str(r["Status"])
        html += f"<tr class='{cls}'><td>{local}</td><td>{qtd}</td><td>{status}</td></tr>"
    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)
else:
    st.success("✅ Nenhum local em manutenção no momento.")

st.markdown("---")

# ---------------- Gráfico de barras (Plotly) ----------------
st.subheader("📊 Comparativo: Online vs Offline")

df_chart = pd.DataFrame({
    "Status": ["Online", "Offline"],
    "Quantidade": [int(cameras_online), int(cameras_offline)]
})

fig = px.bar(df_chart, x="Status", y="Quantidade", text="Quantidade",
             color="Status",
             color_discrete_map={"Online": "#27AE60", "Offline": "#DC3545"},
             height=420)

fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y} câmeras", textposition="outside")
fig.update_layout(xaxis_title="", yaxis_title="Quantidade de câmeras",
                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                  transition={"duration": 400})

st.plotly_chart(fig, use_container_width=True)

# ---------------- Footer ----------------
st.markdown("<div class='footer'>© Grupo Perímetro - 2025</div>", unsafe_allow_html=True)
