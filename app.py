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

if st.button("Registar Compra"):
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

                # --- 2. MENSAGENS COM EMOJIS (CÓDIGO SEGURO) ---
                # Usamos códigos \U... para garantir que funcionam em qualquer telemóvel
                
                # Emojis Definidos:
                # 🍷 = \U0001F377 | ✨ = \u2728 | 🚀 = \U0001F680
                # 🎉 = \U0001F389 | 🥂 = \U0001F942 | 👋 = \U0001F44B
                # 😱 = \U0001F631 | 🏃 = \U0001F3C3 | 📊 = \U0001F4CA
                
                # CASO 1: PRIMEIRA COMPRA
                if novo_total == 1:
                    msg_texto = (
                        f"Olá, {nome}! Tudo bem? \U0001F44B\n\n"
                        f"Seja muito bem-vindo(a) à nossa Adega! \U0001F377\u2728\n"
                        f"Acabamos de ativar o seu Cartão Fidelidade.\n\n"
                        f"\U0001F4CC *Como funciona?*\n"
                        f"A cada compra, você ganha 1 ponto. Juntou 10? Ganhou **50% DE DESCONTO**!\n\n"
                        f"Você já começou com o pé direito e tem **1 ponto**. Obrigado pela preferência! \U0001F680"
                    )
                    aviso_botao = "📲 Enviar Boas-Vindas"

                # CASO 2: PROGRESSO (2 a 8)
                elif novo_total < 9:
                    faltam = 10 - novo_total
                    msg_texto = (
                        f"Olá, {nome}! Que bom te ver de novo! \U0001F60D\U0001F377\n\n"
                        f"Passando para avisar que registramos mais uma compra no seu fidelidade.\n"
                        f"\U0001F4CA **Status Atual:** {novo_total} pontos\n"
                        f"\U0001F3AF **Faltam apenas:** {faltam} compras para o seu prémio!\n\n"
                        f"Estamos te esperando para a próxima! \U0001F942"
                    )
                    aviso_botao = f"📲 Atualizar Saldo ({novo_total}/10)"

                # CASO 3: QUASE LÁ (9)
                elif novo_total == 9:
                    msg_texto = (
                        f"\U0001F631\U0001F525 UAU!! Pare tudo, {nome}!\n\n"
                        f"Você acabou de completar **9 compras**!\n"
                        f"Isso significa que na sua PRÓXIMA visita, você ganha **50% DE DESCONTO**! \U0001F381\U0001F4B8\n\n"
                        f"Não deixe para depois, venha logo aproveitar seu prémio! \U0001F3C3\U0001F4A8\U0001F377"
                    )
                    st.warning("⚠️ ALERTA: O cliente está a 1 passo do prémio!")
                    aviso_botao = "🚨 AVISAR URGENTE (FALTA 1)"

                # CASO 4: PRÉMIO (10 ou mais)
                else: 
                    msg_texto = (
                        f"\U0001F3C6\U0001F389 PARABÉNS, {nome}!! Hoje é dia de festa! \U0001F37E\n\n"
                        f"Você é um cliente VIP e completou **10 compras**!\n"
                        f"\U0001F381 O seu prémio de **50% DE DESCONTO** está liberado para usar HOJE!\n\n"
                        f"O seu cartão será reiniciado para você começar a ganhar de novo. Saúde! \U0001F942\u2728"
                    )
                    st.balloons()
                    aviso_botao = "🏆 ENVIAR PRÉMIO AGORA!"
                    
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. GERAR LINK (AQUI ESTÁ O SEGREDO)
                # O quote garante que os códigos acima virem emojis reais no link
                msg_link = urllib.parse.quote(msg_texto)
                link_zap = f"https://wa.me/{telefone}?text={msg_link}"
                
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
