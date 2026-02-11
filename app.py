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
st.set_page_config(page_title="Adega do Barão v21", page_icon="🍷", layout="wide")

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

# --- 🧮 FUNÇÕES DE CORREÇÃO (FORÇAR PONTO) ---
def converter_input_para_numero(valor):
    """
    Lê o que você digitou (3,99 ou 3.99) e transforma em número real.
    """
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        v = v.replace(".", "") # Tira milhar
        v = v.replace(",", ".") # Vira ponto decimal
    try: return float(v)
    except: return 0.0

def salvar_com_ponto(valor):
    """
    O SEGREDO: Pega o número e transforma em texto COM PONTO.
    Ex: 3.99 vira "3.99" (String) para a planilha aceitar.
    """
    return "{:.2f}".format(valor)

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

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Adega do Barão")
    menu = st.radio("Menu:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])

# ==========================================
# 📦 MÓDULO ESTOQUE (COM PONTO E UNIDADE)
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    
    t1, t2, t3 = st.tabs(["📋 Lista Estoque", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"])

    # --- TAB 1: VISUALIZAÇÃO ---
    if not df_est.empty:
        with t1:
            def formatar_estoque(row):
                total = int(converter_input_para_numero(row['Estoque']))
                ref = int(converter_input_para_numero(row.get('Qtd_Fardo', 12)))
                if ref == 0: ref = 12
                f, u = divmod(total, ref)
                
                txt = ""
                if f > 0: txt += f"📦 {f} fardos "
                if u > 0: txt += f"🍺 {u} un"
                return txt if txt else "Zerado"

            df_est['Físico'] = df_est.apply(formatar_estoque, axis=1)
            st.dataframe(df_est[['Nome', 'Físico', 'Venda', 'Estoque', 'Fornecedor', 'Data Compra']], use_container_width=True)

    # --- TAB 2: CADASTRO NOVO (COM UNIDADE) ---
    with t2:
        st.subheader("Cadastrar Produto")
        with st.form("novo_prod"):
            n_nome = st.text_input("Nome do Produto:").upper()
            
            c1, c2 = st.columns(2)
            n_custo = c1.text_input("Custo Unitário (R$):", placeholder="3.06")
            n_venda = c2.text_input("Venda Unitária (R$):", placeholder="4.99")
            
            c3, c4 = st.columns(2)
            n_forn = c3.text_input("Fornecedor:")
            n_data = c4.date_input("Data da Compra", date.today())
            
            st.divider()
            st.write("📦 **Como você comprou?**")
            tipo_compra = st.radio("Selecione:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
            
            col_a, col_b = st.columns(2)
            # Referência do fardo é sempre necessária para o cálculo visual, mesmo comprando unidade
            n_ref = col_a.number_input("Quantas vêm no Fardo Padrão?", value=12, help="Usado para calcular quantos fardos você tem")
            
            qtd_inicial = 0
            if tipo_compra == "Fardo Fechado":
                qtd_fardos = col_b.number_input("Quantos FARDOS comprou?", min_value=0)
                qtd_inicial = qtd_fardos * n_ref
            else:
                qtd_unidades = col_b.number_input("Quantas UNIDADES comprou?", min_value=0)
                qtd_inicial = qtd_unidades
            
            if st.form_submit_button("✅ CADASTRAR PRODUTO"):
                # Converte para float primeiro
                custo_float = converter_input_para_numero(n_custo)
                venda_float = converter_input_para_numero(n_venda)
                
                # Salva na planilha COM PONTO (String)
                sheet_estoque.append_row([
                    n_nome, 
                    "Geral", 
                    n_forn, 
                    salvar_com_ponto(custo_float), 
                    salvar_com_ponto(venda_float), 
                    qtd_inicial, 
                    n_data.strftime('%d/%m/%Y'), 
                    n_ref
                ])
                
                # Histórico
                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), n_nome, "NOVO CADASTRO", qtd_inicial, n_forn])
                
                st.success(f"Produto cadastrado! Total: {qtd_inicial} unidades.")
                time.sleep(1)
                st.rerun()

    # --- TAB 3: EDIÇÃO ---
    with t3:
        if not df_est.empty:
            sel_e = st.selectbox("Selecione para editar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                
                with st.form("edit_est_form"):
                    st.info(f"Editando: {sel_e}")
                    
                    c_a, c_b = st.columns(2)
                    v_venda = c_a.text_input("Preço Venda:", value=str(row['Venda']))
                    v_custo = c_b.text_input("Preço Custo:", value=str(row['Custo']))
                    
                    c_c, c_d = st.columns(2)
                    v_forn = c_c.text_input("Fornecedor:", value=str(row.get('Fornecedor', '')))
                    # Tenta ler a data
                    try: d_atual = datetime.strptime(row.get('Data Compra', ''), '%d/%m/%Y').date()
                    except: d_atual = date.today()
                    v_data = c_d.date_input("Data Compra:", value=d_atual)

                    st.write("---")
                    st.write("➕ **Adicionar Estoque (Soma ao atual):**")
                    f1, f2 = st.columns(2)
                    add_f = f1.number_input("Add Fardos:", min_value=0, step=1, value=0)
                    add_u = f2.number_input("Add Unidades:", min_value=0, step=1, value=0)
                    
                    b_salvar, b_excluir = st.columns(2)
                    
                    if b_salvar.form_submit_button("💾 SALVAR MUDANÇAS"):
                        # Cálculos
                        ref = int(converter_input_para_numero(row.get('Qtd_Fardo', 12)))
                        est_atual = int(converter_input_para_numero(row['Estoque']))
                        
                        adicional = (add_f * ref) + add_u
                        total_final = est_atual + adicional
                        
                        # Salva COM PONTO
                        custo_str = salvar_com_ponto(converter_input_para_numero(v_custo))
                        venda_str = salvar_com_ponto(converter_input_para_numero(v_venda))
                        
                        sheet_estoque.update_cell(idx+2, 3, v_forn)
                        sheet_estoque.update_cell(idx+2, 4, custo_str)
                        sheet_estoque.update_cell(idx+2, 5, venda_str)
                        sheet_estoque.update_cell(idx+2, 6, total_final)
                        sheet_estoque.update_cell(idx+2, 7, v_data.strftime('%d/%m/%Y'))
                        
                        if adicional > 0:
                            sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "ENTRADA", adicional, f"Forn: {v_forn}"])
                            
                        st.success(f"Atualizado! Novo Total: {total_final}")
                        time.sleep(1); st.rerun()
                    
                    if b_excluir.form_submit_button("🗑️ EXCLUIR PRODUTO", type="primary"):
                        sheet_estoque.delete_rows(int(idx + 2)) 
                        st.warning("Produto Excluído!")
                        time.sleep(1); st.rerun()

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
            p_sel = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_est['Nome'].tolist())
            q1, q2 = st.columns(2)
            v_f = q1.number_input("Fardos:", min_value=0); v_u = q2.number_input("Unidades:", min_value=0)
            
            if st.button("✅ FINALIZAR"):
                tl = limpar_tel(t_c)
                if p_sel != "(Apenas Ponto)":
                    idx = df_est[df_est['Nome'] == p_sel].index[0]
                    # Usa .get para evitar KeyError se a coluna Qtd_Fardo sumir
                    ref = int(converter_input_para_numero(df_est.iloc[idx].get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    atual = int(converter_input_para_numero(df_est.iloc[idx]['Estoque']))
                    sheet_estoque.update_cell(idx+2, 6, atual - baixa)
                    
                    # Log da Venda
                    vlr = converter_input_para_numero(df_est.iloc[idx]['Venda'])
                    tot_rs = baixa * vlr
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), p_sel, "VENDA", baixa, salvar_com_ponto(tot_rs)])

                # Fidelidade
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
                    sheet_clientes.delete_rows(int(idx+2))
                    st.rerun()

# ==========================================
# 📊 HISTÓRICOS
# ==========================================
elif menu == "📊 Históricos":
    st.title("📊 Relatórios")
    t1, t2 = st.tabs(["Vendas (Clientes)", "Movim. Estoque"])
    with t1: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
    with t2: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
