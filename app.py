import streamlit as st
import pandas as pd
from updateweb import processar_planilha_com_resgates

# Configuração da página
st.set_page_config(page_title="Transol Conecta", page_icon="📊", layout="centered")

# Força o modo claro (resolve o bug do dark mode em celulares)
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        background-color: #ffffff;
        color: #333333;
    }

    .reportview-container {
        padding: 2rem 1rem 1rem 1rem;
    }

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

    .logo-container {
        text-align: center;
        margin-bottom: 20px;
    }

    img.logo {
        width: 240px;
    }

    </style>
""", unsafe_allow_html=True)

# Logo
st.markdown("""
<div class="logo-container">
    <img src="https://raw.githubusercontent.com/RyanzDev/transol-streamlit/263c301376aadb18d3b66703ab18a2ed5952d96e/logo.png" class="logo">
</div>
""", unsafe_allow_html=True)

# Título
st.markdown("Insira o **CPF** ou **nome completo** do eletricista abaixo para verificar sua pontuação:")

# Campo de entrada
entrada = st.text_input("", max_chars=100)

# Botão
if st.button("Buscar"):
    if not entrada.strip():
        st.warning("Por favor, insira o nome ou CPF/CNPJ.")
    else:
        entrada_str = entrada.strip().upper()
        entrada_numeros = ''.join(filter(str.isdigit, entrada))

        df = processar_planilha_com_resgates()

        if 'Eletricista' not in df.columns:
            st.error("Erro: Dados não carregados corretamente.")
            st.stop()

        df['Eletricista'] = df['Eletricista'].astype(str).str.strip().str.upper()
        df['CPF/CNPJ'] = df['CPF/CNPJ'].astype(str).str.replace(r'[^0-9]', '', regex=True)

        resultado = df[
            (df['Eletricista'] == entrada_str) |
            (df['CPF/CNPJ'] == entrada_numeros)
        ]

        if not resultado.empty:
            st.success("✅ Eletricista encontrado!")
            for _, row in resultado.iterrows():
                st.markdown(f"""
                    <div class='resultado-container'>
                        <p><strong>Nome:</strong> {row['Eletricista']}</p>
                        <p><strong>CPF/CNPJ:</strong> {row['CPF/CNPJ']}</p>
                        <p><strong>Total Vendido:</strong> R$ {row['Total Vendido (R$)']:.2f}</p>
                        <p><strong>Pontos Finais:</strong> {row['Pontos Finais']}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Eletricista não encontrado.")
