# app.py
import streamlit as st
import pandas as pd
from update import processar_planilha_com_resgates

st.set_page_config(page_title="Transol Conecta", page_icon="📊")
st.markdown("""
    <style>
    .reportview-container {
        padding: 2rem 1rem 1rem 1rem;
    }
    .stButton>button {
        background-color: white;
        color: red;
        border: 1px solid red;
        border-radius: 0.5rem;
        padding: 0.4rem 1.5rem;
    }
    .resultado-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.1);
    }
    .resultado-container p {
        margin: 0.3rem 0;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Consulta de Pontuação do Eletricista")
st.markdown("Digite o CPF ou Nome completo do eletricista")

entrada = st.text_input("", max_chars=100)

if st.button("Buscar"):
    if not entrada.strip():
        st.warning("Por favor, insira o nome ou CPF/CNPJ.")
    else:
        entrada_str = entrada.strip().upper()
        entrada_numeros = ''.join(filter(str.isdigit, entrada))

        df = processar_planilha_com_resgates()

        df['Eletricista'] = df['Eletricista'].astype(str).str.strip().str.upper()
        df['CPF/CNPJ'] = df['CPF/CNPJ'].astype(str).str.replace(r'[^0-9]', '', regex=True)

        resultado = df[
            (df['Eletricista'] == entrada_str) |
            (df['CPF/CNPJ'] == entrada_numeros)
        ]

        if not resultado.empty:
            st.success("Eletricista encontrado!")
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
