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
# 🔐 LOGIN
# ==========================================
SENHA_DO_SISTEMA = "adega123" 
if 'logado' not in st.session_state: st.session_state.logado = False
if 'validando' not in st.session_state: st.session_state.validando = False
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False

if not st.session_state.logado:
    if st.session_state.validando:
        st.write("Sincronizando...")
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
        st.stop()

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
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
except Exception as e:
    st.error(f"Erro Conexão: {e}")
    st.stop()

# --- 🧮 O CORAÇÃO DA CORREÇÃO MATEMÁTICA ---
def para_python(valor):
    """Converte '3,06' ou 'R$ 3.000,00' em float puro 3.06"""
    if not valor or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if "." in v: v = v.replace(".", "") # Tira ponto de milhar
        v = v.replace(",", ".") # Troca virgula decimal por ponto
    try: return float(v)
    except: return 0.0

def para_sheets(valor):
    """Transforma 3.06 em TEXTO '3,06' para o Google Sheets não bugar"""
    return f"{valor:.2f}".replace(".", ",")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

# --- 📱 WHATSAPP ORIGINAL ---
def gerar_mensagem_zap(nome, total):
    if total == 1:
        msg = f"Olá {nome}! Bem-vindo à Adega! 🍷\nStatus: 1 ponto."
        btn = "Enviar Boas-Vindas 🎉"
    elif total < 9:
        msg = f"Olá {nome}! Mais uma compra!\nStatus: {total}/10 pontos."
        btn = f"Enviar Saldo ({total}/10) 📲"
    elif total == 9:
        msg = f"UAU {nome}! Falta 1 para o prémio! 😱"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome}! Ganhou 50% OFF! 🏆"
        btn = "🏆 ENVIAR PRÉMIO AGORA"
    return msg, btn

# ==========================================
# 📦 MÓDULO ESTOQUE (MATEMÁTICA BLINDADA)
# ==========================================
if st.sidebar.radio("Menu:", ["💰 Caixa", "📦 Estoque"]) == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    tab1, tab2 = st.tabs(["📝 Entrada", "📋 Lista"])
    
    df_est = pd.DataFrame(sheet_estoque.get_all_records())

    with tab1:
        modo = st.radio("Tipo:", ["Existente", "Novo"], horizontal=True)
        if modo == "Existente" and not df_est.empty:
            nome = st.selectbox("Produto:", df_est['Nome'].tolist())
            # Busca fardo de referência (se não tiver, assume 12)
            try: ref_fardo = para_python(df_est[df_est['Nome']==nome].iloc[0].get('Qtd_Fardo', 12))
            except: ref_fardo = 12
        else:
            nome = st.text_input("Nome do Produto:").upper()
            ref_fardo = st.number_input("Unidades por fardo:", value=12)

        c1, c2, v = st.columns(3)
        custo_f = c1.text_input("Preço Fardo (R$):", placeholder="36,70")
        qtd_f = c2.text_input("Qtd Fardos:", placeholder="1")
        venda_u = v.text_input("Venda Unitária (R$):", placeholder="4,49")

        if st.button("💾 SALVAR"):
            v_custo = para_python(custo_f)
            v_qtd = para_python(qtd_f)
            v_venda = para_python(venda_u)
            
            if v_custo > 0 and v_qtd > 0:
                custo_un_novo = v_custo / ref_fardo
                total_un_novas = int(v_qtd * ref_fardo)
                
                if modo == "Existente":
                    idx = df_est[df_est['Nome']==nome].index[0]
                    est_antigo = para_python(df_est.iloc[idx]['Estoque'])
                    custo_antigo = para_python(df_est.iloc[idx]['Custo'])
                    
                    # PROTEÇÃO: Se o custo antigo estiver bizarro, ignora e usa o novo
                    if custo_antigo > 1000: custo_antigo = custo_un_novo
                    
                    novo_total = est_antigo + total_un_novas
                    novo_custo_med = ((est_antigo * custo_antigo) + (total_un_novas * custo_un_novo)) / novo_total
                    
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 4, para_sheets(novo_custo_med))
                    sheet_estoque.update_cell(idx+2, 5, para_sheets(v_venda))
                else:
                    sheet_estoque.append_row([nome, "Geral", "Forn", para_sheets(custo_un_novo), para_sheets(v_venda), total_un_novas, date.today().strftime('%d/%m/%Y'), ref_fardo])
                
                st.success("Salvo com sucesso!")
                time.sleep(1)
                st.rerun()

    with tab2:
        if not df_est.empty:
            df_vis = df_est.copy()
            df_vis['Custo'] = df_vis['Custo'].apply(para_python)
            df_vis['Venda'] = df_vis['Venda'].apply(para_python)
            df_vis['Lucro'] = df_vis['Venda'] - df_vis['Custo']
            st.dataframe(df_vis[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro']], use_container_width=True)

# ==========================================
# 💰 CAIXA & FIDELIDADE
# ==========================================
else:
    st.title("💰 Caixa & Fidelidade")
    if st.session_state.venda_sucesso:
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        if sel == "🆕 NOVO":
            n = st.text_input("Nome:").upper()
            t = st.text_input("Telefone:")
        else:
            n = sel.split(" - ")[0]
            t = sel.split(" - ")[1]
        
        p = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
        
        if st.button("CONFIRMAR"):
            t_l = limpar_tel(t)
            # Busca cliente por telefone (evita duplicar)
            df_cli['t_str'] = df_cli['telefone'].astype(str).apply(limpar_tel)
            match = df_cli[df_cli['t_str'] == t_l]
            
            if not match.empty:
                idx = match.index[0]
                pts = int(match.iloc[0]['compras']) + 1
                sheet_clientes.update_cell(idx+2, 3, pts)
            else:
                pts = 1
                sheet_clientes.append_row([n, t_l, 1, date.today().strftime('%d/%m/%Y')])
            
            msg, btn = gerar_mensagem_zap(n, pts)
            st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{t_l}&text={urllib.parse.quote(msg)}"
            st.session_state.txt_btn = btn
            st.session_state.venda_sucesso = True
            st.rerun()
