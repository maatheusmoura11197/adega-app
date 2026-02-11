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
st.set_page_config(page_title="Adega do Barão v20", page_icon="🍷", layout="wide")

st.markdown("""
    <style>
    /* Estilo para abas com cores fortes */
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
    /* Botões Padrão (Azul) */
    div.stButton > button {
        background-color: #008CBA;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        height: 3em;
        border: none;
        width: 100%;
    }
    /* Botão Excluir (Vermelho) */
    div.stButton > button[kind="primary"] {
        background-color: #FF0000 !important;
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
    st.error("Erro Conexão Google Sheets.")
    st.stop()

# --- 🧮 FUNÇÕES DE CORREÇÃO (ANTI-MILHÕES) ---
def tratar_valor_universal(valor):
    """
    Lê o que você digitou (com ponto ou virgula) e transforma em número 
    para o Python fazer conta.
    Ex: '4,50' vira 4.5 | '4.50' vira 4.5
    """
    if not valor or str(valor).strip() == "": return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    
    # Se tem virgula, assume que é decimal brasileiro
    if "," in v:
        v = v.replace(".", "") # Tira ponto de milhar se houver
        v = v.replace(",", ".") # Troca virgula por ponto
    
    try: return float(v)
    except: return 0.0

def para_planilha(valor):
    """
    Transforma o número em TEXTO com vírgula para enviar ao Google Sheets.
    Isso impede que o Google entenda errado e crie milhões.
    """
    return f"{valor:.2f}".replace(".", ",")

def limpar_tel(t): return re.sub(r'\D', '', str(t))

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
        btn = "🏆 ENVIAR PRÉMIO DE 20%!"
    return msg, btn

# ==========================================
# 📱 MENU
# ==========================================
with st.sidebar:
    st.title("🍷 Adega do Barão")
    menu = st.radio("Menu:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])

# ==========================================
# 📦 MÓDULO ESTOQUE (CORRIGIDO)
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    df_est = pd.DataFrame(sheet_estoque.get_all_records())
    
    tab1, tab2, tab3 = st.tabs(["📋 Ver Estoque", "🆕 Novo Produto", "✏️ Editar/Excluir"])

    # --- TAB 1: VISUALIZAÇÃO ---
    if not df_est.empty:
        with tab1:
            def formatar_estoque(row):
                # Usa .get para evitar o KeyError se a coluna não existir
                total = int(tratar_valor_universal(row['Estoque']))
                ref = int(tratar_valor_universal(row.get('Qtd_Fardo', 12)))
                if ref == 0: ref = 12
                f, u = divmod(total, ref)
                
                texto = ""
                if f > 0: texto += f"📦 {f} fardos "
                if u > 0: texto += f"🍺 {u} un"
                return texto if texto else "Zerado"

            df_est['Físico'] = df_est.apply(formatar_estoque, axis=1)
            st.dataframe(df_est[['Nome', 'Físico', 'Venda', 'Estoque', 'Fornecedor', 'Data Compra']], use_container_width=True)

    # --- TAB 2: CADASTRO NOVO ---
    with tab2:
        st.subheader("Cadastrar Novo Item")
        with st.form("novo_prod"):
            n_nome = st.text_input("Nome do Produto (Ex: Skol Lata):").upper()
            
            c1, c2 = st.columns(2)
            # Placeholder indica o formato, mas a função limpa qualquer coisa
            n_custo = c1.text_input("Preço Custo (un):", placeholder="Ex: 2,92")
            n_venda = c2.text_input("Preço Venda (un):", placeholder="Ex: 4,50")
            
            c3, c4 = st.columns(2)
            n_forn = c3.text_input("Fornecedor:", placeholder="Ex: Ambev")
            n_data = c4.date_input("Data da Compra", date.today())
            
            c5, c6 = st.columns(2)
            n_ref = c5.number_input("Quantas vêm no fardo?", value=12)
            n_fardos_ini = c6.number_input("Estoque Inicial (Fardos):", value=0)
            
            if st.form_submit_button("✅ CADASTRAR PRODUTO"):
                # Conversão segura
                custo_float = tratar_valor_universal(n_custo)
                venda_float = tratar_valor_universal(n_venda)
                total_estoque = n_fardos_ini * n_ref
                
                # Envia para planilha formatado com vírgula (string)
                sheet_estoque.append_row([
                    n_nome, 
                    "Geral", 
                    n_forn, 
                    para_planilha(custo_float), 
                    para_planilha(venda_float), 
                    total_estoque, 
                    n_data.strftime('%d/%m/%Y'), 
                    n_ref
                ])
                st.success("Produto cadastrado com sucesso!")
                time.sleep(1)
                st.rerun()

    # --- TAB 3: EDIÇÃO ---
    with tab3:
        if not df_est.empty:
            sel_e = st.selectbox("Selecione o produto para editar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel_e != "Selecione...":
                idx = df_est[df_est['Nome'] == sel_e].index[0]
                row = df_est.iloc[idx]
                
                with st.form("edit_est_form"):
                    st.info(f"Editando: {sel_e}")
                    
                    col_a, col_b = st.columns(2)
                    # Carrega valores atuais
                    v_venda = col_a.text_input("Preço Venda:", value=str(row['Venda']))
                    v_custo = col_b.text_input("Preço Custo:", value=str(row['Custo']))
                    
                    col_c, col_d = st.columns(2)
                    v_forn = col_c.text_input("Fornecedor:", value=str(row.get('Fornecedor', '')))
                    # Tenta ler a data, se falhar usa hoje
                    try: data_atual = datetime.strptime(row.get('Data Compra', ''), '%d/%m/%Y').date()
                    except: data_atual = date.today()
                    v_data = col_d.date_input("Data Compra:", value=data_atual)

                    st.write("---")
                    st.write("📦 **Adicionar Estoque (Soma ao atual):**")
                    f1, f2 = st.columns(2)
                    add_f = f1.number_input("Add Fardos:", min_value=0, step=1, value=0)
                    add_u = f2.number_input("Add Unidades:", min_value=0, step=1, value=0)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    
                    if btn_col1.form_submit_button("💾 SALVAR MUDANÇAS"):
                        # Cálculos
                        ref = int(tratar_valor_universal(row.get('Qtd_Fardo', 12)))
                        if ref == 0: ref = 12
                        
                        estoque_atual = int(tratar_valor_universal(row['Estoque']))
                        adicional = (add_f * ref) + add_u
                        novo_total = estoque_atual + adicional
                        
                        # Atualiza Colunas (Cuidado com índices: A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8)
                        # Nome(1), Tipo(2), Forn(3), Custo(4), Venda(5), Est(6), Data(7), QtdF(8)
                        
                        sheet_estoque.update_cell(idx+2, 3, v_forn)
                        sheet_estoque.update_cell(idx+2, 4, para_planilha(tratar_valor_universal(v_custo)))
                        sheet_estoque.update_cell(idx+2, 5, para_planilha(tratar_valor_universal(v_venda)))
                        sheet_estoque.update_cell(idx+2, 6, novo_total)
                        sheet_estoque.update_cell(idx+2, 7, v_data.strftime('%d/%m/%Y'))
                        
                        if adicional > 0:
                            sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel_e, "ENTRADA", adicional, f"Forn: {v_forn}"])
                            
                        st.success("Atualizado!")
                        time.sleep(1)
                        st.rerun()
                    
                    # CORREÇÃO DO ERRO DE EXCLUSÃO
                    if btn_col2.form_submit_button("🗑️ EXCLUIR PRODUTO", type="primary"):
                        sheet_estoque.delete_rows(int(idx + 2)) # Converte idx para int explicitamente
                        st.warning("Produto Excluído!")
                        time.sleep(1)
                        st.rerun()

# ==========================================
# 💰 CAIXA (FUNCIONAL)
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
                # Baixa Estoque
                if p_sel != "(Apenas Ponto)":
                    idx = df_est[df_est['Nome'] == p_sel].index[0]
                    # Correção KeyError: usa .get
                    ref = int(tratar_valor_universal(df_est.iloc[idx].get('Qtd_Fardo', 12)))
                    baixa = (v_f * ref) + v_u
                    atual = int(tratar_valor_universal(df_est.iloc[idx]['Estoque']))
                    sheet_estoque.update_cell(idx+2, 6, atual - baixa)
                    
                    # Histórico Venda
                    vlr_venda = tratar_valor_universal(df_est.iloc[idx]['Venda'])
                    total_rs = baixa * vlr_venda
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), p_sel, "VENDA", baixa, para_planilha(total_rs)])

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
