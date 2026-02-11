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
st.set_page_config(page_title="Adega do Barão v14", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    .big-btn {
        background-color: #25D366; color: white; padding: 20px; border-radius: 15px; 
        text-align: center; font-weight: bold; font-size: 22px; margin-top: 10px;
        text-decoration: none; display: block; border: none;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }
    .big-btn:hover { background-color: #128C7E; color: white; }
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
except:
    st.error("Erro na conexão. Verifique a internet ou as credenciais.")
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

def gerar_mensagem_amigavel(nome_cliente, pontos):
    nome = nome_cliente.split()[0].capitalize()
    
    if pontos == 1:
        msg = (f"Oi, {nome}! Tudo bem? 😊\n\n"
               f"Passando para agradecer pela compra hoje na Adega do Barão! ✨\n\n"
               f"Já aproveitei e abri seu *Cartão Fidelidade* aqui no sistema. "
               f"Funciona assim: a cada 10 compras você ganha um prêmio especial! "
               f"Você já garantiu o seu 1º ponto. É um prazer ter você como cliente! 🍷")
        btn = "Enviar Boas-Vindas 🎉"
    elif 1 < pontos < 10:
        faltam = 10 - pontos
        # Mensagem especial se faltar só 1
        alerta = "Falta só UM para o seu prêmio! 😱" if faltam == 1 else f"Faltam só {faltam} para o seu prêmio!"
        
        msg = (f"E aí, {nome}! Como estão as coisas? 👊\n\n"
               f"Sua compra foi registrada! Agora você já acumulou *{pontos} pontos* no nosso cartão fidelidade. ✨\n\n"
               f"{alerta} Valeu demais pela parceria de sempre! 🍻")
        btn = f"Enviar Saldo ({pontos}/10) 📲"
    else: 
        msg = (f"OLHA SÓ! Parabéns, {nome}!!! ✨🏆\n\n"
               f"Você acaba de completar seus *10 pontos* no nosso Cartão Fidelidade! \n\n"
               f"Como prometido, você ganhou um **DESCONTO DE 20%** em qualquer produto da Adega! com validade de 7 dias. Aproveite seu prêmio, você merece! 🥳🍷")
        btn = "🏆 ENVIAR PRÊMIO DE 20%!"
    return msg, btn

# ==========================================
# 📱 MENU LATERAL
# ==========================================
menu = st.sidebar.radio("O que vamos fazer?", ["💰 Registrar Venda", "📦 Estoque (Fardos + Latas)"])

# ==========================================
# 📦 MÓDULO ESTOQUE (VISUALIZAÇÃO CORRIGIDA)
# ==========================================
if menu == "📦 Estoque (Fardos + Latas)":
    st.title("📦 Nosso Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())

    if not df_est.empty:
        # Criando a visualização de Fardos + Latas
        def formatar_estoque_humano(row):
            total_un = int(limpar_valor(row['Estoque']))
            ref_fardo = int(limpar_valor(row.get('Qtd_Fardo', 12)))
            fardos = total_un // ref_fardo
            sobra = total_un % ref_fardo
            
            if fardos > 0 and sobra > 0:
                return f"📦 {fardos} fardos e 🍺 {sobra} un"
            elif fardos > 0:
                return f"📦 {fardos} fardos"
            else:
                return f"🍺 {sobra} un"

        df_est['Situação Física'] = df_est.apply(formatar_estoque_humano, axis=1)
        
        # Exibição organizada
        st.dataframe(df_est[['Nome', 'Situação Física', 'Venda', 'Estoque']], 
                     column_config={
                         "Nome": "Produto",
                         "Situação Física": "O que tem na prateleira",
                         "Venda": "Preço (un)",
                         "Estoque": "Total de Unidades"
                     }, use_container_width=True)

        st.divider()
        st.subheader("✏️ Atualizar ou Corrigir")
        with st.expander("Clique aqui para ajustar quantidades"):
            item_edit = st.selectbox("Escolha o Produto:", ["Selecione..."] + df_est['Nome'].tolist())
            if item_edit != "Selecione...":
                idx = df_est[df_est['Nome'] == item_edit].index[0]
                row_e = df_est.iloc[idx]
                
                with st.form("form_ajuste"):
                    fardo_ref = st.number_input("O fardo desse produto vem com quantas?", value=int(limpar_valor(row_e.get('Qtd_Fardo', 12))))
                    st.write("---")
                    st.write("Conte o estoque e coloque aqui:")
                    c1, c2 = st.columns(2)
                    n_f = c1.number_input("Quantos fardos fechados?", min_value=0, step=1)
                    n_u = c2.number_input("Quantas latas soltas?", min_value=0, step=1)
                    
                    if st.form_submit_button("✅ Atualizar Estoque"):
                        total_novo = (n_f * fardo_ref) + n_u
                        sheet_estoque.update_cell(idx+2, 6, int(total_novo))
                        sheet_estoque.update_cell(idx+2, 8, int(fardo_ref))
                        st.success("Estoque ajustado com sucesso!")
                        time.sleep(1)
                        st.rerun()

# ==========================================
# 💰 REGISTRAR VENDA
# ==========================================
elif menu == "💰 Registrar Venda":
    st.title("💰 Nova Venda")
    
    if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False

    if st.session_state.venda_sucesso:
        st.balloons()
        st.success("Tudo certo! Venda e pontos registrados.")
        st.markdown(f'<a href="{st.session_state.link_zap}" target="_blank" class="big-btn">{st.session_state.txt_btn}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"):
            st.session_state.venda_sucesso = False
            st.rerun()
    else:
        df_cli = pd.DataFrame(sheet_clientes.get_all_records())
        df_est = pd.DataFrame(sheet_estoque.get_all_records())

        # CLIENTE
        sel_cli = st.selectbox("Quem é o cliente?", ["🆕 É UM NOVO CLIENTE"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist())
        col_n, col_t = st.columns(2)
        if sel_cli == "🆕 É UM NOVO CLIENTE":
            nome_c = col_n.text_input("Nome:").strip().upper()
            tel_c = col_t.text_input("WhatsApp (com DDD):")
        else:
            nome_c = sel_cli.split(" - ")[0]
            tel_c = sel_cli.split(" - ")[1]

        st.divider()
        
        # PRODUTO
        if not df_est.empty:
            prod_sel = st.selectbox("O que ele levou?", ["(Apenas Ponto / Sem estoque)"] + df_est['Nome'].tolist())
            st.write("Quantidade da venda:")
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos fechados:", min_value=0, step=1)
            v_u = q2.number_input("Latas/Unidades soltas:", min_value=0, step=1)

            if st.button("✅ FINALIZAR AGORA", type="primary"):
                if not nome_c or not tel_c:
                    st.error("Por favor, preencha o nome e o telefone do cliente.")
                else:
                    tel_limpo = re.sub(r'\D', '', tel_c)
                    
                    # 1. Baixa no estoque
                    if prod_sel != "(Apenas Ponto / Sem estoque)":
                        idx_p = df_est[df_est['Nome'] == prod_sel].index[0]
                        row_p = df_est.iloc[idx_p]
                        ref_f = int(limpar_valor(row_p.get('Qtd_Fardo', 12)))
                        total_vendido = (v_f * ref_f) + v_u
                        est_atual = int(limpar_valor(row_p['Estoque']))
                        sheet_estoque.update_cell(idx_p+2, 6, int(est_atual - total_vendido))

                    # 2. Fidelidade
                    df_cli['t_limpo'] = df_cli['telefone'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
                    match = df_cli[df_cli['t_limpo'] == tel_limpo]
                    
                    if not match.empty:
                        idx_c = match.index[0]
                        novos_pts = int(match.iloc[0]['compras']) + 1
                        # Se chegar em 11, reseta para 1 (novo cartão) ou mantém 10 para o prêmio
                        sheet_clientes.update_cell(idx_c+2, 3, novos_pts)
                    else:
                        novos_pts = 1
                        sheet_clientes.append_row([nome_c, tel_limpo, 1, date.today().strftime('%d/%m/%Y')])

                    # 3. Gerar Mensagem e Zap
                    msg, b_txt = gerar_mensagem_amigavel(nome_c, novos_pts)
                    st.session_state.link_zap = f"https://api.whatsapp.com/send?phone=55{tel_limpo}&text={urllib.parse.quote(msg)}"
                    st.session_state.txt_btn = b_txt
                    st.session_state.venda_sucesso = True
                    st.rerun()
