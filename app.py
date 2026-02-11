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
        st.write("Entrando...")
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
    sheet_hist_cli = planilha.worksheet("Historico")
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
except Exception as e:
    st.error(f"Erro Conexão: {e}")
    st.stop()

# --- 🧮 FUNÇÕES DE CORREÇÃO MATEMÁTICA (ANTI-ERRO DE MILHÕES) ---
def tratar_valor_sheets(valor):
    """
    Transforma qualquer formato da planilha (3,06 ou 3.06 ou R$ 3,06) 
    em um número decimal real para o Python.
    """
    if valor is None or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    # Se tiver vírgula e ponto (estilo 1.200,50), remove o ponto e troca a vírgula
    if "." in v and "," in v:
        v = v.replace(".", "").replace(",", ".")
    # Se tiver apenas vírgula (estilo 3,06), troca por ponto
    elif "," in v:
        v = v.replace(",", ".")
    try:
        return float(v)
    except:
        return 0.0

def formatar_para_salvar(valor):
    """Garante que o número seja salvo de forma simples para o Sheets não bugar"""
    return round(float(valor), 2)

def formatar_moeda_br(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

# --- 📱 MENSAGENS WHATSAPP ---
def gerar_mensagem_zap(nome, total):
    if total == 1: msg = f"Olá {nome}! Bem-vindo à Adega! 🍷\nStatus: 1 ponto."
    elif total < 9: msg = f"Olá {nome}! Mais uma compra!\nStatus: {total}/10 pontos."
    elif total == 9: msg = f"UAU {nome}! Falta 1 para o prémio! 😱"
    else: msg = f"PARABÉNS {nome}! Ganhou 50% OFF! 🏆"
    return msg, "Enviar WhatsApp 📲"

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Adega Menu")
    menu = st.radio("Ir para:", ["💰 Caixa & Fidelidade", "📦 Estoque", "👥 Clientes", "📊 Relatórios"])
    st.link_button("📂 Planilha Google", URL_PLANILHA)
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 MÓDULO ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    tab1, tab2, tab3 = st.tabs(["📝 Entrada", "✏️ Editar/Excluir", "📋 Lista"])
    
    # Lendo dados e tratando decimais IMEDIATAMENTE
    dados_est = sheet_estoque.get_all_records()
    df_est = pd.DataFrame(dados_est)

    with tab1:
        modo = st.radio("Produto:", ["Existente", "Novo"], horizontal=True)
        if modo == "Existente" and not df_est.empty:
            nome_sel = st.selectbox("Escolha:", df_est['Nome'].tolist())
            ref_fardo = tratar_valor_sheets(df_est[df_est['Nome']==nome_sel].iloc[0].get('Qtd_Fardo', 12))
        else:
            nome_sel = st.text_input("Nome do Produto:", placeholder="Ex: SKOL LATA").upper()
            ref_fardo = 12

        c1, c2, v = st.columns(3)
        custo_f = c1.text_input("Preço Fardo (R$):", placeholder="36,70")
        qtd_f = c2.text_input("Quantos fardos?", placeholder="1")
        venda_u = v.text_input("Venda Unitária (R$):", placeholder="4,49")

        if st.button("💾 SALVAR NO ESTOQUE"):
            v_custo = tratar_valor_sheets(custo_f)
            v_qtd = tratar_valor_sheets(qtd_f)
            v_venda = tratar_valor_sheets(venda_u)
            
            if v_custo > 0 and v_qtd > 0:
                custo_un_novo = v_custo / ref_fardo
                total_un_novas = int(v_qtd * ref_fardo)
                
                if modo == "Existente":
                    idx = df_est[df_est['Nome']==nome_sel].index[0]
                    est_antigo = tratar_valor_sheets(df_est.iloc[idx]['Estoque'])
                    custo_antigo = tratar_valor_sheets(df_est.iloc[idx]['Custo'])
                    
                    # Proteção: Se o custo antigo estiver em milhões, reseta para o custo novo
                    if custo_antigo > 500: custo_antigo = custo_un_novo 
                    
                    novo_total = est_antigo + total_un_novas
                    novo_custo_med = ((est_antigo * custo_antigo) + (total_un_novas * custo_un_novo)) / novo_total
                    
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 4, formatar_para_salvar(novo_custo_med))
                    sheet_estoque.update_cell(idx+2, 5, formatar_para_salvar(v_venda))
                else:
                    sheet_estoque.append_row([nome_sel, "Geral", "Forn", formatar_para_salvar(custo_un_novo), formatar_para_salvar(v_venda), total_un_novas, date.today().strftime('%d/%m/%Y'), ref_fardo])
                
                st.success("Estoque Atualizado!")
                time.sleep(1)
                st.rerun()

    with tab2:
        if not df_est.empty:
            item_del = st.selectbox("Item para Excluir:", ["Selecione..."] + df_est['Nome'].tolist())
            if item_del != "Selecione...":
                idx = df_est[df_est['Nome']==item_del].index[0]
                if st.button("🗑️ DELETAR PRODUTO", type="primary"):
                    sheet_estoque.delete_rows(int(idx+2))
                    st.rerun()

    with tab3:
        if not df_est.empty:
            df_vis = df_est.copy()
            df_vis['Custo'] = df_vis['Custo'].apply(tratar_valor_sheets)
            df_vis['Venda'] = df_vis['Venda'].apply(tratar_valor_sheets)
            df_vis['Lucro R$'] = df_vis['Venda'] - df_vis['Custo']
            
            st.dataframe(
                df_vis[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro R$']], 
                use_container_width=True,
                column_config={
                    "Venda": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Custo": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Lucro R$": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )

# ==========================================
# 💰 CAIXA & FIDELIDADE (RESOLVIDO DUPLICAÇÃO)
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
    if st.session_state.venda_sucesso:
        st.success("✅ Venda e Pontos registrados!")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("🔄 Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_cli = st.selectbox("Identificar Cliente:", ["🆕 NOVO CLIENTE"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        
        c1, c2 = st.columns(2)
        if sel_cli == "🆕 NOVO CLIENTE":
            n_cli = c1.text_input("Nome:").upper()
            t_cli = c2.text_input("Telefone (Só números):")
        else:
            n_cli = sel_cli.split(" - ")[0]
            t_cli = sel_cli.split(" - ")[1]
        
        prod_venda = st.selectbox("Produto:", ["(Apenas Pontuar)"] + df_est['Nome'].tolist())
        f, u = st.columns(2)
        q_f = f.number_input("Fardos:", min_value=0, step=1)
        q_u = u.number_input("Unidades:", min_value=0, step=1)

        if st.button("✅ CONFIRMAR VENDA"):
            t_limpo = limpar_tel(t_cli)
            if n_cli and t_limpo:
                # Baixa Estoque
                if prod_venda != "(Apenas Pontuar)":
                    item_row = df_est[df_est['Nome']==prod_venda].iloc[0]
                    ref = int(tratar_valor_sheets(item_row['Qtd_Fardo']))
                    total_b = (q_f * ref) + q_u
                    novo_est = int(tratar_valor_sheets(item_row['Estoque'])) - total_b
                    sheet_estoque.update_cell(int(df_est[df_est['Nome']==prod_venda].index[0]+2), 6, novo_est)

                # Fidelidade (Busca por Telefone para evitar duplicação)
                df_cli['tel_str'] = df_cli['telefone'].astype(str).apply(limpar_tel)
                match = df_cli[df_cli['tel_str'] == t_limpo]
                
                if not match.empty:
                    idx_c = match.index[0]
                    novos_p = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(idx_c+2, 3, novos_p)
                else:
                    novos_p = 1
                    sheet_clientes.append_row([n_cli, t_limpo, 1, date.today().strftime('%d/%m/%Y')])
                
                m, b = gerar_mensagem_zap(n_cli, novos_p)
                st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{t_limpo}&text={urllib.parse.quote(m)}"
                st.session_state.txt_btn = b
                st.session_state.venda_sucesso = True
                st.rerun()

# ==========================================
# 👥 CLIENTES & RELATÓRIOS
# ==========================================
elif menu == "👥 Clientes":
    df_cli = pd.DataFrame(sheet_clientes.get_all_records())
    st.dataframe(df_cli, use_container_width=True)
    if st.button("🗑️ EXCLUIR ÚLTIMO CLIENTE (Teste)"):
        sheet_clientes.delete_rows(len(df_cli)+1)
        st.rerun()

elif menu == "📊 Relatórios":
    st.title("📊 Históricos")
    st.write("Histórico de Estoque")
    st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()))
