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
st.set_page_config(page_title="Adega do Barão v17", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block; border: none;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; }
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
    sheet_hist_est = planilha.worksheet("Historico_Estoque") # Para compras/entradas
    sheet_hist_cli = planilha.worksheet("Historico")         # Para vendas/pontos
except:
    st.error("Erro na conexão. Verifique suas planilhas.")
    st.stop()

# --- FUNÇÕES AUXILIARES ---
def limpar_n(valor):
    if not valor or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if v.count(".") > 0: v = v.replace(".", "")
        v = v.replace(",", ".")
    try: return float(v)
    except: return 0.0

def para_texto_br(valor): return f"{valor:.2f}".replace(".", ",")

def gerar_mensagem_amigavel(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    if pontos == 1:
        msg = f"Oi, {nome}! 😊\n\nAgradecemos pela compra na Adega do Barão! ✨\n\nJá abri seu *Cartão Fidelidade*. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. 🍷"
        btn = "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10:
        faltam = 10 - pontos
        msg = f"E aí, {nome}! 👊\n\nSua compra foi registrada! Agora você tem *{pontos} pontos*. ✨\n\nFaltam só {faltam} para o prêmio! Valeu pela parceria! 🍻"
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    else: 
        msg = f"PARABÉNS, {nome}!!! ✨🏆\n\nVocê completou 10 pontos e ganhou um **DESCONTO DE 20%** em qualquer produto hoje! Você merece! 🥳🍷"
        btn = "🏆 ENVIAR PRÊMIO DE 20%!"
    return msg, btn

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Adega do Barão")
    menu = st.radio("Navegar:", ["💰 Caixa & Fidelidade", "📦 Gestão de Estoque", "👥 Clientes", "📊 Históricos Separados"])

# ==========================================
# 📦 MÓDULO ESTOQUE (CADASTRO + VISUALIZAÇÃO)
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    tab1, tab2, tab3 = st.tabs(["📋 Estoque Atual", "🆕 Adicionar Novo Item", "✏️ Editar/Excluir"])

    if not df_est.empty:
        with tab1:
            def formatar_fardo_lata(row):
                total = int(limpar_n(row['Estoque']))
                ref = int(limpar_n(row.get('Qtd_Fardo', 12)))
                f, u = divmod(total, ref)
                if f > 0 and u > 0: return f"📦 {f} fardos e {u} un"
                return f"📦 {f} fardos" if f > 0 else f"🍺 {u} un"

            df_est['Físico'] = df_est.apply(formatar_fardo_lata, axis=1)
            df_est['Lucro Un.'] = df_est['Venda'].apply(limpar_n) - df_est['Custo'].apply(limpar_n)
            st.dataframe(df_est[['Nome', 'Físico', 'Venda', 'Lucro Un.', 'Estoque']], use_container_width=True)

    with tab2:
        st.subheader("Cadastrar Novo Produto no Estoque")
        with st.form("novo_prod"):
            n_nome = st.text_input("Nome do Produto (Ex: Skol Lata):").upper()
            c1, c2 = st.columns(2)
            n_custo = c1.text_input("Preço de Custo (Unidade):", value="0,00")
            n_venda = c2.text_input("Preço de Venda (Unidade):", value="0,00")
            c3, c4 = st.columns(2)
            n_ref = c3.number_input("Itens por Fardo:", value=12)
            n_fardos = c4.number_input("Qtd de Fardos Iniciais:", value=0)
            c5, c6 = st.columns(2)
            n_forn = c5.text_input("Fornecedor:")
            n_data = c6.date_input("Data da Compra", date.today())
            
            if st.form_submit_button("✅ CADASTRAR PRODUTO"):
                total_i = n_fardos * n_ref
                sheet_estoque.append_row([n_nome, "Geral", n_forn, n_custo, n_venda, total_i, n_data.strftime('%d/%m/%Y'), n_ref])
                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "ENTRADA/NOVO", total_i, n_forn])
                st.success("Produto adicionado!"); time.sleep(1); st.rerun()

    with tab3:
        if not df_est.empty:
            sel_e = st.selectbox("Escolha para alterar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                with st.form("edit_est"):
                    v_v = st.text_input("Preço Venda:", value=str(row['Venda']))
                    v_c = st.text_input("Preço Custo:", value=str(row['Custo']))
                    v_f = st.number_input("Ajustar p/ Fardos:", value=0)
                    v_u = st.number_input("Ajustar p/ Unidades:", value=0)
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Salvar Alterações"):
                        total = (v_f * int(limpar_n(row.get('Qtd_Fardo', 12)))) + v_u
                        sheet_estoque.update_cell(idx+2, 4, v_c)
                        sheet_estoque.update_cell(idx+2, 5, v_v)
                        sheet_estoque.update_cell(idx+2, 6, int(total))
                        st.success("Salvo!"); time.sleep(1); st.rerun()
                    if b2.form_submit_button("🗑️ APAGAR PRODUTO"):
                        sheet_estoque.delete_rows(int(idx+2))
                        st.warning("Excluído!"); time.sleep(1); st.rerun()

# ==========================================
# 👥 CLIENTES (EDITAR E EXCLUIR)
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_c.empty:
        sel_c = st.selectbox("Selecione um cliente para editar:", ["Selecione..."] + (df_c['nome'] + " - " + df_c['telefone'].astype(str)).tolist())
        if sel_c != "Selecione...":
            idx_c = df_c.index[0] # Simplificado para o exemplo, buscaria pelo tel
            # Busca correta por telefone (único)
            tel_busca = sel_c.split(" - ")[1]
            idx_c = df_c[df_c['telefone'].astype(str) == tel_busca].index[0]
            row_c = df_c.iloc[idx_c]
            
            with st.form("edit_cliente"):
                ed_nome = st.text_input("Nome:", value=row_c['nome'])
                ed_tel = st.text_input("Telefone:", value=str(row_c['telefone']))
                ed_pts = st.number_input("Pontos Acumulados:", value=int(row_c['compras']))
                c_s, c_e = st.columns(2)
                if c_s.form_submit_button("💾 Salvar Cliente"):
                    sheet_clientes.update_cell(idx_c+2, 1, ed_nome)
                    sheet_clientes.update_cell(idx_c+2, 2, ed_tel)
                    sheet_clientes.update_cell(idx_c+2, 3, ed_pts)
                    st.success("Cliente atualizado!"); time.sleep(1); st.rerun()
                if c_e.form_submit_button("🗑️ EXCLUIR CLIENTE"):
                    sheet_clientes.delete_rows(int(idx_c+2))
                    st.warning("Cliente removido!"); time.sleep(1); st.rerun()
        st.divider()
        st.write("Lista Geral:")
        st.dataframe(df_c[['nome', 'telefone', 'compras']], use_container_width=True)

# ==========================================
# 📊 HISTÓRICOS SEPARADOS
# ==========================================
elif menu == "📊 Históricos Separados":
    st.title("📊 Relatórios de Movimentação")
    t1, t2 = st.tabs(["👤 Histórico de Clientes (Vendas)", "📦 Histórico de Estoque (Entradas)"])
    with t1:
        st.subheader("Registro de Pontos e Compras de Clientes")
        try: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
        except: st.write("Aba 'Historico' não encontrada.")
    with t2:
        st.subheader("Registro de Entradas e Fornecedores")
        try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
        except: st.write("Aba 'Historico_Estoque' não encontrada.")

# ==========================================
# 💰 CAIXA & FIDELIDADE (VENDA)
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
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
            p_sel = st.selectbox("O que ele levou?", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)
            if st.button("✅ FINALIZAR VENDA", type="primary"):
                tel_l = re.sub(r'\D', '', tel_c)
                if p_sel != "(Apenas Ponto)":
                    idx_p = df_est[df_est['Nome'] == p_sel].index[0]
                    total_v = (v_f * int(limpar_n(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))) + v_u
                    novo_e = int(limpar_n(df_est.iloc[idx_p]['Estoque'])) - total_v
                    sheet_estoque.update_cell(idx_p+2, 6, int(novo_e))
                
                df_cli['tl'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                match = df_cli[df_cli['tl'] == tel_l]
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([nome_c, tel_l, 1, date.today().strftime('%d/%m/%Y')])
                
                # Registra no Histórico de Clientes
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), nome_c, tel_l, pts])
                
                msg, btn = gerar_mensagem_amigavel(nome_c, pts)
                st.session_state.l_z = f"https://api.whatsapp.com/send?phone=55{tel_l}&text={urllib.parse.quote(msg)}"
                st.session_state.t_b = btn
                st.session_state.v_suc = True
                st.rerun()
