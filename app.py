import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 
import re 
from datetime import datetime
import pytz 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷")
st.title("🍷 Fidelidade Adega Online")

# --- CONEXÃO COM O GOOGLE SHEETS ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet_resumo = client.open("Fidelidade").worksheet("Página1") 
    try:
        sheet_historico = client.open("Fidelidade").worksheet("Historico")
    except:
        st.error("⚠️ Crie uma aba 'Historico'!")
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
    # (Mantém a mesma lógica das mensagens anteriores...)
    if total_compras == 1:
        msg = f"Olá {nome_cliente}! Bem-vindo à Adega! 🍷"
        btn = "Enviar Boas-Vindas 🎉"
    elif total_compras < 9:
        msg = f"Olá {nome_cliente}! Mais uma compra! Saldo: {total_compras}/10 🍷"
        btn = f"Enviar Saldo ({total_compras}/10) 📲"
    elif total_compras == 9:
        msg = f"UAU {nome_cliente}! Falta 1 para o prémio! 😱"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome_cliente}! Ganhou 50% OFF! 🏆"
        btn = "🏆 ENVIAR PRÉMIO AGORA"
    return msg, btn

# --- ESTADO DA SESSÃO ---
if 'confirmacao' not in st.session_state:
    st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state:
    st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state:
    st.session_state.sucesso_msg = None
# Variáveis para preenchimento automático
if 'nome_auto' not in st.session_state:
    st.session_state.nome_auto = ""
if 'tel_auto' not in st.session_state:
    st.session_state.tel_auto = ""

# --- CARREGAR DADOS ---
if conexao:
    todos_dados = sheet_resumo.get_all_records()
    df = pd.DataFrame(todos_dados)
else:
    df = pd.DataFrame()

# ==========================================
# 📋 IMPORTADOR MÁGICO (NOVIDADE!)
# ==========================================
with st.expander("📋 Importar do Pedido (Copiar e Colar)"):
    texto_pedido = st.text_area("Cole aqui o texto do pedido (iFood, WhatsApp, Site...)", height=100)
    
    if st.button("🔍 Extrair Dados"):
        if texto_pedido:
            # 1. Tenta achar telefone (procura padroes como (88) 9... ou 889...)
            # Regex poderoso para achar numeros de celular no meio do texto
            encontrados = re.findall(r'\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}', texto_pedido)
            
            if encontrados:
                # Pega o primeiro numero que achar e limpa
                numero_bruto = encontrados[0]
                # Remove o 55 se vier junto, ou adiciona se faltar, mas aqui limpamos tudo
                limpo = limpar_telefone(numero_bruto)
                # Se tiver 11 digitos (DDD + 9 + numero), assumimos que é BR
                if len(limpo) >= 10:
                    st.session_state.tel_auto = limpo[-11:] # Pega os ultimos 11 digitos (DDD+NUMERO)
                    st.success(f"Telefone encontrado: {st.session_state.tel_auto}")
            else:
                st.warning("Não achei telefone no texto.")

            # 2. Tenta achar nome (Isso é dificil, entao pegamos a primeira linha ou palavras maiusculas)
            # Dica: Geralmente o nome é a primeira coisa ou vem depois de "Cliente:"
            linhas = texto_pedido.split('\n')
            for linha in linhas:
                if "Cliente" in linha or "Nome" in linha:
                    # Tenta limpar o label "Cliente:"
                    st.session_state.nome_auto = linha.replace("Cliente:", "").replace("Nome:", "").strip().upper()
                    break
            
            # Se nao achou label, pega a primeira linha que nao seja vazia
            if not st.session_state.nome_auto:
                for linha in linhas:
                    if len(linha) > 3 and not re.search(r'\d', linha): # Linha sem numeros
                        st.session_state.nome_auto = linha.strip().upper()
                        break
            
            if st.session_state.nome_auto:
                st.success(f"Nome sugerido: {st.session_state.nome_auto}")
            
            st.rerun() # Recarrega para preencher os campos lá embaixo

# ==========================================
# 📝 REGISTRO
# ==========================================
st.subheader("📝 Novo Registro")

# Se o importador achou algo, usa como valor padrao (value)
nome_inicial = st.session_state.nome_auto if st.session_state.nome_auto else ""
tel_inicial = st.session_state.tel_auto if st.session_state.tel_auto else ""

nome = st.text_input("Nome do Cliente", value=nome_inicial).strip().upper()

st.write("📞 Telefone do Cliente")
col_ddi, col_num = st.columns([0.2, 0.8])

with col_ddi:
    st.text_input("DDI", value="+55", disabled=True, label_visibility="collapsed")

with col_num:
    # Se tiver numero importado, formatamos ele bonito para exibir
    if tel_inicial:
        # Formata visualmente 88999998888 -> 88 99999-8888
        if len(tel_inicial) == 11:
            tel_visual = f"{tel_inicial[:2]} {tel_inicial[2:7]}-{tel_inicial[7:]}"
        else:
            tel_visual = tel_inicial
    else:
        tel_visual = ""
        
    numero_digitado = st.text_input("Número", value=tel_visual, placeholder="88 99999-0000", label_visibility="collapsed")

# Limpa para guardar
telefone_completo = "+55" + numero_digitado
telefone_limpo = limpar_telefone(telefone_completo)

# --- BOTÃO DE AÇÃO ---
if st.button("Verificar e Registar", type="primary"):
    if nome and len(telefone_limpo) > 10 and conexao:
        # ... (O RESTO DO CÓDIGO É IGUAL AO ANTERIOR) ...
        # Copie a lógica de verificação e salvamento do código anterior aqui
        pass # Substitua este pass pelo bloco de salvamento
        
        # DICA: Vou resumir o salvamento aqui para nao ficar gigante a resposta,
        # mas voce deve manter a logica de duplicidade e historico que ja tinhamos!
