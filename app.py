import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuração da página
st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
st.title("🍷 Fidelidade Adega Online")

# --- CONEXÃO COM O GOOGLE SHEETS ---
try:
    # O robô vai buscar a senha que guardaste nos 'Secrets' do site
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    
    # Abre a folha chamada 'Fidelidade' (Tem de ter este nome exato no Google)
    sheet = client.open("Fidelidade").sheet1
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")
    st.info("Verifica se o nome da planilha no Google é exatamente 'Fidelidade' e se partilhaste com o email do robô.")
    conexao = False

# --- O APLICATIVO ---
nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com DDD, apenas números)").strip()

if st.button("Registar Compra"):
    if nome and telefone and conexao:
        try:
            with st.spinner('A registar na nuvem...'):
                # 1. Ler os dados atuais
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)

                # 2. Verificar se cliente existe
                novo_total = 1
                
                # Se a planilha estiver vazia ou cliente não existir
                if df.empty or nome not in df['nome'].values:
                    # Adiciona nova linha
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"🆕 Cliente {nome} cadastrado com sucesso!")
                else:
                    # Encontra onde está o cliente
                    # O gspread conta linhas a partir do 1, e temos o cabeçalho, por isso a matemática:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    
                    # Atualiza a célula específica
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"🔄 Compra somada para {nome}!")

                st.success(f"✅ Feito! {nome} tem agora {novo_total} compras.")

                # 3. Regra dos 50%
                if novo_total >= 9:
                    st.balloons()
                    msg = f"Ola {nome}! Completaste {novo_total} compras. Ganhaste 50% de desconto na proxima!"
                    link_zap = f"https://wa.me/{telefone}?text={msg.replace(' ', '%20')}"
                    st.markdown(f"### [🎁 CLIQUE AQUI PARA ENVIAR O PRÉMIO NO WHATSAPP]({link_zap})")

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão com a planilha.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
