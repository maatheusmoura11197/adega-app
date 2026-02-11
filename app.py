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
st.set_page_config(page_title="Adega do Barão v16", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block; border: none;
    }
    .stButton>button { width: 100%; }
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
except:
    st.error("Erro na conexão com as planilhas.")
    st.stop()

# --- FUNÇÕES DE LIMPEZA ---
def limpar_para_numero(valor):
    if not valor or str(valor).strip() == "": return 0.0
    # Remove R$, espaços e converte vírgula em ponto
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
    menu = st.radio("Navegar:", ["💰 Caixa & Fidelidade", "📦 Estoque & Lucros", "👥 Clientes", "📊 Histórico"])

# ==========================================
# 📦 MÓDULO ESTOQUE E LUCROS
# ==========================================
if menu == "📦 Estoque & Lucros":
    st.title("📦 Gestão de Estoque e Rentabilidade")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    
    tab1, tab2 = st.tabs(["📊 Visão Geral e Lucros", "✏️ Editar / Apagar Item"])

    if not df_est.empty:
        # Converter colunas para números para evitar erros
        df_est['venda_n'] = df_est['Venda'].apply(limpar_para_numero)
        df_est['custo_n'] = df_est['Custo'].apply(limpar_para_numero)
        df_est['estoque_n'] = df_est['Estoque'].apply(limpar_para_numero).astype(int)
        
        # Cálculos de Lucro
        df_est['Lucro Un.'] = df_est['venda_n'] - df_est['custo_n']
        df_est['Lucro Total Est.'] = df_est['Lucro Un.'] * df_est['estoque_n']

        with tab1:
            st.subheader("Cálculo de Lucro Baseado no Estoque Atual")
            lucro_total_adega = df_est['Lucro Total Est.'].sum()
            st.metric("Lucro Potencial Total (Estoque)", f"R$ {lucro_total_adega:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            # Formatação para exibição
            df_view = df_est[['Nome', 'estoque_n', 'venda_n', 'custo_n', 'Lucro Un.', 'Lucro Total Est.']].copy()
            df_view.columns = ['Produto', 'Qtd Unidades', 'Venda (R$)', 'Custo (R$)', 'Lucro p/ Un.', 'Lucro no Estoque']
            st.dataframe(df_view, use_container_width=True)

        with tab2:
            st.subheader("Alterar ou Remover Produto")
            item_sel = st.selectbox("Selecione o produto:", ["Selecione..."] + df_est['Nome'].tolist())
            
            if item_sel != "Selecione...":
                idx = df_est[df_est['Nome'] == item_sel].index[0]
                row = df_est.iloc[idx]
                
                with st.form("form_edit"):
                    c1, c2 = st.columns(2)
                    nova_venda = c1.text_input("Preço de Venda (R$):", value=str(row['Venda']))
                    novo_custo = c2.text_input("Preço de Custo (R$):", value=str(row['Custo']))
                    
                    st.write("---")
                    c3, c4, c5 = st.columns(3)
                    ref_f = c3.number_input("Itens por Fardo (Ref):", value=int(limpar_para_numero(row.get('Qtd_Fardo', 12))))
                    n_f = c4.number_input("Qtd Fardos Inteiros:", value=0)
                    n_u = c5.number_input("Qtd Latas Soltas:", value=0)
                    
                    st.divider()
                    col_btn_salvar, col_btn_del = st.columns(2)
                    
                    if col_btn_salvar.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary"):
                        total_n = (n_f * ref_f) + n_u
                        sheet_estoque.update_cell(idx+2, 4, novo_custo.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 5, nova_venda.replace(".", ","))
                        sheet_estoque.update_cell(idx+2, 6, int(total_n))
                        sheet_estoque.update_cell(idx+2, 8, int(ref_f))
                        st.success("Dados atualizados!")
                        time.sleep(1)
                        st.rerun()
                        
                    if col_btn_del.form_submit_button("🗑️ EXCLUIR PRODUTO"):
                        # Deleta a linha na planilha (idx+2 porque começa em 1 e tem cabeçalho)
                        sheet_estoque.delete_rows(int(idx + 2))
                        st.warning(f"O produto {item_sel} foi removido.")
                        time.sleep(1)
                        st.rerun()

# ==========================================
# 💰 CAIXA & FIDELIDADE
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
    if 'v_sucesso' not in st.session_state: st.session_state.v_sucesso = False
    
    if st.session_state.v_sucesso:
        st.success("✅ Venda Concluída!")
        st.markdown(f'<a href="{st.session_state.l_zap}" target="_blank" class="big-btn">{st.session_state.t_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.v_sucesso = False; st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())
        
        sel_c = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO":
            nome_c = c1.text_input("Nome:").upper(); tel_c = c2.text_input("WhatsApp:")
        else:
            nome_c = sel_c.split(" - ")[0]; tel_c = sel_c.split(" - ")[1]
        
        st.divider()
        if not df_est.empty:
            p_sel = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)

            if st.button("✅ FINALIZAR VENDA", type="primary"):
                tel_l = re.sub(r'\D', '', tel_c)
                if p_sel != "(Apenas Ponto)":
                    idx_p = df_est[df_est['Nome'] == p_sel].index[0]
                    ref_f = int(limpar_para_numero(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    total_v = (v_f * ref_f) + v_u
                    novo_e = int(limpar_para_numero(df_est.iloc[idx_p]['Estoque'])) - total_v
                    sheet_estoque.update_cell(idx_p+2, 6, int(novo_e))
                
                # Fidelidade
                df_cli['tl'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                match = df_cli[df_cli['tl'] == tel_l]
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([nome_c, tel_l, 1, date.today().strftime('%d/%m/%Y')])
                
                msg, btn = gerar_mensagem_amigavel(nome_c, pts)
                st.session_state.l_zap = f"https://api.whatsapp.com/send?phone=55{tel_l}&text={urllib.parse.quote(msg)}"
                st.session_state.t_btn = btn
                st.session_state.v_sucesso = True
                st.rerun()

# --- Funções básicas para manter o sistema rodando ---
elif menu == "👥 Clientes":
    st.title("👥 Clientes")
    st.dataframe(pd.DataFrame(sheet_clientes.get_all_records()), use_container_width=True)

elif menu == "📊 Histórico":
    st.title("📊 Histórico de Estoque")
    st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
