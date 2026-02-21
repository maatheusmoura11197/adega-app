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
ICON_URL = "https://splendid-plum-mslpekoeqx.edgeone.app/cerveja.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
    div.stButton > button {{ background-color: #008CBA; color: white; font-weight: bold; border-radius: 10px; height: 3em; width: 100%; border: none; }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{ padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3; border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }}
    </style>
    <link rel="shortcut icon" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
    """, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN & VARIÁVEIS DE SESSÃO
# ==========================================
SENHA_DO_SISTEMA = "adega123"

if 'logado' not in st.session_state: st.session_state.logado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

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
    
    # CORREÇÃO DA LINHA 56 (Removido o parêntese extra da sua foto)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Fidelidade")
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

    @st.cache_data(ttl=15)
    def carregar_dados_estoque():
        try: return pd.DataFrame(sheet_estoque.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=15)
    def carregar_dados_clientes():
        try: return pd.DataFrame(sheet_clientes.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=15)
    def carregar_historico_cli():
        try: return pd.DataFrame(sheet_hist_cli.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=15)
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
    st.error(f"Erro de conexão: {e}")
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
    if pontos == 1: return f"Oi, {nome}! ✨\nObrigado por comprar na Adega do Barão! Já abri seu Cartão Fidelidade. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. Ah e não esquece de avaliar a gente no *JA PEDIU* 🍷", "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10: return f"E aí, {nome}! 👊\nCompra registrada! Agora você tem *{pontos} pontos*. ✨\nFaltam só {10-pontos} para o prêmio! Tamo junto! 🍻", f"Enviar Saldo ({pontos}/10) 📲"
    else: return f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** hoje! Aproveite! 🥳🍷", "🏆 ENVIAR PRÊMIO!"

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🔧 Menu Principal")
    menu = st.radio("Navegar:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 HISTÓRICOS"])
    st.divider()
    if st.button("SAIR 📴"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = carregar_dados_estoque()
    
    if not df_est.empty:
        if 'ML' not in df_est.columns: df_est['ML'] = "-"
        if 'Tipo' not in df_est.columns: df_est['Tipo'] = "-"
        df_est['Nome_Exibicao'] = df_est['Nome'].astype(str) + " - " + df_est['Tipo'].astype(str) + " (" + df_est['ML'].astype(str) + ")"
    
    aba_estoque = st.radio("Selecione a tela:", ["📋 Lista Detalhada", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if aba_estoque == "📋 Lista Detalhada":
        if not df_est.empty:
            df_vis = df_est.copy()
            df_vis['custo_n'] = df_vis['Custo'].apply(cvt_num)
            df_vis['venda_n'] = df_vis['Venda'].apply(cvt_num)
            df_vis['Lucro Un.'] = df_vis['venda_n'] - df_vis['custo_n']
            df_vis['Custo (R$)'] = df_vis['custo_n'].apply(para_real_visual)
            df_vis['Venda (R$)'] = df_vis['venda_n'].apply(para_real_visual)
            df_vis['Lucro (R$)'] = df_vis['Lucro Un.'].apply(para_real_visual)
            df_vis['Físico'] = df_vis.apply(lambda r: calc_fisico(int(cvt_num(r['Estoque'])), int(cvt_num(r.get('Qtd_Fardo', 12)))), axis=1)
            df_vis = df_vis.sort_values(by='Nome')
            st.dataframe(df_vis[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']], use_container_width=True)
        else:
            st.info("O estoque está vazio.")

    elif aba_estoque == "🆕 Cadastrar Novo":
        st.subheader("Cadastrar Produto")
        with st.form("form_novo_produto", clear_on_submit=True):
            n_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:").upper()
            c_t1, c_t2 = st.columns(2)
            lista_tipos = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
            n_tipo = c_t1.selectbox("Tipo:", lista_tipos)
            lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
            sel_ml = c_t2.selectbox("Volume (ML):", lista_ml)
            n_ml = c_t2.text_input("Se escolheu 'Outros', digite o ML :red[(Obrigatório)]:")
            c1, c2 = st.columns(2)
            n_custo = c1.text_input("Custo Unitário R$ :red[(Obrigatório)]:", placeholder="0.00")
            n_venda = c2.text_input("Venda Unitária R$ :red[(Obrigatório)]:", placeholder="00.00")
            c3, c4 = st.columns(2)
            lista_fornecedores = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
            sel_forn = c3.selectbox("Fornecedor :red[(Obrigatório)]:", lista_fornecedores)
            n_forn_custom = c4.text_input("Se escolheu 'Outros', digite o Fornecedor :red[(Obrigatório)]:")
            n_data = st.date_input("Data Compra", date.today())
            st.divider()
            tipo_compra = st.radio("Formato da Compra:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
            col_a, col_b = st.columns(2)
            n_ref = col_a.number_input("Itens por Fardo (Ref):", value=12)
            qtd_inicial = col_b.number_input("Qtd Fardos / Unidades:" , min_value=0)
            
            if st.form_submit_button("✅ CADASTRAR PRODUTO", type="primary"):
                forn_final = n_forn_custom if sel_forn == "Outros" else sel_forn
                ml_final = n_ml if sel_ml == "Outros" else sel_ml
                qtd_final = qtd_inicial * n_ref if tipo_compra == "Fardo Fechado" else qtd_inicial
                if not n_nome or not n_custo or not n_venda or not forn_final:
                    st.error("Preencha todos os campos obrigatórios!")
                else:
                    sheet_estoque.append_row([n_nome, n_tipo, forn_final, salvar_com_ponto(cvt_num(n_custo)), salvar_com_ponto(cvt_num(n_venda)), qtd_final, n_data.strftime('%d/%m/%Y'), n_ref, ml_final])
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "NOVO", qtd_final, forn_final])
                    limpar_cache()
                    st.success(f"✅ Produto '{n_nome}' cadastrado!")

    elif aba_estoque == "✏️ Editar/Excluir":
        if not df_est.empty:
            lista_prods = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            sel_e = st.selectbox("Selecione para Editar:", ["Selecione..."] + lista_prods)
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome_Exibicao'] == sel_e].index[0]
                row = df_est.iloc[idx]
                with st.form(key=f"ed_form_{idx}", clear_on_submit=True):
                    novo_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:", value=str(row['Nome'])).upper()
                    c_tipo, c_ml = st.columns(2)
                    list_tipos = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
                    idx_t = list_tipos.index(row['Tipo']) if row['Tipo'] in list_tipos else 1
                    novo_tipo = c_tipo.selectbox("Tipo:", list_tipos, index=idx_t)
                    lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
                    idx_m = lista_ml.index(row['ML']) if row['ML'] in lista_ml else 11
                    sel_ml_edit = c_ml.selectbox("Volume (ML):", lista_ml, index=idx_m)
                    n_ml_edit = c_ml.text_input("Se 'Outros', digite o ML:", value=row['ML'] if sel_ml_edit == "Outros" else "")
                    c_a, c_b = st.columns(2)
                    v_venda = c_a.text_input("Venda (R$):", value=str(row['Venda']))
                    v_custo = c_b.text_input("Custo (R$):", value=str(row['Custo']))
                    c_f1, c_f2 = st.columns(2)
                    lista_fornecedores = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
                    idx_f = lista_fornecedores.index(row['Fornecedor']) if row['Fornecedor'] in lista_fornecedores else 5
                    sel_forn_edit = c_f1.selectbox("Fornecedor:", lista_fornecedores, index=idx_f)
                    n_forn_edit = c_f2.text_input("Se 'Outros', digite o Fornecedor:", value=row['Fornecedor'] if sel_forn_edit == "Outros" else "")
                    
                    st.write("---")
                    estoque_atual_num = int(cvt_num(row['Estoque']))
                    ref_fardo = int(cvt_num(row.get('Qtd_Fardo', 12)))
                    st.info(f"📊 Estoque Atual: {calc_fisico(estoque_atual_num, ref_fardo)} ({estoque_atual_num} unid.)")
                    e1, e2, e3 = st.columns(3)
                    estoque_editado = e1.number_input("Corrigir Total:", value=estoque_atual_num)
                    add_f = e2.number_input("➕ Novo Fardo:", min_value=0)
                    add_u = e3.number_input("➕ Nova Unid:", min_value=0)
                    
                    b_sal, b_exc = st.columns(2)
                    if b_sal.form_submit_button("💾 SALVAR"):
                        forn_fin = n_forn_edit if sel_forn_edit == "Outros" else sel_forn_edit
                        ml_fin = n_ml_edit if sel_ml_edit == "Outros" else sel_ml_edit
                        novo_tot = estoque_editado + (add_f * ref_fardo) + add_u
                        sheet_estoque.update_cell(idx+2, 1, novo_nome)
                        sheet_estoque.update_cell(idx+2, 2, novo_tipo)
                        sheet_estoque.update_cell(idx+2, 3, forn_fin)
                        sheet_estoque.update_cell(idx+2, 4, salvar_com_ponto(cvt_num(v_custo)))
                        sheet_estoque.update_cell(idx+2, 5, salvar_com_ponto(cvt_num(v_venda)))
                        sheet_estoque.update_cell(idx+2, 6, novo_tot)
                        sheet_estoque.update_cell(idx+2, 7, date.today().strftime('%d/%m/%Y'))
                        sheet_estoque.update_cell(idx+2, 9, ml_fin)
                        limpar_cache()
                        st.success("Atualizado!"); time.sleep(1); st.rerun()
                    if b_exc.form_submit_button("🗑️ EXCLUIR", type="primary"):
                        sheet_estoque.delete_rows(int(idx + 2))
                        limpar_cache()
                        st.rerun()

# ==========================================
# 💰 CAIXA & CARRINHO
# ==========================================
elif menu == "💰 Caixa":
    st.title("💰 Caixa & Fidelidade")
    if 'v_suc' in st.session_state and st.session_state.v_suc:
        st.success("Venda Realizada!")
        st.markdown(f'<a href="{st.session_state.l_zap}" target="_blank" class="big-btn">{st.session_state.b_txt}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.v_suc = False; st.rerun()
    else:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()
        
        # Garante a coluna inteligente no Caixa também para evitar KeyError
        if not df_est.empty:
            if 'Nome_Exibicao' not in df_est.columns:
                df_est['Nome_Exibicao'] = df_est['Nome'].astype(str) + " - " + df_est['Tipo'].astype(str) + " (" + df_est['ML'].astype(str) + ")"

        lista_c = ["🆕 NOVO"] + sorted((df_cli['nome'].astype(str) + " - " + df_cli['telefone'].astype(str)).tolist()) if not df_cli.empty else ["🆕 NOVO"]
        sel_c = st.selectbox("Cliente:", lista_c)
        c1, c2 = st.columns(2)
        n_c = c1.text_input("Nome:").upper() if sel_c == "🆕 NOVO" else sel_c.split(" - ")[0]
        t_c = c2.text_input("Tel:") if sel_c == "🆕 NOVO" else sel_c.split(" - ")[1]
        
        st.divider()
        if not df_est.empty:
            # CORREÇÃO DO KEYERROR: Verifica se a coluna existe antes de ordenar
            lista_p = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            p_sel = st.selectbox("Produto:", ["(Selecione...)"] + lista_p, key="p_caixa")
            if p_sel != "(Selecione...)":
                # Busca segura da linha do produto
                row_p = df_est[df_est['Nome_Exibicao'] == p_sel].iloc[0]
                idx_p = df_est[df_est['Nome_Exibicao'] == p_sel].index[0]
                st.info(f"💰 Preço: {para_real_visual(cvt_num(row_p['Venda']))} | Estoque: {row_p['Estoque']}")
                q1, q2 = st.columns(2)
                v_f = q1.number_input("Fardos:", min_value=0, key="f_caixa")
                v_u = q2.number_input("Unid:", min_value=0, key="u_caixa")
                if st.button("➕ ADICIONAR"):
                    ref = int(cvt_num(row_p.get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    if int(row_p['Estoque']) >= baixa > 0:
                        st.session_state.carrinho.append({"Produto": p_sel, "Qtd": baixa, "Preço": cvt_num(row_p['Venda']), "idx": idx_p})
                        st.rerun()
                    else: st.error("Qtd inválida ou estoque insuficiente.")
        else:
            st.warning("⚠️ Cadastre produtos no Estoque primeiro!")

        if st.session_state.carrinho:
            st.write("---")
            st.subheader("🛍️ Carrinho")
            df_car = pd.DataFrame(st.session_state.carrinho)
            st.table(df_car[['Produto', 'Qtd', 'Preço']])
            total = sum(item['Qtd'] * item['Preço'] for item in st.session_state.carrinho)
            st.subheader(f"Total: {para_real_visual(total)}")
            
            c_f, c_l = st.columns(2)
            if c_l.button("Limpar Carrinho"): st.session_state.carrinho = []; st.rerun()
            if c_f.button("✅ FINALIZAR VENDA", type="primary"):
                with st.spinner("Finalizando..."):
                    for item in st.session_state.carrinho:
                        prod_row = df_est.iloc[item['idx']]
                        novo_est = int(prod_row['Estoque']) - item['Qtd']
                        sheet_estoque.update_cell(int(item['idx']+2), 6, novo_est)
                        sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), item['Produto'], "VENDA", item['Qtd'], salvar_com_ponto(item['Qtd']*item['Preço'])])
                    
                    tl = limpar_tel(t_c)
                    pts = 1
                    if not df_cli.empty and not df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl].empty:
                        cli_row = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl]
                        pts = int(cli_row.iloc[0]['compras']) + 1
                        sheet_clientes.update_cell(int(cli_row.index[0]+2), 3, pts)
                    else:
                        sheet_clientes.append_row([n_c, tl, 1, date.today().strftime('%d/%m/%Y')])
                    
                    sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_c, tl, pts])
                    msg, btn = gerar_mensagem(n_c, pts)
                    st.session_state.carrinho = []
                    st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{tl}&text={urllib.parse.quote(msg)}"
                    st.session_state.b_txt = btn
                    st.session_state.v_suc = True
                    limpar_cache()
                    st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = carregar_dados_clientes()
    st.metric("Total", len(df_c) if not df_c.empty else 0)
    t1, t2 = st.tabs(["📋 Lista", "⚙️ Editar"])
    with t1:
        if not df_c.empty: st.dataframe(df_c.sort_values('nome'), use_container_width=True)
    with t2:
        if not df_c.empty:
            sel = st.selectbox("Cliente:", ["Selecione..."] + sorted(df_c['nome'].tolist()))
            if sel != "Selecione...":
                idx = df_c[df_c['nome']==sel].index[0]
                with st.form(f"cli_{idx}"):
                    nn = st.text_input("Nome:", value=df_c.iloc[idx]['nome'])
                    nt = st.text_input("Tel:", value=str(df_c.iloc[idx]['telefone']))
                    np = st.number_input("Pontos:", value=int(df_c.iloc[idx]['compras']))
                    if st.form_submit_button("💾 Salvar"):
                        sheet_clientes.update_cell(idx+2, 1, nn)
                        sheet_clientes.update_cell(idx+2, 2, nt)
                        sheet_clientes.update_cell(idx+2, 3, np)
                        limpar_cache(); st.rerun()

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 HISTÓRICOS":
    st.title("📊 Relatórios")
    h1, h2 = st.tabs(["Clientes", "Estoque"])
    with h1: st.dataframe(carregar_historico_cli(), use_container_width=True)
    with h2: st.dataframe(carregar_historico_est(), use_container_width=True)
