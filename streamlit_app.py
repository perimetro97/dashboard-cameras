# =========================================================
# Dashboard Operacional – Grupo Perímetro (v5.6.2 → v5.7)
# CFTV & Alarmes • Visual Pro •
# =========================================================
import os, requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
import pytz  # <-- adicionado para horário de Brasília

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Dashboard Operacional – CFTV & Alarmes",
                   page_icon="📹", layout="wide")

# === NOVO: leitura direta do Excel no Google Drive (Opção B) ===
DRIVE_FILE_ID = "1LofqwV9_fXfKAGbqjk2LEfgSQmJvUiuA"
DRIVE_URL = f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}"

PLANILHA = "dados.xlsx"              # mantido (compatibilidade)
ROOT_PATH = Path(__file__).parent
PLANILHA_PATH = ROOT_PATH / PLANILHA # mantido

# Logo somente do repositório / arquivo (sem Base64)
LOGO_FILE_CANDIDATES = [
    "logo.png", "./logo.png", "/app/logo.png", "/mount/src/dashboard-cameras/logo.png",
    "logo_perimetro.png", "./logo_perimetro.png"
]
LOGO_URL_RAW = "https://raw.githubusercontent.com/perimetro97/dashboard-cameras/main/logo.png"

# Ícones na raiz do repositório (apenas para os títulos de seção)
ICON_CAMERA     = "camera.png"
ICON_ALARME     = "alarme.png"
ICON_ENGRENAGEM = "engrenagem.png"
ICON_RELATORIO  = "relatorio.png"

# Paleta (AZUL AJUSTADO PARA O TOM DA LOGO)
CLR_BG     = "#F5F6FA"
CLR_PANEL  = "#FFFFFF"
CLR_TEXT   = "#111827"  # preto suave
CLR_SUB    = "#6B7280"
CLR_BORDER = "#E5E7EB"
CLR_BLUE   = "#1B1F3B"   # Azul exato da logo (antes #0B66C3)
CLR_ORANGE = "#F37021"   # Laranja institucional
CLR_GREEN  = "#16A34A"   # OK
CLR_RED    = "#E11D48"   # Offline

# ------------------ CSS ------------------
st.markdown(f"""
<style>
  .stApp {{
    background:{CLR_BG};
    color:{CLR_TEXT};
    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif;
    animation: fadein .25s ease;
  }}
  @keyframes fadein {{ from {{ opacity:0 }} to {{ opacity:1 }} }}

  /* Barra superior com gradiente azul->laranja (modelo 18) */
  .top-wrap {{
    background: linear-gradient(90deg, {CLR_BLUE} 0%, {CLR_ORANGE} 100%);
    border-radius: 18px;
    padding: 14px 16px;
    box-shadow: 0 10px 22px rgba(0,0,0,.10);
    color: #fff;
  }}
  .logo-card {{
    background: rgba(255,255,255,.20);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 12px;
    padding: 8px;
    backdrop-filter: blur(3px);
  }}
  /* Título preto, sem sombra */
  .title {{
    font-size: 28px; font-weight: 900; letter-spacing:.2px;
    color:{CLR_TEXT};
    margin-bottom: 2px;
  }}
  .subtitle {{ font-size: 12px; color: rgba(17,24,39,.75); }}

  /* Botões das abas – mais próximos e com hover */
  .btn-row .stButton>button {{
    background: #fff;
    color: {CLR_BLUE};
    border: 1px solid {CLR_BORDER};
    border-radius: 12px;
    padding: 10px 14px;
    font-weight: 700;
    box-shadow: 0 6px 14px rgba(0,0,0,.06);
    transition: transform .08s ease, box-shadow .15s ease, background .15s ease;
    margin-right: 6px;
  }}
  .btn-row .stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 10px 22px rgba(0,0,0,.12); }}
  .btn-active {{ background: {CLR_BLUE} !important; color: #fff !important; }}

  /* Cards */
  .card {{
    background:{CLR_PANEL}; border:1px solid {CLR_BORDER}; border-radius:16px; padding:16px;
    box-shadow: 0 10px 24px rgba(2,12,27,.06); margin-bottom: 12px;
    transition: transform .08s ease, box-shadow .15s ease;
  }}
  .card:hover {{ transform: translateY(-1px); box-shadow:0 14px 30px rgba(2,12,27,.12); }}
  .metric {{ font-size:30px; font-weight:900; margin-top:2px }}
  .metric-sub {{ font-size:12px; color:{CLR_SUB} }}

  /* Chips */
  .chip {{ font-weight:800; padding:4px 10px; border-radius:999px; font-size:12px; }}
  .ok   {{ color:{CLR_GREEN};  background:rgba(22,163,74,.12) }}
  .warn {{ color:{CLR_ORANGE}; background:rgba(243,112,33,.12) }}
  .off  {{ color:{CLR_RED};    background:rgba(225,29,72,.12) }}

  /* Cartões de locais */
  .local-card {{
    background:#FAFBFF; border:1px solid {CLR_BORDER}; border-left:6px solid {CLR_ORANGE};
    border-radius:14px; padding:12px 14px; margin-bottom:10px;
  }}
  .local-card.offline {{ border-left-color:{CLR_RED}; }}
  .local-title {{ font-weight:900; font-size:16px; }}
  .local-info  {{ color:{CLR_SUB}; font-size:12px; margin-top:2px; }}

  /* Destaque discreto no campo de busca */
  .search-box .stTextInput>div>div>input {{
    border:1px solid {CLR_BORDER};
    box-shadow: 0 2px 8px rgba(27,31,59,.07);
  }}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGO (repositório/arquivo) ------------------
def load_logo_bytes() -> bytes | None:
    for p in LOGO_FILE_CANDIDATES:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f.read()
            except Exception:
                pass
    try:
        r = requests.get(LOGO_URL_RAW, timeout=6)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None

# ------------------ HELPERS ------------------
def _to_int(x):
    if pd.isna(x): return 0
    s = str(x).strip().replace(",", ".").upper()
    if s in ("OFFLINE", "SEM ALARME", "SEM CAMERAS", "SEM CÂMERAS"): return 0
    try: return int(float(s))
    except: return 0

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    """
    Mantém a estrutura original, mas:
    - Se 'path' for URL (Drive), lê direto do link.
    - Senão, tenta a planilha local (compatibilidade).
    - >>> Ajuste mínimo: inclui a coluna H (Apelido) mesmo sem cabeçalho.
    """
    try:
        if isinstance(path, str) and path.strip().lower().startswith(("http://", "https://")):
            raw = pd.read_excel(path, header=None)
        else:
            p = Path(path)
            if not p.exists():
                p = PLANILHA_PATH
            raw = pd.read_excel(p, header=None)
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return pd.DataFrame()

    # <<< ALTERAÇÃO MINÍMA: agora traz até H (8 colunas) e garante Apelido se faltar >>>
    raw = raw.dropna(how="all").iloc[:, 0:8]
    if raw.shape[1] < 8:
        raw[7] = ""  # cria coluna H vazia se a planilha vier só até G

    raw.columns = ["Local","Cam_Total","Cam_Online","Cam_Status","Alm_Total","Alm_Online","Alm_Status","Apelido"]
    raw = raw.dropna(subset=["Local"])
    raw = raw[~raw["Local"].astype(str).str.contains("TOTAL|RELATÓRIO|RELATORIO", case=False, na=False)]
    for c in ["Cam_Total","Cam_Online","Alm_Total","Alm_Online"]:
        raw[c] = raw[c].apply(_to_int)
    raw["Cam_Falta"] = (raw["Cam_Total"] - raw["Cam_Online"]).clip(lower=0)
    raw["Alm_Falta"] = (raw["Alm_Total"] - raw["Alm_Online"]).clip(lower=0)
    raw["Cam_OfflineBool"] = (raw["Cam_Total"]>0) & (raw["Cam_Online"]==0)
    raw["Alm_OfflineBool"] = (raw["Alm_Total"]>0) & (raw["Alm_Online"]==0)
    def cam_status(r):
        if r["Cam_Total"]==0: return "SEM CÂMERAS"
        if r["Cam_Online"]==0: return "OFFLINE"
        if r["Cam_Online"]<r["Cam_Total"]: return f"FALTANDO {int(r['Cam_Falta'])}"
        return "OK"
    raw["Cam_Status"] = raw.apply(cam_status, axis=1)
    def alm_status(r):
        if r["Alm_Total"]==0: return "SEM ALARME"
        if r["Alm_Online"]==0: return "OFFLINE"
        if r["Alm_Online"]<r["Alm_Total"]: return f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        return "100%"
    raw["Alm_Status"] = raw.apply(alm_status, axis=1)
    return raw.reset_index(drop=True)

def chip(texto, tipo):
    cls = "ok" if tipo=="ok" else ("warn" if tipo=="warn" else "off")
    return f"<span class='chip {cls}'>{texto}</span>"

# ------------------ GRAFICO ------------------
def bar_values(values: dict, title: str):
    dfc = pd.DataFrame({
        "Categoria": list(values.keys()),
        "Quantidade": list(values.values())
    })
    fig = px.bar(
        dfc,
        x="Categoria",
        y="Quantidade",
        text="Quantidade",
        color="Categoria",
        color_discrete_map={
            "Online": CLR_GREEN,
            "Offline": CLR_RED,
            "Locais p/ manutenção": CLR_ORANGE
        }
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=10, r=10, t=50, b=20),
        paper_bgcolor=CLR_PANEL,
        plot_bgcolor=CLR_PANEL,
        font=dict(size=13),
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Quantidade"
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "toImageFilename": f"grafico_{title.lower().replace(' ','_')}",
            "modeBarButtonsToAdd": ["toImage"]
        },
        key=f"chart_{title.replace(' ','_')}"
    )

# ------------------ HEADER ------------------
_logo_bytes = load_logo_bytes()

st.markdown("<div class='top-wrap'>", unsafe_allow_html=True)
c_logo, c_title, c_search = st.columns([0.12, 0.58, 0.30])
with c_logo:
    st.markdown("<div class='logo-card'>", unsafe_allow_html=True)
    if _logo_bytes:
        try:
            st.image(_logo_bytes, use_container_width=True)
        except Exception:
            st.warning("⚠️ Erro ao carregar logo. O sistema continua funcionando.")
    else:
        st.warning("⚠️ Logo não carregada, mas o sistema continua funcionando.")
    st.markdown("</div>", unsafe_allow_html=True)

with c_title:
    # <-- apenas esta linha mudou para horário de Brasília
    hora_brasilia = datetime.now(pytz.timezone("America/Sao_Paulo"))
    st.markdown(
        f"<div class='title'>Dashboard Operacional – CFTV &amp; Alarmes</div>"
        f"<div class='subtitle'>Atualizado em {hora_brasilia.strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with c_search:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    query = st.text_input("Pesquisar local ou apelido...", "", placeholder="Digite o nome ou apelido…")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ ABAS ------------------
st.markdown("<div class='btn-row'>", unsafe_allow_html=True)
b1, b2, b3, _ = st.columns([0.11,0.11,0.11,0.67], gap="small")
if "tab" not in st.session_state: st.session_state.tab = "Câmeras"

def tab_button(label, tab_name, key):
    active = (st.session_state.tab == tab_name)
    if st.button(label, key=key):
        st.session_state.tab = tab_name
    js = f"""
    <script>
      const btns = Array.from(window.parent.document.querySelectorAll('button'));
      btns.forEach(b=>{{ if(b.innerText.trim()==='{label}') {{
          if({str(active).lower()}) b.classList.add('btn-active'); else b.classList.remove('btn-active');
      }}}});
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)

# Mantidos os botões originais com ícones/emoji (acionados)
with b1: tab_button("📷 Câmeras", "Câmeras", "btn_cam")
with b2: tab_button("🚨 Alarmes", "Alarmes", "btn_alm")
with b3: tab_button("📊 Geral",   "Geral",   "btn_ger")

st.divider()

# ------------------ DADOS ------------------
# Agora LENDO DIRETO DO DRIVE (sem mexer na assinatura da função)
df = load_data(DRIVE_URL)
if df.empty:
    st.error("Não foi possível ler dados do Google Drive. Verifique o link e permissões.")
    st.stop()
# >>>>>>>> REMOVIDO o st.info(...) a pedido <<<<<<<<

# <<< ALTERAÇÃO MINÍMA: busca híbrida Local + Apelido (case-insensitive) >>>
has_query = bool(query.strip())
if has_query:
    termo = query.strip().lower()
    dfv = df[
        df["Local"].astype(str).str.lower().str.contains(termo, na=False) |
        df["Apelido"].astype(str).str.lower().str.contains(termo, na=False)
    ]
else:
    dfv = df

# ------------------ RENDER: CÂMERAS ------------------
def render_cameras(dfx: pd.DataFrame):
    base = dfx[dfx["Cam_Total"] > 0]
    # >>> Troca mínima: padroniza título com os mesmos ícones dos botões
    st.markdown(f"#### 📷 Câmeras", unsafe_allow_html=True)

    total = int(base["Cam_Total"].sum())
    online = int(base["Cam_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Cam_OfflineBool"]) | (base["Cam_Falta"] > 0)).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='card'><div class='metric-sub'>Total</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    rows = base.copy()
    rows["__prio"] = np.where(rows["Cam_OfflineBool"], 2, np.where(rows["Cam_Falta"] > 0, 1, 0))
    rows = rows[rows["__prio"] > 0].sort_values(["__prio", "Cam_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100% OK.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Cam_OfflineBool"] else f"FALTANDO {int(r['Cam_Falta'])}"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'>"
            f"<div class='local-title'>📍 {r['Local']} — {chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Cam_Total']} • Online: {r['Cam_Online']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut}, "Resumo de Câmeras")


# ------------------ RENDER: ALARMES ------------------
def render_alarms(dfx: pd.DataFrame):
    base = dfx[dfx["Alm_Total"] > 0]
    # >>> Troca mínima: padroniza título com os mesmos ícones dos botões
    st.markdown(f"#### 🚨 Alarmes", unsafe_allow_html=True)

    total = int(base["Alm_Total"].sum())
    online = int(base["Alm_Online"].sum())
    offline = max(total - online, 0)
    locais_manut = int(((base["Alm_OfflineBool"]) | (base["Alm_Falta"] > 0)).sum())

    a1, a2, a3, a4 = st.columns(4)
    a1.markdown(f"<div class='card'><div class='metric-sub'>Centrais Totais</div><div class='metric'>{total}</div></div>", unsafe_allow_html=True)
    a2.markdown(f"<div class='card'><div class='metric-sub'>Online</div><div class='metric' style='color:{CLR_GREEN};'>{online}</div></div>", unsafe_allow_html=True)
    a3.markdown(f"<div class='card'><div class='metric-sub'>Offline</div><div class='metric' style='color:{CLR_RED};'>{offline}</div></div>", unsafe_allow_html=True)
    a4.markdown(f"<div class='card'><div class='metric-sub'>Locais p/ manutenção</div><div class='metric' style='color:{CLR_ORANGE};'>{locais_manut}</div></div>", unsafe_allow_html=True)

    rows = base.copy()
    rows["__prio"] = np.where(rows["Alm_OfflineBool"], 2, np.where(rows["Alm_Falta"] > 0, 1, 0))
    rows = rows[rows["__prio"] > 0].sort_values(["__prio", "Alm_Falta"], ascending=[False, False])

    st.markdown("#### Locais para manutenção / offline")
    if rows.empty:
        st.info("Nenhum local em manutenção. Use a busca para visualizar locais 100%.")
    for _, r in rows.iterrows():
        status = "OFFLINE" if r["Alm_OfflineBool"] else f"PARCIAL ({int(r['Alm_Online'])}/{int(r['Alm_Total'])})"
        cls = "offline" if "OFFLINE" in status else ""
        st.markdown(
            f"<div class='local-card {cls}'>"
            f"<div class='local-title'>📍 {r['Local']} — {chip(status, 'off' if 'OFFLINE' in status else 'warn')}</div>"
            f"<div class='local-info'>Total: {r['Alm_Total']} • Online: {r['Alm_Online']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    bar_values({"Online": online, "Offline": offline, "Locais p/ manutenção": locais_manut}, "Resumo de Alarmes")

# ------------------ RENDER: GERAL ------------------
def render_geral(dfx: pd.DataFrame):
    # >>> Troca mínima: padroniza título com os mesmos ícones dos botões
    st.markdown(f"#### 📊 Geral (Câmeras + Alarmes)",
                unsafe_allow_html=True)

    cam = dfx[dfx["Cam_Total"]>0]; alm = dfx[dfx["Alm_Total"]>0]
    cam_tot, cam_on = int(cam["Cam_Total"].sum()), int(cam["Cam_Online"].sum())
    alm_tot, alm_on = int(alm["Alm_Total"].sum()), int(alm["Alm_Online"].sum())
    cam_off, alm_off = cam_tot-cam_on, alm_tot-alm_on

    # Locais p/ manutenção (inalterado)
    locais_manut = int(((dfx["Cam_OfflineBool"]) | (dfx["Cam_Falta"]>0) |
                        (dfx["Alm_OfflineBool"]) | (dfx["Alm_Falta"]>0)).sum())

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Online</div><div class='metric' style='color:{CLR_GREEN};'>{cam_on}</div></div>", unsafe_allow_html=True)
    g2.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Online</div><div class='metric' style='color:{CLR_GREEN};'>{alm_on}</div></div>", unsafe_allow_html=True)
    g3.markdown(f"<div class='card'><div class='metric-sub'>Total de Câmeras</div><div class='metric'>{cam_tot}</div></div>", unsafe_allow_html=True)
    g4.markdown(f"<div class='card'><div class='metric-sub'>Total de Alarmes</div><div class='metric'>{alm_tot}</div></div>", unsafe_allow_html=True)
    g5.markdown(f"<div class='card'><div class='metric-sub'>Câmeras Offline</div><div class='metric' style='color:{CLR_RED};'>{cam_off}</div></div>", unsafe_allow_html=True)
    g6.markdown(f"<div class='card'><div class='metric-sub'>Alarmes Offline</div><div class='metric' style='color:{CLR_RED};'>{alm_off}</div></div>", unsafe_allow_html=True)

    bar_values(
        {"Online": cam_on+alm_on, "Offline": cam_off+alm_off, "Locais p/ manutenção": locais_manut},
        "Resumo Geral"
    )

    # --------- Relatório PDF (apenas locais com falhas) ---------
    st.markdown("### 📄 Relatório de Locais com Problemas")
    if st.button("🖨️ Gerar Relatório PDF"):
        faltando = dfx[(dfx["Cam_Falta"] > 0) | (dfx["Alm_Falta"] > 0)].copy()

        if faltando.empty:
            st.info("Nenhum local com falhas no momento.")
        else:
            table_df = faltando.loc[:, ["Local", "Cam_Falta", "Alm_Falta"]].rename(
                columns={"Cam_Falta": "Câmeras Faltantes", "Alm_Falta": "Alarmes Faltantes"}
            )

            # >>> adição mínima: logo centralizada e proporcional no topo do PDF
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

            pdf_name = "Relatório_Cftv&alarmes.pdf"
            doc = SimpleDocTemplate(pdf_name, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            # Logo: tenta arquivo; se não, usa bytes carregados do app
            try:
                logo_path = next((p for p in LOGO_FILE_CANDIDATES if os.path.exists(p)), None)
            except StopIteration:
                logo_path = None

            try:
                if logo_path:
                    im = Image(logo_path, width=120)  # preserva proporção
                elif _logo_bytes:
                    im = Image(BytesIO(_logo_bytes), width=120)
                else:
                    im = None
                if im:
                    im.hAlign = "CENTER"
                    elements.append(im)
                    elements.append(Spacer(1, 8))
            except Exception:
                pass

            title = Paragraph("<b>Relatório de Locais com Falhas</b>", styles["Title"])
            elements.append(title)
            elements.append(Spacer(1, 10))
            subtitle = Paragraph(f"Gerado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')}", styles["Normal"])
            elements.append(subtitle)
            elements.append(Spacer(1, 12))

            data = [list(table_df.columns)]
            for _, row in table_df.iterrows():
                data.append([str(row["Local"]), int(row["Câmeras Faltantes"]), int(row["Alarmes Faltantes"])])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B1F3B")),  # azul da logo
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            doc.build(elements)

            with open(pdf_name, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar Relatório PDF",
                    data=f,
                    file_name=pdf_name,
                    mime="application/pdf"
                )

# ------------------ DISPATCH ------------------
tab = st.session_state.tab
if tab == "Câmeras":
    render_cameras(dfv)
elif tab == "Alarmes":
    render_alarms(dfv)
else:
    render_geral(dfv)

st.caption("© Grupo Perímetro & Monitoramento • Dashboard Operacional")
