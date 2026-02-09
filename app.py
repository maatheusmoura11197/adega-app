import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
st.title("🍷 Fidelidade Adega Online")

# Configuração para ligar ao Google Sheets
# O Streamlit vai procurar as senhas nos "Secrets" que vamos configurar a seguir
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Aqui ele busca a senha secreta que vamos criar
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    
    # Abre a planilha pelo nome (tem de ser exato)
    sheet = client.open("Fidelidade").sheet1
    conexao_ok = True
except:
    conexao_ok = False
    st.warning("⚠️ A configurar conexão... (Ainda falta a Chave Secreta)")

nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com DDD)").strip()

if st.button("Registar Compra"):
    if nome and telefone and conexao_ok:
        try:
            # 1. Busca todos os dados da planilha
            dados = sheet.get_all_records()
            df = pd.DataFrame(dados)

            # 2. Procura o cliente
            # Se a planilha estiver vazia ou cliente nao existir
            if df.empty or nome not in df['nome'].values:
                # Adiciona nova linha no Google Sheets
                sheet.append_row([nome, telefone, 1])
                total = 1
                st.toast(f"Novo cliente {nome} cadastrado!")
            else:
                # Encontra a linha do cliente e soma +1
                # (O gspread usa linhas começando em 1, e cabeçalho é linha 1, então somamos +2 no index)
                idx = df[df['nome'] == nome].index[0]
                linha_excel = idx + 2 
                compras_atuais = df.loc[idx, 'compras']
                total = compras_atuais + 1
                sheet.update_cell(linha_excel, 3, int(total))
            
            st.success(f"✅ Registado! {nome} tem agora {total} compras.")

            # 3. Verifica Fidelidade
            if total >= 9:
                st.balloons()
                msg = f"Ola {nome}! Completaste {total} compras. Ganhaste 50% de desconto na proxima!"
                link = f"https://wa.me/{telefone}?text={msg.replace(' ', '%20')}"
                st.markdown(f"### [🎁 CLIQUE AQUI PARA ENVIAR WHATSAPP]({link})")

        except Exception as e:
            st.error(f"Erro na gravação: {e}")
    elif not conexao_ok:
        st.error("Ainda falta configurar a Chave Secreta no site!")
    else:
        st.warning("Preenche o nome e telefone.")
