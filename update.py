#update.py
import json
import os
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
from config import obter_diretorio_ativo

ARQUIVO_PROCESSADO = "ultimo_arquivo_processado.txt"
def obter_caminho_arquivo():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        return os.path.join(config["diretorio_planilha"], "db.xlsx")

CAMINHO_ARQUIVO = obter_caminho_arquivo()

def obter_arquivo_mais_recente(diretorio):
    arquivos = [os.path.join(diretorio, f) for f in os.listdir(diretorio) if f.endswith('.xlsx')]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)


def arquivo_ja_processado(caminho_arquivo):
    if not os.path.exists(ARQUIVO_PROCESSADO):
        return False
    with open(ARQUIVO_PROCESSADO, 'r') as f:
        ultima_data = f.read().strip()
    data_arquivo = str(os.path.getmtime(caminho_arquivo))
    return ultima_data == data_arquivo


def salvar_arquivo_processado(caminho_arquivo):
    data_arquivo = str(os.path.getmtime(caminho_arquivo))
    with open(ARQUIVO_PROCESSADO, 'w') as f:
        f.write(data_arquivo)


def atualizar_dados():
    diretorio = obter_diretorio_ativo()
    if not diretorio:
        return

    caminho_arquivo = obter_arquivo_mais_recente(diretorio)
    if not caminho_arquivo:
        messagebox.showwarning("Aviso", "Nenhuma planilha encontrada no diretório selecionado.")
        return

    if arquivo_ja_processado(caminho_arquivo):
        messagebox.showinfo("Atualização", "Nenhuma nova planilha detectada.")
        return

    try:
        df = pd.read_excel(caminho_arquivo, sheet_name='TAB01')
        relatorio = df.groupby('Nome Instalador')['Total Ped.'].sum().reset_index()
        relatorio.rename(columns={'Total Ped.': 'Total em Vendas'}, inplace=True)
        relatorio['Pontos'] = (relatorio['Total em Vendas'] // 100).astype(int)
        relatorio['Valor em Reais'] = relatorio['Pontos'] * 1.5

        # Salva como CSV
        relatorio.to_csv("relatorio_pontuacao.csv", index=False)

        salvar_arquivo_processado(caminho_arquivo)

        messagebox.showinfo("Sucesso", "Relatório gerado com sucesso como 'relatorio_pontuacao.csv'.")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao processar a planilha: {str(e)}")

def processar_planilha():
    diretorio = obter_diretorio_ativo()
    caminho = os.path.join(diretorio, "db.xlsx")

    df = pd.read_excel(caminho, sheet_name='TAB01')
    
    df = df[df['Nome Instalador'].notna()]
    df['Total Vendido (R$)'] = df['Total Ped.']
    df = df.groupby('Nome Instalador')['Total Vendido (R$)'].sum().reset_index()
    df['Pontos'] = (df['Total Vendido (R$)'] // 100).astype(int)
    df['Valor em R$'] = df['Pontos'] * 1.5
    df = df.rename(columns={'Nome Instalador': 'Eletricista'})
    
    return df

# Função para processar os dados considerando os resgates e associar com CPF/CNPJ
def processar_planilha_com_resgates():
    df = pd.read_excel(CAMINHO_ARQUIVO, sheet_name="TAB01")
    df = df[df['Nome Instalador'].notna()]
    df['Total Vendido (R$)'] = pd.to_numeric(df['Total Ped.'], errors='coerce').fillna(0)
    df_agrupado = df.groupby('Nome Instalador')['Total Vendido (R$)'].sum().reset_index()

    df_agrupado['Pontos'] = (df_agrupado['Total Vendido (R$)'] / 100).astype(int)
    df_agrupado['Valor em R$'] = df_agrupado['Pontos'] * 1.5

    # Resgates
    df_resgates = pd.read_excel(CAMINHO_ARQUIVO, sheet_name="TAB02")
    df_resgates = df_resgates[df_resgates['Nome Instalador'].notna()]
    df_resgates['Pontos Resgatados'] = pd.to_numeric(df_resgates['Valor Resgatado'], errors='coerce').fillna(0).astype(int)
    df_resgates = df_resgates.groupby('Nome Instalador')['Pontos Resgatados'].sum().reset_index()

    # Junta com os dados principais
    df_merged = pd.merge(df_agrupado, df_resgates, how='left', on='Nome Instalador')
    df_merged['Pontos Resgatados'] = df_merged['Pontos Resgatados'].fillna(0).astype(int)
    df_merged['Pontos Finais'] = df_merged['Pontos'] - df_merged['Pontos Resgatados']
    df_merged['Pontos Finais'] = df_merged['Pontos Finais'].clip(lower=0)

    # Carrega os CPFs
    try:
        df_ident = pd.read_excel(CAMINHO_ARQUIVO, sheet_name="TAB03", dtype={"CPF/CNPJ": str})
        df_ident = df_ident[df_ident['Nome'].notna() & df_ident['CPF/CNPJ'].notna()]
        df_ident['Nome'] = df_ident['Nome'].str.strip().str.upper()
        df_ident['CPF/CNPJ'] = df_ident['CPF/CNPJ'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar identificações da TAB03: {e}")
        df_ident = pd.DataFrame(columns=['Nome', 'CPF/CNPJ'])

    # Junta os CPFs ao resultado
    df_merged['Nome Instalador'] = df_merged['Nome Instalador'].str.strip().str.upper()
    df_merged = df_merged.merge(df_ident, how='left', left_on='Nome Instalador', right_on='Nome')
    df_merged = df_merged.rename(columns={
        'Nome Instalador': 'Eletricista',
        'CPF/CNPJ': 'CPF/CNPJ'
    })

    # Reorganiza as colunas para mostrar CPF/CNPJ corretamente
    colunas = ['Eletricista', 'CPF/CNPJ', 'Total Vendido (R$)', 'Pontos Finais', 'Valor em R$']
    for col in colunas:
        if col not in df_merged.columns:
            df_merged[col] = None

    return df_merged[colunas]

# Função para registrar um novo resgate na TAB02
def registrar_resgate(nome, pontos):
    df_resgates = pd.read_excel(CAMINHO_ARQUIVO, sheet_name="TAB02")
    novo_resgate = pd.DataFrame({
        'Nome Instalador': [nome],
        'Valor Resgatado': [pontos]  # já são pontos
    })
    df_atualizado = pd.concat([df_resgates, novo_resgate], ignore_index=True)
    with pd.ExcelWriter(CAMINHO_ARQUIVO, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df_atualizado.to_excel(writer, sheet_name="TAB02", index=False)

# Função para abrir o formulário de resgate
def abrir_formulario_resgate(janela_pai, callback_atualizar=None):
    form = tk.Toplevel(janela_pai)
    form.title("Registrar Resgate")
    form.geometry("300x200")

    tk.Label(form, text="Nome do Eletricista:").pack(pady=5)
    entry_nome = tk.Entry(form)
    entry_nome.pack(pady=5)

    tk.Label(form, text="Pontos a Resgatar:").pack(pady=5)
    entry_pontos = tk.Entry(form)
    entry_pontos.pack(pady=5)

    def salvar():
        nome = entry_nome.get().strip()
        try:
            pontos = int(entry_pontos.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um número válido de pontos.")
            return

        if not nome or pontos <= 0:
            messagebox.showerror("Erro", "Preencha todos os campos corretamente.")
            return

        try:
            registrar_resgate(nome, pontos)
            messagebox.showinfo("Sucesso", "Resgate registrado com sucesso!")
            form.destroy()
            if callback_atualizar:
                callback_atualizar()  # atualiza a treeview após salvar
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao registrar resgate: {e}")

    ttk.Button(form, text="Salvar Resgate", command=salvar).pack(pady=10)


