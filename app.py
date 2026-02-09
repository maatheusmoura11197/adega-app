import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse # Ferramenta essencial para os emojis funcionarem no link

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

                st.success(f"✅ Sucesso! {nome} tem agora {novo_total} compras.")

                # --- 2. INTELIGÊNCIA DA MENSAGEM (Com Emojis Bonitos) ---
                
                if novo_total < 5:
                    # Mensagem para quem está no começo
                    faltam = 10 - novo_total
                    msg_texto = f"Olá {nome}! 🍇 Obrigado pela preferência! Acabamos de registar a sua {novo_total}ª compra no Cartão Fidelidade. Faltam apenas {faltam} para o seu prémio de 50%! 🚀🍷"
                    aviso_botao = f"📲 Enviar Saldo ({novo_total}/10)"

                elif novo_total < 9:
                    # Mensagem para quem está na metade
                    faltam = 10 - novo_total
                    msg_texto = f"Olá {nome}! 🥂 O seu cartão fidelidade está a encher! Já tem {novo_total} compras. Faltam só {faltam} para garantir os 50% de desconto. Estamos à sua espera! 🧀🍷"
                    aviso_botao = f"📲 Avisar Cliente ({novo_total}/10)"

                elif novo_total == 9:
                    # Mensagem de quase lá
                    msg_texto = f"Olá {nome}! 😱 Uau! Atenção: Você completou 9 compras! A sua PRÓXIMA visita vale 50% de DESCONTO. Venha logo aproveitar! 🏃‍♂️💨🍷"
                    st.warning("⚠️ ALERTA: O cliente está a 1 passo do prémio!")
                    aviso_botao = "🚨 AVISAR QUE FALTA 1!"

                else: # 10 ou mais (Ciclo completado)
                    msg_texto = f"PARABÉNS {nome}! 🎉🍾 Você é um cliente VIP! Completou 10 compras e ganhou 50% de DESCONTO HOJE! O seu cartão será reiniciado para ganhar de novo. Saúde! 🥂"
                    st.balloons()
                    aviso_botao = "🏆 ENVIAR PRÉMIO AGORA!"
                    
                    # Opcional: Zerar a contagem na planilha automaticamente
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. Criar o Link Corrigido (Sem o erro do )
                # O comando 'quote' transforma os emojis em códigos que o WhatsApp entende
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://wa.me/{telefone}?text={msg_link}"
                
                # Botão verde bonito
                st.markdown(f"""
                <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                    <button style="
                        width: 100%;
                        background-color: #25D366; 
                        color: white; 
                        padding: 15px; 
                        border-radius: 12px; 
                        border: none; 
                        font-size: 18px; 
                        font-weight: bold; 
                        box-shadow: 0px 4px 6px rgba(0,0,0,0.2);
                        cursor: pointer;">
                        {aviso_botao}
                    </button>
                </a>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
