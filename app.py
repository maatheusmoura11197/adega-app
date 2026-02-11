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
st.set_page_config(page_title="Adega App v13", page_icon="🍷", layout="wide", initial_sidebar_state="expanded")

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
# 🔐 LOGIN (SESSÃO)
# ==========================================
SENHA_DO_SISTEMA = "adega123" 
if 'logado' not in st.session_state: st.session_state.logado = False
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False

if not st.session_state.logado:
    st.title("🔒 Acesso Adega")
    senha = st.text_input("Senha:", type="password")
    if st.button("ENTRAR"):
        if senha == SENHA_DO_SISTEMA:
            st.session_state.logado = True
            st.rerun()
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
except:
    st.error("Erro ao conectar na Planilha.")
    st.stop()

# --- 🧮 FUNÇÕES DE LIMPEZA ---
def limpar_valor(valor):
    """Limpa o valor vindo do Sheets ou do usuário para o Python entender"""
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if v.count(".") > 0: v = v.replace(".", "") # Tira milhar
        v = v.replace(",", ".")
    try: return float(v)
    except: return 0.0

def para_texto_br(valor):
    """Converte o número para texto com vírgula para o Sheets não bugar"""
    return f"{valor:.2f}".replace(".", ",")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

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
    st.title("🍷 Adega Sistema")
    menu = st.radio("Escolha:", ["💰 Caixa & Fidelidade", "📦 Estoque (Entrada/Editar)", "👥 Gerenciar Clientes", "📊 Relatórios"])
    st.divider()
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 MÓDULO ESTOQUE (COMPLETO)
# ==========================================
if menu == "📦 Estoque (Entrada/Editar)":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    tab1, tab2, tab3 = st.tabs(["📝 Registrar Compra", "✏️ Editar/Excluir", "📋 Lista Atual"])

    with tab1:
        modo = st.radio("Item:", ["Existente", "Novo"], horizontal=True)
        if modo == "Existente" and not df_est.empty:
            nome_sel = st.selectbox("Selecione o Produto:", df_est['Nome'].tolist())
            ref_fardo = limpar_valor(df_est[df_est['Nome']==nome_sel].iloc[0].get('Qtd_Fardo', 12))
        else:
            nome_sel = st.text_input("Nome:", placeholder="SKOL LATA").upper()
            ref_fardo = st.number_input("Unidades por Fardo:", value=12)

        c1, c2, c3 = st.columns(3)
        custo_f = c1.text_input("Preço Fardo (R$):", placeholder="36,70")
        qtd_f = c2.text_input("Qtd Fardos:", placeholder="1")
        venda_un = c3.text_input("Venda Unitária (R$):", placeholder="4,49")

        if st.button("💾 SALVAR ESTOQUE"):
            v_custo = limpar_valor(custo_f)
            v_qtd = limpar_valor(qtd_f)
            v_venda = limpar_valor(venda_un)
            
            if v_custo > 0 and v_qtd > 0:
                custo_un_novo = v_custo / ref_fardo
                novas_unidades = int(v_qtd * ref_fardo)
                
                if modo == "Existente":
                    idx = df_est[df_est['Nome']==nome_sel].index[0]
                    est_antigo = limpar_valor(df_est.iloc[idx]['Estoque'])
                    custo_antigo = limpar_valor(df_est.iloc[idx]['Custo'])
                    if custo_antigo > 1000: custo_antigo = custo_un_novo # Reseta erro de milhão
                    
                    novo_total = est_antigo + novas_unidades
                    novo_custo_med = ((est_antigo * custo_antigo) + (novas_unidades * custo_un_novo)) / novo_total
                    
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 4, para_texto_br(novo_custo_med))
                    sheet_estoque.update_cell(idx+2, 5, para_texto_br(v_venda))
                else:
                    sheet_estoque.append_row([nome_sel, "Geral", "", para_texto_br(custo_un_novo), para_texto_br(v_venda), novas_unidades, date.today().strftime('%d/%m/%Y'), ref_fardo])
                
                st.success("Estoque Atualizado!")
                time.sleep(1)
                st.rerun()

    with tab2:
        if not df_est.empty:
            edit_nome = st.selectbox("Escolha para Editar ou Excluir:", ["Selecione..."] + df_est['Nome'].tolist())
            if edit_nome != "Selecione...":
                idx_e = df_est[df_est['Nome']==edit_nome].index[0]
                row_e = df_est.iloc[idx_e]
                with st.form("form_edit"):
                    st.write(f"Editando: **{edit_nome}**")
                    new_v = st.text_input("Preço Venda:", value=str(row_e['Venda']))
                    new_c = st.text_input("Custo Médio:", value=str(row_e['Custo']))
                    new_q = st.number_input("Estoque Real (Qtd):", value=int(row_e['Estoque']))
                    
                    c_salvar, c_excluir = st.columns(2)
                    if c_salvar.form_submit_button("💾 Salvar"):
                        sheet_estoque.update_cell(idx_e+2, 5, new_v)
                        sheet_estoque.update_cell(idx_e+2, 4, new_c)
                        sheet_estoque.update_cell(idx_e+2, 6, int(new_q))
                        st.success("Atualizado!")
                        st.rerun()
                    if c_excluir.form_submit_button("🗑️ EXCLUIR ITEM"):
                        sheet_estoque.delete_rows(int(idx_e+2))
                        st.rerun()

    with tab3:
        if not df_est.empty:
            df_v = df_est.copy()
            df_v['Custo'] = df_v['Custo'].apply(limpar_valor)
            df_v['Venda'] = df_v['Venda'].apply(limpar_valor)
            df_v['Lucro'] = df_v['Venda'] - df_v['Custo']
            st.dataframe(df_v[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro']], use_container_width=True)

# ==========================================
# 💰 CAIXA & FIDELIDADE
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
    if st.session_state.venda_sucesso:
        st.success("✅ Venda Registrada!")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_cli = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c_n, c_t = st.columns(2)
        if sel_cli == "🆕 NOVO":
            nome_c = c_n.text_input("Nome:").upper()
            tel_c = c_t.text_input("Tel:")
        else:
            nome_c = sel_cli.split(" - ")[0]
            tel_c = sel_cli.split(" - ")[1]
        
        st.divider()
        prod_sel = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
        q_f, q_u = st.columns(2)
        v_f = q_f.number_input("Fardos:", min_value=0, step=1)
        v_u = q_u.number_input("Unidades:", min_value=0, step=1)

        if st.button("✅ CONFIRMAR"):
            t_l = limpar_tel(tel_c)
            # Baixa estoque
            if prod_sel != "(Apenas Ponto)":
                row_p = df_est[df_est['Nome']==prod_sel].iloc[0]
                total_b = (v_f * int(row_p['Qtd_Fardo'])) + v_u
                sheet_estoque.update_cell(int(df_est[df_est['Nome']==prod_sel].index[0]+2), 6, int(row_p['Estoque']) - total_b)
            
            # Fidelidade
            df_cli['t_str'] = df_cli['telefone'].astype(str).apply(limpar_tel)
            match = df_cli[df_cli['t_str'] == t_l]
            if not match.empty:
                idx_c = match.index[0]
                novos_pts = int(match.iloc[0]['compras']) + 1
                sheet_clientes.update_cell(int(idx_c+2), 3, novos_pts)
            else:
                novos_pts = 1
                sheet_clientes.append_row([nome_c, t_l, 1, date.today().strftime('%d/%m/%Y')])
            
            msg, b_t = gerar_mensagem_zap(nome_c, novos_pts)
            st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{t_l}&text={urllib.parse.quote(msg)}"
            st.session_state.txt_btn = b_t
            st.session_state.venda_sucesso = True
            st.rerun()

# ==========================================
# 👥 GERENCIAR CLIENTES
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_c.empty:
        df_c['Display'] = df_c['nome'] + " - " + df_c['telefone'].astype(str)
        sel = st.selectbox("Selecione:", df_c['Display'].tolist())
        idx = df_c[df_c['Display']==sel].index[0]
        row = df_c.iloc[idx]
        
        with st.form("edit_cli"):
            n_n = st.text_input("Nome:", value=row['nome'])
            n_t = st.text_input("Telefone:", value=str(row['telefone']))
            n_p = st.number_input("Pontos:", value=int(row['compras']))
            if st.form_submit_button("Salvar Alterações"):
                sheet_clientes.update_cell(idx+2, 1, n_n)
                sheet_clientes.update_cell(idx+2, 2, n_t)
                sheet_clientes.update_cell(idx+2, 3, n_p)
                st.success("Salvo!")
                st.rerun()
            if st.form_submit_button("🗑️ EXCLUIR CLIENTE"):
                sheet_clientes.delete_rows(int(idx+2))
                st.rerun()

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios")
    st.subheader("Vendas (Estoque)")
    st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
    st.subheader("Visitas (Fidelidade)")
    st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
