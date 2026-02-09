import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
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

                # --- 2. CONSTRUÇÃO DA MENSAGEM (LINHA A LINHA) ---
                # Aqui garantimos que cada frase fica na sua linha
                
                if novo_total == 1:
                    l1 = f"Olá, {nome}! Seja bem-vindo(a)!"
                    l2 = "Acabamos de iniciar o seu fidelidade."
                    l3 = "*Status Atual:* 1 ponto"
                    l4 = "*Faltam apenas:* 9 compras para o seu prémio!"
                    l5 = "Obrigado pela preferência!"
                    
                    # Junta tudo com \n (Enter)
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    texto_botao = "Enviar Boas-Vindas"

                elif novo_total < 9:
                    faltam = 10 - novo_total
                    
                    l1 = f"Olá, {nome}! Que bom te ver de novo!"
                    l2 = "Passando para avisar que registamos mais uma compra."
                    # AQUI ESTÁ A LISTA UM EMBAIXO DO OUTRO
                    l3 = f"*Status Atual:* {novo_total} pontos"
                    l4 = f"*Faltam apenas:* {faltam} compras para o seu prémio!"
                    l5 = "Estamos te esperando para a próxima!"
                    
                    # O segredo: \n entre l3 e l4 garante que ficam separados
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    texto_botao = f"Enviar Saldo ({novo_total}/10)"

                elif novo_total == 9:
                    l1 = f"Olá, {nome}! Falta muito pouco!"
                    l2 = "Passando para avisar que completou 9 compras."
                    l3 = "*Status Atual:* 9 pontos"
                    l4 = "*Faltam apenas:* 1 compra"
                    l5 = "Na sua PRÓXIMA visita você ganha *50% DE DESCONTO*!"
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
                    st.warning("⚠️ ALERTA: FALTA 1 PARA O PRÉMIO!")
                    texto_botao = "AVISAR QUE FALTA 1"

                else: 
                    l1 = f"PARABÉNS {nome}! Você completou o fidelidade!"
                    l2 = "*Status Atual:* 10 pontos (COMPLETO)"
                    l3 = "*Prémio:* 50% DE DESCONTO LIBERADO HOJE!"
                    l4 = "O seu cartão será reiniciado agora."
                    
                    msg_texto = f"{l1}\n\n{l2}\n{l3}\n\n{l4}"
                    st.balloons()
                    texto_botao = "ENVIAR PRÉMIO AGORA"
                    
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
