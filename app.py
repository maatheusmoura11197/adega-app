import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 
import re 
from datetime import datetime
import pytz # Para pegar o horário do Brasil

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

# --- FUNÇÕES ÚTEIS ---
def limpar_telefone(tel):
    """Remove tudo que não for número"""
    return re.sub(r'\D', '', tel)

def pegar_data_hora():
    """Pega a data e hora atual de Brasília"""
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

def gerar_mensagem_zap(nome_cliente, total_compras):
    """Gera o texto carismático e formatado"""
    if total_compras == 1:
        l1 = f"Olá, {nome_cliente}! Que alegria ter você aqui na nossa Adega! 🍷✨"
        l2 = "Seja muito bem-vindo(a)! Já começamos com o pé direito o seu cartão fidelidade."
        l3 = "*Status Atual:* 1 ponto (O início da jornada!)"
        l4 = "*Faltam apenas:* 9 compras para o seu super desconto!"
        l5 = "Muito obrigado pela preferência! 🚀"
        msg = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
        btn = "Enviar Boas-Vindas 🎉"

    elif total_compras < 9:
        faltam = 10 - total_compras
        l1 = f"Fala, {nome_cliente}! Tudo ótimo? Que bom te ver de novo! 😍🍷"
        l2 = "Ficamos muito felizes com a sua visita! Já registramos aqui:"
        l3 = f"*Status Atual:* {total_compras} pontos"
        l4 = f"*Faltam apenas:* {faltam} compras para o prémio!"
        l5 = "O prémio está cada vez mais perto! Até a próxima! 🥂"
        msg = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
        btn = f"Enviar Saldo ({total_compras}/10) 📲"

    elif total_compras == 9:
        l1 = f"UAU, {nome_cliente}!! Pare tudo! 😱🔥"
        l2 = "Você está a um passo da glória! Olha só isso:"
        l3 = "*Status Atual:* 9 pontos"
        l4 = "*Faltam apenas:* 1 compra (É A ÚLTIMA!)"
        l5 = "Na sua PRÓXIMA visita, o desconto de 50% é SEU! Vem logo! 🏃💨"
        msg = f"{l1}\n\n{l2}\n{l3}\n{l4}\n\n{l5}"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"

    else: 
        l1 = f"PARABÉNS, {nome_cliente}!! HOJE É DIA DE FESTA! 🎉🍾"
        l2 = "Você é nosso cliente VIP e completou a cartela!"
        l3 = "*Status Atual:* 10 pontos (COMPLETO)"
        l4 = "*Prémio:* 50% DE DESCONTO LIBERADO AGORA!"
        l5 = "Muito obrigado pela parceria! Vamos reiniciar seu cartão para ganhar de novo! 🥂✨"
        msg = f"{l1}\n\n{l2}\n{l3}\n\n{l4}\n\n{l5}"
        btn = "🏆 ENVIAR PRÉMIO AGORA"

    return msg, btn

# --- ESTADO DA SESSÃO (MEMÓRIA) ---
if 'confirmacao' not in st.session_state:
    st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state:
    st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state:
    st.session_state.sucesso_msg = None

# --- CARREGAR DADOS INICIAIS ---
if conexao:
    todos_dados = sheet.get_all_records()
    df = pd.DataFrame(todos_dados)
else:
    df = pd.DataFrame()

# ==========================================
# 📊 OPÇÃO 4: O PAINEL DO PATRÃO (DASHBOARD)
# ==========================================
if not df.empty and conexao:
    st.markdown("### 📊 Visão Geral da Adega")
    col1, col2, col3 = st.columns(3)
    
    total_clientes = len(df)
    # Tenta somar as compras, se a coluna existir e tiver numeros
    try:
        total_pontos = df['compras'].sum()
        # Clientes VIPs (com 9 ou 10 pontos)
        total_vip = len(df[df['compras'] >= 9])
    except:
        total_pontos = 0
        total_vip = 0

    col1.metric("Clientes", total_clientes)
    col3.metric("Quase Ganhando", total_vip)
    st.divider()

# --- INTERFACE DE REGISTRO ---
st.subheader("📝 Novo Registro")
nome = st.text_input("Nome do Cliente").strip().upper()
telefone_input = st.text_input("Telefone", value="+55 ", help="Apenas digite, eu arrumo os números.")
telefone_limpo = limpar_telefone(telefone_input)

# --- BOTÃO 1: VERIFICAR ---
if st.button("Verificar e Registar", type="primary"):
    if nome and telefone_limpo and conexao:
        st.session_state.sucesso_msg = None 
        
        # Converte coluna telefone para texto para comparar
        if not df.empty:
            df['telefone'] = df['telefone'].astype(str)
            cliente_encontrado = df[df['telefone'] == telefone_limpo]
        else:
            cliente_encontrado = pd.DataFrame()

        if not cliente_encontrado.empty:
            # CASO 1: JÁ EXISTE -> Confirmação
            dados_existentes = cliente_encontrado.iloc[0]
            idx = cliente_encontrado.index[0]
            
            st.session_state.dados_temp = {
                'indice': idx,
                'nome_antigo': dados_existentes['nome'],
                'nome_novo': nome,
                'telefone': telefone_limpo,
                'compras_atuais': dados_existentes['compras']
            }
            st.session_state.confirmacao = True
            st.rerun()

        else:
            # CASO 2: NOVO -> Grava direto com DATA (OPÇÃO 2)
            data_hoje = pegar_data_hora()
            
            # Adicionamos a data na 4ª coluna
            sheet.append_row([nome, telefone_limpo, 1, data_hoje])
            
            msg, btn_txt = gerar_mensagem_zap(nome, 1)
            msg_link = urllib.parse.quote(msg)
            link_zap = f"https://api.whatsapp.com/send?phone={telefone_limpo}&text={msg_link}"
            
            st.session_state.sucesso_msg = {
                'texto': f"🎉 Novo cliente {nome} cadastrado em {data_hoje}!",
                'link': link_zap,
                'btn_label': btn_txt
            }
            st.rerun()

    elif not conexao:
        st.error("Sem conexão com o Google.")
    else:
        st.warning("Preencha o nome e o telefone.")

# --- ZONA DE CONFIRMAÇÃO ---
if st.session_state.confirmacao:
    dados = st.session_state.dados_temp
    
    st.divider()
    st.warning(f"🚨 **CLIENTE JÁ CADASTRADO!**")
    st.write(f"📞 Telefone: **{dados['telefone']}**")
    st.write(f"👤 Nome na Planilha: **{dados['nome_antigo']}**")
    st.info("Deseja atualizar e somar a compra?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ SIM, Atualizar"):
            with st.spinner('Atualizando...'):
                linha_real = dados['indice'] + 2
                novo_total = int(dados['compras_atuais']) + 1
                data_hoje = pegar_data_hora() # Pega data atual
                
                # Atualiza Nome, Compras e DATA (OPÇÃO 2)
                sheet.update_cell(linha_real, 1, dados['nome_novo']) 
                sheet.update_cell(linha_real, 3, novo_total)
                sheet.update_cell(linha_real, 4, data_hoje) # Atualiza a coluna 4
                
                msg, btn_txt = gerar_mensagem_zap(dados['nome_novo'], novo_total)
                msg_link = urllib.parse.quote(msg)
                link_zap = f"https://api.whatsapp.com/send?phone={dados['telefone']}&text={msg_link}"
                
                st.session_state.sucesso_msg = {
                    'texto': f"✅ Atualizado! {dados['nome_novo']} agora tem {novo_total} compras. (Última: {data_hoje})",
                    'link': link_zap,
                    'btn_label': btn_txt,
                    'salao_festa': (novo_total >= 10)
                }
                
                st.session_state.confirmacao = False
                st.rerun()

    with col2:
        if st.button("❌ Cancelar"):
            st.session_state.confirmacao = False
            st.rerun()

# --- ZONA DE SUCESSO ---
if st.session_state.sucesso_msg:
    resultado = st.session_state.sucesso_msg
    st.divider()
    st.success(resultado['texto'])
    
    if resultado.get('salao_festa'):
        st.balloons()

    st.markdown(f"""
    <a href="{resultado['link']}" target="_blank" style="text-decoration: none;">
        <div style="
            background-color: #25D366;
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            margin-top: 20px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.2);
            display: block;
            width: 100%;">
            {resultado['btn_label']}
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Novo Atendimento"):
        st.session_state.sucesso_msg = None
        st.rerun()
