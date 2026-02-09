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
            with st.spinner('Gravando...'):
                # 1. LER DADOS
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                novo_total = 1
                if df.empty or nome not in df['nome'].values:
                    sheet.append_row([nome, telefone, 1])
                    st.toast(f"Novo cliente!")
                else:
                    indice = df[df['nome'] == nome].index[0]
                    linha_real = indice + 2 
                    compras_atuais = df.loc[indice, 'compras']
                    novo_total = int(compras_atuais) + 1
                    sheet.update_cell(linha_real, 3, novo_total)
                    st.toast(f"Compra somada!")

                st.success(f"✅ Feito! {nome} tem agora {novo_total} compras.")

                # --- 2. MENSAGENS COM EMOJIS REAIS ---
                # Aqui escrevemos como se fosse no WhatsApp mesmo
                
                if novo_total == 1:
                    msg_texto = f"""Olá, {nome}! Tudo bem? 👋😃

Seja muito bem-vindo(a) à nossa Adega! 🍷✨
Acabamos de ativar o seu Cartão Fidelidade.

📌 *Como funciona?*
A cada compra, você ganha 1 ponto. Juntou 10? Ganhou *50% DE DESCONTO*!

Você já começou com o pé direito e tem *1 ponto*. Obrigado pela preferência! 🚀"""
                    label_botao = "📲 Enviar Boas-Vindas"

                elif novo_total < 9:
                    faltam = 10 - novo_total
                    msg_texto = f"""Olá, {nome}! Que bom te ver de novo! 😍🍷

Registamos mais uma compra no seu fidelidade.
📊 *Status Atual:* {novo_total} pontos
🎯 *Faltam apenas:* {faltam} compras para o seu prémio!

Estamos te esperando para a próxima! 🥂"""
                    label_botao = f"📲 Atualizar Saldo ({novo_total}/10)"

                elif novo_total == 9:
                    msg_texto = f"""😱🔥 UAU!! Pare tudo, {nome}!

Você acabou de completar *9 compras*!
Isso significa que na sua PRÓXIMA visita, você ganha *50% DE DESCONTO*! 🎁💸

Não deixe para depois, venha logo aproveitar seu prémio! 🏃‍♂️💨🍷"""
                    st.warning("⚠️ ALERTA: FALTA 1 PARA O PRÉMIO!")
                    label_botao = "🚨 AVISAR URGENTE (FALTA 1)"

                else: 
                    msg_texto = f"""🏆🎉 PARABÉNS, {nome}!! Hoje é dia de festa! 🍾

Você é um cliente VIP e completou *10 compras*!
🎁 O seu prémio de *50% DE DESCONTO* está liberado para usar HOJE!

O seu cartão será reiniciado. Saúde! 🥂✨"""
                    st.balloons()
                    label_botao = "🏆 ENVIAR PRÉMIO AGORA"
                    
                    sheet.update_cell(linha_real, 3, 0) 

                # 3. LINK NATIVO (Sem HTML complicado)
                # Esta função prepara o texto para link
                texto_final = urllib.parse.quote(msg_texto)
                link_zap = f"https://wa.me/{telefone}?text={texto_final}"
                
                # Usamos o botão nativo do Streamlit (mais seguro contra erros de emoji)
                st.link_button(label_botao, link_zap)

        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
    
    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Por favor, preenche o nome e o telefone.")
