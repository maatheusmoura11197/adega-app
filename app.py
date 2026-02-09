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
    
    # ABAS
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
    """Deixa apenas números"""
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
if 'confirmacao' not in st.session_state:
    st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state:
    st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state:
    st.session_state.sucesso_msg = None
# Variáveis para preenchimento automático (Importador)
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
# 📋 IMPORTADOR MÁGICO
# ==========================================
with st.expander("📋 Importar do Pedido (Copiar e Colar)"):
    texto_pedido = st.text_area("Cole aqui o texto do pedido:", height=80)
    if st.button("🔍 Extrair Dados"):
        if texto_pedido:
            # Busca Telefone
            encontrados = re.findall(r'\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}', texto_pedido)
            if encontrados:
                limpo = limpar_telefone(encontrados[0])
                if len(limpo) >= 10:
                    st.session_state.tel_auto = limpo[-11:] # Pega os ultimos 11
                    st.success(f"Achei o telefone: {st.session_state.tel_auto}")
            
            # Busca Nome (Simples)
            linhas = texto_pedido.split('\n')
            for linha in linhas:
                if "Cliente" in linha or "Nome" in linha:
                    st.session_state.nome_auto = linha.replace("Cliente:", "").replace("Nome:", "").strip().upper()
                    break
            st.rerun()

# ==========================================
# 📝 REGISTRO INTELIGENTE
# ==========================================
st.subheader("📝 Novo Registro")

# Recupera valores do importador ou vazio
nome_inicial = st.session_state.nome_auto if st.session_state.nome_auto else ""
tel_inicial = st.session_state.tel_auto if st.session_state.tel_auto else ""

nome = st.text_input("Nome do Cliente", value=nome_inicial).strip().upper()

st.write("📞 Telefone do Cliente")
col_ddi, col_num = st.columns([0.2, 0.8])
with col_ddi:
    st.text_input("DDI", value="+55", disabled=True, label_visibility="collapsed")
with col_num:
    # Formata visualmente se vier do importador
    if tel_inicial and len(tel_inicial) == 11:
        tel_visual = f"{tel_inicial[:2]} {tel_inicial[2:7]}-{tel_inicial[7:]}"
    else:
        tel_visual = tel_inicial
    numero_digitado = st.text_input("Número", value=tel_visual, placeholder="88 99999-0000", label_visibility="collapsed")

# Prepara o telefone oficial para salvar (Sempre com 55)
# Se o usuario colou um numero que ja tinha 55, a gente limpa antes de somar
numero_limpo_digitado = limpar_telefone(numero_digitado)
if numero_limpo_digitado.startswith("55") and len(numero_limpo_digitado) > 11:
    numero_limpo_digitado = numero_limpo_digitado[2:] # Tira o 55 duplicado

telefone_para_salvar = "55" + numero_limpo_digitado

# --- BOTÃO DE AÇÃO ---
if st.button("Verificar e Registar", type="primary"):
    # Validação básica: tem nome OU tem telefone válido
    tem_telefone_valido = len(numero_limpo_digitado) >= 10
    
    if (nome or tem_telefone_valido) and conexao:
        st.session_state.sucesso_msg = None 
        
        cliente_encontrado = pd.DataFrame()
        
        # ---------------------------------------------------------
        # 🧠 LÓGICA DE BUSCA AVANÇADA (NOME OU TELEFONE)
        # ---------------------------------------------------------
        if not df.empty:
            df['telefone'] = df['telefone'].astype(str) # Garante que é texto
            
            # 1. Tenta achar pelo TELEFONE (Ignorando se tem 55 ou não)
            if tem_telefone_valido:
                # O "core" é o numero sem o pais (ex: 88999991234)
                core_telefone = numero_limpo_digitado
                # Verifica se o telefone no banco TERMINA com o numero digitado
                # Isso acha tanto '5588...' quanto '88...'
                match_telefone = df[df['telefone'].str.endswith(core_telefone)]
                
                if not match_telefone.empty:
                    cliente_encontrado = match_telefone
                    print("Encontrado por Telefone")

            # 2. Se não achou por telefone, tenta pelo NOME
            if cliente_encontrado.empty and nome:
                match_nome = df[df['nome'] == nome]
                if not match_nome.empty:
                    cliente_encontrado = match_nome
                    st.toast(f"🔍 Cliente encontrado pelo nome: {nome}")

        # ---------------------------------------------------------
        # FIM DA LÓGICA
        # ---------------------------------------------------------

        if not cliente_encontrado.empty:
            # JÁ EXISTE (Seja por nome ou telefone)
            dados_existentes = cliente_encontrado.iloc[0]
            idx = cliente_encontrado.index[0]
            
            # Se achou pelo nome mas o telefone está vazio no input, preenchemos
            tel_encontrado = str(dados_existentes['telefone'])
            
            st.session_state.dados_temp = {
                'indice': idx,
                'nome_antigo': dados_existentes['nome'],
                'nome_novo': nome if nome else dados_existentes['nome'], # Mantem o antigo se nao digitou
                'telefone': tel_encontrado,
                'compras_atuais': dados_existentes['compras']
            }
            st.session_state.confirmacao = True
            st.rerun()

        else:
            # NOVO CLIENTE
            if tem_telefone_valido and nome:
                data_hoje = pegar_data_hora()
                sheet_resumo.append_row([nome, telefone_para_salvar, 1, data_hoje])
                registrar_historico(nome, telefone_para_salvar, "Cadastro + 1ª Compra")
                
                msg, btn_txt = gerar_mensagem_zap(nome, 1)
                msg_link = urllib.parse.quote(msg)
                link_zap = f"https://api.whatsapp.com/send?phone={telefone_para_salvar}&text={msg_link}"
                
                st.session_state.sucesso_msg = {
                    'texto': f"🎉 Novo cliente {nome} cadastrado!",
                    'link': link_zap,
                    'btn_label': btn_txt
                }
                st.rerun()
            else:
                st.warning("⚠️ Para cadastrar um NOVO cliente, preciso do Nome e do Telefone completos.")

    elif not conexao:
        st.error("Sem conexão.")
    else:
        st.warning("Preencha os dados.")

# --- CONFIRMAÇÃO ---
if st.session_state.confirmacao:
    dados = st.session_state.dados_temp
    
    st.divider()
    st.warning(f"🚨 **CLIENTE ENCONTRADO!**")
    st.write(f"👤 Nome no Sistema: **{dados['nome_antigo']}**")
    st.write(f"📞 Telefone no Sistema: **{dados['telefone']}**")
    st.info(f"Deseja adicionar +1 compra para {dados['nome_novo']}?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ SIM, Adicionar Compra"):
            with st.spinner('Gravando...'):
                linha_real = dados['indice'] + 2
                novo_total = int(dados['compras_atuais']) + 1
                data_hoje = pegar_data_hora()
                
                # Atualiza Nome (caso tenha corrigido) e Compras
                sheet_resumo.update_cell(linha_real, 1, dados['nome_novo']) 
                sheet_resumo.update_cell(linha_real, 3, novo_total)
                sheet_resumo.update_cell(linha_real, 4, data_hoje) 
                
                registrar_historico(dados['nome_novo'], dados['telefone'], f"Compra ({novo_total}º ponto)")

                msg, btn_txt = gerar_mensagem_zap(dados['nome_novo'], novo_total)
                msg_link = urllib.parse.quote(msg)
                link_zap = f"https://api.whatsapp.com/send?phone={dados['telefone']}&text={msg_link}"
                
                st.session_state.sucesso_msg = {
                    'texto': f"✅ Atualizado! Total: {novo_total} compras.",
                    'link': link_zap,
                    'btn_label': btn_txt,
                    'salao_festa': (novo_total >= 10)
                }
                
                if novo_total >= 10:
                     registrar_historico(dados['nome_novo'], dados['telefone'], "🏆 PRÉMIO LIBERADO")

                st.session_state.confirmacao = False
                st.rerun()

    with col2:
        if st.button("❌ Não é este"):
            st.session_state.confirmacao = False
            st.rerun()

# --- SUCESSO ---
if st.session_state.sucesso_msg:
    resultado = st.session_state.sucesso_msg
    st.divider()
    st.success(resultado['texto'])
    
    if resultado.get('salao_festa'):
        st.balloons()

    st.markdown(f"""
    <a href="{resultado['link']}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px;
            text-align: center; font-weight: bold; font-size: 18px; margin-top: 20px;
            display: block; width: 100%;">
            {resultado['btn_label']}
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Novo Atendimento"):
        st.session_state.sucesso_msg = None
        st.rerun()

# --- HISTÓRICO ---
st.markdown("---")
with st.expander("🔎 Consultar Histórico"):
    busca = st.text_input("Digite Telefone ou Nome para buscar")
    if st.button("Buscar"):
        if busca:
            df_hist = pd.DataFrame(sheet_historico.get_all_records())
            df_hist['Telefone'] = df_hist['Telefone'].astype(str)
            # Busca em qualquer coluna
            res = df_hist[df_hist.astype(str).apply(lambda x: x.str.contains(busca, case=False)).any(axis=1)]
            if not res.empty:
                st.dataframe(res[['Data', 'Nome', 'Ação']], use_container_width=True)
            else:
                st.warning("Nada encontrado.")
