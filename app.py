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
    page_title="Super Adega 5.0",
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
                border-color: #ff4b4b;
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
def limpar_telefone_bruto(tel):
    """Remove tudo que não for número"""
    return re.sub(r'\D', '', str(tel))

def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
def converter_valor(v): 
    try: return float(str(v).replace(',', '.')) 
    except: return 0.0
def formatar_moeda(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_mensagem_zap(nome, total, prod):
    """CORRIGIDO: Agora aceita 3 argumentos (nome, total, produto)"""
    if total == 1: 
        msg = f"Olá {nome}! Bem-vindo à Adega! 🍷\nVocê levou: {prod}.\nSaldo Fidelidade: 1 ponto."
        btn = "Enviar Boas-Vindas 🎉"
    elif total < 9: 
        msg = f"Olá {nome}! Obrigado pela preferência!\nVocê levou: {prod}.\nSaldo Fidelidade: {total}/10 pontos."
        btn = f"Enviar Saldo ({total}/10) 📲"
    elif total == 9: 
        msg = f"UAU {nome}! Falta só 1 compra para o prémio! 😱"
        btn = "🚨 AVISAR (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome}! Ganhou seu PRÊMIO! 🏆"
        btn = "🏆 ENVIAR PRÉMIO"
    return msg, btn

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu")
    st.link_button("📂 Abrir Planilha", URL_PLANILHA)
    st.divider()
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "👥 Gerenciar Clientes", "📊 Relatórios"])
    st.markdown("---")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 GESTÃO DE ESTOQUE
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    
    aba_cad, aba_ver = st.tabs(["📝 Entrada (Compra)", "📋 Ver Estoque & Lucro"])
    
    try:
        dados_raw = sheet_estoque.get_all_records()
        df_estoque = pd.DataFrame(dados_raw)
    except: df_estoque = pd.DataFrame()
    
    with aba_cad:
        st.subheader("Registrar Compra")
        
        lista_nomes = df_estoque['Nome'].unique().tolist() if not df_estoque.empty else []
        modo_cadastro = st.radio("Produto:", ["Selecionar Existente", "Cadastrar Novo"], horizontal=True)
        
        nome_final = ""
        qtd_fardo_ref = 12 
        
        if modo_cadastro == "Selecionar Existente":
            if lista_nomes:
                nome_selecionado = st.selectbox("Escolha o Item:", lista_nomes)
                nome_final = nome_selecionado
                item_dados = df_estoque[df_estoque['Nome'] == nome_selecionado].iloc[0]
                try: qtd_fardo_ref = int(item_dados['Qtd_Fardo'])
                except: qtd_fardo_ref = 12
            else:
                st.warning("Nenhum item cadastrado.")
        else:
            nome_digitado = st.text_input("Nome do Novo Produto:", placeholder="Ex: Skol Lata").upper()
            tipo = st.selectbox("Tipo:", ["Lata", "Long Neck", "Garrafa 600ml", "Litro/Outros"])
            nome_final = f"{nome_digitado} ({tipo})" if nome_digitado else ""
            
        st.divider()
        
        col_forma, col_vals = st.columns([1, 2])
        
        with col_forma:
            st.write("Como você comprou?")
            forma_compra = st.radio("Formato:", ["Fardo Fechado", "Unidades Soltas"])
            data_compra = st.date_input("Data da Compra", date.today())
            fornecedor = st.text_input("Fornecedor", placeholder="Ex: Atacadão")

        with col_vals:
            custo_unitario_novo = 0.0
            qtd_total_adicionada = 0
            
            if forma_compra == "Fardo Fechado":
                custo_fardo = st.number_input("Valor pago no FARDO (R$)", min_value=0.0, format="%.2f")
                qtd_dentro = st.selectbox("Quantas vêm no fardo?", list(range(1, 25)), index=11)
                qtd_fardos_compra = st.number_input("Quantos FARDOS comprou?", min_value=0, step=1)
                
                if qtd_dentro > 0:
                    custo_unitario_novo = custo_fardo / qtd_dentro
                    qtd_total_adicionada = qtd_fardos_compra * qtd_dentro
                    qtd_fardo_ref = qtd_dentro
            else:
                custo_unit = st.number_input("Valor pago na UNIDADE (R$)", min_value=0.0, format="%.2f")
                qtd_soltas_compra = st.number_input("Quantas UNIDADES comprou?", min_value=0, step=1)
                qtd_fardo_ref = st.selectbox("Tamanho padrão do fardo (Ref):", list(range(1, 25)), index=11)
                custo_unitario_novo = custo_unit
                qtd_total_adicionada = qtd_soltas_compra

            preco_venda = st.number_input("Preço de Venda Unitário (R$)", min_value=0.0, format="%.2f")

        if st.button("💾 Salvar Estoque", type="primary"):
            if nome_final and qtd_total_adicionada > 0:
                with st.spinner("Calculando e Salvando..."):
                    encontrado = False
                    idx_planilha = 2
                    
                    if not df_estoque.empty:
                        for i, row in df_estoque.iterrows():
                            if row['Nome'] == nome_final:
                                estoque_antigo = int(row['Estoque'])
                                custo_antigo = converter_valor(row['Custo'])
                                
                                # Custo Médio Ponderado
                                valor_antigo = estoque_antigo * custo_antigo
                                valor_novo = qtd_total_adicionada * custo_unitario_novo
                                novo_total = estoque_antigo + qtd_total_adicionada
                                novo_custo = (valor_antigo + valor_novo) / novo_total if novo_total > 0 else custo_unitario_novo
                                
                                sheet_estoque.update_cell(idx_planilha + i, 6, novo_total)
                                sheet_estoque.update_cell(idx_planilha + i, 4, novo_custo)
                                sheet_estoque.update_cell(idx_planilha + i, 5, preco_venda)
                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor)
                                sheet_estoque.update_cell(idx_planilha + i, 7, data_compra.strftime('%d/%m/%Y'))
                                try: sheet_estoque.update_cell(idx_planilha + i, 8, qtd_fardo_ref)
                                except: pass
                                
                                encontrado = True
                                break
                    
                    if not encontrado:
                        # Ordem: Nome|Tipo|Forn|Custo|Venda|Estoque|Data|QtdFardo
                        sheet_estoque.append_row([nome_final, "Geral", fornecedor, custo_unitario_novo, preco_venda, qtd_total_adicionada, data_compra.strftime('%d/%m/%Y'), qtd_fardo_ref])
                    
                    sheet_hist_est.append_row([pegar_data_hora(), nome_final, "COMPRA", qtd_total_adicionada, f"R$ {qtd_total_adicionada*custo_unitario_novo:.2f}", f"Forn: {fornecedor}"])
                    
                    st.success(f"✅ {qtd_total_adicionada}x {nome_final} adicionados.")
                    time.sleep(1.5)
                    st.rerun()
            else:
                st.error("Preencha o nome e quantidade maior que 0.")

    with aba_ver:
        if not df_estoque.empty:
            busca = st.text_input("🔍 Buscar Estoque:", placeholder="Digite o nome...").upper()
            if busca: df_estoque = df_estoque[df_estoque['Nome'].str.contains(busca, case=False)]
            
            df_display = df_estoque.copy()
            
            # Cálculos Financeiros
            df_display['Custo'] = df_display['Custo'].apply(converter_valor)
            df_display['Venda'] = df_display['Venda'].apply(converter_valor)
            df_display['Lucro Un.'] = df_display['Venda'] - df_display['Custo']
            
            # Formatação
            df_display['Custo Médio'] = df_display['Custo'].apply(formatar_moeda)
            df_display['Preço Venda'] = df_display['Venda'].apply(formatar_moeda)
            df_display['Lucro Líquido'] = df_display['Lucro Un.'].apply(formatar_moeda)
            
            if 'Qtd_Fardo' in df_display.columns:
                df_display['Visual Estoque'] = df_display.apply(lambda x: f"{int(x['Estoque']//(x['Qtd_Fardo'] or 12))} Fardos + {int(x['Estoque']%(x['Qtd_Fardo'] or 12))} Un", axis=1)
            else:
                df_display['Visual Estoque'] = df_display['Estoque']

            cols_show = ['Nome', 'Visual Estoque', 'Preço Venda', 'Custo Médio', 'Lucro Líquido', 'Data']
            if 'Data' not in df_display.columns: df_display['Data'] = "-"
            
            st.dataframe(df_display[cols_show], use_container_width=True, hide_index=True)
        else:
            st.info("Estoque vazio.")

# ==========================================
# 💰 FIDELIDADE & CAIXA
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    st.title("💰 Caixa & Fidelidade")
    
    # Recarrega dados
    df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
    df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
    
    # 1. IDENTIFICAÇÃO (CORREÇÃO DE DUPLICIDADE)
    st.markdown("### 👤 Quem é o cliente?")
    
    lista_clientes_display = ["🆕 NOVO CLIENTE"]
    dict_clientes = {}
    
    if not df_clientes.empty:
        # Cria chave limpa para evitar erro
        df_clientes['tel_limpo'] = df_clientes['telefone'].apply(limpar_telefone_bruto)
        
        df_clientes['Display'] = df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)
        lista_clientes_display += df_clientes['Display'].tolist()
        for idx, row in df_clientes.iterrows():
            dict_clientes[row['Display']] = row['telefone']
            
    cliente_selecionado = st.selectbox("Selecione ou Cadastre:", lista_clientes_display)
    
    col_nome, col_tel = st.columns(2)
    
    is_new_client = False
    if cliente_selecionado == "🆕 NOVO CLIENTE":
        is_new_client = True
        nome_input = col_nome.text_input("Nome Completo:", placeholder="Digite o nome...").strip().upper()
        tel_input = col_tel.text_input("Telefone:", placeholder="88999990000")
    else:
        dados_nome = cliente_selecionado.split(" - ")[0]
        dados_tel = dict_clientes.get(cliente_selecionado, "")
        nome_input = col_nome.text_input("Nome:", value=dados_nome, disabled=True)
        tel_input = col_tel.text_input("Telefone:", value=dados_tel, disabled=True)
        
    # Limpa o input atual para comparação
    tel_input_limpo = limpar_telefone_bruto(tel_input)

    st.divider()

    # 2. CARRINHO
    st.markdown("### 🛒 O que ele está levando?")
    
    if not df_estoque.empty:
        df_estoque['Menu'] = df_estoque.apply(lambda x: f"{x['Nome']} (Estoque: {x['Estoque']})", axis=1)
        lista_prod = ["(Apenas Pontuar - Sem Produto)"] + df_estoque['Menu'].tolist()
        prod_escolhido_menu = st.selectbox("Produto:", lista_prod)
        
        if prod_escolhido_menu != "(Apenas Pontuar - Sem Produto)":
            nome_produto_real = prod_escolhido_menu.split(" (Estoque:")[0]
        else:
            nome_produto_real = "(Apenas Pontuar - Sem Produto)"

        st.write("Quantidade:")
        c_fardo, c_unid = st.columns(2)
        
        qtd_fardos_venda = c_fardo.selectbox("Quantos FARDOS?", list(range(0, 11)))
        qtd_soltas_venda = c_unid.selectbox("Quantas UNIDADES?", list(range(0, 41)))
        
        tamanho_fardo_real = 12
        if nome_produto_real != "(Apenas Pontuar - Sem Produto)":
            item_data = df_estoque[df_estoque['Nome'] == nome_produto_real].iloc[0]
            try: tamanho_fardo_real = int(item_data['Qtd_Fardo'])
            except: tamanho_fardo_real = 12
            
        total_unidades_venda = (qtd_fardos_venda * tamanho_fardo_real) + qtd_soltas_venda
        
        if total_unidades_venda > 0:
            st.info(f"🧾 Baixando: **{total_unidades_venda} garrafas** de {nome_produto_real}")
    else:
        st.warning("Estoque vazio.")
        nome_produto_real = "(Apenas Pontuar - Sem Produto)"
        total_unidades_venda = 0

    st.divider()

    # 3. BOTÃO DE AÇÃO
    if st.button("✅ CONFIRMAR VENDA", type="primary"):
        erro = False
        if not nome_input: 
            st.error("Falta o nome do cliente."); erro = True
        
        if not erro:
            with st.spinner("Processando..."):
                
                # A: BAIXA DE ESTOQUE
                if nome_produto_real != "(Apenas Pontuar - Sem Produto)" and total_unidades_venda > 0:
                    idx_est = -1
                    est_atual = 0
                    
                    for i, r in df_estoque.iterrows():
                        if r['Nome'] == nome_produto_real:
                            idx_est = i + 2
                            est_atual = int(r['Estoque'])
                            venda_val = converter_valor(r['Venda'])
                            break
                    
                    if idx_est != -1:
                        if est_atual >= total_unidades_venda:
                            sheet_estoque.update_cell(idx_est, 6, est_atual - total_unidades_venda)
                            total_monetario = total_unidades_venda * venda_val
                            sheet_hist_est.append_row([pegar_data_hora(), nome_produto_real, "VENDA", total_unidades_venda, f"R$ {total_monetario:.2f}", f"Cli: {nome_input}"])
                        else:
                            st.error(f"Estoque insuficiente! Tem {est_atual}, tentou vender {total_unidades_venda}.")
                            st.stop()
                
                elif nome_produto_real != "(Apenas Pontuar - Sem Produto)" and total_unidades_venda == 0:
                    nome_produto_real = f"Visita ({nome_produto_real} - Qtd 0)"
                
                # B: FIDELIDADE (ANTI-DUPLICIDADE RIGOROSO)
                cliente_ja_existe = False
                row_cli = -1
                pts_old = 0
                
                if not df_clientes.empty:
                    # Compara usando a coluna limpa
                    match = df_clientes[df_clientes['tel_limpo'] == tel_input_limpo]
                    if not match.empty:
                        cliente_ja_existe = True
                        row_cli = match.index[0] + 2
                        pts_old = int(match.iloc[0]['compras'])
                
                if cliente_ja_existe:
                    # ATUALIZA
                    novos_pts = pts_old + 1
                    sheet_clientes.update_cell(row_cli, 3, novos_pts)
                    sheet_clientes.update_cell(row_cli, 4, pegar_data_hora())
                    if is_new_client: 
                         sheet_clientes.update_cell(row_cli, 1, nome_input)
                else:
                    # CADASTRA NOVO
                    novos_pts = 1
                    sheet_clientes.append_row([nome_input, tel_input, 1, pegar_data_hora()])
                
                # Log
                msg_hist = f"Venda: {nome_produto_real}" if total_unidades_venda > 0 else f"Ponto: {nome_produto_real}"
                sheet_hist_cli.append_row([pegar_data_hora(), nome_input, tel_input, msg_hist])
                
                # ZAP (ARGUMENTOS CORRIGIDOS)
                msg, btn_txt = gerar_mensagem_zap(nome_input, novos_pts, nome_produto_real)
                # Usa o telefone digitado (mas limpo de caracteres especiais) para o link
                link = f"https://api.whatsapp.com/send?phone={tel_input_limpo}&text={urllib.parse.quote(msg)}"
                
                st.success("Venda Concluída!")
                st.markdown(f"### [📲 Enviar WhatsApp]({link})")
                time.sleep(3)
                st.rerun()

# ==========================================
# 👥 GERENCIAR CLIENTES
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Gerenciar Clientes")
    try: df_cli_edit = pd.DataFrame(sheet_clientes.get_all_records())
    except: df_cli_edit = pd.DataFrame()

    if not df_cli_edit.empty:
        df_cli_edit['Display'] = df_cli_edit['nome'] + " - " + df_cli_edit['telefone'].astype(str)
        lista_edit = ["Selecione..."] + df_cli_edit['Display'].tolist()
        escolha_edit = st.selectbox("Buscar:", lista_edit)
        
        if escolha_edit != "Selecione...":
            idx_edit = df_cli_edit[df_cli_edit['Display'] == escolha_edit].index[0]
            row_edit = df_cli_edit.iloc[idx_edit]
            linha_sheet_edit = idx_edit + 2
            
            with st.form("form_edicao"):
                c1, c2, c3 = st.columns(3)
                novo_nome = c1.text_input("Nome", value=row_edit['nome'])
                novo_tel = c2.text_input("Telefone", value=row_edit['telefone'])
                novos_pts = c3.number_input("Pontos", value=int(row_edit['compras']), step=1)
                
                col_save, col_del = st.columns(2)
                salvar = col_save.form_submit_button("💾 Salvar Alterações")
                deletar = col_del.form_submit_button("🗑️ EXCLUIR CLIENTE", type="primary")
                
                if salvar:
                    sheet_clientes.update_cell(linha_sheet_edit, 1, novo_nome)
                    sheet_clientes.update_cell(linha_sheet_edit, 2, novo_tel)
                    sheet_clientes.update_cell(linha_sheet_edit, 3, novos_pts)
                    st.success("Atualizado!")
                    st.rerun()
                
                if deletar:
                    sheet_clientes.delete_rows(linha_sheet_edit)
                    st.warning("Cliente excluído!")
                    st.rerun()
    else: st.warning("Sem clientes.")

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios")
    c1, c2 = st.columns(2)
    with c1: 
        st.subheader("Estoque Log")
        try: 
            df_re = pd.DataFrame(sheet_hist_est.get_all_records())
            st.dataframe(df_re, use_container_width=True, hide_index=True)
        except: st.write("Vazio")
    with c2:
        st.subheader("Clientes Log")
        try: 
            df_rc = pd.DataFrame(sheet_hist_cli.get_all_records())
            st.dataframe(df_rc, use_container_width=True, hide_index=True)
        except: st.write("Vazio")
