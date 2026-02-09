import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Controle Fidelidade", page_icon="🤑")
st.title("🍷 Fidelidade Adega Online")

# --- CONEXÃO COM O GOOGLE SHEETS ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open("Fidelidade").sheet1
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")
    conexao = False

# --- DADOS DO CLIENTE ---
nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com DDD, apenas números)").strip()

if st.button("Registar Compra", type="primary"):
    if nome and telefone and conexao:
        try:
            with st.spinner('A processar...'):
                # 1. LER DADOS
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                novo_total = 1
                if df.empty or nome not in df['nome'].values:
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"Novo cliente cadastrado!")
                else:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"Compra registada!")

                st.success(f"✅ Feito! {nome} tem agora {novo_total} compras.")

                # --- 2. MENSAGENS (TEXTO PADRÃO) ---
                # Podes editar o texto dentro das aspas abaixo como quiseres
                
                if novo_total == 1:
                    msg_texto = f"Ola {nome}! Seja bem-vindo a nossa Adega! Ativamos o seu Cartao Fidelidade. A cada compras voce acumula 1 ponto, ao completar as 10 você irá ganhar 50% de desconto. Agora você ja tem 1 ponto. Obrigado!"
                    texto_botao = "Enviar Boas-Vindas"

                elif novo_total < 9:
                    faltam = 10 - novo_total
                    msg_texto = f"Ola {nome}! Registramos mais uma compra no seu cartão fidelidade. Voce tem {novo_total} pontos. Faltam apenas {faltam} para o premio!"
                    texto_botao = f"Enviar Saldo ({novo_total}/10)"

                elif novo_total == 9:
                    msg_texto = f"Ola {nome}! Você acabou de completar 9 compras! Na sua PROXIMA compra você ganhará 50% DE DESCONTO. Cuida em aproveitar!"
                    st.warning("⚠️ ALERTA: FALTA 1 PARA O PRÉMIO!")
                    texto_botao = "AVISAR QUE FALTA 1"

                else: 
                    msg_texto = f"PARABENS {nome}! Voce completou 10 compras e ganhou 50% DE DESCONTO HOJE! O seu cartao sera reiniciado."
                    st.balloons()
                    texto_botao = "ENVIAR PREMIO AGORA"
                    
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. LINK WHATSAPP (Via API Oficial)
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://api.whatsapp.com/send?phone={telefone}&text={msg_link}"
                
                # 4. BOTÃO VERDE (HTML SIMPLES)
                st.markdown(f"""
                <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                    <div style="
                        background-color: #25D366;
                        color: white;
                        padding: 15px;
                        border-radius: 10px;
                        text-align: center;
                        font-weight: bold;
                        font-size: 18px;
                        margin-top: 20px;
                        display: block;
                        width: 100%;">
                        {texto_botao} 📲
                    </div>
                </a>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
