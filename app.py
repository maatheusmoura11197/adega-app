import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import re
from datetime import datetime, date
import time

# ==========================================
# ⚙️ CONFIGURAÇÃO E ESTILO
# ==========================================
ICON_URL = "https://cdn-icons-png.flaticon.com/512/3175/3175199.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{ background-color: #0047AB; color: white !important; border-radius: 10px 10px 0px 0px; padding: 10px 20px; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #002D6E !important; }}
    div.stButton > button {{ background-color: #008CBA; color: white; font-weight: bold; border-radius: 10px; height: 3em; width: 100%; border: none; }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{ padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3; border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }}
    </style>
    <link rel="shortcut icon" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
    """, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN
# ==========================================
SENHA_DO_SISTEMA = "adega123"

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>🔒 Adega do Barão</h1>", unsafe_allow_html=True)
    c_a, c_b, c_c = st.columns([1, 2, 1])
    with c_b:
        with st.form("login_form"):
            senha = st.text_input("Senha de Acesso:", type="password", placeholder="Digite e aperte Enter ↵")
            if st.form_submit_button("ACESSAR SISTEMA"):
                if senha == SENHA_DO_SISTEMA:
                    st.success("✅ Senha Correta!")
                    with st.spinner("Acessando Adega..."):
                        time.sleep(1) 
                        st.session_state.logado = True
                        st.rerun()
                else:
                    st.error("🚫 Senha incorreta!")
    st.stop()

# ==========================================
# 📡 CONEXÃO E CACHE (ANTI-BLOQUEIO)
# ==========================================
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Fidelidade")
    
    # URL da Planilha
    LINK_PLANILHA = f"https://docs.google.com/spreadsheets/d/{planilha.id}/edit"

    sheet_clientes = planilha.worksheet("Página1") 
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    sheet_hist_cli = planilha.worksheet("Historico")
    
    def garantir_cabecalhos():
        headers_padrao = ["Nome", "Tipo", "Fornecedor", "Custo", "Venda", "Estoque", "Data Compra", "Qtd_Fardo", "ML"]
        try:
            atuais = sheet_estoque.row_values(1)
            if not atuais or len(atuais) < 9:
                for i, h in enumerate(headers_padrao): sheet_estoque.update_cell(1, i+1, h)
        except: pass

    @st.cache_data(ttl=5)
    def carregar_dados_estoque():
        try: return pd.DataFrame(sheet_estoque.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_dados_clientes():
        try: return pd.DataFrame(sheet_clientes.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_historico_cli():
        try: return pd.DataFrame(sheet_hist_cli.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_historico_est():
        try: return pd.DataFrame(sheet_hist_est.get_all_records())
        except: return pd.DataFrame()

    def limpar_cache():
        carregar_dados_estoque.clear()
        carregar_dados_clientes.clear()
        carregar_historico_cli.clear()
        carregar_historico_est.clear()

    garantir_cabecalhos()

except Exception as e:
    st.error("Erro de conexão. Verifique sua internet.")
    st.stop()

# --- FUNÇÕES ---
def cvt_num(valor):
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v: v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

def para_real_visual(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def salvar_com_ponto(valor): return "{:.2f}".format(valor)
def limpar_tel(t): return re.sub(r'\D', '', str(t))

def calc_fisico(total, ref_fardo):
    if ref_fardo == 0: ref_fardo = 12
    f, u = divmod(total, ref_fardo)
    txt = ""
    if f > 0: txt += f"📦 {f} fardos "
    if u > 0: txt += f"🍺 {u} un"
    return txt if txt else "Zerado"

def gerar_mensagem(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    if pontos == 1: return f"Oi, {nome}! ✨\nObrigado por comprar na Adega do Barão! Já abri seu Cartão Fidelidade. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. 🍷", "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10: return f"E aí, {nome}! 👊\nCompra registrada! Agora você tem *{pontos} pontos*. ✨\nFaltam só {10-pontos} para o prêmio! Tamo junto! 🍻", f"Enviar Saldo ({pontos}/10) 📲"
    else: return f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** hoje! Aproveite! 🥳🍷", "🏆 ENVIAR PRÊMIO!"

# ==========================================
# 📱 MENU LATERAL (COM LINK SIMPLES)
# ==========================================
with st.sidebar:
    st.image(ICON_URL, width=80)
    st.title("🍷 Menu Principal")
    menu = st.radio("Navegar:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])
    
    st.divider()
    
    # Link de texto nativo do Streamlit (Clicável e à prova de falhas)
    st.markdown(f"**[📊 CLIQUE AQUI PARA ABRIR A PLANILHA]({LINK_PLANILHA})**")
    
    st.divider()
    
    if st.button("🚪 SAIR (Logout)", type="primary"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    
    df_est = carregar_dados_estoque()
    
    t1, t2, t3 = st.tabs(["📋 Lista Detalhada", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"])

    # --- LISTA ---
    if not df_est.empty:
        with t1:
            if 'ML' not in df_est.columns: df_est['ML'] = "-"

            df_est['custo_n'] = df_est['Custo'].apply(cvt_num)
            df_est['venda_n'] = df_est['Venda'].apply(cvt_num)
            df_est['Lucro Un.'] = df_est['venda_n'] - df_est['custo_n']
            df_est['Custo (R$)'] = df_est['custo_n'].apply(para_real_visual)
            df_est['Venda (R$)'] = df_est['venda_n'].apply(para_real_visual)
            df_est['Lucro (R$)'] = df_est['Lucro Un.'].apply(para_real_visual)
            df_est['Físico'] = df_est.apply(lambda r: calc_fisico(int(cvt_num(r['Estoque'])), int(cvt_num(r.get('Qtd_Fardo', 12)))), axis=1)
            
            st.dataframe(df_est[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']], use_container_width=True)

    # --- NOVO ---
    with t2:
        st.subheader("Cadastrar Produto")
        n_nome = st.text_input("Nome do Produto (Obrigatório):").upper()
        
        c_t1, c_t2 = st.columns(2)
        n_tipo = c_t1.selectbox("Tipo:", ["LATA", "LONG NECK", "GARRAFA 600ML", "LITRÃO", "OUTROS"])
        lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
        sel_ml = c_t2.selectbox("Volume (ML):", lista_ml)
        n_ml = c_t2.text_input("Digite o volume:", key="novo_ml_custom") if sel_ml == "Outros" else sel_ml

        c1, c2 = st.columns(2)
        n_custo = c1.text_input("Custo Unitário R$ (Obrigatório):", placeholder="3.06")
        n_venda = c2.text_input("Venda Unitária R$ (Obrigatório):", placeholder="4.99")
        
        c3, c4 = st.columns(2)
        n_forn = c3.text_input("Fornecedor (Obrigatório):")
        n_data = c4.date_input("Data da Compra", date.today())
        
        st.divider()
        st.write("📦 **Estoque Inicial:**")
        tipo_compra = st.radio("Formato da Compra:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
        col_a, col_b = st.columns(2)
        n_ref = col_a.number_input("Itens por Fardo (Ref):", value=12)
        
        qtd_inicial = col_b.number_input("Qtd Fardos:" if tipo_compra == "Fardo Fechado" else "Qtd Unidades:", min_value=0)
        qtd_final = qtd_inicial * n_ref if tipo_compra == "Fardo Fechado" else qtd_inicial
        
        if st.button("✅ CADASTRAR PRODUTO", type="primary"):
            erro = False
            if not n_nome: st.error("⚠️ Nome Obrigatório"); erro = True
            if not n_custo: st.error("⚠️ Custo Obrigatório"); erro = True
            if not n_venda: st.error("⚠️ Venda Obrigatória"); erro = True
            if not n_forn: st.error("⚠️ Fornecedor Obrigatório"); erro = True
            if sel_ml == "Outros" and not n_ml: st.error("⚠️ Digite o ML"); erro = True
            
            if not erro:
                sheet_estoque.append_row([n_nome, n_tipo, n_forn, salvar_com_ponto(cvt_num(n_custo)), salvar_com_ponto(cvt_num(n_venda)), qtd_final, n_data.strftime('%d/%m/%Y'), n_ref, n_ml])
                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "NOVO", qtd_final, n_forn])
                limpar_cache()
                st.success("Cadastrado com Sucesso!"); time.sleep(1); st.rerun()

    # --- EDITAR ---
    with t3:
        if not df_est.empty:
            sel_e = st.selectbox("Editar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                
                c_tipo, c_ml = st.columns(2)
                list_tipos = ["LATA", "LONG NECK", "GARRAFA 600ML", "LITRÃO", "OUTROS"]
                novo_tipo = c_tipo.selectbox("Tipo:", list_tipos, index=list_tipos.index(row.get('Tipo', 'LATA')) if row.get('Tipo', 'LATA') in list_tipos else 0)
                
                ml_banco = str(row.get('ML', '350ml'))
                idx_ml_ini = lista_ml.index(ml_banco) if ml_banco in lista_ml else 11
                sel_ml_edit = c_ml.selectbox("Volume (ML):", lista_ml, index=idx_ml_ini, key="ml_edit_select")
                final_ml = c_ml.text_input("Digite o volume personalizado:", value=ml_banco if ml_banco not in lista_ml else "", key="ml_edit_custom") if sel_ml_edit == "Outros" else sel_ml_edit

                c_a, c_b = st.columns(2)
                v_venda = c_a.text_input("Venda (R$):", value=str(row['Venda']))
                v_custo = c_b.text_input("Custo (R$):", value=str(row['Custo']))
                v_forn = st.text_input("Fornecedor:", value=str(row.get('Fornecedor', '')))
                
                st.write("---")
                f1, f2 = st.columns(2)
                add_f = f1.number_input("Add Fardos:", min_value=0)
                add_u = f2.number_input("Add Unidades:", min_value=0)
                
                b_sal, b_exc = st.columns(2)
                if b_sal.button("💾 SALVAR ALTERAÇÕES"):
                    ref = int(cvt_num(row.get('Qtd_Fardo', 12)))
                    novo_tot = int(cvt_num(row['Estoque'])) + (add_f * ref) + add_u
                    
                    sheet_estoque.update_cell(idx+2, 2, novo_tipo)
                    sheet_estoque.update_cell(idx+2, 3, v_forn)
                    sheet_estoque.update_cell(idx+2, 4, salvar_com_ponto(cvt_num(v_custo)))
                    sheet_estoque.update_cell(idx+2, 5, salvar_com_ponto(cvt_num(v_venda)))
                    sheet_estoque.update_cell(idx+2, 6, novo_tot)
                    sheet_estoque.update_cell(idx+2, 7, date.today().strftime('%d/%m/%Y'))
                    try: sheet_estoque.update_cell(idx+2, 9, final_ml)
                    except: pass
                    
                    if (add_f * ref) + add_u > 0: sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "ENTRADA", (add_f * ref) + add_u, f"Forn: {v_forn}"])
                    limpar_cache()
                    st.success("Atualizado!"); time.sleep(1); st.rerun()
                
                if b_exc.button("🗑️ EXCLUIR PRODUTO"):
                    sheet_estoque.delete_rows(int(idx + 2))
                    limpar_cache()
                    st.warning("Excluído!"); time.sleep(1); st.rerun()

# ==========================================
# 💰 CAIXA
# ==========================================
elif menu == "💰 Caixa":
    st.title("💰 Caixa & Fidelidade")
    if 'v_suc' not in st.session_state: st.session_state.v_suc = False
    
    if st.session_state.v_suc:
        st.success("Venda Realizada!")
        st.markdown(f'<a href="{st.session_state.l_zap}" target="_blank" class="big-btn">{st.session_state.b_txt}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.v_suc = False; st.rerun()
    else:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()
        
        sel_c = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist() if not df_cli.empty else ["🆕 NOVO"])
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO": n_c = c1.text_input("Nome:").upper(); t_c = c2.text_input("Tel:")
        else: n_c = sel_c.split(" - ")[0]; t_c = sel_c.split(" - ")[1]
        
        st.divider()
        if not df_est.empty:
            p_sel = st.selectbox("Produto:", ["(Selecione...)"] + df_est['Nome'].tolist())
            if p_sel != "(Selecione...)":
                idx_p = df_est[df_est['Nome'] == p_sel].index[0]
                row_p = df_est.iloc[idx_p]
                st.markdown(f'<div class="estoque-info">📊 EM ESTOQUE: {calc_fisico(int(cvt_num(row_p["Estoque"])), int(cvt_num(row_p.get("Qtd_Fardo", 12))))}</div>', unsafe_allow_html=True)

            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)
            
            if st.button("✅ FINALIZAR VENDA"):
                tl = limpar_tel(t_c)
                if p_sel != "(Selecione...)":
                    ref = int(cvt_num(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    atual = int(cvt_num(df_est.iloc[idx_p]['Estoque']))
                    
                    if atual >= baixa:
                        sheet_estoque.update_cell(idx_p+2, 6, atual - baixa)
                        sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), p_sel, "VENDA", baixa, salvar_com_ponto(baixa * cvt_num(df_est.iloc[idx_p]['Venda']))])
                    else: st.error(f"Estoque insuficiente! Você tem {atual} unidades."); st.stop()

                if not df_cli.empty and not df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl].empty:
                    match = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl]
                    pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([n_c, tl, 1, date.today().strftime('%d/%m/%Y')])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_c, tl, pts])
                msg, btn = gerar_mensagem(n_c, pts)
                
                limpar_cache()
                st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{tl}&text={urllib.parse.quote(msg)}"
                st.session_state.b_txt = btn; st.session_state.v_suc = True; st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = carregar_dados_clientes()
    if not df_c.empty:
        sel = st.selectbox("Editar Cliente:", ["Selecione..."] + df_c['nome'].tolist())
        if sel != "Selecione...":
            idx = df_c[df_c['nome']==sel].index[0]
            with st.form("ed_c"):
                nn = st.text_input("Nome:", value=df_c.iloc[idx]['nome'])
                nt = st.text_input("Tel:", value=str(df_c.iloc[idx]['telefone']))
                np = st.number_input("Pontos:", value=int(df_c.iloc[idx]['compras']))
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 Salvar"):
                    sheet_clientes.update_cell(idx+2, 1, nn); sheet_clientes.update_cell(idx+2, 2, nt); sheet_clientes.update_cell(idx+2, 3, np)
                    limpar_cache()
                    st.success("Salvo!"); time.sleep(1); st.rerun()
                if b2.form_submit_button("🗑️ Excluir", type="primary"):
                    sheet_clientes.delete_rows(int(idx+2))
                    limpar_cache()
                    st.rerun()

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 Históricos":
    st.title("📊 Relatórios")
    t1, t2 = st.tabs(["Vendas (Clientes)", "Movim. Estoque"])
    with t1: st.dataframe(carregar_historico_cli(), use_container_width=True)
    with t2: st.dataframe(carregar_historico_est(), use_container_width=True)
