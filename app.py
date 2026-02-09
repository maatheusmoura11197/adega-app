import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 
import re 

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

# --- ESTADO DA SESSÃO (Para controlar a confirmação) ---
if 'confirmacao_pendente' not in st.session_state:
    st.session_state.confirmacao_pendente = False
if 'dados_duplicados' not in st.session_state:
    st.session_state.dados_duplicados = {}

# --- DADOS DO CLIENTE ---
nome = st.text_input("Nome do Cliente").strip().upper()
telefone_input = st.text_input("Telefone (DDD + Número)", value="+55 ", help="Ex: +55 88 99995-7161")

# Limpeza do telefone
telefone_limpo = re.sub(r'\D', '', telefone_input) 

# --- FUNÇÃO PARA PROCESSAR A MENSAGEM ---
def gerar_mensagem_zap(nome_cliente, total_compras):
    # Lógica das mensagens carismáticas
    if total_compras == 1:
        l1 = f"Olá, {nome_cliente}! Que alegria ter você aqui na nossa Adega!"
        l2 = "Seja muito bem-vindo(a)! Já começamos com o pé direito o seu fidelidade."
        l3 = "*Status Atual:* 1 ponto (O início da jornada!)"
        l4 = "*Faltam apenas:* 9 compras para o seu super desconto!"
        l5 = "Muito obrigado pela preferência!"
        texto_botao = "Enviar Boas-Vindas 🎉"
        msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"

    elif total_compras < 9:
        faltam = 10 - total_compras
        l1 = f"Fala, {nome_cliente}! Tudo ótimo? Que bom te ver de novo!"
        l2 = "Ficamos muito felizes com a sua visita! Já registramos aqui:"
        l3 = f"*Status Atual:* {total_compras} pontos"
        l4 = f"*Faltam apenas:* {faltam} compras para o prémio!"
        l5 = "O prémio está cada vez mais perto! Até a próxima!"
        texto_botao = f"Enviar Saldo ({total_compras}/10) 📲"
        msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"

    elif total_compras == 9:
        l1 = f"UAU, {nome_cliente}!! Desconto exclusivo tá muito perto!"
        l2 = "Você está a um passo da glória! Olha só isso:"
        l3 = "*Status Atual:* 9 pontos"
        l4 = "*Faltam apenas:* 1 compra (É A ÚLTIMA!)"
        l5 = "Na sua PRÓXIMA visita, o desconto de 50% é SEU! Vem logo!"
        st.warning("⚠️ ALERTA: CLIENTE ESTÁ A 1 PASSO DO PRÉMIO!")
        texto_botao = "🚨 AVISAR URGENTE (FALTA 1)"
        msg_texto = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"

    else: 
        l1 = f"PARABÉNS, {nome_cliente}!! HOJE É DIA DE FESTA!"
        l2 = "Você é nosso cliente VIP e completou a cartela!"
        l3 = "*Status Atual:* 10 pontos (COMPLETO)"
        l4 = "*Prémio:* 50% DE DESCONTO LIBERADO AGORA, qual item deseja ter o desconto"
        l5 = "Muito obrigado pela parceria! Vamos reiniciar seu cartão para ganhar de novo! 🥂✨"
        st.balloons()
        texto_botao = "🏆 ENVIAR PRÉMIO AGORA"
        msg_texto = f"{l1}\n\n{l2}\n{l3}\n\n{l4}\n\n{l5}"

    return msg_texto, texto_botao

# --- BOTÃO PRINCIPAL ---
if st.button("Verificar e Registar", type="primary"):
    if nome and telefone_limpo and conexao:
        # 1. Baixar dados para verificar
        todos_dados = sheet.get_all_records()
        df = pd.DataFrame(todos_dados)

        # Converter coluna telefone para string para garantir a busca
        if not df.empty:
            df['telefone'] = df['telefone'].astype(str)
            
            # Verifica se o telefone já existe
            cliente_existente = df[df['telefone'] == telefone_limpo]
            
            if not cliente_existente.empty:
                # OPA! Telefone já existe. Vamos pedir confirmação.
                nome_antigo = cliente_existente.iloc[0]['nome']
                idx = cliente_existente.index[0]
                
                # Guardamos os dados na memória (sessão)
                st.session_state.confirmacao_pendente = True
                st.session_state.dados_duplicados = {
                    'indice': idx,
                    'nome_antigo': nome_antigo,
                    'nome_novo': nome,
                    'telefone': telefone_limpo
                }
                # Forçamos o rerun para mostrar o aviso fora deste bloco
                st.rerun()
            
            else:
                # Telefone NOVO -> Segue vida normal
                with st.spinner('A registar novo cliente...'):
                    sheet.append_row([nome, telefone_limpo, 1])
                    st.toast("🎉 Novo cliente registado!")
                    st.success(f"✅ Feito! {nome} tem agora 1 compra.")
                    
                    # Gerar Link
                    msg, btn = gerar_mensagem_zap(nome, 1)
                    msg_link = urllib.parse.quote(msg)
                    link = f"https://api.whatsapp.com/send?phone={telefone_limpo}&text={msg_link}"
                    
                    st.markdown(f"""<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;margin-top:20px;">{btn}</div></a>""", unsafe_allow_html=True)

        else:
            # Planilha vazia -> Adiciona direto
            sheet.append_row([nome, telefone_limpo, 1])
            st.success(f"✅ Primeiro cliente registado!")

    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Preencha nome e telefone.")

# --- BLOCO DE CONFIRMAÇÃO (Aparece se o telefone já existir) ---
if st.session_state.confirmacao_pendente:
    dados = st.session_state.dados_duplicados
    nome_velho = dados['nome_antigo']
    nome_novo = dados['nome_novo']
    
    st.warning(f"🚨 **ATENÇÃO:** O telefone {dados['telefone']} já está cadastrado para **{nome_velho}**.")
    st.info(f"Você digitou o nome: **{nome_novo}**.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Sim, Atualizar Nome e Somar Compra"):
            with st.spinner('A atualizar cadastro...'):
                todos_dados = sheet.get_all_records()
                df = pd.DataFrame(todos_dados)
                
                # Pegar linha correta (Google Sheets começa do 2)
                linha_real = dados['indice'] + 2
                
                # 1. Atualizar Nome (caso tenha mudado)
                sheet.update_cell(linha_real, 1, nome_novo)
                
                # 2. Somar Compra
                compras_atuais = df.loc[dados['indice'], 'compras']
                novo_total = int(compras_atuais) + 1
                sheet.update_cell(linha_real, 3, novo_total)
                
                # Se completou o ciclo, zera (opcional)
                if novo_total >= 10:
                     sheet.update_cell(linha_real, 3, 0)

                st.success(f"✅ Cadastro atualizado! {nome_novo} agora tem {novo_total} compras.")
                
                # Gerar Link Zap
                msg, btn = gerar_mensagem_zap(nome_novo, novo_total)
                msg_link = urllib.parse.quote(msg)
                link = f"https://api.whatsapp.com/send?phone={dados['telefone']}&text={msg_link}"
                st.markdown(f"""<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;margin-top:20px;">{btn}</div></a>""", unsafe_allow_html=True)
                
                # Limpar sessão
                st.session_state.confirmacao_pendente = False
                
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state.confirmacao_pendente = False
            st.rerun()
