import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import re
from datetime import datetime, date
import time

# ==========================================
# ⚙️ CONFIGURAÇÃO E ESTILO (CORES VIVAS)
# ==========================================
st.set_page_config(page_title="Adega do Barão v19", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    /* Estilo para botões de ABAS (Simulados) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
        color: #31333F;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0047AB !important; /* Azul destaque na aba ativa */
        color: white !important;
    }
    /* Botões de Ação */
    div.stButton > button {
        background-color: #008CBA; /* Azul */
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        height: 3em;
        border: none;
    }
    /* Botão Vermelho (Excluir) */
    div.stButton > button[kind="primary"] {
        background-color: #FF0000 !important; /* Vermelhão */
        color: white !important;
    }
    /* WhatsApp */
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block;
    }
    </style>
    """, unsafe_allow_html=True)

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
    st.error("Erro na conexão com as planilhas.")
    st.stop()

# --- FUNÇÕES ---
def limpar_n(valor):
    if not valor or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if v.count(".") > 0: v = v.replace(".", "")
        v = v.replace(",", ".")
    try: return float(v)
    except: return 0.0

def gerar_mensagem_amigavel(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    if pontos == 1:
        msg = f"Oi, {nome}! ✨\nAgradecemos pela compra na Adega do Barão! Já abri seu Cartão Fidelidade. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. 🍷"
        btn = "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10:
        faltam = 10 - pontos
        msg = f"E aí, {nome}! 👊\nSua compra foi registrada! Agora você tem *{pontos} pontos*. ✨\nFaltam só {faltam} para o prêmio! Valeu pela parceria! 🍻"
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    else: 
        msg = f"PARABÉNS, {nome}!!! ✨🏆\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** em qualquer produto hoje! Aproveite! 🥳🍷"
        btn = "🏆 ENVIAR PRÊMIO DE 20%!"
    return msg, btn

# ==========================================
# 📱 MENU PRINCIPAL
# ==========================================
with st.sidebar:
    st.title("🍷 Adega do Barão")
    menu = st.radio("Escolha a Aba:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])

# ==========================================
# 📦 GESTÃO DE ESTOQUE (EDIÇÃO INTELIGENTE)
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    tab1, tab2, tab3 = st.tabs(["📋 Ver Estoque", "🆕 Cadastrar Novo", "✏️ Editar/Adicionar"])

    if not df_est.empty:
        with tab1:
            def formatar_fardo_lata(row):
                total = int(limpar_n(row['Estoque']))
                ref = int(limpar_n(row.get('Qtd_Fardo', 12)))
                f, u = divmod(total, ref)
                if f > 0 and u > 0: return f"📦 {f} fardos e {u} un"
                return f"📦 {f} fardos" if f > 0 else f"🍺 {u} un"
            df_est['Físico'] = df_est.apply(formatar_fardo_lata, axis=1)
            st.dataframe(df_est[['Nome', 'Físico', 'Venda', 'Estoque']], use_container_width=True)

    with tab2:
        st.subheader("Novo Produto")
        with st.form("novo_prod"):
            n_nome = st.text_input("Nome:").upper()
            c1, c2 = st.columns(2)
            n_custo = c1.text_input("Custo (Un):", value="0,00")
            n_venda = c2.text_input("Venda (Un):", value="0,00")
            n_ref = st.number_input("Itens p/ fardo:", value=12)
            n_forn = st.text_input("Fornecedor:")
            if st.form_submit_button("✅ SALVAR NOVO"):
                sheet_estoque.append_row([n_nome, "Geral", n_forn, n_custo, n_venda, 0, date.today().strftime('%d/%m/%Y'), n_ref])
                st.success("Criado!"); time.sleep(1); st.rerun()

    with tab3:
        if not df_est.empty:
            sel_e = st.selectbox("Escolha o item para EDITAR ou ADICIONAR:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                est_atual = int(row['Estoque'])
                
                with st.form("edit_est_inteligente"):
                    st.info(f"Produto: {sel_e} | Estoque Atual: {est_atual} un")
                    v_v = st.text_input("Preço de Venda (Un):", value=str(row['Venda']))
                    v_c = st.text_input("Preço de Custo (Un):", value=str(row['Custo']))
                    
                    st.write("---")
                    st.write("➕ **ADICIONAR** ao estoque (O que você digitar aqui será somado ao atual):")
                    c_f, c_u = st.columns(2)
                    add_f = c_f.number_input("Adicionar Fardos:", min_value=0, step=1, value=0)
                    add_u = c_u.number_input("Adicionar Unidades Soltas:", min_value=0, step=1, value=0)
                    
                    col1, col2 = st.columns(2)
                    if col1.form_submit_button("💾 SALVAR MUDANÇAS"):
                        ref = int(limpar_n(row.get('Qtd_Fardo', 12)))
                        # LÓGICA DE SOMA: Atual + (Novo Fardo * Ref) + Unidades
                        total_adicional = (add_f * ref) + add_u
                        total_final = est_atual + total_adicional
                        
                        sheet_estoque.update_cell(idx+2, 4, v_c.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 5, v_v.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 6, int(total_final))
                        
                        # Se adicionou algo, registra no histórico
                        if total_adicional > 0:
                            sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "EDIÇÃO/SOMA", total_adicional, "Ajuste Manual"])
                        
                        st.success(f"Estoque atualizado! Total agora: {total_final} un")
                        time.sleep(1); st.rerun()
                    
                    if col2.form_submit_button("🗑️ APAGAR PRODUTO", type="primary"):
                        sheet_estoque.delete_rows(idx+2)
                        st.warning("Removido!"); time.sleep(1); st.rerun()

# ==========================================
# 📊 HISTÓRICOS (CORES DE DESTAQUE)
# ==========================================
elif menu == "📊 Históricos":
    st.title("📊 Relatórios de Movimentação")
    t1, t2 = st.tabs(["✅ Vendas Clientes", "📥 Entradas Estoque"])
    with t1: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
    with t2: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_c.empty:
        df_c['disp'] = df_c['nome'] + " - " + df_c['telefone'].astype(str)
        sel = st.selectbox("Escolha o cliente:", ["Selecione..."] + df_c['disp'].tolist())
        if sel != "Selecione...":
            idx_c = df_c[df_c['disp'] == sel].index[0]
            row_c = df_c.iloc[idx_c]
            with st.form("ed_cli"):
                n_n = st.text_input("Nome:", value=row_c['nome'])
                n_t = st.text_input("Tel:", value=str(row_c['telefone']))
                n_p = st.number_input("Pontos:", value=int(row_c['compras']))
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 SALVAR"):
                    sheet_clientes.update_cell(idx_c+2, 1, n_n); sheet_clientes.update_cell(idx_c+2, 2, n_t); sheet_clientes.update_cell(idx_c+2, 3, n_p)
                    st.success("Salvo!"); time.sleep(1); st.rerun()
                if b2.form_submit_button("🗑️ EXCLUIR", type="primary"):
                    sheet_clientes.delete_rows(idx_c+2)
                    st.rerun()

# ==========================================
# 💰 CAIXA
# ==========================================
elif menu == "💰 Caixa":
    if 'v_suc' not in st.session_state: st.session_state.v_suc = False
    if st.session_state.v_suc:
        st.success("Venda salva!")
        st.markdown(f'<a href="{st.session_state.l_z}" target="_blank" class="big-btn">{st.session_state.t_b}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.v_suc = False; st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        sel_cli = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c1, c2 = st.columns(2)
        if sel_cli == "🆕 NOVO":
            nome_c = c1.text_input("Nome:").upper(); tel_c = c2.text_input("WhatsApp:")
        else:
            nome_c = sel_cli.split(" - ")[0]; tel_c = sel_cli.split(" - ")[1]
        
        st.divider()
        if not df_est.empty:
            p_sel = st.selectbox("O que ele levou?", ["(Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)
            if st.button("✅ FINALIZAR VENDA"):
                tel_l = re.sub(r'\D', '', tel_c)
                if p_sel != "(Ponto)":
                    idx_p = df_est[df_est['Nome'] == p_sel].index[0]
                    ref = int(limpar_n(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    sheet_estoque.update_cell(idx_p+2, 6, int(row['Estoque']) - baixa)
                
                df_cli['tl'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                match = df_cli[df_cli['tl'] == tel_l]
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1; sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1; sheet_clientes.append_row([nome_c, tel_l, 1, date.today().strftime('%d/%m/%Y')])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), nome_c, tel_l, pts])
                msg, btn = gerar_mensagem_amigavel(nome_c, pts)
                st.session_state.l_z = f"https://api.whatsapp.com/send?phone=55{tel_l}&text={urllib.parse.quote(msg)}"
                st.session_state.t_b = btn; st.session_state.v_suc = True; st.rerun()
