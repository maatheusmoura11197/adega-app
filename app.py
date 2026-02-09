import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DO TEU CADERNO ---
# 1. Abre a tua folha no Google Sheets
# 2. Clica em Partilhar -> Qualquer pessoa com o link -> Editor
# 3. Cola o link aqui entre as aspas:
LINK_GOOGLE = "COLA_AQUI_O_TEU_LINK_DO_GOOGLE_SHEETS"

# Esta linha transforma o link normal num link que o Python consegue ler
if "edit?usp=sharing" in LINK_GOOGLE:
    URL_CSV = LINK_GOOGLE.replace("edit?usp=sharing", "export?format=csv")
else:
    URL_CSV = LINK_GOOGLE + "/export?format=csv"

st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
st.title("🍷 Fidelidade Adega Online")

# Campos de entrada
nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com o 55 da frente)").strip()

if st.button("Registar Compra"):
    if nome and telefone:
        try:
            # Lê os dados da internet
            df = pd.read_csv(URL_CSV)
            
            # Se o cliente existe, soma 1. Se não, começa com 1.
            if nome in df['nome'].values:
                df.loc[df['nome'] == nome, 'compras'] += 1
                total = df.loc[df['nome'] == nome, 'compras'].values[0]
            else:
                total = 1
                st.info("Novo cliente registado!")

            st.success(f"Sucesso! {nome} tem {total} compras.")

            # Regra dos 50%
            if total >= 9:
                st.balloons()
                st.warning("🚨 GANHOU 50% DE DESCONTO!")
                msg = f"Ola {nome}! Voce completou {total} compras e ganhou 50% de desconto na proxima!"
                link_zap = f"https://wa.me/{telefone}?text={msg.replace(' ', '%20')}"
                st.markdown(f"### [CLIQUE AQUI PARA MANDAR WHATSAPP]({link_zap})")
            
            st.write("⚠️ Nota: Para salvar permanentemente, lembra-te de atualizar a folha do Google (ou usaremos um banco de dados real no próximo passo).")
            
        except Exception as e:
            st.error(f"Erro ao ler o Google Sheets. Verificaste o link? {e}")
    else:
        st.error("Preenche o nome e o telefone!")
