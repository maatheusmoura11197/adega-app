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
# ⚙️ CONFIGURAÇÃO E ESTILO
# ==========================================
st.set_page_config(page_title="Adega do Barão v13", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    .big-btn {
        background-color: #25D366; color: white; padding: 18px; border-radius: 12px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block; border: none;
    }
    .stProgress > div > div > div > div { background-color: #ff4b4b; }
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

# --- FUNÇÕES DE APOIO ---
def limpar_valor(valor):
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        if v.count(".") > 0: v = v.replace(".", "")
        v = v.replace(",", ".")
    try: return float(v)
    except: return 0.0

def para_texto_br(valor):
    return f"{valor:.2f}".replace(".", ",")

def gerar_mensagem_humana(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize() # Pega só o primeiro nome
    
    if pontos == 1:
        msg = f"Olá, {nome}! Tudo bem? ✨\n\nPassando para agradecer a preferência e te dar as boas-vindas ao nosso Clube de Fidelidade! 🍷\n\nVocê acabou de ganhar seu *1º ponto*. A cada 10 compras, você ganha um super desconto de 50%! É um prazer ter você com a gente."
        btn = "Dar Boas-Vindas 🎉"
    elif pontos < 9:
        msg = f"Oi, {nome}! Ficamos felizes em te ver de novo! 😊\n\nSua compra foi registrada com sucesso. Agora você já tem *{pontos} pontos* no nosso cartão fidelidade.\n\nFaltam só {10-pontos} para o seu prêmio! Até a próxima! 🍻"
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    elif pontos == 9:
        msg = f"Segura o coração, {nome}! 😂\n\nVocê acaba de completar seu *9º ponto*! Isso significa que a sua PRÓXIMA compra vale o seu prêmio de 50% de desconto! 😱\n\nJá vai pensando no que vai pedir! Te esperamos!"
        btn = "🚨 AVISAR: FALTA SÓ 1!"
    else: 
        msg = f"ESTAMOS EM FESTA! ✨ Parabéns, {nome}!\n\nVocê completou seus *10 pontos* e acaba de ganhar seu PRÊMIO: **50% de DESCONTO** na sua compra agora! 🏆\n\nVocê merece! Obrigado por ser um cliente tão especial para a Adega do Barão!"
        btn = "🏆 ENVIAR PRÊMIO AGORA!"
    return msg, btn

# ==========================================
# 📦 MÓDULO ESTOQUE (COM CÁLCULO DE FARDOS)
# ==========================================
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False

menu = st.sidebar.radio("Navegar:", ["💰 Caixa & Fidelidade", "📦 Estoque (Ver/Editar)"])

if menu == "📦 Estoque (Ver/Editar)":
    st.title("📦 Controle de Estoque")
    dados_est = sheet_estoque.get_all_records()
    df_est = pd.DataFrame(dados_est)

    if not df_est.empty:
        # Preparação dos dados para exibição humana
        df_visual = df_est.copy()
        
        def calcular_fardos_vivos(row):
            total_un = int(limpar_valor(row['Estoque']))
            ref_fardo = int(limpar_valor(row.get('Qtd_Fardo', 12)))
            fardos = total_un // ref_fardo
            sobra = total_un % ref_fardo
            if fardos > 0:
                return f"{fardos} fardos e {sobra} un" if sobra > 0 else f"{fardos} fardos"
            return f"{sobra} un"

        df_visual['Estoque Físico'] = df_visual.apply(calcular_fardos_vivos, axis=1)
        
        st.subheader("📋 Estoque Atual")
        st.dataframe(df_visual[['Nome', 'Estoque Físico', 'Venda', 'Estoque']], use_container_width=True)

        st.divider()
        st.subheader("✏️ Atualizar Estoque")
        item_edit = st.selectbox("Escolha o Produto para editar:", ["Selecione..."] + df_est['Nome'].tolist())
        
        if item_edit != "Selecione...":
            idx = df_est[df_est['Nome'] == item_edit].index[0]
            row = df_est.iloc[idx]
            
            with st.form("edit_estoque"):
                st.write(f"Editando: **{item_edit}**")
                c1, c2 = st.columns(2)
                nova_venda = c1.text_input("Preço de Venda (R$):", value=str(row['Venda']))
                fardo_ref = c2.number_input("Itens por Fardo (Ref):", value=int(limpar_valor(row.get('Qtd_Fardo', 12))))
                
                st.write("---")
                st.write("Ajustar Quantidade Total:")
                q1, q2 = st.columns(2)
                novo_fardo = q1.number_input("Qtd Fardos Inteiros:", value=0)
                novo_un = q2.number_input("Qtd Unidades Soltas:", value=0)
                
                if st.form_submit_button("💾 SALVAR ALTERAÇÕES"):
                    total_final = (novo_fardo * fardo_ref) + novo_un
                    # Atualiza Planilha
                    sheet_estoque.update_cell(idx+2, 5, nova_venda.replace(".", ","))
                    sheet_estoque.update_cell(idx+2, 6, int(total_final))
                    sheet_estoque.update_cell(idx+2, 8, int(fardo_ref))
                    st.success("Estoque Atualizado!")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# 💰 CAIXA & FIDELIDADE
# ==========================================
elif menu == "💰 Caixa & Fidelidade":
    st.title("💰 Venda e Fidelidade")
    
    if st.session_state.venda_sucesso:
        st.success("✅ Venda e Pontos registrados!")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("🔄 Próxima Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())

        # --- CLIENTE ---
        sel_cli = st.selectbox("Cliente:", ["🆕 NOVO CLIENTE"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        c1, c2 = st.columns(2)
        if sel_cli == "🆕 NOVO CLIENTE":
            nome_c = c1.text_input("Nome do Cliente:").upper()
            tel_c = c2.text_input("WhatsApp (com DDD):")
        else:
            nome_c = sel_cli.split(" - ")[0]
            tel_c = sel_cli.split(" - ")[1]

        st.divider()
        
        # --- PRODUTO ---
        if not df_est.empty:
            prod_sel = st.selectbox("O que ele comprou?", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0, step=1)
            v_u = q2.number_input("Unidades:", min_value=0, step=1)

            if st.button("🚀 FINALIZAR VENDA", type="primary"):
                tel_limpo = re.sub(r'\D', '', tel_c)
                
                # 1. Baixa de Estoque
                if prod_sel != "(Apenas Ponto)":
                    idx_p = df_est[df_est['Nome'] == prod_sel].index[0]
                    row_p = df_est.iloc[idx_p]
                    ref_f = int(limpar_valor(row_p.get('Qtd_Fardo', 12)))
                    qtd_venda = (v_f * ref_f) + v_u
                    novo_est = int(limpar_valor(row_p['Estoque'])) - qtd_venda
                    sheet_estoque.update_cell(idx_p+2, 6, int(novo_est))

                # 2. Atualiza Fidelidade
                df_cli['t_limpo'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                match = df_cli[df_cli['t_limpo'] == tel_limpo]
                
                if not match.empty:
                    idx_c = match.index[0]
                    novos_pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(idx_c+2, 3, novos_pts)
                else:
                    novos_pts = 1
                    sheet_clientes.append_row([nome_c, tel_limpo, 1, date.today().strftime('%d/%m/%Y')])

                # 3. Prepara Zap
                msg, b_txt = gerar_mensagem_humana(nome_c, novos_pts)
                st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{tel_limpo}&text={urllib.parse.quote(msg)}"
                st.session_state.txt_btn = b_txt
                st.session_state.venda_sucesso = True
                st.rerun()
