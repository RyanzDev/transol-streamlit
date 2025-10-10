# app.py
import re
import streamlit as st
import pandas as pd
from updateweb import processar_planilha_com_resgates
import updateweb as uw  # para carregar histórico de resgates (TAB02)

# =========================
# Config e estilo
# =========================
st.set_page_config(page_title="Transol Conecta", page_icon="📊", layout="centered")

st.markdown("""
    <style>
    html, body, [class*="css"] {
        background-color: #ffffff;
        color: #333333;
    }

    .reportview-container { padding: 2rem 1rem 1rem 1rem; }

    .stButton>button {
        background-color: #d91c1c;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #b91818;
        color: #f0f0f0;
        cursor: pointer;
    }

    .resultado-container {
        background-color: #f8f8f8;
        padding: 1rem;
        border-radius: 0.75rem;
        margin-top: 1rem;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
    }
    .resultado-container p {
        margin: 0.3rem 0;
        font-size: 1.05rem;
    }

    .logo-container { text-align: center; margin-bottom: 20px; }
    img.logo { width: 240px; }
    </style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
VALOR_POR_PONTO = 1.50

def only_digits(s: str) -> str:
    return re.sub(r'\D', '', str(s or ''))

def norm_doc(s: str) -> str:
    d = only_digits(s)
    return d.zfill(11) if len(d) <= 11 else d.zfill(14)

def fmt_brl(x) -> str:
    try:
        return "R$ " + f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

# =========================
# Logo e título
# =========================
st.markdown("""
<div class="logo-container">
    <img src="https://raw.githubusercontent.com/RyanzDev/transol-streamlit/main/logo.png" class="logo">
</div>
""", unsafe_allow_html=True)

st.markdown("Insira o **CPF** ou **nome completo** do eletricista abaixo para verificar sua pontuação:")

# Campo com label oculto
entrada = st.text_input(
    "Digite aqui o nome ou CPF/CNPJ do eletricista:",
    label_visibility="collapsed",
    max_chars=100
)

# =========================
# Busca
# =========================
if st.button("Buscar"):
    if not entrada.strip():
        st.warning("Por favor, insira o nome ou CPF/CNPJ.")
    else:
        entrada_nome = entrada.strip().upper()
        entrada_doc = norm_doc(entrada)

        df = processar_planilha_com_resgates()

        if 'Eletricista' not in df.columns:
            st.error("Erro: Dados não carregados corretamente.")
            st.stop()

        # Normalização para comparação
        df['Eletricista'] = df['Eletricista'].astype(str).str.strip().str.upper()
        df['CPF/CNPJ'] = df['CPF/CNPJ'].astype(str).apply(norm_doc)

        # Match por nome exato OU CPF/CNPJ
        resultado = df[(df['Eletricista'] == entrada_nome) | (df['CPF/CNPJ'] == entrada_doc)]

        if not resultado.empty:
            st.success("✅ Eletricista encontrado!")
            for _, row in resultado.iterrows():
                nome = row.get('Eletricista', '')
                doc  = row.get('CPF/CNPJ', '')
                total_vendido = row.get('Total Vendido (R$)', 0.0)
                pontos_totais = int(row.get('Pontos', 0))
                pontos_resgatados = int(row.get('Pontos Resgatados', 0))
                pontos_finais = int(row.get('Pontos Finais', 0))

                st.markdown(f"""
                    <div class='resultado-container'>
                        <p><strong>Nome:</strong> {nome}</p>
                        <p><strong>CPF/CNPJ:</strong> {doc}</p>
                        <p><strong>Total Vendido:</strong> {fmt_brl(total_vendido)}</p>
                        <p><strong>Total de pontos:</strong> {pontos_totais}</p>
                        <p><strong>Pontos resgatados:</strong> {pontos_resgatados}</p>
                        <p><strong>Pontos Finais:</strong> {pontos_finais}</p>
                    </div>
                """, unsafe_allow_html=True)

                # Histórico de resgates (opcional) — TAB02
                with st.expander("Ver histórico de resgates (opcional)"):
                    try:
                        hist = uw.carregar_resgates_por_nome(nome)
                        if hist.empty:
                            st.info("Nenhum resgate encontrado para este eletricista.")
                        else:
                            hist = hist.copy()
                            hist["Valor Resgatado"] = hist["Valor Resgatado"].apply(fmt_brl)
                            st.dataframe(hist, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao carregar histórico de resgates: {e}")
        else:
            st.error("❌ Eletricista não encontrado.")

# Rodapé
st.markdown("""
<hr style="margin-top: 3rem;">
<p style="text-align:center; font-size:0.9rem; color:#999999;">
    Desenvolvido por <strong>– Eletro Transol Tecnologia</strong> • Todos os direitos reservados
</p>
""", unsafe_allow_html=True)

