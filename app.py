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
    
    # AGORA ABRIMOS AS DUAS ABAS
    sheet_resumo = client.open("Fidelidade").worksheet("Página1") # Aba Principal (Se chama Página1 ou Sheet1)
    # Tenta abrir a aba Historico. Se não existir, avisa.
    try:
        sheet_historico = client.open("Fidelidade").worksheet("Historico")
    except:
        st.error("⚠️ Crie uma aba chamada 'Historico' na sua planilha!")
        st.stop()
        
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}. Verifique se a aba principal se chama 'Página1' ou 'Sheet1'.")
    conexao = False

# --- FUNÇÕES ÚTEIS ---
def limpar_telefone(tel):
    return re.sub(r'\D', '', tel)

def pegar_data_hora():
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

def registrar_historico(nome, telefone, acao):
    """Grava uma linha nova na aba Historico"""
    data = pegar_data_hora()
    sheet_historico.append_row([data, nome, telefone, acao])

def gerar_mensagem_zap(nome_cliente, total_compras):
    if total_compras == 1:
        l1 = f"Olá, {nome_cliente}! Que alegria ter você aqui na nossa Adega! 🍷✨"
        l2 = "Seja muito bem-vindo(a)! Já começamos com o pé direito o seu fidelidade."
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
        l5 = "Vamos reiniciar seu cartão para ganhar de novo! 🥂✨"
        msg = f"{l1}\n\n{l2}\n{l3}\n\n{l4}\n\n{l5}"
        btn = "🏆 ENVIAR PRÉMIO AGORA"

    return msg, btn

# --- ESTADO DA SESSÃO ---
if 'confirmacao' not in st.session_state:
    st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state:
    st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state:
    st.session_state.sucesso_msg = None

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
# 📝 REGISTRO DE COMPRAS
# ==========================================
st.subheader("📝 Novo Registro")
nome = st.text_input("Nome do Cliente").strip().upper()
telefone_input = st.text_input("Telefone", value="+55 ", help="Apenas digite.")
telefone_limpo = limpar_telefone(telefone_input)

if st.button("Verificar e Registar", type="primary"):
    if nome and telefone_limpo and conexao:
        st.session_state.sucesso_msg = None 
        
        if not df.empty:
            df['telefone'] = df['telefone'].astype(str)
            cliente_encontrado = df[df['telefone'] == telefone_limpo]
        else:
            cliente_encontrado = pd.DataFrame()

        if not cliente_encontrado.empty:
            # JÁ EXISTE -> Confirmação
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
            
            # 1. Grava no Resumo
            sheet_resumo.append_row([nome, telefone_limpo, 1, data_hoje])
            # 2. Grava no Histórico
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
    else:
        st.warning("Preencha o nome e o telefone.")

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
                
                # 1. Atualiza Resumo
                sheet_resumo.update_cell(linha_real, 1, dados['nome_novo']) 
                sheet_resumo.update_cell(linha_real, 3, novo_total)
                sheet_resumo.update_cell(linha_real, 4, data_hoje) 
                
                # 2. Grava no Histórico
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
                     # Se ganhou prémio, regista no histórico também
                     registrar_historico(dados['nome_novo'], dados['telefone'], "🏆 PRÉMIO LIBERADO")
                     # Se quiser zerar automatico, descomente:
                     # sheet_resumo.update_cell(linha_real, 3, 0)
                     # registrar_historico(dados['nome_novo'], dados['telefone'], "Ciclo Reiniciado")

                st.session_state.confirmacao = False
                st.rerun()

    with col2:
        if st.button("❌ Cancelar"):
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
        <div style="
            background-color: #25D366; color: white; padding: 15px; border-radius: 10px;
            text-align: center; font-weight: bold; font-size: 18px; margin-top: 20px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.2); display: block; width: 100%;">
            {resultado['btn_label']}
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Novo Atendimento"):
        st.session_state.sucesso_msg = None
        st.rerun()

# ==========================================
# 🔎 CONSULTAR HISTÓRICO (NOVO!)
# ==========================================
st.markdown("---")
st.subheader("🔎 Consultar Histórico do Cliente")

# Caixa para pesquisar por telefone
busca_tel_input = st.text_input("Digite o Telefone para pesquisar", value="", placeholder="Ex: 88999...")
busca_tel = limpar_telefone(busca_tel_input)

if st.button("Buscar Histórico"):
    if busca_tel:
        try:
            # Baixa os dados da aba Historico
            dados_hist = sheet_historico.get_all_records()
            df_hist = pd.DataFrame(dados_hist)
            
            # Garante que a coluna Telefone é texto para comparar
            df_hist['Telefone'] = df_hist['Telefone'].astype(str)
            
            # Filtra pelo telefone digitado
            resultado = df_hist[df_hist['Telefone'] == busca_tel]
            
            if not resultado.empty:
                st.info(f"Histórico encontrado para: **{resultado.iloc[0]['Nome']}**")
                # Mostra a tabela bonitinha (sem o telefone pra não poluir)
                st.dataframe(resultado[['Data', 'Ação']], use_container_width=True)
            else:
                st.warning("Nenhum histórico encontrado para este número.")
                
        except Exception as e:
            st.error(f"Erro ao buscar histórico: {e}")
            st.info("Dica: Verifique se a aba 'Historico' tem os cabeçalhos: Data, Nome, Telefone, Ação")
