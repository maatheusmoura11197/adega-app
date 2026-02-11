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
st.set_page_config(page_title="Adega do Barão - Sistema Oficial", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    /* Estilo das Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0047AB; /* Azul Royal */
        color: white !important;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #002D6E !important; /* Azul Escuro */
    }
    /* Botões */
    div.stButton > button {
        background-color: #008CBA; color: white; font-weight: bold;
        border-radius: 10px; height: 3em; width: 100%; border: none;
    }
    div.stButton > button[kind="primary"] { background-color: #FF0000 !important; }
    
    /* WhatsApp */
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block;
    }
    /* Alerta de Estoque */
    .estoque-info {
        padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3;
        border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN (LINK DA ANIMAÇÃO CORRIGIDO)
# ==========================================
SENHA_DO_SISTEMA = "adega123"

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>🔒 Adega do Barão</h1>", unsafe_allow_html=True)
    
    c_a, c_b, c_c = st.columns([1, 2, 1])
    with c_b:
        with st.form("login_form"):
            senha = st.text_input("Senha de Acesso:", type="password", placeholder="Digite e aperte Enter ↵")
            submit = st.form_submit_button("ACESSAR SISTEMA")
            
            if submit:
                if senha == SENHA_DO_SISTEMA:
                    st.success("Senha Correta! Carregando...")
                    # Link novo e estável (Canecas Brindando)
                    st.image("https://media1.tenor.com/m/5-2_9lK2mY8AAAAC/cheers-beer.gif", use_container_width=True)
                    time.sleep(2.5) 
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("🚫 Senha incorreta!")
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
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    sheet_hist_cli = planilha.worksheet("Historico")
except:
    st.error("Erro crítico de conexão. Verifique sua internet.")
    st.stop()

# --- 🧮 FUNÇÕES ---
def converter_input_para_numero(valor):
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

def salvar_com_ponto(valor):
    return "{:.2f}".format(valor)

def para_real_visual(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

def gerar_mensagem_amigavel(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    if pontos == 1:
        msg = f"Oi, {nome}! ✨\nObrigado por comprar na Adega do Barão! Já abri seu Cartão Fidelidade. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. 🍷"
        btn = "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10:
        faltam = 10 - pontos
        msg = f"E aí, {nome}! 👊\nCompra registrada! Agora você tem *{pontos} pontos*. ✨\nFaltam só {faltam} para o prêmio! Tamo junto! 🍻"
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    else: 
        msg = f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** hoje! Aproveite! 🥳🍷"
        btn = "🏆 ENVIAR PRÊMIO AGORA!"
    return msg, btn

def calcular_estoque_fisico(total, ref_fardo):
    if ref_fardo == 0: ref_fardo = 12
    f, u = divmod(total, ref_fardo)
    txt = ""
    if f > 0: txt += f"📦 {f} fardos "
    if u > 0: txt += f"🍺 {u} un"
    return txt if txt else "Zerado"

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu Principal")
    menu = st.radio("Navegar:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])
    st.divider()
    if st.button("SAIR (Logout)"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 MÓDULO ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    
    t1, t2, t3 = st.tabs(["📋 Lista Detalhada", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"])

    # --- TAB 1: VISUALIZAÇÃO ---
    if not df_est.empty:
        with t1:
            # === AUTO-REPARO ===
            if 'ML' not in df_est.columns:
                if st.button("🔧 Reparar Coluna ML"):
                    try: sheet_estoque.update_cell(1, 9, "ML"); st.rerun()
                    except: pass

            df_est['custo_n'] = df_est['Custo'].apply(converter_input_para_numero)
            df_est['venda_n'] = df_est['Venda'].apply(converter_input_para_numero)
            df_est['Lucro Un.'] = df_est['venda_n'] - df_est['custo_n']
            
            df_est['Custo (R$)'] = df_est['custo_n'].apply(para_real_visual)
            df_est['Venda (R$)'] = df_est['venda_n'].apply(para_real_visual)
            df_est['Lucro (R$)'] = df_est['Lucro Un.'].apply(para_real_visual)
            df_est['Físico'] = df_est.apply(lambda row: calcular_estoque_fisico(int(converter_input_para_numero(row['Estoque'])), int(converter_input_para_numero(row.get('Qtd_Fardo', 12)))), axis=1)
            
            if 'ML' not in df_est.columns: df_est['ML'] = "-"
            
            st.dataframe(
                df_est[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']], 
                use_container_width=True
            )

    # --- TAB 2: CADASTRO NOVO (SEM FORMULÁRIO PARA REAGIR AO VIVO) ---
    with t2:
        st.subheader("Cadastrar Produto")
        
        n_nome = st.text_input("Nome do Produto (Obrigatório):").upper()
        
        col_t1, col_t2 = st.columns(2)
        n_tipo = col_t1.selectbox("Tipo:", ["LATA", "LONG NECK", "GARRAFA 600ML", "LITRÃO", "OUTROS"])
        
        # LOGICA ML AO VIVO
        lista_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
        sel_ml = col_t2.selectbox("Volume (ML):", lista_ml)
        
        if sel_ml == "Outros":
            n_ml = col_t2.text_input("Digite o volume (ex: 750ml):", key="novo_ml_custom")
        else:
            n_ml = sel_ml

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
        
        qtd_inicial = 0
        if tipo_compra == "Fardo Fechado":
            q_f = col_b.number_input("Qtd Fardos:", min_value=0)
            qtd_inicial = q_f * n_ref
        else:
            q_u = col_b.number_input("Qtd Unidades:", min_value=0)
            qtd_inicial = q_u
        
        if st.button("✅ CADASTRAR PRODUTO", type="primary"):
            erro = False
            if not n_nome: st.error("⚠️ Nome Obrigatório"); erro = True
            if not n_custo: st.error("⚠️ Custo Obrigatório"); erro = True
            if not n_venda: st.error("⚠️ Venda Obrigatória"); erro = True
            if not n_forn: st.error("⚠️ Fornecedor Obrigatório"); erro = True
            if sel_ml == "Outros" and not n_ml: st.error("⚠️ Digite o ML personalizado"); erro = True
            
            if not erro:
                sheet_estoque.append_row([
                    n_nome, n_tipo, n_forn, 
                    salvar_com_ponto(converter_input_para_numero(n_custo)), 
                    salvar_com_ponto(converter_input_para_numero(n_venda)), 
                    qtd_inicial, n_data.strftime('%d/%m/%Y'), n_ref, n_ml
                ])
                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "NOVO", qtd_inicial, n_forn])
                st.success("Cadastrado com Sucesso!"); time.sleep(1); st.rerun()

    # --- TAB 3: EDIÇÃO (SEM FORMULÁRIO PARA REAGIR AO VIVO) ---
    with t3:
        if not df_est.empty:
            sel_e = st.selectbox("Editar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                
                st.info(f"Editando: {sel_e}")
                
                c_tipo, c_ml = st.columns(2)
                
                list_tipos = ["LATA", "LONG NECK", "GARRAFA 600ML", "LITRÃO", "OUTROS"]
                t_atual = row.get('Tipo', 'LATA')
                idx_t = list_tipos.index(t_atual) if t_atual in list_tipos else 0
                novo_tipo = c_tipo.selectbox("Tipo:", list_tipos, index=idx_t)
                
                # LOGICA ML INTELIGENTE
                list_ml = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
                ml_banco = str(row.get('ML', '350ml'))
                
                idx_ml_ini = 5 # Padrão
                if ml_banco in list_ml:
                    idx_ml_ini = list_ml.index(ml_banco)
                else:
                    idx_ml_ini = list_ml.index("Outros")

                sel_ml_edit = c_ml.selectbox("Volume (ML):", list_ml, index=idx_ml_ini, key="ml_edit_select")
                
                final_ml = sel_ml_edit
                if sel_ml_edit == "Outros":
                    val_padrao = ml_banco if ml_banco not in list_ml else ""
                    final_ml = c_ml.text_input("Digite o volume personalizado:", value=val_padrao, key="ml_edit_custom")

                c_a, c_b = st.columns(2)
                v_venda = c_a.text_input("Venda (R$):", value=str(row['Venda']))
                v_custo = c_b.text_input("Custo (R$):", value=str(row['Custo']))
                v_forn = st.text_input("Fornecedor:", value=str(row.get('Fornecedor', '')))
                
                st.write("---")
                st.write("➕ **Adicionar Estoque:**")
                f1, f2 = st.columns(2)
                add_f = f1.number_input("Add Fardos:", min_value=0)
                add_u = f2.number_input("Add Unidades:", min_value=0)
                
                b_sal, b_exc = st.columns(2)
                if b_sal.button("💾 SALVAR ALTERAÇÕES"):
                    ref = int(converter_input_para_numero(row.get('Qtd_Fardo', 12)))
                    est_atual = int(converter_input_para_numero(row['Estoque']))
                    novo_tot = est_atual + (add_f * ref) + add_u
                    
                    sheet_estoque.update_cell(idx+2, 2, novo_tipo)
                    sheet_estoque.update_cell(idx+2, 3, v_forn)
                    sheet_estoque.update_cell(idx+2, 4, salvar_com_ponto(converter_input_para_numero(v_custo)))
                    sheet_estoque.update_cell(idx+2, 5, salvar_com_ponto(converter_input_para_numero(v_venda)))
                    sheet_estoque.update_cell(idx+2, 6, novo_tot)
                    sheet_estoque.update_cell(idx+2, 7, date.today().strftime('%d/%m/%Y'))
                    try: sheet_estoque.update_cell(idx+2, 9, final_ml)
                    except: pass
                    
                    if (add_f * ref) + add_u > 0:
                        sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "ENTRADA", (add_f * ref) + add_u, f"Forn: {v_forn}"])
                    st.success("Atualizado!"); time.sleep(1); st.rerun()
                
                if b_exc.button("🗑️ EXCLUIR PRODUTO"):
                    sheet_estoque.delete_rows(int(idx + 2)); st.warning("Excluído!"); time.sleep(1); st.rerun()

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
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_c = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO":
            n_c = c1.text_input("Nome:").upper(); t_c = c2.text_input("Tel:")
        else:
            n_c = sel_c.split(" - ")[0]; t_c = sel_c.split(" - ")[1]
        
        st.divider()
        if not df_est.empty:
            p_sel = st.selectbox("Produto:", ["(Selecione...)"] + df_est['Nome'].tolist())
            
            if p_sel != "(Selecione...)":
                idx_p = df_est[df_est['Nome'] == p_sel].index[0]
                row_p = df_est.iloc[idx_p]
                estoque_txt = calcular_estoque_fisico(
                    int(converter_input_para_numero(row_p['Estoque'])), 
                    int(converter_input_para_numero(row_p.get('Qtd_Fardo', 12)))
                )
                st.markdown(f"""
                <div class="estoque-info">
                    📊 EM ESTOQUE: {estoque_txt}
                </div>
                """, unsafe_allow_html=True)

            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)
            
            if st.button("✅ FINALIZAR VENDA"):
                tl = limpar_tel(t_c)
                if p_sel != "(Selecione...)":
                    ref = int(converter_input_para_numero(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    atual = int(converter_input_para_numero(df_est.iloc[idx_p]['Estoque']))
                    
                    if atual >= baixa:
                        sheet_estoque.update_cell(idx_p+2, 6, atual - baixa)
                        vlr = converter_input_para_numero(df_est.iloc[idx_p]['Venda'])
                        sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), p_sel, "VENDA", baixa, salvar_com_ponto(baixa * vlr)])
                    else:
                        st.error(f"Estoque insuficiente! Você só tem {atual} unidades."); st.stop()

                df_cli['tl'] = df_cli['telefone'].astype(str).apply(limpar_tel)
                match = df_cli[df_cli['tl'] == tl]
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1; sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1; sheet_clientes.append_row([n_c, tl, 1, date.today().strftime('%d/%m/%Y')])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_c, tl, pts])
                msg, btn = gerar_mensagem_amigavel(n_c, pts)
                st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{tl}&text={urllib.parse.quote(msg)}"
                st.session_state.b_txt = btn; st.session_state.v_suc = True; st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
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
                    st.success("Salvo!"); time.sleep(1); st.rerun()
                if b2.form_submit_button("🗑️ Excluir", type="primary"):
                    sheet_clientes.delete_rows(int(idx+2)); st.rerun()

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 Históricos":
    st.title("📊 Relatórios")
    t1, t2 = st.tabs(["Vendas (Clientes)", "Movim. Estoque"])
    with t1: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
    with t2: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
