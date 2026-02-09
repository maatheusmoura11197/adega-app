import streamlit as st
import pandas as pd

# O LINK DA TUA FOLHA (Já coloquei o teu link correto aqui)
LINK_GOOGLE = "https://docs.google.com/spreadsheets/d/191D0UIDvwDJPWRtp_0cBFS9rWaq6CkSj5ET_1HO2sLI/export?format=csv"

st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
st.title("🍷 Fidelidade Adega Online")

# Interface do Utilizador
nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com o 55 da frente)").strip()

if st.button("Registar Compra"):
    if nome and telefone:
        try:
            # Tenta ler a folha
            df = pd.read_csv(LINK_GOOGLE)
            
            # Procura o cliente
            if nome in df['nome'].values:
                # Se encontrar, mostra o valor que está lá + 1
                compras_na_folha = df.loc[df['nome'] == nome, 'compras'].values[0]
                total = compras_na_folha + 1
            else:
                total = 1
            
            st.success(f"Sucesso! {nome} tem agora {total} compras.")
            
            # --- ATENÇÃO ---
            # Para o Python GRAVAR na folha, precisamos de configurar as 'Secrets' no Streamlit.
            # Enquanto não fazemos isso, o valor só aparece na tela.
            st.warning("⚠️ O sistema está em modo de teste. Os dados ainda não estão a ser gravados na folha do Google.")

            if total >= 9:
                st.balloons()
                msg = f"Ola {nome}! Voce ganhou 50% de desconto na sua 10ª compra!"
                link_zap = f"https://wa.me/{telefone}?text={msg.replace(' ', '%20')}"
                st.markdown(f"### [CLIQUE AQUI PARA MANDAR WHATSAPP]({link_zap})")

        except Exception as e:
            st.error(f"Erro ao ler a folha: {e}")
