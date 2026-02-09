import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

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
            with st.spinner('A processar...'):
                # 1. Ler e Processar Dados
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                novo_total = 1
                if df.empty or nome not in df['nome'].values:
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"✨ Bem-vindo(a) {nome}!")
                else:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"🚀 Mais uma compra registada!")

                st.success(f"✅ Feito! {nome} tem agora {novo_total} compras.")

                # --- 2. MENSAGENS DIVERTIDAS E HUMANIZADAS ---
                # O segredo: usei \n para pular linha e emojis variados
                
                # CASO 1: PRIMEIRA COMPRA
                if novo_total == 1:
                    msg_texto = (
                        f"Olá, {nome}! Tudo bem? 👋😃\n\n"
                        f"Seja muito bem-vindo(a) à nossa Adega! 🍷✨\n"
                        f"Acabamos de ativar o seu Cartão Fidelidade.\n\n"
                        f"📌 *Como funciona?*\n"
                        f"A cada compra, você ganha 1 ponto. Juntou 10? Ganhou **50% DE DESCONTO**!\n\n"
                        f"Você já começou com o pé direito e tem **1 ponto**. Obrigado pela preferência! 🚀"
                    )
                    aviso_botao = "📲 Enviar Boas-Vindas"

                # CASO 2: PROGRESSO (2 a 8)
                elif novo_total < 9:
                    faltam = 10 - novo_total
                    msg_texto = (
                        f"Olá, {nome}! Que bom te ver de novo! 😍🍷\n\n"
                        f"Passando para avisar que registamos mais uma compra no seu fidelidade.\n"
                        f"📊 **Status Atual:** {novo_total} pontos\n"
                        f"🎯 **Faltam apenas:** {faltam} compras para o seu prémio!\n\n"
                        f"Estamos te esperando para a próxima! 🥂"
                    )
                    aviso_botao = f"📲 Atualizar Saldo ({novo_total}/10)"

                # CASO 3: QUASE LÁ (9)
                elif novo_total == 9:
                    msg_texto = (
                        f"😱🔥 UAU!! Pare tudo, {nome}!\n\n"
                        f"Você acabou de completar **9 compras**!\n"
                        f"Isso significa que na sua PRÓXIMA visita, você ganha **50% DE DESCONTO**! 🎁💸\n\n"
                        f"Não deixe para depois, venha logo aproveitar seu prémio! 🏃‍♂️💨🍷"
                    )
                    st.warning("⚠️ ALERTA: O cliente está a 1 passo do prémio!")
                    aviso_botao = "🚨 AVISAR URGENTE (FALTA 1)"

                # CASO 4: PRÉMIO (10 ou mais)
                else: 
                    msg_texto = (
                        f"🏆🎉 PARABÉNS, {nome}!! Hoje é dia de festa! 🍾\n\n"
                        f"Você é um cliente VIP e completou **10 compras**!\n"
                        f"🎁 O seu prémio de **50% DE DESCONTO** está liberado para usar HOJE!\n\n"
                        f"O seu cartão será reiniciado para você começar a ganhar de novo. Saúde! 🥂✨"
                    )
                    st.balloons()
                    aviso_botao = "🏆 ENVIAR PRÉMIO AGORA!"
                    
                    # Reiniciar contagem na planilha
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. TRADUÇÃO PERFEITA PARA O LINK (Correção do )
                # O 'quote' garante que espaços virem %20 e emojis virem código
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://wa.me/{telefone}?text={msg_link}"
                
                # Botão com estilo moderno
                st.markdown(f"""
                <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                    <button style="
                        width: 100%;
                        background-color: #25D366; 
                        color: white; 
                        padding: 18px; 
                        border-radius: 15px; 
                        border: none; 
                        font-size: 20px; 
                        font-weight: bold; 
                        box-shadow: 0px 5px 15px rgba(37, 211, 102, 0.4);
                        transition: all 0.3s ease;
                        cursor: pointer;">
                        {aviso_botao} 💬
                    </button>
                </a>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
