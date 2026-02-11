import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import re
from datetime import datetime
import pytz
import time

# ==========================================
# ⚙️ CONFIGURAÇÃO INICIAL (CORREÇÃO AQUI)
# ==========================================
st.set_page_config(
    page_title="Sistema Integrado Adega",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"  # <--- ISSO FORÇA O MENU A COMEÇAR ABERTO
)

# --- BLOQUEIO VISUAL SUAVE ---
# Removemos o bloqueio do 'header' para o menu aparecer no celular e PC
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;} 
            footer {visibility: hidden;} 
            
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
# 🔐 LOGIN
# ==========================================
SENHA_DO_SISTEMA = "adega123" 
TEMPO_LIMITE_MINUTOS = 60

if 'logado' not in st.session_state: st.session_state.logado = False
if 'validando' not in st.session_state: st.session_state.validando = False
if 'ultima_atividade' not in st.session_state: st.session_state.ultima_atividade = time.time()

def verificar_sessao():
    if st.session_state.logado:
        agora = time.time()
        tempo_passado = agora - st.session_state.ultima_atividade
        if tempo_passado > (TEMPO_LIMITE_MINUTOS * 60):
            st.session_state.logado = False
            st.error("⏳ Sessão expirada.")
            return False
        st.session_state.ultima_atividade = agora
        return True
    return False

if not st.session_state.logado:
    if st.session_state.validando:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="brinde">🍷</div>', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Abrindo Sistema Integrado...</h3>", unsafe_allow_html=True)
        time.sleep(1.5)
        st.session_state.logado = True
        st.session_state.validando = False
        st.session_state.ultima_atividade = time.time()
        st.rerun()
    else:
        st.title("🔒 Sistema Adega & Fidelidade")
        with st.form("login_form"):
            senha_digitada = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR", type="primary"):
                if senha_digitada == SENHA_DO_SISTEMA:
                    st.session_state.validando = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        st.stop()

if not verificar_sessao(): st.stop()

# ==========================================
# 📡 CONEXÃO GOOGLE SHEETS
# ==========================================
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    
    # Abre a planilha
    planilha = client.open("Fidelidade")
    
    # Conecta nas 4 abas
    sheet_clientes = planilha.worksheet("Página1") 
    sheet_hist_cli = planilha.worksheet("Historico")
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão com Google Sheets: {e}")
    st.info("⚠️ Verifique se criou as abas 'Estoque' e 'Historico_Estoque' na sua planilha.")
    st.stop()

# --- FUNÇÕES ÚTEIS GERAIS ---
def limpar_telefone(tel): return re.sub(r'\D', '', tel)
def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
def converter_valor(v): 
    try: return float(str(v).replace(',', '.')) 
    except: return 0.0

# ==========================================
# 📱 MENU LATERAL (AGORA VISÍVEL)
# ==========================================
with st.sidebar:
    st.title("🍷 Menu Principal")
    st.info("Navegue abaixo:")
    menu = st.radio("Ir para:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "📊 Relatórios"])
    st.markdown("---")
    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 MÓDULO 1: GESTÃO DE ESTOQUE
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    
    aba_cad, aba_ver = st.tabs(["📝 Cadastrar Compra", "📋 Ver Estoque"])
    
    # --- CARREGAR ESTOQUE ---
    try:
        dados_estoque = sheet_estoque.get_all_records()
        df_estoque = pd.DataFrame(dados_estoque)
    except:
        df_estoque = pd.DataFrame()
    
    with aba_cad:
        st.subheader("Entrada de Mercadoria")
        col_nome, col_tipo = st.columns(2)
        with col_nome:
            # Lista existente para autocomplete
            lista_nomes = df_estoque['Nome'].tolist() if not df_estoque.empty else []
            nome_prod = st.selectbox("Nome do Produto (ou digite novo):", ["Digitar Novo..."] + lista_nomes)
            if nome_prod == "Digitar Novo...":
                nome_prod = st.text_input("Digite o nome do novo produto:").upper()
        
        with col_tipo:
            tipo_prod = st.selectbox("Tipo:", ["Lata", "Long Neck", "Garrafa 600ml", "Litro/Outros"])
            
        c1, c2, c3 = st.columns(3)
        custo = c1.number_input("Custo Unitário (R$)", min_value=0.0, format="%.2f")
        venda = c2.number_input("Preço Venda (R$)", min_value=0.0, format="%.2f")
        qtd = c3.number_input("Quantidade Comprada", min_value=1, step=1)
        fornecedor = st.text_input("Fornecedor")
        
        if st.button("💾 Salvar no Estoque", type="primary"):
            if nome_prod and qtd > 0:
                with st.spinner("Salvando na nuvem..."):
                    # Verifica se produto já existe
                    encontrado = False
                    idx_planilha = 2 # Começa na linha 2 (1 é cabeçalho)
                    
                    if not df_estoque.empty:
                        for i, row in df_estoque.iterrows():
                            if row['Nome'] == nome_prod:
                                # Atualiza Existente (Soma estoque e atualiza preços)
                                nova_qtd = int(row['Estoque']) + qtd
                                sheet_estoque.update_cell(idx_planilha + i, 6, nova_qtd) # Coluna 6 = Estoque
                                sheet_estoque.update_cell(idx_planilha + i, 4, custo)    # Coluna 4 = Custo
                                sheet_estoque.update_cell(idx_planilha + i, 5, venda)    # Coluna 5 = Venda
                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor) # Col 3 = Fornecedor
                                encontrado = True
                                break
                    
                    if not encontrado:
                        # Cria Novo (Ordem: Nome | Tipo | Fornecedor | Custo | Venda | Estoque | Data)
                        sheet_estoque.append_row([nome_prod, tipo_prod, fornecedor, custo, venda, qtd, pegar_data_hora()])
                    
                    # Log no Historico
                    sheet_hist_est.append_row([pegar_data_hora(), nome_prod, "COMPRA", qtd, custo*qtd, f"Fornecedor: {fornecedor}"])
                    
                    st.success(f"✅ {qtd}x {nome_prod} adicionado com sucesso!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Preencha nome e quantidade.")

    with aba_ver:
        st.subheader("Estoque Atual")
        if not df_estoque.empty:
            # Filtro
            busca = st.text_input("🔍 Buscar Produto:").upper()
            if busca:
                df_estoque = df_estoque[df_estoque['Nome'].str.contains(busca, case=False)]
            
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Estoque vazio.")

# ==========================================
# 💰 MÓDULO 2: FIDELIDADE & CAIXA
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    st.title("💰 Caixa & Fidelidade")
    
    # --- CARREGAR DADOS ---
    dados_clientes = sheet_clientes.get_all_records()
    df_clientes = pd.DataFrame(dados_clientes)
    
    dados_estoque = sheet_estoque.get_all_records()
    df_estoque = pd.DataFrame(dados_estoque)
    
    # Lista de produtos para venda
    if not df_estoque.empty:
        # Cria uma lista bonita para o selectbox
        df_estoque['Display'] = df_estoque.apply(lambda x: f"{x['Nome']} - R$ {x['Venda']} ({x['Estoque']} un)", axis=1)
        lista_venda = ["Selecione o produto..."] + df_estoque['Display'].tolist()
    else:
        lista_venda = ["Estoque Vazio"]

    # --- IDENTIFICAR CLIENTE ---
    st.markdown("### 👤 Cliente")
    col_nome_cli, col_tel_cli = st.columns(2)
    
    nome_input = col_nome_cli.text_input("Nome (Primeiro nome)").strip().upper()
    tel_input = col_tel_cli.text_input("Telefone (Só números)", placeholder="Ex: 88999990000")
    
    tel_limpo = limpar_telefone("+55" + tel_input) if tel_input else ""
    
    # --- CARRINHO / BAIXA ---
    st.markdown("### 🛒 O que ele comprou?")
    produto_selecionado_str = st.selectbox("Selecione o Item para dar baixa:", lista_venda)
    qtd_venda = st.number_input("Quantidade:", min_value=1, value=1)
    
    # Botão Principal
    if st.button("✅ Confirmar Venda & Pontuar", type="primary"):
        erro = False
        
        # Validações
        if not nome_input or len(tel_input) < 8:
            st.warning("⚠️ Preencha Nome e Telefone do cliente.")
            erro = True
        
        if "Selecione" in produto_selecionado_str or "Vazio" in produto_selecionado_str:
            st.warning("⚠️ Selecione um produto do estoque.")
            erro = True
            
        if not erro:
            with st.spinner("Processando Venda..."):
                
                # --- A: BAIXA NO ESTOQUE ---
                nome_produto_real = produto_selecionado_str.split(" - R$")[0]
                
                idx_estoque = -1
                estoque_atual = 0
                preco_venda = 0
                
                # Procura o produto no DataFrame
                for i, row in df_estoque.iterrows():
                    if row['Nome'] == nome_produto_real:
                        idx_estoque = i + 2 
                        estoque_atual = int(row['Estoque'])
                        preco_venda = float(row['Venda'])
                        break
                
                if idx_estoque != -1:
                    if estoque_atual >= qtd_venda:
                        # Baixa na Planilha
                        nova_qtd_est = estoque_atual - qtd_venda
                        sheet_estoque.update_cell(idx_estoque, 6, nova_qtd_est)
                        
                        # Histórico Estoque
                        total_rs = preco_venda * qtd_venda
                        sheet_hist_est.append_row([pegar_data_hora(), nome_produto_real, "VENDA", qtd_venda, total_rs, f"Cliente: {nome_input}"])
                    else:
                        st.error(f"🚫 Estoque insuficiente! Tem: {estoque_atual}, Pedido: {qtd_venda}.")
                        st.stop()
                else:
                    st.error("Erro ao encontrar produto.")
                    st.stop()

                # --- B: PONTUAR CLIENTE ---
                cliente_encontrado = False
                linha_cliente = -1
                pontos_atuais = 0
                
                if not df_clientes.empty:
                    df_clientes['telefone'] = df_clientes['telefone'].astype(str)
                    match = df_clientes[df_clientes['telefone'] == tel_limpo]
                    if not match.empty:
                        cliente_encontrado = True
                        linha_cliente = match.index[0] + 2
                        pontos_atuais = int(match.iloc[0]['compras'])
                
                if cliente_encontrado:
                    novos_pontos = pontos_atuais + 1 
                    sheet_clientes.update_cell(linha_cliente, 1, nome_input)
                    sheet_clientes.update_cell(linha_cliente, 3, novos_pontos)
                    sheet_clientes.update_cell(linha_cliente, 4, pegar_data_hora())
                    msg_acao = f"Compra: {nome_produto_real} ({novos_pontos}º pt)"
                else:
                    novos_pontos = 1
                    sheet_clientes.append_row([nome_input, tel_limpo, 1, pegar_data_hora()])
                    msg_acao = f"Cadastro + Compra: {nome_produto_real}"
                
                # Histórico Cliente
                sheet_hist_cli.append_row([pegar_data_hora(), nome_input, tel_limpo, msg_acao])
                
                # --- C: ZAP E FIM ---
                if novos_pontos < 10:
                    msg_zap = f"Olá {nome_input}! Obrigado pela compra na Adega! 🍷\nVocê comprou: {nome_produto_real}.\nSeu Saldo Fidelidade: {novos_pontos}/10 pontos."
                else:
                    msg_zap = f"PARABÉNS {nome_input}! 🏆 Você completou 10 pontos e ganhou seu prêmio!"
                    st.balloons()
                
                link_zap = f"https://api.whatsapp.com/send?phone={tel_limpo}&text={urllib.parse.quote(msg_zap)}"
                
                st.success(f"✅ Venda Realizada! {nome_produto_real} baixado do estoque.")
                st.markdown(f"### [📲 Enviar WhatsApp para Cliente]({link_zap})")
                
                time.sleep(4) 
                st.rerun()

# ==========================================
# 📊 MÓDULO 3: RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios Gerais")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Histórico de Vendas (Estoque)")
        try:
            dados_he = sheet_hist_est.get_all_records()
            st.dataframe(pd.DataFrame(dados_he), use_container_width=True)
        except: st.info("Sem dados de estoque.")
        
    with col2:
        st.subheader("Histórico de Fidelidade (Clientes)")
        try:
            dados_hc = sheet_hist_cli.get_all_records()
            st.dataframe(pd.DataFrame(dados_hc), use_container_width=True)
        except: st.info("Sem dados de clientes.")
