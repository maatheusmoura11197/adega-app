import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse # Para arranjar os acentos no link do WhatsApp

# Configuração da página
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

# --- O APLICATIVO ---
nome = st.text_input("Nome do Cliente").strip().upper()
telefone = st.text_input("Telefone (com DDD, apenas números)").strip()

if st.button("Registar Compra"):
    if nome and telefone and conexao:
        try:
            with st.spinner('A registar na nuvem...'):
                # 1. Ler e Processar Dados
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                novo_total = 1
                if df.empty or nome not in df['nome'].values:
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"🆕 Cliente cadastrado!")
                else:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"🔄 Compra somada!")

                st.success(f"✅ Feito! {nome} tem agora {novo_total} compras.")

                # --- 2. INTELIGÊNCIA DA MENSAGEM DO WHATSAPP ---
                # Aqui definimos qual mensagem enviar dependendo do número de compras
                
                if novo_total < 9:
                    faltam = 10 - novo_total
                    msg_texto = f"Olá {nome}! 🍷 Obrigado pela preferência! Você já completou {novo_total} compras no nosso cartão fidelidade. Faltam apenas {faltam} para ganhar 50% de desconto!"
                    cor_botao = "primary" # Botão normal
                    aviso = f"📲 Enviar comprovante ({novo_total}/10)"

                elif novo_total == 9:
                    msg_texto = f"Olá {nome}! 🍷 Uau! Você chegou a 9 compras. Na sua PRÓXIMA visita, você ganha 50% de desconto! Não perca!"
                    st.warning("⚠️ O cliente está a 1 passo do prémio!")
                    cor_botao = "primary"
                    aviso = "📲 Avisar que falta 1!"

                else: # 10 ou mais
                    msg_texto = f"Olá {nome}! 🎉 Parabéns! Completou 10 compras e ganhou 50% de desconto HOJE! O seu cartão fidelidade será reiniciado."
                    st.balloons()
                    cor_botao = "primary" # O Streamlit não deixa mudar cor facilmente, mas o destaque é o balão
                    aviso = "🎁 ENVIAR PRÉMIO AGORA!"
                    
                    # Zerar a contagem na planilha (opcional, se quiseres manter o ciclo)
                    # sheet.update_cell(linha_real, 3, 0) 

                # 3. Criar o Link e Mostrar o Botão
                # Codifica a mensagem para aceitar espaços e acentos no link
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://wa.me/{telefone}?text={msg_link}"
                
                st.markdown(f"""
                <a href="{link_zap}" target="_blank">
                    <button style="
                        width: 100%;
                        background-color: #25D366;
                        color: white;
                        padding: 15px;
                        border: none;
                        border-radius: 10px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;">
                        {aviso} 
                    </button>
                </a>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
