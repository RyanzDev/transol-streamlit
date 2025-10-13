# updateweb.py  (versão sem cache)
import re
import pandas as pd
import streamlit as st

# Link direto para o Excel no Google Drive (exportação como .xlsx)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1sEsnNi-gGYDuwZ9qZexvbAfp4dvqKoPN/export?format=xlsx"

VALOR_POR_PONTO = 1.50  # 1 ponto = R$ 1,50

# ---------------------------
# Helpers
# ---------------------------
def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", str(s or ""))

def _norm_doc(s: str) -> str:
    d = _only_digits(s)
    return d.zfill(11) if len(d) <= 11 else d.zfill(14)

def _safe_read(sheet_name: str, expected_cols=None) -> pd.DataFrame:
    """Lê uma aba do Google Sheets. Se falhar, retorna DF vazio com as colunas esperadas."""
    try:
        df = pd.read_excel(URL_PLANILHA, sheet_name=sheet_name)
        if expected_cols:
            for c in expected_cols:
                if c not in df.columns:
                    df[c] = pd.NA
        return df
    except Exception:
        return pd.DataFrame(columns=expected_cols or [])

# ---------------------------
# API principal
# ---------------------------
def processar_planilha_com_resgates() -> pd.DataFrame:
    try:
        # --- TAB03: Identificação (Nome <-> DOC normalizado) ---
        df_ident = _safe_read("TAB03", expected_cols=["Nome", "CPF/CNPJ"]).copy()
        df_ident = df_ident[df_ident["Nome"].notna() & df_ident["CPF/CNPJ"].notna()]
        df_ident["Nome"] = df_ident["Nome"].astype(str).str.strip().str.upper()
        df_ident["DOC"] = df_ident["CPF/CNPJ"].apply(_norm_doc)
        df_ident = df_ident[["Nome", "DOC"]]

        # --- TAB01: Base de vendas ---
        df1 = _safe_read("TAB01", expected_cols=["Nome Instalador", "Total Ped."])
        df1 = df1[df1["Nome Instalador"].notna()].copy()
        df1["Nome Instalador"] = df1["Nome Instalador"].astype(str).str.strip().str.upper()
        df1["Total Vendido (R$)"] = pd.to_numeric(df1["Total Ped."], errors="coerce").fillna(0.0)
        base_por_nome = df1.groupby("Nome Instalador", as_index=False)["Total Vendido (R$)"].sum()

        # --- TAB04: Lançamentos extras ---
        df4 = _safe_read("TAB04", expected_cols=["CPF/CNPJ", "Numero Pedido", "Data Pedido", "Valor"])
        extras_por_nome = pd.DataFrame(columns=["Nome Instalador", "Valor Extra (R$)"])
        if not df4.empty:
            df4["DOC"] = df4["CPF/CNPJ"].apply(_norm_doc)
            df4["Valor"] = pd.to_numeric(df4["Valor"], errors="coerce").fillna(0.0)
            df4 = df4.merge(df_ident, how="left", left_on="DOC", right_on="DOC")
            df4["Nome"] = df4["Nome"].astype(str).str.strip().str.upper()
            extras_por_nome = (
                df4.groupby("Nome", as_index=False)["Valor"]
                .sum()
                .rename(columns={"Nome": "Nome Instalador", "Valor": "Valor Extra (R$)"})
            )

        # --- Unifica TAB01 + TAB04 ---
        df_agr = base_por_nome.merge(extras_por_nome, how="outer", on="Nome Instalador")
        df_agr["Total Vendido (R$)"] = (
            df_agr["Total Vendido (R$)"].fillna(0.0) +
            df_agr["Valor Extra (R$)"].fillna(0.0)
        )
        if "Valor Extra (R$)" in df_agr.columns:
            df_agr.drop(columns=["Valor Extra (R$)"], inplace=True)

        # Pontos totais
        df_agr["Pontos"] = (df_agr["Total Vendido (R$)"] // 100).astype(int)

        # --- TAB02: Resgates ---
        df2 = _safe_read("TAB02", expected_cols=["Nome Instalador", "Valor Resgatado", "DataHora Resgate", "Usuario"])
        df2 = df2[df2["Nome Instalador"].notna()].copy()
        df2["Nome Instalador"] = df2["Nome Instalador"].astype(str).str.strip().str.upper()
        df2["Valor Resgatado"] = pd.to_numeric(df2["Valor Resgatado"], errors="coerce").fillna(0.0)
        df2["Pontos Resgatados"] = (df2["Valor Resgatado"] / VALOR_POR_PONTO).apply(lambda x: int(x // 1))
        df2_grp = df2.groupby("Nome Instalador", as_index=False)["Pontos Resgatados"].sum()

        # --- Merge ---
        df_m = df_agr.merge(df2_grp, how="left", on="Nome Instalador")
        df_m["Pontos Resgatados"] = df_m["Pontos Resgatados"].fillna(0).astype(int)
        df_m["Pontos Finais"] = (df_m["Pontos"] - df_m["Pontos Resgatados"]).clip(lower=0)
        df_m["Valor em R$"] = df_m["Pontos Finais"] * VALOR_POR_PONTO

        # --- Junta CPF/CNPJ ---
        df_m = df_m.merge(
            df_ident.rename(columns={"Nome": "Nome Instalador"})[["Nome Instalador", "DOC"]],
            how="left",
            on="Nome Instalador"
        ).rename(columns={"DOC": "CPF/CNPJ"})

        # --- Saída final ---
        df_final = df_m.rename(columns={"Nome Instalador": "Eletricista"})
        colunas = [
            "Eletricista",
            "CPF/CNPJ",
            "Total Vendido (R$)",
            "Pontos",
            "Pontos Resgatados",
            "Pontos Finais",
            "Valor em R$"
        ]
        for c in colunas:
            if c not in df_final.columns:
                df_final[c] = 0 if "Pontos" in c else None

        return df_final[colunas]

    except Exception as e:
        return pd.DataFrame({"Erro": [f"Falha ao processar planilha: {e}"]})

# ---------------------------
# Histórico de resgates (sem Valor Resgatado)
# ---------------------------
def carregar_resgates_por_nome(nome: str) -> pd.DataFrame:
    """
    Retorna o histórico de resgates para um eletricista (pelo Nome),
    com colunas: DataHora Resgate, Pontos Resgatados e Usuario.
    """
    df2 = _safe_read(
        "TAB02",
        expected_cols=["Nome Instalador", "Valor Resgatado", "DataHora Resgate", "Usuario"]
    ).copy()

    if df2.empty:
        return pd.DataFrame(columns=["DataHora Resgate", "Pontos Resgatados", "Usuario"])

    alvo = str(nome).strip().upper()
    df2["Nome Instalador"] = df2["Nome Instalador"].astype(str).str.strip().str.upper()
    df2["Valor Resgatado"] = pd.to_numeric(df2["Valor Resgatado"], errors="coerce").fillna(0.0)

    hist = df2[df2["Nome Instalador"] == alvo].copy()
    if hist.empty:
        return pd.DataFrame(columns=["DataHora Resgate", "Pontos Resgatados", "Usuario"])

    hist["Pontos Resgatados"] = (hist["Valor Resgatado"] / VALOR_POR_PONTO).astype(int)

    if "DataHora Resgate" in hist.columns:
        hist["_dt"] = pd.to_datetime(hist["DataHora Resgate"], errors="coerce")
        hist = hist.sort_values(by="_dt", ascending=False).drop(columns=["_dt"])

    cols = ["DataHora Resgate", "Pontos Resgatados", "Usuario"]
    for c in cols:
        if c not in hist.columns:
            hist[c] = ""
    return hist[cols].reset_index(drop=True)
