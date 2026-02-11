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
    page_title="Super Adega 12.0",
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
            .big-btn {
                background-color: #25D366; 
                color: white; 
                padding: 15px; 
                border-radius: 10px; 
                text-align: center; 
                font-weight: bold; 
                font-size: 20px; 
                margin-top: 10px;
                text-decoration: none;
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
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False
if 'link_zap_atual' not in st.session_state: st.session_state.link_zap_atual = ""
if 'msg_zap_btn' not in st.session_state: st.session_state.msg_zap_btn = ""

def verificar_sessao():
    if st.session_state.logado:
        agora = time.time()
        tempo_passado = agora - st.session_state.ultima_atividade
        if tempo_passado > (TEMPO_LIMITE_MINUTOS * 60):
            st.session_state.logado = False
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
        st.rerun()
    else:
        st.title("🔒 Acesso Restrito")
        with st.form("login_form"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR"):
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

# --- 🧮 FUNÇÕES DE CORREÇÃO MATEMÁTICA ---
def limpar_telefone(tel): return re.sub(r'\D', '', str(tel))
def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

def ler_numero_input(valor):
    """Garante que '2,92' vire '2.92' para o Python não calcular milhões"""
    if valor is None or str(valor).strip() == "": return 0.0
    val_str = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try: return float(val_str)
    except: return 0.0

def float_para_sheets(valor):
    """Manda de volta para o Sheets com vírgula para não bugar"""
    return f"{valor:.2f}".replace(".", ",")

def formatar_moeda_visual(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- 📱 MENSAGEM WHATSAPP ---
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

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu")
    st.link_button("📂 Abrir Planilha", URL_PLANILHA)
    st.divider()
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "👥 Gerenciar Clientes", "📊 Relatórios"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 GESTÃO DE ESTOQUE
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    aba_cad, aba_edit, aba_ver = st.tabs(["📝 Entrada", "✏️ Editar/Excluir", "📋 Lista"])
    
    try:
        dados_raw = sheet_estoque.get_all_records()
        df_estoque = pd.DataFrame(dados_raw)
    except: df_estoque = pd.DataFrame()

    with aba_cad:
        st.subheader("Registrar Compra")
        lista_nomes = df_estoque['Nome'].unique().tolist() if not df_estoque.empty else []
        modo = st.radio("Produto:", ["Existente", "Novo"], horizontal=True)
        
        nome_final = ""
        qtd_fardo_ref = 12 
        
        if modo == "Existente":
            if lista_nomes:
                nome_sel = st.selectbox("Escolha:", lista_nomes)
                nome_final = nome_sel
                item_dados = df_estoque[df_estoque['Nome'] == nome_sel].iloc[0]
                try: qtd_fardo_ref = int(ler_numero_input(item_dados['Qtd_Fardo']))
                except: qtd_fardo_ref = 12
            else: st.warning("Estoque vazio.")
        else:
            nome_final = st.text_input("Nome do Produto:").upper()
            
        c1, c2, c3 = st.columns(3)
        custo_f = c1.text_input("Preço Fardo (R$):", placeholder="36,70")
        qtd_f = c2.text_input("Quantos fardos?", placeholder="1")
        venda_u = c3.text_input("Venda Unidade (R$):", placeholder="4,49")

        if st.button("💾 Salvar Entrada"):
            v_custo = ler_numero_input(custo_f)
            v_qtd = ler_numero_input(qtd_f)
            v_venda = ler_numero_input(venda_u)
            
            if v_custo > 0 and v_qtd > 0:
                custo_un_novo = v_custo / qtd_fardo_ref
                total_itens = int(v_qtd * qtd_fardo_ref)
                
                if modo == "Existente":
                    idx = df_estoque[df_estoque['Nome'] == nome_final].index[0]
                    est_antigo = ler_numero_input(df_estoque.iloc[idx]['Estoque'])
                    custo_antigo = ler_numero_input(df_estoque.iloc[idx]['Custo'])
                    
                    if custo_antigo > 1000: custo_antigo = custo_un_novo # Limpa erro de milhão
                    
                    novo_total = est_antigo + total_itens
                    novo_custo = ((est_antigo * custo_antigo) + (total_itens * custo_un_novo)) / novo_total
                    
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 4, float_para_sheets(novo_custo))
                    sheet_estoque.update_cell(idx+2, 5, float_para_sheets(v_venda))
                else:
                    sheet_estoque.append_row([nome_final, "Geral", "", float_para_sheets(custo_un_novo), float_para_sheets(v_venda), total_itens, date.today().strftime('%d/%m/%Y'), qtd_fardo_ref])
                
                st.success("Salvo!")
                st.rerun()

    with aba_edit:
        if not df_estoque.empty:
            prod_edit = st.selectbox("Selecione para excluir:", ["Selecione..."] + df_estoque['Nome'].tolist())
            if prod_edit != "Selecione...":
                idx = df_estoque[df_estoque['Nome'] == prod_edit].index[0]
                if st.button("🗑️ DELETAR ITEM"):
                    sheet_estoque.delete_rows(int(idx + 2))
                    st.rerun()

    with aba_ver:
        if not df_estoque.empty:
            df_display = df_estoque.copy()
            df_display['Custo'] = df_display['Custo'].apply(ler_numero_input)
            df_display['Venda'] = df_display['Venda'].apply(ler_numero_input)
            df_display['Lucro Real'] = df_display['Venda'] - df_display['Custo']
            st.dataframe(df_display[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro Real']], 
                         column_config={"Venda": st.column_config.NumberColumn(format="R$ %.2f"),
                                        "Custo": st.column_config.NumberColumn(format="R$ %.2f"),
                                        "Lucro Real": st.column_config.NumberColumn(format="R$ %.2f")}, use_container_width=True)

# ==========================================
# 💰 FIDELIDADE & CAIXA
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    if st.session_state.venda_sucesso:
        st.success("✅ Venda Registrada!")
        st.markdown(f'<a href="{st.session_state.link_zap_atual}" target="_blank" class="big-btn">{st.session_state.msg_zap_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
        df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_c = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)).tolist())
        
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO":
            nome_c = c1.text_input("Nome:").upper()
            tel_c = c2.text_input("Tel:")
        else:
            nome_c = sel_c.split(" - ")[0]
            tel_c = sel_c.split(" - ")[1]
        
        prod_v = st.selectbox("Produto:", ["(Ponto)"] + df_estoque['Nome'].tolist())
        q_f = st.number_input("Fardos:", min_value=0, step=1)
        q_u = st.number_input("Unidades:", min_value=0, step=1)

        if st.button("✅ CONFIRMAR"):
            t_limpo = limpar_telefone(tel_c)
            # Baixa estoque
            if prod_v != "(Ponto)":
                idx_e = df_estoque[df_estoque['Nome'] == prod_v].index[0]
                ref = int(ler_numero_input(df_estoque.iloc[idx_e]['Qtd_Fardo']))
                baixa = (q_f * ref) + q_u
                novo_est = int(ler_numero_input(df_estoque.iloc[idx_e]['Estoque'])) - baixa
                sheet_estoque.update_cell(idx_e + 2, 6, novo_est)

            # Pontos (Busca por Telefone Limpo)
            df_clientes['tel_purged'] = df_clientes['telefone'].apply(limpar_telefone)
            match = df_clientes[df_clientes['tel_purged'] == t_limpo]
            
            if not match.empty:
                novos_pts = int(ler_numero_input(match.iloc[0]['compras'])) + 1
                sheet_clientes.update_cell(int(match.index[0] + 2), 3, novos_pts)
            else:
                novos_pts = 1
                sheet_clientes.append_row([nome_c, t_limpo, 1, date.today().strftime('%d/%m/%Y')])

            msg, btn = gerar_mensagem_zap(nome_c, novos_pts)
            st.session_state.link_zap_atual = f"https://api.whatsapp.com/send?phone=55{t_limpo}&text={urllib.parse.quote(msg)}"
            st.session_state.msg_zap_btn = btn
            st.session_state.venda_sucesso = True
            st.rerun()

# ==========================================
# 👥 GERENCIAR CLIENTES
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Clientes")
    df_cli = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_cli.empty:
        df_cli['Display'] = df_cli['nome'] + " - " + df_cli['telefone'].astype(str)
        sel_edit = st.selectbox("Escolha:", df_cli['Display'].tolist())
        idx_ed = df_cli[df_cli['Display'] == sel_edit].index[0]
        
        if st.button("🗑️ EXCLUIR CLIENTE"):
            sheet_clientes.delete_rows(int(idx_ed + 2))
            st.rerun()

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Dados")
    st.write("Estoque")
    st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()))
    st.write("Fidelidade")
    st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()))
