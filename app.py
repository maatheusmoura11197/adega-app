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
if 'carrinho' not in st.session_state: st.session_state.carrinho = [] # Criando o Carrinho de Compras

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
    if pontos == 1: return f"Oi, {nome}! ✨\nObrigado por comprar na Adega do Barão! Já abri seu Cartão Fidelidade. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. Ah e não esquece de avaliar a gente no *JA PEDIU* 🍷", "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10: return f"E aí, {nome}! 👊\nCompra registrada! Agora você tem *{pontos} pontos*. ✨\nFaltam só {10-pontos} para o prêmio! Tamo junto! 🍻", f"Enviar Saldo ({pontos}/10) 📲"
    else: return f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** hoje! Aproveite! 🥳🍷", "🏆 ENVIAR PRÊMIO!"

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🔧 Menu Principal")
    menu = st.radio("Navegar:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])
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
    
    # --- INTELIGÊNCIA: NOME DE EXIBIÇÃO COMPOSTO ---
    if not df_est.empty:
        if 'ML' not in df_est.columns: df_est['ML'] = "-"
        if 'Tipo' not in df_est.columns: df_est['Tipo'] = "-"
        # Cria a coluna inteligente "Nome_Exibicao"
        df_est['Nome_Exibicao'] = df_est['Nome'].astype(str) + " - " + df_est['Tipo'].astype(str) + " (" + df_est['ML'].astype(str) + ")"
    
    aba_estoque = st.radio("Selecione a tela:", ["📋 Lista Detalhada", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"], horizontal=True, label_visibility="collapsed")
    st.divider()

    # --- LISTA ---
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
            
            # Ordenação Alfabética Rigorosa
            df_vis = df_vis.sort_values(by='Nome')
            st.dataframe(df_vis[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']], use_container_width=True)
        else:
            st.info("O estoque está vazio. Cadastre o primeiro produto na tela 'Cadastrar Novo'.")

    # --- NOVO ---
    elif aba_estoque == "🆕 Cadastrar Novo":
        st.subheader("Cadastrar Produto")
        with st.form("form_novo_produto", clear_on_submit=True):
            n_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:").upper()
            
            c_t1, c_t2 = st.columns(2)
            # Tipos em Ordem Alfabética
            lista_tipos = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
            n_tipo = c_t1.selectbox("Tipo:", lista_tipos)
            
            lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
            sel_ml = c_t2.selectbox("Volume (ML):", lista_ml)
            n_ml = c_t2.text_input("Se escolheu 'Outros', digite o ML :red[(Obrigatório)]:")

            c1, c2 = st.columns(2)
            n_custo = c1.text_input("Custo Unitário R$ :red[(Obrigatório)]:", placeholder="0.00")
            n_venda = c2.text_input("Venda Unitária R$ :red[(Obrigatório)]:", placeholder="00.00")
            
            # --- Fornecedores em Ordem Alfabética e Lógica Anti-Travamento ---
            c3, c4 = st.columns(2)
            lista_fornecedores = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
            sel_forn = c3.selectbox("Fornecedor :red[(Obrigatório)]:", lista_fornecedores)
            n_forn_custom = c4.text_input("Se escolheu 'Outros', digite o Fornecedor :red[(Obrigatório)]:")
            
            n_data = st.date_input("Data Compra", date.today())
            
            st.divider()
            st.write("📦 **Estoque Inicial:**")
            tipo_compra = st.radio("Formato da Compra:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
            col_a, col_b = st.columns(2)
            n_ref = col_a.number_input("Itens por Fardo (Ref):", value=12)
            
            qtd_inicial = col_b.number_input("Qtd Fardos / Unidades:" , min_value=0)
            
            if st.form_submit_button("✅ CADASTRAR PRODUTO", type="primary"):
                qtd_final = qtd_inicial * n_ref if tipo_compra == "Fardo Fechado" else qtd_inicial
                ml_final = n_ml if sel_ml == "Outros" else sel_ml
                forn_final = n_forn_custom if sel_forn == "Outros" else sel_forn
                
                erro = False
                if not n_nome: st.error("⚠️ Nome Obrigatório"); erro = True
                if not n_custo: st.error("⚠️ Custo Obrigatório"); erro = True
                if not n_venda: st.error("⚠️ Venda Obrigatória"); erro = True
                if not forn_final: st.error("⚠️ Fornecedor Obrigatório"); erro = True
                if sel_ml == "Outros" and not n_ml: st.error("⚠️ Digite o ML"); erro = True
                
                if not erro:
                    sheet_estoque.append_row([n_nome, n_tipo, forn_final, salvar_com_ponto(cvt_num(n_custo)), salvar_com_ponto(cvt_num(n_venda)), qtd_final, n_data.strftime('%d/%m/%Y'), n_ref, ml_final])
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "NOVO", qtd_final, forn_final])
                    limpar_cache()
                    st.success(f"✅ O produto '{n_nome}' foi cadastrado com sucesso! A tela já está limpa para o próximo.")

    # --- EDITAR ---
    elif aba_estoque == "✏️ Editar/Excluir":
        if not df_est.empty:
            lista_produtos_ordenada = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            sel_e = st.selectbox("Selecione o produto para Editar:", ["Selecione..."] + lista_produtos_ordenada)
            
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome_Exibicao'] == sel_e].index[0]
                row = df_est.iloc[idx]
                
                with st.form("form_editar_produto"):
                    novo_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:", value=str(row['Nome'])).upper()
                    
                    c_tipo, c_ml = st.columns(2)
                    # Tipos em Ordem Alfabética
                    list_tipos = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
                    t_atual = row.get('Tipo', 'LATA')
                    idx_t = list_tipos.index(t_atual) if t_atual in list_tipos else 1
                    novo_tipo = c_tipo.selectbox("Tipo:", list_tipos, index=idx_t)
                    
                    lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
                    ml_banco = str(row.get('ML', '350ml'))
                    idx_ml_ini = lista_ml.index(ml_banco) if ml_banco in lista_ml else 11
                    sel_ml_edit = c_ml.selectbox("Volume (ML):", lista_ml, index=idx_ml_ini)
                    final_ml_txt = c_ml.text_input("Se 'Outros', digite o ML :red[(Obrigatório)]:", value=ml_banco if ml_banco not in lista_ml else "")

                    c_a, c_b = st.columns(2)
                    v_venda = c_a.text_input("Venda (R$) :red[(Obrigatório)]:", value=str(row['Venda']))
                    v_custo = c_b.text_input("Custo (R$) :red[(Obrigatório)]:", value=str(row['Custo']))
                    
                    # --- Fornecedores em Ordem Alfabética e Lógica Anti-Travamento ---
                    c_f1, c_f2 = st.columns(2)
                    lista_fornecedores = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
                    forn_atual = str(row.get('Fornecedor', ''))
                    idx_forn = lista_fornecedores.index(forn_atual) if forn_atual in lista_fornecedores else 5
                    
                    sel_forn_edit = c_f1.selectbox("Fornecedor :red[(Obrigatório)]:", lista_fornecedores, index=idx_forn)
                    final_forn_txt = c_f2.text_input("Se 'Outros', digite o Fornecedor :red[(Obrigatório)]:", value=forn_atual if forn_atual not in lista_fornecedores else "")
                    
                    st.write("---")
                    st.write("📦 **Controle de Estoque:**")
                    
                    estoque_atual_num = int(cvt_num(row['Estoque']))
                    ref_fardo = int(cvt_num(row.get('Qtd_Fardo', 12)))
                    
                    st.info(f"📊 Estoque Físico Atual no Sistema: **{calc_fisico(estoque_atual_num, ref_fardo)}** (Total: {estoque_atual_num} unid.)")
                    
                    e1, e2, e3 = st.columns(3)
                    estoque_editado = e1.number_input("Corrigir Total (Unid.):", value=estoque_atual_num, min_value=0, help="Altere aqui se o sistema estiver com o número errado.")
                    add_f = e2.number_input("➕ Nova Compra (Fardos):", min_value=0)
                    add_u = e3.number_input("➕ Nova Compra (Unid.):", min_value=0)
                    
                    st.write("---")
                    b_sal, b_exc = st.columns(2)
                    btn_salvar = b_sal.form_submit_button("💾 SALVAR ALTERAÇÕES")
                    btn_excluir = b_exc.form_submit_button("🗑️ EXCLUIR PRODUTO")
                    
                    if btn_salvar:
                        forn_final_salvar = final_forn_txt if sel_forn_edit == "Outros" else sel_forn_edit
                        ml_save = final_ml_txt if sel_ml_edit == "Outros" else sel_ml_edit
                        
                        if not novo_nome:
                            st.error("⚠️ O nome do produto não pode ficar vazio!")
                        elif not forn_final_salvar:
                            st.error("⚠️ O fornecedor não pode ficar vazio!")
                        elif sel_ml_edit == "Outros" and not ml_save:
                            st.error("⚠️ O ML não pode ficar vazio!")
                        else:
                            novo_tot = estoque_editado + (add_f * ref_fardo) + add_u
                            
                            sheet_estoque.update_cell(idx+2, 1, novo_nome)
                            sheet_estoque.update_cell(idx+2, 2, novo_tipo)
                            sheet_estoque.update_cell(idx+2, 3, forn_final_salvar)
                            sheet_estoque.update_cell(idx+2, 4, salvar_com_ponto(cvt_num(v_custo)))
                            sheet_estoque.update_cell(idx+2, 5, salvar_com_ponto(cvt_num(v_venda)))
                            sheet_estoque.update_cell(idx+2, 6, novo_tot)
                            sheet_estoque.update_cell(idx+2, 7, date.today().strftime('%d/%m/%Y'))
                            try: sheet_estoque.update_cell(idx+2, 9, ml_save)
                            except: pass
                            
                            if (add_f * ref_fardo) + add_u > 0: 
                                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "ENTRADA", (add_f * ref_fardo) + add_u, f"Forn: {forn_final_salvar}"])
                            elif estoque_editado != estoque_atual_num:
                                diff = estoque_editado - estoque_atual_num
                                tipo_ajuste = "AJUSTE (+)" if diff > 0 else "AJUSTE (-)"
                                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, tipo_ajuste, abs(diff), "Correção Manual"])
                                
                            limpar_cache()
                            st.success("Atualizado!"); time.sleep(1); st.rerun()
                    
                    if btn_excluir:
                        sheet_estoque.delete_rows(int(idx + 2))
                        limpar_cache()
                        st.warning("Excluído!"); time.sleep(1); st.rerun()

# ==========================================
# 💰 CAIXA & CARRINHO DE COMPRAS
# ==========================================
elif menu == "💰 Caixa":
    st.title("💰 Caixa & Fidelidade")
    
    if 'v_suc' in st.session_state and st.session_state.v_suc:
        st.success("Venda Realizada com Sucesso!")
        st.markdown(f'<a href="{st.session_state.l_zap}" target="_blank" class="big-btn">{st.session_state.b_txt}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): 
            st.session_state.v_suc = False
            st.rerun()
    else:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()
        
        # 1. Seleção do Cliente
        if not df_cli.empty:
            lista_clientes_ordenada = sorted((df_cli['nome'].astype(str) + " - " + df_cli['telefone'].astype(str)).tolist())
            opcoes_clientes = ["🆕 NOVO"] + lista_clientes_ordenada
        else:
            opcoes_clientes = ["🆕 NOVO"]
            
        sel_c = st.selectbox("Cliente da Venda:", opcoes_clientes)
        
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO": 
            n_c = c1.text_input("Nome:").upper()
            t_c = c2.text_input("Tel:")
        else: 
            n_c = sel_c.split(" - ")[0]
            t_c = sel_c.split(" - ")[1]
        
        st.divider()
        st.write("🛒 **Adicionar Produtos ao Carrinho**")
        
        if not df_est.empty:
            if 'ML' not in df_est.columns: df_est['ML'] = "-"
            if 'Tipo' not in df_est.columns: df_est['Tipo'] = "-"
            df_est['Nome_Exibicao'] = df_est['Nome'].astype(str) + " - " + df_est['Tipo'].astype(str) + " (" + df_est['ML'].astype(str) + ")"
            
            lista_produtos_caixa = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            
            # --- CHAVE DE MEMÓRIA PARA O SELECTBOX DE PRODUTO ---
            p_sel = st.selectbox("Selecione o Produto:", ["(Selecione...)"] + lista_produtos_caixa, key="select_prod_caixa")
            
            if p_sel != "(Selecione...)":
                idx_p = df_est[df_est['Nome_Exibicao'] == p_sel].index[0]
                row_p = df_est.iloc[idx_p]
                
                atual = int(cvt_num(row_p["Estoque"]))
                ref = int(cvt_num(row_p.get("Qtd_Fardo", 12)))
                vlr_un = cvt_num(row_p['Venda'])
                
                st.markdown(f'<div class="estoque-info">📊 EM ESTOQUE: {calc_fisico(atual, ref)} | 💰 Preço Un: {para_real_visual(vlr_un)}</div>', unsafe_allow_html=True)

                q1, q2 = st.columns(2)
                # Chaves de memória para as quantidades
                v_f = q1.number_input("Fardos:", min_value=0, key="c_fardos")
                v_u = q2.number_input("Unidades:", min_value=0, key="c_unid")
                
                if st.button("➕ ADICIONAR AO CARRINHO"):
                    baixa = (v_f * ref) + v_u
                    
                    if baixa == 0:
                        st.warning("⚠️ Adicione pelo menos 1 unidade ou fardo para colocar no carrinho.")
                    elif atual >= baixa:
                        total_item_reais = baixa * vlr_un
                        sucesso_ao_adicionar = False
                        achou = False
                        
                        # Verifica se já está no carrinho
                        for item in st.session_state.carrinho:
                            if item["Produto"] == p_sel:
                                achou = True
                                if (item["Total Unid."] + baixa) > atual:
                                    st.error("⚠️ Estoque insuficiente para essa soma!")
                                else:
                                    item["Fardos"] += v_f
                                    item["Unidades"] += v_u
                                    item["Total Unid."] += baixa
                                    item["Valor R$"] += total_item_reais
                                    sucesso_ao_adicionar = True
                                break
                        
                        # Adiciona como item novo se não estiver
                        if not achou:
                            st.session_state.carrinho.append({
                                "Produto": p_sel,
                                "Fardos": v_f,
                                "Unidades": v_u,
                                "Total Unid.": baixa,
                                "Valor R$": total_item_reais
                            })
                            sucesso_ao_adicionar = True
                            
                        # --- LIMPEZA MÁGICA APÓS ADICIONAR ---
                        if sucesso_ao_adicionar:
                            if 'select_prod_caixa' in st.session_state:
                                del st.session_state['select_prod_caixa']
                            if 'c_fardos' in st.session_state:
                                del st.session_state['c_fardos']
                            if 'c_unid' in st.session_state:
                                del st.session_state['c_unid']
                            st.rerun() # Recarrega a tela com os campos limpos!
                    else: 
                        st.error(f"⚠️ Estoque insuficiente! Você tem apenas {atual} unidades disponíveis.")

        # ========================================
        # MOSTRAR O CARRINHO E FINALIZAR A VENDA
        # ========================================
        if len(st.session_state.carrinho) > 0:
            st.write("---")
            st.subheader("🛍️ Seu Carrinho:")
            
            df_carrinho = pd.DataFrame(st.session_state.carrinho)
            df_carrinho_vis = df_carrinho.copy()
            df_carrinho_vis['Valor R$'] = df_carrinho_vis['Valor R$'].apply(para_real_visual)
            st.dataframe(df_carrinho_vis, use_container_width=True)
            
            valor_total_compra = sum(item['Valor R$'] for item in st.session_state.carrinho)
            st.success(f"💰 **VALOR TOTAL DA COMPRA: {para_real_visual(valor_total_compra)}**")
            
            col_fin, col_limp = st.columns(2)
            
            if col_limp.button("🗑️ Limpar Carrinho"):
                st.session_state.carrinho = []
                st.rerun()
                
            if col_fin.button("✅ FINALIZAR VENDA COMPLETA", type="primary"):
                tl = limpar_tel(t_c)
                
                with st.spinner("Registrando produtos e baixando estoque..."):
                    for item in st.session_state.carrinho:
                        nome_prod = item["Produto"]
                        qtd_baixa = item["Total Unid."]
                        valor_total_item = item["Valor R$"]
                        
                        match_prod = df_est[df_est['Nome_Exibicao'] == nome_prod]
                        if not match_prod.empty:
                            idx_p_planilha = match_prod.index[0]
                            estoque_atualizado = int(cvt_num(match_prod.iloc[0]['Estoque'])) - qtd_baixa
                            
                            sheet_estoque.update_cell(idx_p_planilha+2, 6, estoque_atualizado)
                            sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), nome_prod, "VENDA", qtd_baixa, salvar_com_ponto(valor_total_item)])
                            time.sleep(0.5) 

                if not df_cli.empty and not df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl].empty:
                    match_cli = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tl]
                    pts = int(match_cli.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match_cli.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([n_c, tl, 1, date.today().strftime('%d/%m/%Y')])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_c, tl, pts])
                msg, btn = gerar_mensagem(n_c, pts)
                
                st.session_state.carrinho = []
                limpar_cache()
                
                st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{tl}&text={urllib.parse.quote(msg)}"
                st.session_state.b_txt = btn
                st.session_state.v_suc = True
                st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = carregar_dados_clientes()
    
    total_clientes = len(df_c) if not df_c.empty else 0
    st.metric("Total de Clientes Cadastrados", total_clientes)
    
    t_lista, t_editar = st.tabs(["📋 Lista de Clientes", "⚙️ Editar/Excluir"])
    
    with t_lista:
        if not df_c.empty:
            df_view = df_c[['nome', 'telefone', 'compras']].copy()
            df_view.columns = ["Nome do Cliente", "Telefone", "Pontos Acumulados"]
            
            df_view = df_view.sort_values(by="Nome do Cliente")
            
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum cliente cadastrado ainda.")

    with t_editar:
        if not df_c.empty:
            lista_nomes_ordenada = sorted(df_c['nome'].astype(str).tolist())
            sel = st.selectbox("Editar Cliente:", ["Selecione..."] + lista_nomes_ordenada)
            
            if sel != "Selecione...":
                idx = df_c[df_c['nome']==sel].index[0]
                pts_atuais = int(df_c.iloc[idx]['compras'])
                
                if pts_atuais < 10:
                    st.info(f"🏆 Pontuação Atual: **{pts_atuais} pontos** (Faltam {10-pts_atuais} para o prêmio!)")
                else:
                    st.info(f"🏆 Pontuação Atual: **{pts_atuais} pontos** - PRÊMIO DISPONÍVEL! 🎁")
                
                with st.form("ed_c"):
                    nn = st.text_input("Nome:", value=df_c.iloc[idx]['nome'])
                    nt = st.text_input("Tel:", value=str(df_c.iloc[idx]['telefone']))
                    np = st.number_input("Pontos:", value=pts_atuais)
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Salvar"):
                        sheet_clientes.update_cell(idx+2, 1, nn)
                        sheet_clientes.update_cell(idx+2, 2, nt)
                        sheet_clientes.update_cell(idx+2, 3, np)
                        limpar_cache()
                        st.success("Salvo!"); time.sleep(1); st.rerun()
                    if b2.form_submit_button("🗑️ Excluir", type="primary"):
                        sheet_clientes.delete_rows(int(idx+2))
                        limpar_cache()
                        st.rerun()

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 HISTÓRICOS":
    st.title("📊 Relatórios")
    aba_hist = st.radio("Selecione o Relatório:", ["Vendas (Clientes)", "Movim. Estoque"], horizontal=True, label_visibility="collapsed")
    st.divider()
    
    if aba_hist == "Vendas (Clientes)":
        st.dataframe(carregar_historico_cli(), use_container_width=True)
    elif aba_hist == "Movim. Estoque":
        st.dataframe(carregar_historico_est(), use_container_width=True)
