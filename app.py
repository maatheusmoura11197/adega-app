import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Controle de fidelidades", page_icon=")
st.title("🍷 Controle de Fidelidades")

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
            with st.spinner('A processar com carinho...'):
                # 1. LER DADOS
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                novo_total = 1
                if df.empty or nome not in df['nome'].values:
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"🎉 Novo cliente na casa!")
                else:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"🍷 Compra registada com sucesso!")

                st.success(f"✅ Maravilha! {nome} agora tem {novo_total} compras.")

                # --- 2. MENSAGENS CHEIAS DE CARISMA ---
                # Cada linha (l1, l2...) é uma parte da mensagem para garantir a quebra
                
                if novo_total == 1:
                    l1 = f"Olá, {nome}! Que alegria ter você aqui na nossa Adega!"
                    l2 = "Seja muito bem-vindo(a)! Já começamos com o pé direito o seu fidelidade."
                    l3 = "*Status Atual:* 1 ponto (O início da jornada!)"
                    l4 = "*Faltam apenas:* 9 compras para o seu super desconto!"
                    l5 = "Muito obrigado pela preferência!"
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    texto_botao = "Enviar Boas-Vindas 🎉"

                elif novo_total < 9:
                    faltam = 10 - novo_total
                    
                    l1 = f"Fala, {nome}! Tudo ótimo? Que bom te ver de novo!"
                    l2 = "Ficamos muito felizes com a sua visita! Já registramos aqui:"
                    l3 = f"*Status Atual:* {novo_total} pontos"
                    l4 = f"*Faltam apenas:* {faltam} compras para o prémio!"
                    l5 = "O prémio está cada vez mais perto! Até a próxima!"
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    texto_botao = f"Enviar Saldo ({novo_total}/10) 📲"

                elif novo_total == 9:
                    l1 = f"UAU, {nome}!! Nunca esteve tão perto!"
                    l2 = "Você está a um passo da glória! Olha só isso:"
                    l3 = "*Status Atual:* 9 pontos"
                    l4 = "*Faltam apenas:* 1 compra (É PRA FECHAR O CARTÃO!)"
                    l5 = "Na sua PRÓXIMA compra, o desconto de 50% é SEU! já cuida em utiliza-lo! 🏃💨"
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    st.warning("⚠️ ALERTA: CLIENTE ESTÁ A 1 PASSO DO PRÉMIO!")
                    texto_botao = "🚨 AVISAR URGENTE (FALTA 1)"

                else: 
                    l1 = f"PARABÉNS, {nome}!! HOJE É DIA DE FESTA! 🎉🍾"
                    l2 = "Você é nosso cliente VIP e completou a cartela!"
                    l3 = "*Status Atual:* 10 pontos (COMPLETO)"
                    l4 = "*Prémio:* 50% DE DESCONTO LIBERADO AGORA!"
                    l5 = "Muito obrigado pela parceria! Vamos reiniciar seu cartão para ganhar de novo! 🥂✨"
                    16 = "Qual item você deseja usar o seu desconto"
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n\n{l4}\n\n{l5}"
                    st.balloons()
                    texto_botao = "🏆 ENVIAR PRÉMIO AGORA"
                    
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. GERAR LINK
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://api.whatsapp.com/send?phone={telefone}&text={msg_link}"
                
                # 4. BOTÃO VERDE
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
                        {texto_botao}
                    </div>
                </a>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
