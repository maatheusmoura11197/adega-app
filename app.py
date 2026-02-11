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
st.set_page_config(page_title="Adega do Barão v15", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block; border: none;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
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

# --- FUNÇÕES DE APOIO ---
def limpar_valor(valor):
    if not valor or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if v.count(".") > 0: v = v.replace(".", "")
        v = v.replace(",", ".")
    try: return float(v)
    except: return 0.0

def para_texto_br(valor):
    return f"{valor:.2f}".replace(".", ",")

def gerar_mensagem_amigavel(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    if pontos == 1:
        msg = f"Oi, {nome}! Tudo bem? 😊\n\nPassando para agradecer pela compra hoje na Adega do Barão! ✨\n\nJá abri seu *Cartão Fidelidade* aqui. A cada 10 compras você ganha um prêmio! Você garantiu o seu 1º ponto. É um prazer ter você aqui! 🍷"
        btn = "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10:
        faltam = 10 - pontos
        alerta = "Falta só UM para o prêmio! 😱" if faltam == 1 else f"Faltam só {faltam} para o seu prêmio!"
        msg = f"E aí, {nome}! Como estão as coisas? 👊\n\nSua compra foi registrada! Agora você tem *{pontos} pontos*. ✨\n\n{alerta} Valeu demais pela parceria! 🍻"
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    else: 
        msg = f"OLHA SÓ! Parabéns, {nome}!!! ✨🏆\n\nVocê completou seus *10 pontos*! \n\nVocê ganhou um **DESCONTO DE 20%** em qualquer produto hoje! Aproveite, você merece! 🥳🍷"
        btn = "🏆 ENVIAR PRÊMIO DE 20%!"
    return msg, btn

# ==========================================
# 📱 MENU LATERAL (RESTAURADO)
# ==========================================
with st.sidebar:
    st.title("🍷 Adega do Barão")
    menu = st.radio("Escolha a função:", 
                    ["💰 Caixa & Fidelidade", 
                     "📦 Estoque (Ver/Editar)", 
                     "👥 Gerenciar Clientes", 
                     "📊 Relatórios de Vendas"])
    st.divider()
    if st.button("Sair"): st.stop()

# ==========================================
# 📦 MÓDULO ESTOQUE (COMPLETO)
# ==========================================
if menu == "📦 Estoque (Ver/Editar)":
    st.title("📦 Controle de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    tab1, tab2 = st.tabs(["📋 Estoque Atual (Fardos)", "✏️ Ajustar Preço e Qtd"])

    if not df_est.empty:
        with tab1:
            def formatar_estoque_humano(row):
                total_un = int(limpar_valor(row['Estoque']))
                ref_fardo = int(limpar_valor(row.get('Qtd_Fardo', 12)))
                fardos = total_un // ref_fardo
                sobra = total_un % ref_fardo
                if fardos > 0 and sobra > 0: return f"📦 {fardos} fardos e {sobra} un"
                elif fardos > 0: return f"📦 {fardos} fardos"
                else: return f"🍺 {sobra} un"

            df_est['Situação Real'] = df_est.apply(formatar_estoque_humano, axis=1)
            st.dataframe(df_est[['Nome', 'Situação Real', 'Venda', 'Estoque']], use_container_width=True)

        with tab2:
            item_edit = st.selectbox("Selecione o produto para alterar:", ["Selecione..."] + df_est['Nome'].tolist())
            if item_edit != "Selecione...":
                idx = df_est[df_est['Nome'] == item_edit].index[0]
                row = df_est.iloc[idx]
                with st.form("form_edit_completo"):
                    col1, col2 = st.columns(2)
                    venda_atual = col1.text_input("Novo Preço de Venda (R$):", value=str(row['Venda']))
                    custo_atual = col2.text_input("Novo Preço de Custo (R$):", value=str(row['Custo']))
                    
                    st.divider()
                    st.write("Atualizar Quantidade Físicas:")
                    c3, c4, c5 = st.columns(3)
                    ref_f = c3.number_input("Itens por Fardo:", value=int(limpar_valor(row.get('Qtd_Fardo', 12))))
                    n_f = c4.number_input("Qtd Fardos Inteiros:", value=0)
                    n_u = c5.number_input("Qtd Latas Soltas:", value=0)
                    
                    if st.form_submit_button("💾 Salvar Todas as Alterações"):
                        total_novo = (n_f * ref_f) + n_u
                        sheet_estoque.update_cell(idx+2, 4, custo_atual.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 5, venda_atual.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 6, int(total_novo))
                        sheet_estoque.update_cell(idx+2, 8, int(ref_f))
                        st.success("Produto atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()

# ==========================================
# 💰 CAIXA & FIDELIDADE (RESTAURADO)
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
    if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False
    
    if st.session_state.venda_sucesso:
        st.success("✅ Venda Registrada!")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.venda_sucesso = False; st.rerun()
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
            prod_sel = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)

            if st.button("✅ FINALIZAR VENDA", type="primary"):
                tel_l = re.sub(r'\D', '', tel_c)
                if prod_sel != "(Apenas Ponto)":
                    idx_p = df_est[df_est['Nome'] == prod_sel].index[0]
                    ref_f = int(limpar_valor(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    total_v = (v_f * ref_f) + v_u
                    novo_e = int(limpar_valor(df_est.iloc[idx_p]['Estoque'])) - total_v
                    sheet_estoque.update_cell(idx_p+2, 6, int(novo_e))
                
                df_cli['t_l'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                match = df_cli[df_cli['t_l'] == tel_l]
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([nome_c, tel_l, 1, date.today().strftime('%d/%m/%Y')])
                
                msg, btn = gerar_mensagem_amigavel(nome_c, pts)
                st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{tel_l}&text={urllib.parse.quote(msg)}"
                st.session_state.txt_btn = btn
                st.session_state.venda_sucesso = True
                st.rerun()

# ==========================================
# 👥 GERENCIAR CLIENTES (RESTAURADO)
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Gestão de Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_c.empty:
        df_c['Display'] = df_c['nome'] + " - " + df_c['telefone'].astype(str)
        sel = st.selectbox("Selecione o Cliente:", df_c['Display'].tolist())
        idx = df_c[df_c['Display'] == sel].index[0]
        with st.form("edit_cli"):
            n_n = st.text_input("Nome:", value=df_c.iloc[idx]['nome'])
            n_t = st.text_input("Telefone:", value=str(df_c.iloc[idx]['telefone']))
            n_p = st.number_input("Pontos:", value=int(df_c.iloc[idx]['compras']))
            if st.form_submit_button("Salvar Alterações"):
                sheet_clientes.update_cell(idx+2, 1, n_n)
                sheet_clientes.update_cell(idx+2, 2, n_t)
                sheet_clientes.update_cell(idx+2, 3, n_p)
                st.success("Salvo!"); st.rerun()

# ==========================================
# 📊 RELATÓRIOS (RESTAURADO)
# ==========================================
elif menu == "📊 Relatórios de Vendas":
    st.title("📊 Relatórios")
    tab_est, tab_fid = st.tabs(["Histórico de Estoque", "Histórico de Clientes"])
    with tab_est:
        try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
        except: st.write("Aba Histórico_Estoque não encontrada ou vazia.")
    with tab_fid:
        try: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
        except: st.write("Aba Historico não encontrada ou vazia.")
