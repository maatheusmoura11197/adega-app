import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import re
from datetime import datetime, date
import pytz
import time

# ==========================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(
    page_title="Super Adega Integrada",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VISUAL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;} 
            footer {visibility: hidden;} 
            .stSelectbox div[data-baseweb="select"] > div:first-child {
                border-color: #ff4b4b; /* Destaque visual */
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
        st.write("Entrando...")
        time.sleep(1)
        st.session_state.logado = True
        st.session_state.validando = False
        st.session_state.ultima_atividade = time.time()
        st.rerun()
    else:
        st.title("🔒 Acesso Restrito")
        with st.form("login_form"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR", type="primary"):
                if senha == SENHA_DO_SISTEMA:
                    st.session_state.validando = True
                    st.rerun()
                else: st.error("Senha errada")
        st.stop()

if not verificar_sessao(): st.stop()

# ==========================================
# 📡 CONEXÃO GOOGLE SHEETS
# ==========================================
# SEU LINK AQUI
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
except Exception as e:
    st.error(f"Erro Conexão: {e}")
    st.stop()

# --- FUNÇÕES AUXILIARES ---
def limpar_telefone(tel): return re.sub(r'\D', '', tel)
def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
def converter_valor(v): 
    try: return float(str(v).replace(',', '.')) 
    except: return 0.0

def gerar_mensagem_zap(nome, total, prod):
    if total == 1: msg = f"Olá {nome}! Bem-vindo! 🍷\nLevou: {prod}.\nPontos: 1."
    elif total < 9: msg = f"Olá {nome}! Levou: {prod}.\nSaldo: {total}/10 pontos."
    elif total == 9: msg = f"UAU {nome}! Falta 1 para o prémio! 😱"
    else: msg = f"PARABÉNS {nome}! Ganhou PRÊMIO! 🏆"
    return msg

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu")
    st.link_button("📂 Abrir Planilha", URL_PLANILHA)
    st.divider()
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "📊 Relatórios"])
    st.markdown("---")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 GESTÃO DE ESTOQUE (COM CUSTO MÉDIO E DATA)
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque Inteligente")
    
    aba_cad, aba_ver = st.tabs(["📝 Entrada (Compra)", "📋 Ver Estoque"])
    
    # Carrega dados
    try:
        dados_raw = sheet_estoque.get_all_records()
        df_estoque = pd.DataFrame(dados_raw)
    except: df_estoque = pd.DataFrame()
    
    with aba_cad:
        st.subheader("Registrar Compra")
        
        # 1. ESCOLHA DO PRODUTO (AUTOCOMPLETE)
        lista_nomes = df_estoque['Nome'].unique().tolist() if not df_estoque.empty else []
        modo_cadastro = st.radio("Produto:", ["Selecionar Existente", "Cadastrar Novo"], horizontal=True)
        
        nome_final = ""
        qtd_fardo_ref = 12 # Padrão
        
        if modo_cadastro == "Selecionar Existente":
            if lista_nomes:
                nome_selecionado = st.selectbox("Escolha o Item:", lista_nomes)
                nome_final = nome_selecionado
                # Tenta pegar a referência do fardo desse item
                item_dados = df_estoque[df_estoque['Nome'] == nome_selecionado].iloc[0]
                try: qtd_fardo_ref = int(item_dados['Qtd_Fardo']) # Tenta ler coluna 8
                except: qtd_fardo_ref = 12
            else:
                st.warning("Nenhum item cadastrado. Escolha 'Cadastrar Novo'.")
        else:
            nome_digitado = st.text_input("Nome do Novo Produto:").upper()
            tipo = st.selectbox("Tipo:", ["Lata", "Long Neck", "Garrafa 600ml", "Litro/Outros"])
            nome_final = f"{nome_digitado} ({tipo})" if nome_digitado else ""
            
        st.divider()
        
        # 2. DADOS DA COMPRA (INTELIGÊNCIA DE CUSTO)
        col_forma, col_vals = st.columns([1, 2])
        
        with col_forma:
            st.write("Como você comprou?")
            forma_compra = st.radio("Formato:", ["Fardo Fechado", "Unidades Soltas"])
            data_compra = st.date_input("Data da Compra", date.today())
            fornecedor = st.text_input("Fornecedor")

        with col_vals:
            custo_unitario_novo = 0.0
            qtd_total_adicionada = 0
            
            if forma_compra == "Fardo Fechado":
                custo_fardo = st.number_input("Valor pago no FARDO (R$)", min_value=0.0, format="%.2f")
                # Referência do Fardo
                qtd_dentro = st.selectbox("Quantas vêm no fardo?", list(range(1, 25)), index=11)
                qtd_fardos_compra = st.number_input("Quantos FARDOS comprou?", min_value=1, step=1)
                
                if qtd_dentro > 0:
                    custo_unitario_novo = custo_fardo / qtd_dentro
                    qtd_total_adicionada = qtd_fardos_compra * qtd_dentro
                    qtd_fardo_ref = qtd_dentro # Atualiza a referência
            else:
                custo_unit = st.number_input("Valor pago na UNIDADE (R$)", min_value=0.0, format="%.2f")
                qtd_soltas_compra = st.number_input("Quantas UNIDADES comprou?", min_value=1, step=1)
                # Pergunta a referência mesmo comprando solto
                qtd_fardo_ref = st.selectbox("Tamanho padrão do fardo (Ref):", list(range(1, 25)), index=11)
                
                custo_unitario_novo = custo_unit
                qtd_total_adicionada = qtd_soltas_compra

            # Preço de Venda (Sempre manual ou mantem o antigo se for edição)
            preco_venda = st.number_input("Preço de Venda Unitário (R$)", min_value=0.0, format="%.2f")

        # 3. BOTÃO DE SALVAR COM CUSTO MÉDIO
        if st.button("💾 Atualizar Estoque (Custo Médio)", type="primary"):
            if nome_final and qtd_total_adicionada > 0:
                with st.spinner("Calculando custo médio e salvando..."):
                    encontrado = False
                    idx_planilha = 2
                    
                    if not df_estoque.empty:
                        for i, row in df_estoque.iterrows():
                            if row['Nome'] == nome_final:
                                # DADOS ANTIGOS
                                estoque_antigo = int(row['Estoque'])
                                custo_antigo = converter_valor(row['Custo'])
                                
                                # CÁLCULO CUSTO MÉDIO
                                valor_estoque_antigo = estoque_antigo * custo_antigo
                                valor_compra_nova = qtd_total_adicionada * custo_unitario_novo
                                novo_total_estoque = estoque_antigo + qtd_total_adicionada
                                
                                if novo_total_estoque > 0:
                                    novo_custo_medio = (valor_estoque_antigo + valor_compra_nova) / novo_total_estoque
                                else:
                                    novo_custo_medio = custo_unitario_novo
                                
                                # ATUALIZAR CÉLULAS
                                sheet_estoque.update_cell(idx_planilha + i, 6, novo_total_estoque) # Estoque
                                sheet_estoque.update_cell(idx_planilha + i, 4, novo_custo_medio)   # Custo Médio
                                sheet_estoque.update_cell(idx_planilha + i, 5, preco_venda)        # Venda
                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor)         # Fornecedor
                                sheet_estoque.update_cell(idx_planilha + i, 7, data_compra.strftime('%d/%m/%Y')) # Data (Col 7)
                                # Tenta salvar a Referencia do Fardo na Coluna 8 (Se existir, senao ignora pra nao dar erro)
                                try: sheet_estoque.update_cell(idx_planilha + i, 8, qtd_fardo_ref)
                                except: pass 
                                
                                encontrado = True
                                break
                    
                    if not encontrado:
                        # CRIA NOVO (Nome, Tipo, Forn, Custo, Venda, Estoque, Data, Qtd_Fardo)
                        sheet_estoque.append_row([
                            nome_final, 
                            "Geral", 
                            fornecedor, 
                            custo_unitario_novo, 
                            preco_venda, 
                            qtd_total_adicionada, 
                            data_compra.strftime('%d/%m/%Y'),
                            qtd_fardo_ref
                        ])
                    
                    # LOG
                    sheet_hist_est.append_row([pegar_data_hora(), nome_final, "COMPRA", qtd_total_adicionada, qtd_total_adicionada*custo_unitario_novo, f"Forn: {fornecedor}"])
                    
                    st.success(f"✅ Sucesso! {qtd_total_adicionada}x {nome_final} inseridos.")
                    time.sleep(2)
                    st.rerun()
            else:
                st.error("Preencha o nome e quantidade.")

    with aba_ver:
        if not df_estoque.empty:
            busca = st.text_input("🔍 Buscar Estoque:").upper()
            if busca: df_estoque = df_estoque[df_estoque['Nome'].str.contains(busca, case=False)]
            
            # Formatação Visual
            df_display = df_estoque.copy()
            # Tenta mostrar visualmente fardos + soltas se tiver a coluna 8
            if 'Qtd_Fardo' in df_display.columns:
                df_display['Visual'] = df_display.apply(lambda x: f"{int(x['Estoque']//(x['Qtd_Fardo'] or 12))} Fardos + {int(x['Estoque']%(x['Qtd_Fardo'] or 12))} Un", axis=1)
                st.dataframe(df_display[['Nome', 'Visual', 'Estoque', 'Venda', 'Custo']], use_container_width=True)
            else:
                st.dataframe(df_display, use_container_width=True)
        else:
            st.info("Vazio.")

# ==========================================
# 💰 FIDELIDADE & CAIXA (INTEGRAÇÃO TOTAL)
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    st.title("💰 Caixa & Fidelidade")
    
    # Carregar Dados
    df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
    df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
    
    # 1. IDENTIFICAÇÃO DO CLIENTE (COM SELECTBOX BONITO)
    st.markdown("### 👤 Quem é o cliente?")
    
    # Cria lista inteligente para o selectbox
    lista_clientes_display = ["🆕 NOVO CLIENTE"]
    dict_clientes = {} # Para achar rápido
    
    if not df_clientes.empty:
        # Cria formato "NOME - TELEFONE"
        df_clientes['Display'] = df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)
        lista_clientes_db = df_clientes['Display'].tolist()
        lista_clientes_display += lista_clientes_db
        # Dicionário auxiliar
        for idx, row in df_clientes.iterrows():
            dict_clientes[row['Display']] = row['telefone']
            
    # O SELETOR BONITO
    cliente_selecionado = st.selectbox("Selecione ou Cadastre:", lista_clientes_display)
    
    col_nome, col_tel = st.columns(2)
    if cliente_selecionado == "🆕 NOVO CLIENTE":
        nome_input = col_nome.text_input("Nome Completo:").strip().upper()
        tel_input = col_tel.text_input("Telefone:", placeholder="88999990000")
    else:
        # Preenche automático
        dados_nome = cliente_selecionado.split(" - ")[0]
        dados_tel = dict_clientes.get(cliente_selecionado, "")
        
        nome_input = col_nome.text_input("Nome:", value=dados_nome, disabled=True)
        tel_input = col_tel.text_input("Telefone:", value=dados_tel, disabled=True)
        
    tel_limpo = limpar_telefone("+55" + str(tel_input))

    st.divider()

    # 2. O CARRINHO (FARDO E UNIDADE)
    st.markdown("### 🛒 O que ele está levando?")
    
    if not df_estoque.empty:
        # Lista de Produtos
        lista_prod = ["(Apenas Pontuar - Sem Baixa)"] + df_estoque['Nome'].tolist()
        prod_escolhido = st.selectbox("Produto:", lista_prod)
        
        # ÁREA DE QUANTIDADE INTELIGENTE
        st.write("Quantidade:")
        c_fardo, c_unid = st.columns(2)
        
        # Opções limitadas como pediu
        qtd_fardos_venda = c_fardo.selectbox("Quantos FARDOS?", list(range(0, 11))) # 0 a 10
        qtd_soltas_venda = c_unid.selectbox("Quantas UNIDADES?", list(range(0, 41))) # 0 a 40
        
        # Preview do Total
        tamanho_fardo_real = 12 # Default
        if prod_escolhido != "(Apenas Pontuar - Sem Baixa)":
            item_data = df_estoque[df_estoque['Nome'] == prod_escolhido].iloc[0]
            try: tamanho_fardo_real = int(item_data['Qtd_Fardo'])
            except: tamanho_fardo_real = 12 # Fallback
            
        total_unidades_venda = (qtd_fardos_venda * tamanho_fardo_real) + qtd_soltas_venda
        
        if total_unidades_venda > 0:
            st.info(f"🧾 Total a baixar: **{total_unidades_venda} garrafas** ({qtd_fardos_venda} fardos de {tamanho_fardo_real} + {qtd_soltas_venda} soltas)")
    else:
        st.warning("Estoque vazio. Cadastre produtos primeiro.")
        prod_escolhido = "(Apenas Pontuar - Sem Baixa)"
        total_unidades_venda = 0

    st.divider()

    # 3. BOTÃO DE AÇÃO
    if st.button("✅ CONFIRMAR VENDA", type="primary"):
        erro = False
        if not nome_input: 
            st.error("Falta o nome do cliente."); erro = True
        
        if not erro:
            with st.spinner("Processando..."):
                
                # A: BAIXA DE ESTOQUE (Se selecionado)
                nome_produto_real = "Pontos"
                if prod_escolhido != "(Apenas Pontuar - Sem Baixa)" and total_unidades_venda > 0:
                    nome_produto_real = prod_escolhido
                    # Busca índice
                    idx_est = -1
                    est_atual = 0
                    for i, r in df_estoque.iterrows():
                        if r['Nome'] == prod_escolhido:
                            idx_est = i + 2
                            est_atual = int(r['Estoque'])
                            venda_val = float(r['Venda'])
                            break
                    
                    if idx_est != -1:
                        if est_atual >= total_unidades_venda:
                            sheet_estoque.update_cell(idx_est, 6, est_atual - total_unidades_venda)
                            sheet_hist_est.append_row([pegar_data_hora(), nome_produto_real, "VENDA", total_unidades_venda, total_unidades_venda*venda_val, f"Cli: {nome_input}"])
                        else:
                            st.error(f"Estoque insuficiente! Tem {est_atual}, tentou vender {total_unidades_venda}.")
                            st.stop()
                
                # B: FIDELIDADE
                cliente_ja_existe = False
                row_cli = -1
                pts_old = 0
                
                if not df_clientes.empty:
                    df_clientes['telefone'] = df_clientes['telefone'].astype(str)
                    match = df_clientes[df_clientes['telefone'] == str(tel_limpo)]
                    if not match.empty:
                        cliente_ja_existe = True
                        row_cli = match.index[0] + 2
                        pts_old = int(match.iloc[0]['compras'])
                
                if cliente_ja_existe:
                    novos_pts = pts_old + 1
                    sheet_clientes.update_cell(row_cli, 3, novos_pts)
                    sheet_clientes.update_cell(row_cli, 4, pegar_data_hora())
                else:
                    novos_pts = 1
                    sheet_clientes.append_row([nome_input, tel_limpo, 1, pegar_data_hora()])
                
                sheet_hist_cli.append_row([pegar_data_hora(), nome_input, tel_limpo, f"Levou: {nome_produto_real} ({total_unidades_venda}un)"])
                
                # ZAP
                msg, btn_txt = gerar_mensagem_zap(nome_input, novos_pts, nome_produto_real)
                link = f"https://api.whatsapp.com/send?phone={tel_limpo}&text={urllib.parse.quote(msg)}"
                
                st.success("Venda Concluída!")
                st.markdown(f"### [📲 Enviar WhatsApp]({link})")
                time.sleep(3)
                st.rerun()

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios")
    c1, c2 = st.columns(2)
    with c1: 
        st.write("Estoque Log")
        st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
    with c2:
        st.write("Clientes Log")
        st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
