import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 
import re 
from datetime import datetime
import pytz 
import time 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Registro de Fidelidade", page_icon="🤑", layout="centered")

# --- 🔒 BLOQUEIO VISUAL (AJUSTADO PARA CELULAR) ---
# AQUI ESTAVA O PROBLEMA: Removemos o bloqueio do header para a setinha do menu aparecer
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;} /* Esconde os 3 pontinhos */
            footer {visibility: hidden;}    /* Esconde o rodapé */
            
            /* Animação do Brinde */
            @keyframes bounce {
                0% { transform: scale(1); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
            .brinde {
                font-size: 80px;
                animation: bounce 1s infinite;
                text-align: center;
                display: block;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 🔐 SISTEMA DE LOGIN (ESTÁVEL)
# ==========================================
SENHA_DO_SISTEMA = "adega123"  
TEMPO_LIMITE_MINUTOS = 30

# Inicializa variáveis
if 'logado' not in st.session_state: st.session_state.logado = False
if 'validando' not in st.session_state: st.session_state.validando = False
if 'ultima_atividade' not in st.session_state: st.session_state.ultima_atividade = time.time()

def verificar_sessao():
    """Verifica inatividade"""
    if st.session_state.logado:
        agora = time.time()
        tempo_passado = agora - st.session_state.ultima_atividade
        if tempo_passado > (TEMPO_LIMITE_MINUTOS * 60):
            st.session_state.logado = False
            st.error("⏳ Sessão expirada. Entre novamente.")
            return False
        st.session_state.ultima_atividade = agora
        return True
    return False

# --- LÓGICA DO LOGIN ---
if not st.session_state.logado:
    if st.session_state.validando:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="brinde">🍻</div>', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Abrindo a Adega...</h3>", unsafe_allow_html=True)
        time.sleep(2.5)
        st.session_state.logado = True
        st.session_state.validando = False
        st.session_state.ultima_atividade = time.time()
        st.rerun()
    else:
        st.title("🔒 Adega do Barão")
        st.markdown("Acesso Restrito ao Sistema")
        with st.form("login_form"):
            senha_digitada = st.text_input("Digite a senha:", type="password")
            entrar_btn = st.form_submit_button("ENTRAR", type="primary")
            if entrar_btn:
                if senha_digitada == SENHA_DO_SISTEMA:
                    st.session_state.validando = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        st.stop()

if not verificar_sessao():
    st.stop()

# ==========================================
# 🍻 O SISTEMA COMEÇA AQUI
# ==========================================

# CABEÇALHO COM BOTÃO DE SAIR (FÁCIL ACESSO NO CELULAR)
col_tit, col_sair = st.columns([0.8, 0.2])
with col_tit:
    st.title("🍻 Adega do Barão")
with col_sair:
    st.markdown("<br>", unsafe_allow_html=True) # Espaço para alinhar
    if st.button("Sair", type="secondary"):
        st.session_state.logado = False
        st.rerun()

# --- 🔗 LINK DA SUA PLANILHA ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/191D0UIDvwDJPWRtp_0cBFS9rWaq6CkSj5ET_1HO2sLI/edit?usp=sharing" 

# --- CONEXÃO COM O GOOGLE SHEETS ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet_resumo = client.open("Fidelidade").worksheet("Página1") 
    try:
        sheet_historico = client.open("Fidelidade").worksheet("Historico")
    except:
        st.error("⚠️ Crie uma aba chamada 'Historico' na planilha!")
        st.stop()
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")
    conexao = False

# --- FUNÇÕES ÚTEIS ---
def limpar_telefone(tel_completo):
    return re.sub(r'\D', '', tel_completo)

def pegar_data_hora():
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

def registrar_historico(nome, telefone, acao):
    data = pegar_data_hora()
    sheet_historico.append_row([data, nome, telefone, acao])

def gerar_mensagem_zap(nome_cliente, total_compras):
    if total_compras == 1:
        msg = f"Olá {nome_cliente}! Bem-vindo à Adega! 🍷\nStatus: 1 ponto."
        btn = "Enviar Boas-Vindas 🎉"
    elif total_compras < 9:
        msg = f"Olá {nome_cliente}! Mais uma compra!\nStatus: {total_compras}/10 pontos."
        btn = f"Enviar Saldo ({total_compras}/10) 📲"
    elif total_compras == 9:
        msg = f"UAU {nome_cliente}! Falta 1 para o prémio! 😱"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome_cliente}! Ganhou 50% OFF! 🏆"
        btn = "🏆 ENVIAR PRÉMIO AGORA"
    return msg, btn

# --- ESTADO DA SESSÃO ---
if 'confirmacao' not in st.session_state: st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state: st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state: st.session_state.sucesso_msg = None

# --- CARREGAR DADOS ---
if conexao:
    todos_dados = sheet_resumo.get_all_records()
    df = pd.DataFrame(todos_dados)
else:
    df = pd.DataFrame()

# ==========================================
# 📊 PAINEL DO PATRÃO
# ==========================================
if not df.empty and conexao:
    st.markdown("### 📊 Visão Geral")
    col1, col2, col3 = st.columns(3)
    
    total_clientes = len(df)
    try:
        total_pontos = df['compras'].sum()
        total_vip = len(df[df['compras'] >= 9])
    except:
        total_pontos = 0
        total_vip = 0

    col1.metric("Clientes", total_clientes)
    col2.metric("Pontos Totais", total_pontos)
    col3.metric("Quase Ganhando", total_vip)
    st.divider()

# ==========================================
# 📝 REGISTRO
# ==========================================
st.subheader("📝 Novo Registro")
nome = st.text_input("Nome do Cliente").strip().upper()

st.write("📞 Telefone do Cliente")
col_ddi, col_num = st.columns([0.2, 0.8])

with col_ddi:
    st.text_input("DDI", value="+55", disabled=True, label_visibility="collapsed")

with col_num:
    numero_digitado = st.text_input("Número", placeholder="99 99999-0000", label_visibility="collapsed")

telefone_completo = "+55" + numero_digitado
telefone_limpo = limpar_telefone(telefone_completo)

# --- BOTÃO DE AÇÃO ---
if st.button("Verificar/Registar", type="primary"):
    if nome and len(telefone_limpo) > 10 and conexao:
        st.session_state.sucesso_msg = None 
        
        if not df.empty:
            df['telefone'] = df['telefone'].astype(str)
            cliente_encontrado = df[df['telefone'] == telefone_limpo]
        else:
            cliente_encontrado = pd.DataFrame()

        if not cliente_encontrado.empty:
            # JÁ EXISTE
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
            # NOVO CLIENTE
            data_hoje = pegar_data_hora()
            sheet_resumo.append_row([nome, telefone_limpo, 1, data_hoje])
            registrar_historico(nome, telefone_limpo, "Cadastro + 1ª Compra")
            
            msg, btn_txt = gerar_mensagem_zap(nome, 1)
            msg_link = urllib.parse.quote(msg)
            link_zap = f"https://api.whatsapp.com/send?phone={telefone_limpo}&text={msg_link}"
            
            st.session_state.sucesso_msg = {
                'texto': f"🎉 Novo cliente {nome} cadastrado!",
                'link': link_zap,
                'btn_label': btn_txt
            }
            st.rerun()

    elif not conexao:
        st.error("Sem conexão.")
    elif len(telefone_limpo) <= 4:
        st.warning("Por favor, digite o número do telefone.")
    else:
        st.warning("Preencha o nome corretamente.")

# --- CONFIRMAÇÃO ---
if st.session_state.confirmacao:
    dados = st.session_state.dados_temp
    
    st.divider()
    st.warning(f"🚨 **CLIENTE JÁ CADASTRADO!**")
    st.write(f"Nome Atual: **{dados['nome_antigo']}**")
    st.info("Deseja atualizar e somar a compra?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ SIM, Atualizar"):
            with st.spinner('Gravando...'):
                linha_real = dados['indice'] + 2
                novo_total = int(dados['compras_atuais']) + 1
                data_hoje = pegar_data_hora()
                
                sheet_resumo.update_cell(linha_real, 1, dados['nome_novo']) 
                sheet_resumo.update_cell(linha_real, 3, novo_total)
                sheet_resumo.update_cell(linha_real, 4, data_hoje) 
                
                registrar_historico(dados['nome_novo'], dados['telefone'], f"Compra ({novo_total}º ponto)")

                msg, btn_txt = gerar_mensagem_zap(dados['nome_novo'], novo_total)
                msg_link = urllib.parse.quote(msg)
                link_zap = f"https://api.whatsapp.com/send?phone={dados['telefone']}&text={msg_link}"
                
                st.session_state.sucesso_msg = {
                    'texto': f"✅ Atualizado! {dados['nome_novo']} agora tem {novo_total} compras.",
                    'link': link_zap,
                    'btn_label': btn_txt,
                    'salao_festa': (novo_total >= 10)
                }
                
                if novo_total >= 10:
                     registrar_historico(dados['nome_novo'], dados['telefone'], "🏆 PRÉMIO LIBERADO")

                st.session_state.confirmacao = False
                st.rerun()

    with col2:
