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
# ⚙️ CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(
    page_title="Sistema Integrado Adega",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VISUAL (CABEÇALHO VISÍVEL) ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;} 
            footer {visibility: hidden;} 
            
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
            /* Destaque para o Link da Planilha */
            .planilha-btn {
                background-color: #f0f2f6;
                border: 1px solid #dce4ed;
                padding: 10px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 20px;
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
        st.markdown("<h3 style='text-align: center;'>Abrindo Sistema...</h3>", unsafe_allow_html=True)
        time.sleep(1.5)
        st.session_state.logado = True
        st.session_state.validando = False
        st.session_state.ultima_atividade = time.time()
        st.rerun()
    else:
        st.title("🔒 Acesso Restrito")
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
# SEU LINK DA PLANILHA AQUI (PARA O BOTÃO FUNCIONAR)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/191D0UIDvwDJPWRtp_0cBFS9rWaq6CkSj5ET_1HO2sLI/edit?usp=sharing"

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    
    planilha = client.open("Fidelidade")
    sheet_clientes = planilha.worksheet("Página1") 
    sheet_hist_cli = planilha.worksheet("Historico")
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")
    st.info("⚠️ Verifique as abas: 'Página1', 'Historico', 'Estoque', 'Historico_Estoque'")
    st.stop()

# --- FUNÇÕES ÚTEIS (RESTORED) ---
def limpar_telefone(tel): return re.sub(r'\D', '', tel)
def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

def gerar_mensagem_zap(nome_cliente, total_compras, produto_compra):
    """Gera a mensagem personalizada baseada na lógica antiga"""
    if total_compras == 1:
        msg = f"Olá {nome_cliente}! Bem-vindo à Adega! 🍷\nVocê levou: {produto_compra}.\nStatus: 1 ponto."
        btn = "Enviar Boas-Vindas 🎉"
    elif total_compras < 9:
        msg = f"Olá {nome_cliente}! Obrigado pela preferência!\nVocê levou: {produto_compra}.\nSaldo Fidelidade: {total_compras}/10 pontos."
        btn = f"Enviar Saldo ({total_compras}/10) 📲"
    elif total_compras == 9:
        msg = f"UAU {nome_cliente}! Falta só 1 compra para o prémio! 😱"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome_cliente}! Ganhou seu PRÊMIO! 🏆"
        btn = "🏆 ENVIAR PRÉMIO AGORA"
    return msg, btn

def registrar_historico_cli(nome, telefone, acao):
    sheet_hist_cli.append_row([pegar_data_hora(), nome, telefone, acao])

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu")
    
    # LINK DIRETO DA PLANILHA (RESTAURADO)
    st.link_button("📂 Abrir Planilha Google", URL_PLANILHA)
    st.divider()
    
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "📊 Relatórios"])
    st.markdown("---")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 MÓDULO 1: ESTOQUE (SÓ CADASTRO, SEM VENDA)
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    st.info("Aqui você APENAS cadastra ou repõe produtos. Para vender, vá em 'Fidelidade & Caixa'.")
    
    aba_cad, aba_ver = st.tabs(["📝 Entrada de Mercadoria", "📋 Ver Estoque Completo"])
    
    try:
        df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
    except:
        df_estoque = pd.DataFrame()
    
    with aba_cad:
        col_nome, col_tipo = st.columns(2)
        with col_nome:
            lista_nomes = df_estoque['Nome'].tolist() if not df_estoque.empty else []
            nome_prod = st.selectbox("Nome do Produto:", ["🆕 CADASTRAR NOVO"] + lista_nomes)
            if nome_prod == "🆕 CADASTRAR NOVO":
                nome_prod_final = st.text_input("Digite o nome do novo produto:").upper()
            else:
                nome_prod_final = nome_prod
        
        with col_tipo:
            tipo_prod = st.selectbox("Tipo:", ["Lata", "Long Neck", "Garrafa 600ml", "Litro/Outros"])
            
        c1, c2, c3 = st.columns(3)
        custo = c1.number_input("Custo Unitário (R$)", min_value=0.0, format="%.2f")
        venda = c2.number_input("Preço Venda (R$)", min_value=0.0, format="%.2f")
        qtd = c3.number_input("Quantidade (Entrada)", min_value=1, step=1)
        fornecedor = st.text_input("Fornecedor")
        
        if st.button("💾 Salvar Entrada", type="primary"):
            if nome_prod_final and qtd > 0:
                with st.spinner("Atualizando nuvem..."):
                    encontrado = False
                    idx_planilha = 2
                    
                    if not df_estoque.empty:
                        for i, row in df_estoque.iterrows():
                            if row['Nome'] == nome_prod_final:
                                nova_qtd = int(row['Estoque']) + qtd
                                sheet_estoque.update_cell(idx_planilha + i, 6, nova_qtd)
                                sheet_estoque.update_cell(idx_planilha + i, 4, custo)
                                sheet_estoque.update_cell(idx_planilha + i, 5, venda)
                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor)
                                encontrado = True
                                break
                    
                    if not encontrado:
                        sheet_estoque.append_row([nome_prod_final, tipo_prod, fornecedor, custo, venda, qtd, pegar_data_hora()])
                    
                    sheet_hist_est.append_row([pegar_data_hora(), nome_prod_final, "COMPRA", qtd, custo*qtd, f"Forn: {fornecedor}"])
                    
                    st.success(f"✅ Entrada de {qtd}x {nome_prod_final} registrada!")
                    time.sleep(1)
                    st.rerun()

    with aba_ver:
        if not df_estoque.empty:
            busca = st.text_input("🔍 Buscar Produto:").upper()
            if busca: df_estoque = df_estoque[df_estoque['Nome'].str.contains(busca, case=False)]
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Estoque vazio.")

# ==========================================
# 💰 MÓDULO 2: FIDELIDADE & CAIXA (INTEGRADO)
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    st.title("💰 Caixa & Fidelidade")
    
    # Carregar dados
    df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
    df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
    
    # Preparar lista de produtos
    if not df_estoque.empty:
        df_estoque['Display'] = df_estoque.apply(lambda x: f"{x['Nome']} - R$ {x['Venda']} ({x['Estoque']} un)", axis=1)
        lista_venda = ["(Nenhum - Apenas Pontuar)"] + df_estoque['Display'].tolist()
    else:
        lista_venda = ["Estoque Vazio"]

    # --- INPUTS DO CLIENTE ---
    st.subheader("1. Identificação")
    col_c1, col_c2 = st.columns(2)
    nome_input = col_c1.text_input("Nome do Cliente").strip().upper()
    tel_input = col_c2.text_input("Telefone", placeholder="Ex: 88 99999-0000")
    tel_limpo = limpar_telefone("+55" + tel_input) if tel_input else ""

    # --- INPUTS DA VENDA ---
    st.subheader("2. O que ele comprou?")
    c_prod, c_qtd = st.columns([0.7, 0.3])
    prod_selecionado = c_prod.selectbox("Produto (Baixa Automática):", lista_venda)
    qtd_venda = c_qtd.number_input("Qtd:", min_value=1, value=1)
    
    st.divider()

    # --- BOTÃO ÚNICO DE AÇÃO ---
    if st.button("✅ FINALIZAR VENDA & PONTUAR", type="primary"):
        erro = False
        
        # Validações Básicas
        if not nome_input or len(tel_limpo) < 10:
            st.warning("⚠️ Preencha Nome e Telefone corretamente.")
            erro = True
        
        # --- LÓGICA DE ESTOQUE ---
        nome_produto_real = "Apenas Pontos"
        preco_venda = 0
        
        if "(Nenhum" not in prod_selecionado and not erro:
            nome_produto_real = prod_selecionado.split(" - R$")[0]
            
            # Buscar no estoque
            idx_estoque = -1
            estoque_atual = 0
            
            for i, row in df_estoque.iterrows():
                if row['Nome'] == nome_produto_real:
                    idx_estoque = i + 2
                    estoque_atual = int(row['Estoque'])
                    preco_venda = float(row['Venda'])
                    break
            
            if idx_estoque != -1:
                if estoque_atual >= qtd_venda:
                    # BAIXA DE ESTOQUE
                    sheet_estoque.update_cell(idx_estoque, 6, estoque_atual - qtd_venda)
                    sheet_hist_est.append_row([pegar_data_hora(), nome_produto_real, "VENDA", qtd_venda, preco_venda*qtd_venda, f"Cli: {nome_input}"])
                else:
                    st.error(f"🚫 Estoque insuficiente de {nome_produto_real}!")
                    st.stop()
            else:
                st.error("Erro no estoque.")
                st.stop()

        # --- LÓGICA DE CLIENTE (NOVO OU ANTIGO) ---
        if not erro:
            with st.spinner("Registrando..."):
                cliente_existe = False
                linha_cli = -1
                pontos_antigos = 0
                
                if not df_clientes.empty:
                    df_clientes['telefone'] = df_clientes['telefone'].astype(str)
                    match = df_clientes[df_clientes['telefone'] == tel_limpo]
                    if not match.empty:
                        cliente_existe = True
                        linha_cli = match.index[0] + 2
                        pontos_antigos = int(match.iloc[0]['compras'])
                
                if cliente_existe:
                    # ATUALIZA EXISTENTE
                    novos_pontos = pontos_antigos + 1
                    sheet_clientes.update_cell(linha_cli, 1, nome_input) # Atualiza nome
                    sheet_clientes.update_cell(linha_cli, 3, novos_pontos)
                    sheet_clientes.update_cell(linha_cli, 4, pegar_data_hora())
                    registrar_historico_cli(nome_input, tel_limpo, f"Compra: {nome_produto_real} ({novos_pontos}º pt)")
                else:
                    # CADASTRA NOVO
                    novos_pontos = 1
                    sheet_clientes.append_row([nome_input, tel_limpo, 1, pegar_data_hora()])
                    registrar_historico_cli(nome_input, tel_limpo, f"Cadastro Novo + {nome_produto_real}")

                # --- GERAR MENSAGEM ZAP (RESTORED) ---
                msg_zap, texto_botao = gerar_mensagem_zap(nome_input, novos_pontos, nome_produto_real)
                link_zap = f"https://api.whatsapp.com/send?phone={tel_limpo}&text={urllib.parse.quote(msg_zap)}"
                
                # SUCESSO
                st.success(f"✅ Sucesso! Estoque baixado e Cliente pontuado ({novos_pontos}).")
                if novos_pontos >= 10: st.balloons()
                
                # BOTÃO GRANDE DO ZAP
                st.markdown(f"""
                <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 18px; margin-top: 10px;">
                        {texto_botao}
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
                # Botão para limpar a tela
                if st.button("🔄 Próximo Cliente"):
                    st.rerun()

    # --- PAINEL ADMIN (RESTAURADO) ---
    st.divider()
    with st.expander("⚙️ Painel Administrativo (Editar/Excluir Clientes)"):
        st.write("Gerenciar cadastro de clientes")
        if not df_clientes.empty:
            df_clientes['rotulo'] = df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)
            cli_edit = st.selectbox("Selecione Cliente:", [""] + df_clientes['rotulo'].tolist())
            
            if cli_edit:
                idx = df_clientes[df_clientes['rotulo'] == cli_edit].index[0]
                dados_cli = df_clientes.iloc[idx]
                linha_sheet = idx + 2
                
                with st.form("edit_cli"):
                    nn = st.text_input("Nome", value=dados_cli['nome'])
                    nt = st.text_input("Telefone", value=dados_cli['telefone'])
                    np = st.number_input("Pontos", value=int(dados_cli['compras']))
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 Salvar"):
                        sheet_clientes.update_cell(linha_sheet, 1, nn)
                        sheet_clientes.update_cell(linha_sheet, 2, nt)
                        sheet_clientes.update_cell(linha_sheet, 3, np)
                        st.success("Atualizado!")
                        st.rerun()
                    
                    if c2.form_submit_button("🗑️ Excluir"):
                        sheet_clientes.delete_rows(linha_sheet)
                        st.warning("Excluído!")
                        st.rerun()

# ==========================================
# 📊 MÓDULO 3: RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Dados Gerais")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Movimentação de Estoque**")
        try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
        except: st.write("Vazio")
    with c2:
        st.write("**Histórico de Clientes**")
        try: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
        except: st.write("Vazio")
