import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import re
from datetime import datetime, date
import time
import os
import json

# ==========================================
# ⚙️ CONFIGURAÇÃO
# ==========================================
ICON_URL = "https://splendid-plum-mslpekoeqx.edgeone.app/cerveja.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

# Estilos CSS
st.markdown(f"""
    <style>
    div.stButton > button {{ background-color: #008CBA; color: white; font-weight: bold; border-radius: 10px; height: 3em; width: 100%; border: none; }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{ padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3; border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# Login e Sessão
SENHA_DO_SISTEMA = "adega123"
if 'logado' not in st.session_state: st.session_state.logado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

# Tela de Login
if not st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>🔒 Adega do Barão</h1>", unsafe_allow_html=True)
    c_a, c_b, c_c = st.columns([1, 2, 1])
    with c_b:
        with st.form("login_form"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR"):
                if senha == SENHA_DO_SISTEMA:
                    st.success("Logado!"); time.sleep(1); st.session_state.logado = True; st.rerun()
                else: st.error("Senha incorreta!")
    st.stop()

# ==========================================
# 📡 CONEXÃO BLINDADA (RAILWAY + STREAMLIT)
# ==========================================
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. Tenta pegar a chave do Railway (Variáveis de Ambiente)
    if "GCP_SERVICE_ACCOUNT" in os.environ:
        creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    
    # 2. Se não achar, tenta pegar do Streamlit (Secrets)
    elif "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
    
    else:
        st.error("⚠️ ERRO: Chave não encontrada! Configure no Railway ou Secrets.")
        st.stop()

    # Cria a conexão (SEM O PARÊNTESE EXTRA)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Abre as abas
    planilha = client.open("Fidelidade")
    sheet_clientes = planilha.worksheet("Página1") 
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    sheet_hist_cli = planilha.worksheet("Historico")

    # Funções Auxiliares
    def cvt_num(v): 
        try: return float(str(v).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip())
        except: return 0.0
    def para_real_visual(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    def salvar_com_ponto(v): return "{:.2f}".format(v)
    def limpar_tel(t): return re.sub(r'\D', '', str(t))
    def calc_fisico(total, ref): return f"📦 {total // (ref if ref > 0 else 12)} fardos 🍺 {total % (ref if ref > 0 else 12)} un"
    def gerar_mensagem(nome, pts):
        nome = nome.split()[0].capitalize()
        if pts == 1: return f"Oi, {nome}! ✨\nObrigado por comprar na Adega do Barão! Já abri seu Cartão Fidelidade. 1º ponto garantido! 🍷", "Enviar Zap"
        elif 1 < pts < 10: return f"E aí, {nome}! 👊\nCompra registrada! Agora você tem *{pts} pontos*. Faltam {10-pts}! 🍻", "Enviar Zap"
        else: return f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **PRÊMIO** hoje! Aproveite! 🥳🍷", "🏆 ENVIAR PRÊMIO"

except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# ==========================================
# 📱 MENU
# ==========================================
with st.sidebar:
    st.title("Menu")
    menu = st.radio("Ir para:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])
    if st.button("SAIR"): st.session_state.logado = False; st.rerun()

# ==========================================
# 📦 ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Estoque")
    # Carrega dados com segurança
    try:
        dados_brutos = sheet_estoque.get_all_records()
        df = pd.DataFrame(dados_brutos)
    except: df = pd.DataFrame()
    
    if not df.empty: 
        if 'Nome' not in df.columns: df['Nome'] = ""
        if 'Tipo' not in df.columns: df['Tipo'] = ""
        if 'ML' not in df.columns: df['ML'] = ""
        df['Nome_Exibicao'] = df['Nome'].astype(str) + " - " + df['Tipo'].astype(str) + " (" + df['ML'].astype(str) + ")"
    
    aba = st.radio("Ação:", ["Lista", "Novo", "Editar"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if aba == "Lista":
        if not df.empty:
            df['Físico'] = df.apply(lambda r: calc_fisico(int(cvt_num(r['Estoque'])), int(cvt_num(r.get('Qtd_Fardo', 12)))), axis=1)
            st.dataframe(df[['Nome', 'Tipo', 'ML', 'Físico', 'Venda', 'Fornecedor']].sort_values('Nome'), use_container_width=True)
        else: st.info("Estoque vazio.")

    elif aba == "Novo":
        with st.form("novo_prod", clear_on_submit=True):
            n = st.text_input("Nome :red[(Obrigatório)]:").upper()
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Tipo:", ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"])
            ml_sel = c2.selectbox("ML:", ["269ml", "350ml", "473ml", "600ml", "1 Litro", "Outros"])
            ml_txt = c2.text_input("Digite o ML:") if ml_sel == "Outros" else ""
            
            c3, c4 = st.columns(2)
            custo = c3.text_input("Custo R$:")
            venda = c4.text_input("Venda R$:")
            
            c5, c6 = st.columns(2)
            forn_sel = c5.selectbox("Fornecedor:", ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"])
            forn_txt = c6.text_input("Digite Fornecedor:") if forn_sel == "Outros" else ""
            
            st.divider()
            ref = st.number_input("Itens por Fardo:", value=12)
            qtd = st.number_input("Qtd Inicial (Unid):", min_value=0)
            
            if st.form_submit_button("CADASTRAR"):
                final_forn = forn_txt if forn_sel == "Outros" else forn_sel
                final_ml = ml_txt if ml_sel == "Outros" else ml_sel
                if n and custo and venda and final_forn:
                    sheet_estoque.append_row([n, tipo, final_forn, custo, venda, qtd, date.today().strftime('%d/%m/%Y'), ref, final_ml])
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m %H:%M'), n, "NOVO", qtd, final_forn])
                    st.success("Cadastrado!"); time.sleep(1); st.rerun()
                else: st.error("Preencha tudo!")

    elif aba == "Editar":
        if not df.empty:
            sel = st.selectbox("Produto:", ["Selecione..."] + sorted(df['Nome_Exibicao'].tolist()))
            if sel != "Selecione...":
                idx = df[df['Nome_Exibicao'] == sel].index[0]
                row = df.iloc[idx]
                
                with st.form(f"edit_{idx}", clear_on_submit=True):
                    nn = st.text_input("Nome:", value=row['Nome']).upper()
                    c1, c2 = st.columns(2)
                    
                    list_t = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
                    idx_t = list_t.index(row['Tipo']) if row['Tipo'] in list_t else 0
                    nt = c1.selectbox("Tipo:", list_t, index=idx_t)
                    
                    list_m = ["269ml", "350ml", "473ml", "600ml", "1 Litro", "Outros"]
                    idx_m = list_m.index(row['ML']) if row['ML'] in list_m else 5
                    nm_sel = c2.selectbox("ML:", list_m, index=idx_m)
                    nm_txt = c2.text_input("Digite ML:", value=row['ML'] if nm_sel == "Outros" else "")

                    c3, c4 = st.columns(2)
                    nc = c3.text_input("Custo:", value=row['Custo'])
                    nv = c4.text_input("Venda:", value=row['Venda'])
                    
                    c5, c6 = st.columns(2)
                    lista_f = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
                    idx_f = lista_f.index(row['Fornecedor']) if row['Fornecedor'] in lista_f else 5
                    nf_sel = c5.selectbox("Forn:", lista_f, index=idx_f)
                    nf_txt = c6.text_input("Digite Forn:", value=row['Fornecedor'] if nf_sel == "Outros" else "")

                    st.write("---")
                    atual = int(cvt_num(row['Estoque']))
                    st.info(f"Atual: {atual}")
                    col_adj, col_add = st.columns(2)
                    adj = col_adj.number_input("Corrigir Total:", value=atual)
                    add = col_add.number_input("Adicionar (+):", min_value=0)
                    
                    if st.form_submit_button("SALVAR"):
                        final_f = nf_txt if nf_sel == "Outros" else nf_sel
                        final_m = nm_txt if nm_sel == "Outros" else nm_sel
                        novo_tot = adj + add
                        
                        sheet_estoque.update_cell(idx+2, 1, nn)
                        sheet_estoque.update_cell(idx+2, 2, nt)
                        sheet_estoque.update_cell(idx+2, 3, final_f)
                        sheet_estoque.update_cell(idx+2, 4, nc)
                        sheet_estoque.update_cell(idx+2, 5, nv)
                        sheet_estoque.update_cell(idx+2, 6, novo_tot)
                        try: sheet_estoque.update_cell(idx+2, 9, final_m)
                        except: pass
                        
                        if add > 0: sheet_hist_est.append_row([datetime.now().strftime('%d/%m %H:%M'), sel, "ENTRADA", add, f"Forn: {final_f}"])
                        st.success("Salvo!"); time.sleep(1); st.rerun()
                    
                    if st.form_submit_button("EXCLUIR PRODUTO"):
                        sheet_estoque.delete_rows(int(idx + 2))
                        st.warning("Excluído!"); time.sleep(1); st.rerun()

# ==========================================
# 💰 CAIXA
# ==========================================
elif menu == "💰 Caixa":
    st.title("💰 Caixa")
    if st.session_state.get('v_suc'):
        st.success("Venda Feita!")
        st.markdown(f'<a href="{st.session_state.l_zap}" target="_blank" class="big-btn">{st.session_state.b_txt}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.v_suc = False; st.rerun()
    else:
        try:
            df_cli = pd.DataFrame(sheet_clientes.get_all_records())
            df_est = pd.DataFrame(sheet_estoque.get_all_records())
        except: df_cli = pd.DataFrame(); df_est = pd.DataFrame()
        
        if not df_est.empty:
            if 'Nome' not in df_est.columns: df_est['Nome'] = ""
            if 'Tipo' not in df_est.columns: df_est['Tipo'] = ""
            if 'ML' not in df_est.columns: df_est['ML'] = ""
            df_est['Nome_Exibicao'] = df_est['Nome'].astype(str) + " - " + df_est['Tipo'].astype(str) + " (" + df_est['ML'].astype(str) + ")"
        
        lista_c = ["NOVO"] + sorted(df_cli['nome'].tolist()) if not df_cli.empty else ["NOVO"]
        cli = st.selectbox("Cliente:", lista_c)
        c1, c2 = st.columns(2)
        n_c = c1.text_input("Nome:") if cli == "NOVO" else cli
        t_c = c2.text_input("Tel:") if cli == "NOVO" else ""

        st.divider()
        if not df_est.empty:
            p = st.selectbox("Produto:", ["..."] + sorted(df_est['Nome_Exibicao'].tolist()), key="psel")
            if p != "...":
                filtro = df_est[df_est['Nome_Exibicao'] == p]
                if not filtro.empty:
                    row = filtro.iloc[0]
                    idx = filtro.index[0]
                    st.info(f"💰 {row['Venda']} | Estoque: {row['Estoque']}")
                    
                    c_qtd, c_btn = st.columns([1, 2])
                    q = c_qtd.number_input("Qtd:", 1, key="qsel")
                    
                    if c_btn.button("➕ Adicionar"):
                        if int(cvt_num(row['Estoque'])) >= q:
                            st.session_state.carrinho.append({"Produto": p, "Qtd": q, "Valor": cvt_num(row['Venda']), "idx": idx})
                            del st.session_state['psel']; del st.session_state['qsel']
                            st.rerun()
                        else: st.error("Estoque insuficiente!")
        else:
            st.warning("Cadastre produtos no Estoque primeiro.")

        if st.session_state.carrinho:
            df_car = pd.DataFrame(st.session_state.carrinho)
            st.dataframe(df_car, use_container_width=True)
            total = sum(i['Qtd'] * i['Valor'] for i in st.session_state.carrinho)
            st.subheader(f"Total: R$ {total:.2f}")
            
            if st.button("✅ FINALIZAR", type="primary"):
                for i in st.session_state.carrinho:
                    novo = int(cvt_num(df_est.iloc[i['idx']]['Estoque'])) - i['Qtd']
                    sheet_estoque.update_cell(i['idx']+2, 6, novo)
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m %H:%M'), i['Produto'], "VENDA", i['Qtd'], i['Valor']])
                
                if not df_cli.empty and n_c in df_cli['nome'].values:
                    idx_c = df_cli[df_cli['nome'] == n_c].index[0]
                    pts = int(df_cli.iloc[idx_c]['compras']) + 1
                    sheet_clientes.update_cell(idx_c+2, 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([n_c, t_c, 1])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m %H:%M'), n_c, t_c, pts])
                
                msg, btn = gerar_mensagem(n_c, pts)
                st.session_state.carrinho = []
                st.session_state.v_suc = True
                st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{limpar_tel(t_c)}&text={urllib.parse.quote(msg)}"
                st.session_state.b_txt = btn
                st.rerun()
            
            if st.button("Limpar"): st.session_state.carrinho = []; st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("Clientes")
    try: df = pd.DataFrame(sheet_clientes.get_all_records())
    except: df = pd.DataFrame()
    st.dataframe(df, use_container_width=True)

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 HISTÓRICOS":
    st.title("Relatórios")
    try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
    except: st.info("Sem histórico.")
