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
