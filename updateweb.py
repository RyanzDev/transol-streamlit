# update.py (versão para Streamlit web)
import pandas as pd

# Link direto para o Excel no Google Drive (exportação como .xlsx)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1sEsnNi-gGYDuwZ9qZexvbAfp4dvqKoPN/export?format=xlsx"

def processar_planilha_com_resgates():
    try:
        # Carrega a aba principal
        df = pd.read_excel(URL_PLANILHA, sheet_name="TAB01")
        df = df[df['Nome Instalador'].notna()]
        df['Total Vendido (R$)'] = pd.to_numeric(df['Total Ped.'], errors='coerce').fillna(0)
        df_agrupado = df.groupby('Nome Instalador')['Total Vendido (R$)'].sum().reset_index()

        df_agrupado['Pontos'] = (df_agrupado['Total Vendido (R$)'] / 100).astype(int)
        df_agrupado['Valor em R$'] = df_agrupado['Pontos'] * 1.5

        # Resgates
        df_resgates = pd.read_excel(URL_PLANILHA, sheet_name="TAB02")
        df_resgates = df_resgates[df_resgates['Nome Instalador'].notna()]
        df_resgates['Pontos Resgatados'] = pd.to_numeric(df_resgates['Valor Resgatado'], errors='coerce').fillna(0).astype(int)
        df_resgates = df_resgates.groupby('Nome Instalador')['Pontos Resgatados'].sum().reset_index()

        # Junta com os dados principais
        df_merged = pd.merge(df_agrupado, df_resgates, how='left', on='Nome Instalador')
        df_merged['Pontos Resgatados'] = df_merged['Pontos Resgatados'].fillna(0).astype(int)
        df_merged['Pontos Finais'] = df_merged['Pontos'] - df_merged['Pontos Resgatados']
        df_merged['Pontos Finais'] = df_merged['Pontos Finais'].clip(lower=0)

        # Identificação CPF/CNPJ
        try:
            df_ident = pd.read_excel(URL_PLANILHA, sheet_name="TAB03", dtype={"CPF/CNPJ": str})
            df_ident = df_ident[df_ident['Nome'].notna() & df_ident['CPF/CNPJ'].notna()]
            df_ident['Nome'] = df_ident['Nome'].str.strip().str.upper()
            df_ident['CPF/CNPJ'] = df_ident['CPF/CNPJ'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        except Exception:
            df_ident = pd.DataFrame(columns=['Nome', 'CPF/CNPJ'])

        df_merged['Nome Instalador'] = df_merged['Nome Instalador'].str.strip().str.upper()
        df_merged = df_merged.merge(df_ident, how='left', left_on='Nome Instalador', right_on='Nome')

        df_merged = df_merged.rename(columns={
            'Nome Instalador': 'Eletricista',
            'CPF/CNPJ': 'CPF/CNPJ'
        })

        # Organiza as colunas
        colunas = ['Eletricista', 'CPF/CNPJ', 'Total Vendido (R$)', 'Pontos Finais', 'Valor em R$']
        for col in colunas:
            if col not in df_merged.columns:
                df_merged[col] = None

        return df_merged[colunas]

    except Exception as e:
        # Em ambiente web, erros devem ser tratados no app.py
        return pd.DataFrame({'Erro': [f'Falha ao processar planilha: {e}']})
