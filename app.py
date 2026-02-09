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

                # --- 2. MENSAGENS FORMATADAS ---
                # Usamos *texto* para negrito e \n para pular linha
                
                if novo_total == 1:
                    msg_texto = f"Olá, {nome}! Seja bem-vindo(a)!\n\nAcabamos de iniciar o seu fidelidade.\n *Status Atual:* 1 ponto\n *Faltam apenas:* 9 compras para o seu prémio!\n\nObrigado pela preferência!"
                    texto_botao = "Enviar Boas-Vindas"

                elif novo_total < 9:
                    faltam = 10 - novo_total
                    # AQUI ESTÁ A FORMATAÇÃO EXATA QUE PEDISTE
                    msg_texto = f"Olá, {nome}! Que bom te ver de novo!\n\nPassando para avisar que registamos mais uma compra no seu fidelidade.\n *Status Atual:* {novo_total} pontos\n *Faltam apenas:* {faltam} compras para o seu prémio!\n\nEstamos te esperando para a próxima!"
                    texto_botao = f"Enviar Saldo ({novo_total}/10)"

                elif novo_total == 9:
                    msg_texto = f"Olá, {nome}! Falta muito pouco!\n\nPassando para avisar que completou 9 compras.\n *Status Atual:* 9 pontos\n *Faltam apenas:* 1 compra\n\nNa sua PRÓXIMA visita você ganha *50% DE DESCONTO*!"
                    st.warning("⚠️ ALERTA: FALTA 1 PARA O PRÉMIO!")
                    texto_botao = "AVISAR QUE FALTA 1"

                else: 
                    msg_texto = f"PARABÉNS {nome}! Você completou o fidelidade!\n\n *Status Atual:* 10 pontos (COMPLETO)\n *Prémio:* 50% DE DESCONTO LIBERADO HOJE!\n\nO seu cartão será reiniciado agora."
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
