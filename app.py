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
st.set_page_config(page_title="Super Adega 12.0", page_icon="🍷", layout="wide", initial_sidebar_state="expanded")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;} 
            footer {visibility: hidden;} 
            .stSelectbox div[data-baseweb="select"] > div:first-child { border-color: #ff4b4b; }
            .big-btn {
                background-color: #25D366; color: white; padding: 15px; border-radius: 10px; 
                text-align: center; font-weight: bold; font-size: 20px; margin-top: 10px;
                text-decoration: none; display: block;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN E SESSÃO
# ==========================================
SENHA_DO_SISTEMA = "adega123" 

if 'logado' not in st.session_state: st.session_state.logado = False
if 'validando' not in st.session_state: st.session_state.validando = False
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False

if not st.session_state.logado:
    if st.session_state.validando:
        st.write("Abrindo Adega...")
        time.sleep(1)
        st.session_state.logado = True
        st.session_state.validando = False
        st.rerun()
    else:
        with st.form("login"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR"):
                if senha == SENHA_DO_SISTEMA:
                    st.session_state.validando = True
                    st.rerun()
                else: st.error("Senha incorreta")
        st.stop()

# ==========================================
# 📡 CONEXÃO GOOGLE SHEETS
# ==========================================
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
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# --- 🧮 FUNÇÕES DE TRATAMENTO DE NÚMEROS (RESOLVE O ERRO DOS MILHÕES) ---
def para_python(valor_str):
    """Converte '4,49' ou '4.49' para float 4.49"""
    if not valor_str: return 0.0
    s = str(valor_str).replace("R$", "").replace(" ", "").strip()
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

def para_sheets(valor_float):
    """Converte float 4.49 para string '4,49' (formato que o Sheets BR aceita)"""
    return f"{valor_float:.2f}".replace(".", ",")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

# --- 📱 MENSAGEM WHATSAPP ORIGINAL ---
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
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "👥 Gerenciar Clientes", "📊 Relatórios"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 GESTÃO DE ESTOQUE (CÁLCULO CORRIGIDO)
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    tab1, tab2, tab3 = st.tabs(["📝 Entrada", "✏️ Editar/Excluir", "📋 Ver Tudo"])
    
    df_est = pd.DataFrame(sheet_estoque.get_all_records())

    with tab1:
        modo = st.radio("Item:", ["Existente", "Novo"], horizontal=True)
        if modo == "Existente" and not df_est.empty:
            nome = st.selectbox("Produto:", df_est['Nome'].tolist())
            ref_fardo = para_python(df_est[df_est['Nome']==nome].iloc[0]['Qtd_Fardo'])
        else:
            nome = st.text_input("Nome:", placeholder="Ex: SKOL LATA").upper()
            ref_fardo = 12

        c1, c2 = st.columns(2)
        custo_fardo = c1.text_input("Preço pago no FARDO (R$):", placeholder="36,70")
        qtd_fardos = c2.text_input("Qtd Fardos comprados:", placeholder="1")
        venda_un = st.text_input("Preço de VENDA por UNIDADE (R$):", placeholder="4,49")

        if st.button("💾 SALVAR ENTRADA"):
            v_custo = para_python(custo_fardo)
            v_qtd = para_python(qtd_fardos)
            v_venda = para_python(venda_un)
            
            if v_custo > 0 and v_qtd > 0:
                custo_un_novo = v_custo / ref_fardo
                total_itens_novos = int(v_qtd * ref_fardo)
                
                # Lógica de Custo Médio
                if modo == "Existente":
                    idx = df_est[df_est['Nome']==nome].index[0]
                    est_antigo = para_python(df_est.iloc[idx]['Estoque'])
                    custo_antigo = para_python(df_est.iloc[idx]['Custo'])
                    
                    novo_total = est_antigo + total_itens_novos
                    novo_custo_med = ((est_antigo * custo_antigo) + (total_itens_novos * custo_un_novo)) / novo_total
                    
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 4, para_sheets(novo_custo_med))
                    sheet_estoque.update_cell(idx+2, 5, para_sheets(v_venda))
                else:
                    sheet_estoque.append_row([nome, "Geral", "Forn", para_sheets(custo_un_novo), para_sheets(v_venda), total_itens_novos, datetime.now().strftime('%d/%m/%Y'), ref_fardo])
                
                st.success("Estoque atualizado!")
                time.sleep(1)
                st.rerun()

    with tab2:
        if not df_est.empty:
            item_sel = st.selectbox("Escolha para Editar/Excluir:", ["Selecione..."] + df_est['Nome'].tolist())
            if item_sel != "Selecione...":
                idx = df_est[df_est['Nome']==item_sel].index[0]
                if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary"):
                    sheet_estoque.delete_rows(int(idx+2))
                    st.rerun()

    with tab3:
        if not df_est.empty:
            df_vis = df_est.copy()
            df_vis['Custo'] = df_vis['Custo'].apply(para_python)
            df_vis['Venda'] = df_vis['Venda'].apply(para_python)
            df_vis['Lucro'] = df_vis['Venda'] - df_vis['Custo']
            st.dataframe(df_vis[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro']], use_container_width=True)

# ==========================================
# 💰 FIDELIDADE & CAIXA
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    if st.session_state.venda_sucesso:
        st.success("✅ Venda e Pontos registrados!")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_cli = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c1, c2 = st.columns(2)
        if sel_cli == "🆕 NOVO":
            nome_c = c1.text_input("Nome:").upper()
            tel_c = c2.text_input("Telefone:")
        else:
            nome_c = sel_cli.split(" - ")[0]
            tel_c = sel_cli.split(" - ")[1]
        
        prod_sel = st.selectbox("Produto:", ["(Apenas Pontuar)"] + df_est['Nome'].tolist())
        q_f = st.number_input("Fardos:", min_value=0, step=1)
        q_u = st.number_input("Unidades:", min_value=0, step=1)

        if st.button("CONFIRMAR"):
            t_limpo = limpar_tel(tel_c)
            total_baixa = 0
            if prod_sel != "(Apenas Pontuar)":
                ref = int(df_est[df_est['Nome']==prod_sel].iloc[0]['Qtd_Fardo'])
                total_baixa = (q_f * ref) + q_u
                est_at = int(df_est[df_est['Nome']==prod_sel].iloc[0]['Estoque'])
                sheet_estoque.update_cell(int(df_est[df_est['Nome']==prod_sel].index[0]+2), 6, est_at - total_baixa)

            # Pontos
            row_c = df_cli[df_cli['telefone'].astype(str) == t_limpo]
            if not row_c.empty:
                novos_p = int(row_c.iloc[0]['compras']) + 1
                sheet_clientes.update_cell(int(row_c.index[0]+2), 3, novos_p)
            else:
                novos_p = 1
                sheet_clientes.append_row([nome_c, t_limpo, 1, datetime.now().strftime('%d/%m/%Y')])
            
            m, b = gerar_mensagem_zap(nome_c, novos_p)
            st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{t_limpo}&text={urllib.parse.quote(m)}"
            st.session_state.txt_btn = b
            st.session_state.venda_sucesso = True
            st.rerun()

# ==========================================
# 👥 GERENCIAR CLIENTES
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Gerenciar Clientes")
    df_cli = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_cli.empty:
        sel = st.selectbox("Cliente:", df_cli['nome'].tolist())
        idx = df_cli[df_cli['nome']==sel].index[0]
        if st.button("🗑️ EXCLUIR CLIENTE"):
            sheet_clientes.delete_rows(int(idx+2))
            st.rerun()

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Históricos")
    st.write("Vendas Estoque")
    st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()))
    st.write("Fidelidade")
    st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()))
