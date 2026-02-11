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
# ⚙️ CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(
    page_title="Super Adega 12.0",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VISUAL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;} 
            footer {visibility: hidden;} 
            .stSelectbox div[data-baseweb="select"] > div:first-child {
                border-color: #ff4b4b;
            }
            .big-btn {
                background-color: #25D366; 
                color: white; 
                padding: 15px; 
                border-radius: 10px; 
                text-align: center; 
                font-weight: bold; 
                font-size: 20px; 
                margin-top: 10px;
                text-decoration: none;
                display: block;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN
# ==========================================
SENHA_DO_SISTEMA = "adega123" 
TEMPO_LIMITE_MINUTOS = 60

if 'logado' not in st.session_state: st.session_state.logado = False
if 'validando' not in st.session_state: st.session_state.validando = False
if 'ultima_atividade' not in st.session_state: st.session_state.ultima_atividade = time.time()
if 'venda_sucesso' not in st.session_state: st.session_state.venda_sucesso = False
if 'link_zap_atual' not in st.session_state: st.session_state.link_zap_atual = ""
if 'msg_zap_btn' not in st.session_state: st.session_state.msg_zap_btn = ""

def verificar_sessao():
    if st.session_state.logado:
        agora = time.time()
        tempo_passado = agora - st.session_state.ultima_atividade
        if tempo_passado > (TEMPO_LIMITE_MINUTOS * 60):
            st.session_state.logado = False
            return False
        st.session_state.ultima_atividade = agora
        return True
    return False

if not st.session_state.logado:
    if st.session_state.validando:
        st.write("Entrando...")
        time.sleep(1)
        st.session_state.logado = True
        st.session_state.validando = False
        st.rerun()
    else:
        st.title("🔒 Acesso Restrito")
        with st.form("login_form"):
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("ENTRAR", type="primary"):
                if senha == SENHA_DO_SISTEMA:
                    st.session_state.validando = True
                    st.rerun()
                else: st.error("Senha errada")
        st.stop()

if not verificar_sessao(): st.stop()

# ==========================================
# 📡 CONEXÃO GOOGLE SHEETS
# ==========================================
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/191D0UIDvwDJPWRtp_0cBFS9rWaq6CkSj5ET_1HO2sLI/edit?usp=sharing"

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Fidelidade")
    sheet_clientes = planilha.worksheet("Página1") 
    sheet_hist_cli = planilha.worksheet("Historico")
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
except Exception as e:
    st.error(f"Erro Conexão: {e}")
    st.stop()

# --- FUNÇÕES AUXILIARES ---
def limpar_telefone(tel): return re.sub(r'\D', '', str(tel))
def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

def ler_numero_input(valor):
    if not valor or str(valor).strip() == "": return 0.0
    val_str = str(valor).replace("R$", "").strip()
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try: return float(val_str)
    except: return 0.0

def float_para_sheets(valor):
    return f"{valor:.2f}".replace(".", ",")

def formatar_moeda_visual(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_mensagem_zap(nome_cliente, total_compras):
    if total_compras == 1:
        msg = f"Olá {nome_cliente}! Bem-vindo à Adega! 🍷\nStatus: 1 ponto."
        btn = "Enviar Boas-Vindas 🎉"
    elif total_compras < 9:
        msg = f"Olá {nome_cliente}! Mais uma compra!\nStatus: {total_compras}/10 pontos."
        btn = f"Enviar Saldo ({total_compras}/10) 📲"
    elif total_compras == 9:
        msg = f"UAU {nome_cliente}! Falta 1 para o prémio! 😱"
        btn = "🚨 AVISAR URGENTE (FALTA 1)"
    else: 
        msg = f"PARABÉNS {nome_cliente}! Ganhou 50% OFF! 🏆"
        btn = "🏆 ENVIAR PRÉMIO AGORA"
    return msg, btn

# ==========================================
# 📱 MENU LATERAL
# ==========================================
with st.sidebar:
    st.title("🍷 Menu")
    st.link_button("📂 Abrir Planilha", URL_PLANILHA)
    st.divider()
    menu = st.radio("Navegar:", ["💰 Fidelidade & Caixa", "📦 Gestão de Estoque", "👥 Gerenciar Clientes", "📊 Relatórios"])
    st.markdown("---")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 GESTÃO DE ESTOQUE
# ==========================================
if menu == "📦 Gestão de Estoque":
    st.title("📦 Controle de Estoque")
    aba_cad, aba_edit, aba_ver = st.tabs(["📝 Entrada (Compra)", "✏️ Editar/Excluir Item", "📋 Ver Estoque"])
    
    try:
        dados_raw = sheet_estoque.get_all_records()
        df_estoque = pd.DataFrame(dados_raw)
    except: df_estoque = pd.DataFrame()

    with aba_cad:
        st.subheader("Registrar Compra")
        lista_nomes = df_estoque['Nome'].unique().tolist() if not df_estoque.empty else []
        modo_cadastro = st.radio("Produto:", ["Selecionar Existente", "Cadastrar Novo"], horizontal=True)
        
        nome_final = ""
        qtd_fardo_ref = 12 
        
        if modo_cadastro == "Selecionar Existente":
            if lista_nomes:
                nome_sel = st.selectbox("Escolha o Item:", lista_nomes)
                nome_final = nome_sel
                item_dados = df_estoque[df_estoque['Nome'] == nome_sel].iloc[0]
                # CORREÇÃO KEYERROR: Verifica se a coluna existe
                try: qtd_fardo_ref = int(ler_numero_input(item_dados['Qtd_Fardo']))
                except: qtd_fardo_ref = 12
            else: st.warning("Estoque vazio.")
        else:
            nome_digitado = st.text_input("Nome do Novo Produto:", placeholder="Ex: Skol Lata").upper()
            tipo = st.selectbox("Tipo:", ["Lata", "Long Neck", "Garrafa 600ml", "Litro/Outros"])
            nome_final = f"{nome_digitado} ({tipo})" if nome_digitado else ""
            
        st.divider()
        col_forma, col_vals = st.columns([1, 2])
        with col_forma:
            st.write("Como comprou?")
            forma_compra = st.radio("Formato:", ["Fardo Fechado", "Unidades Soltas"])
            data_compra = st.date_input("Data da Compra", date.today())
            fornecedor = st.text_input("Fornecedor", placeholder="Ex: Atacadão")
        with col_vals:
            custo_unitario_novo = 0.0
            qtd_total_adicionada = 0
            if forma_compra == "Fardo Fechado":
                custo_fardo_str = st.text_input("Valor pago no FARDO (R$)", placeholder="Ex: 36,70")
                qtd_dentro = st.selectbox("Quantas vêm no fardo?", list(range(1, 25)), index=11)
                qtd_fardos_str = st.text_input("Quantos FARDOS comprou?", placeholder="Ex: 10")
                custo_fardo = ler_numero_input(custo_fardo_str)
                qtd_fardos_compra = ler_numero_input(qtd_fardos_str)
                if custo_fardo > 0 and qtd_dentro > 0 and qtd_fardos_compra > 0:
                    custo_unitario_novo = custo_fardo / qtd_dentro
                    qtd_total_adicionada = int(qtd_fardos_compra * qtd_dentro)
                    qtd_fardo_ref = qtd_dentro
            else:
                custo_unit_str = st.text_input("Valor pago na UNIDADE (R$)", placeholder="Ex: 4,50")
                qtd_soltas_str = st.text_input("Quantas UNIDADES comprou?", placeholder="Ex: 50")
                qtd_fardo_ref = st.selectbox("Tamanho padrão do fardo (Ref):", list(range(1, 25)), index=11)
                custo_unit = ler_numero_input(custo_unit_str)
                qtd_soltas = ler_numero_input(qtd_soltas_str)
                if custo_unit > 0 and qtd_soltas > 0:
                    custo_unitario_novo = custo_unit
                    qtd_total_adicionada = int(qtd_soltas)
            preco_venda_str = st.text_input("Preço de Venda Unitário (R$)", placeholder="Ex: 4,49")
            preco_venda = ler_numero_input(preco_venda_str)

        if st.button("💾 Salvar Estoque", type="primary"):
            if nome_final and qtd_total_adicionada > 0 and preco_venda > 0:
                with st.spinner("Calculando..."):
                    encontrado = False
                    idx_planilha = 2
                    if not df_estoque.empty:
                        for i, row in df_estoque.iterrows():
                            if row['Nome'] == nome_final:
                                est_antigo = int(ler_numero_input(row['Estoque']))
                                custo_antigo = ler_numero_input(row['Custo'])
                                if custo_antigo > 1000: custo_antigo = custo_unitario_novo
                                val_antigo = est_antigo * custo_antigo
                                val_novo = qtd_total_adicionada * custo_unitario_novo
                                n_total = est_antigo + qtd_total_adicionada
                                n_custo = (val_antigo + val_novo) / n_total if n_total > 0 else custo_unitario_novo
                                sheet_estoque.update_cell(idx_planilha + i, 6, n_total)
                                sheet_estoque.update_cell(idx_planilha + i, 4, float_para_sheets(n_custo))
                                sheet_estoque.update_cell(idx_planilha + i, 5, float_para_sheets(preco_venda))
                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor)
                                sheet_estoque.update_cell(idx_planilha + i, 7, data_compra.strftime('%d/%m/%Y'))
                                try: sheet_estoque.update_cell(idx_planilha + i, 8, qtd_fardo_ref)
                                except: pass
                                encontrado = True
                                break
                    if not encontrado:
                        sheet_estoque.append_row([nome_final, "Geral", fornecedor, float_para_sheets(custo_unitario_novo), float_para_sheets(preco_venda), qtd_total_adicionada, data_compra.strftime('%d/%m/%Y'), qtd_fardo_ref])
                    sheet_hist_est.append_row([pegar_data_hora(), nome_final, "COMPRA", qtd_total_adicionada, float_para_sheets(qtd_total_adicionada*custo_unitario_novo), f"Forn: {fornecedor}"])
                    st.success("✅ Salvo!")
                    time.sleep(1)
                    st.rerun()

    with aba_edit:
        st.subheader("✏️ Editar/Excluir")
        if not df_estoque.empty:
            prod_edit = st.selectbox("Selecione:", ["Selecione..."] + df_estoque['Nome'].tolist())
            if prod_edit != "Selecione...":
                idx_edit = df_estoque[df_estoque['Nome'] == prod_edit].index[0]
                row_edit = df_estoque.iloc[idx_edit]
                linha_s = idx_edit + 2
                with st.form("form_edit"):
                    st.info(f"Editando: {prod_edit}")
                    c1, c2, c3 = st.columns(3)
                    n_v = c1.text_input("Venda (R$)", value=float_para_sheets(ler_numero_input(row_edit['Venda'])))
                    n_c = c2.text_input("Custo (R$)", value=float_para_sheets(ler_numero_input(row_edit['Custo'])))
                    n_e = c3.number_input("Estoque", value=int(ler_numero_input(row_edit['Estoque'])), step=1)
                    c_s, c_d = st.columns(2)
                    if c_s.form_submit_button("💾 Salvar"):
                        sheet_estoque.update_cell(linha_s, 5, n_v)
                        sheet_estoque.update_cell(linha_s, 4, n_c)
                        sheet_estoque.update_cell(linha_s, 6, n_e)
                        st.success("Atualizado!")
                        st.rerun()
                    if c_d.form_submit_button("🗑️ EXCLUIR"):
                        sheet_estoque.delete_rows(int(linha_s))
                        st.rerun()

    with aba_ver:
        if not df_estoque.empty:
            df_display = df_estoque.copy()
            df_display['Custo_N'] = df_display['Custo'].apply(ler_numero_input)
            df_display['Venda_N'] = df_display['Venda'].apply(ler_numero_input)
            df_display['Lucro Real'] = df_display['Venda_N'] - df_display['Custo_N']
            st.dataframe(df_display[['Nome', 'Estoque', 'Venda', 'Custo', 'Lucro Real']], use_container_width=True)

# ==========================================
# 💰 FIDELIDADE & CAIXA
# ==========================================
elif menu == "💰 Fidelidade & Caixa":
    st.title("💰 Caixa & Fidelidade")
    if st.session_state.venda_sucesso:
        st.success("✅ Sucesso!")
        st.markdown(f"""<a href="{st.session_state.link_zap_atual}" target="_blank" class="big-btn">📱 {st.session_state.msg_zap_btn}</a>""", unsafe_allow_html=True)
        if st.button("Nova Venda"): st.session_state.venda_sucesso = False; st.rerun()
    else:
        df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
        df_estoque = pd.DataFrame(sheet_estoque.get_all_records())
        st.markdown("### 👤 Cliente")
        lista_c = ["🆕 NOVO CLIENTE"] + (df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)).tolist() if not df_clientes.empty else ["🆕 NOVO CLIENTE"]
        sel_c = st.selectbox("Selecione:", lista_c)
        c1, c2 = st.columns(2)
        if sel_c == "🆕 NOVO CLIENTE":
            n_i = c1.text_input("Nome:").strip().upper()
            t_i = c2.text_input("Tel:")
        else:
            n_i = sel_c.split(" - ")[0]
            t_i = sel_c.split(" - ")[1]
        t_limpo = limpar_telefone(t_i)
        st.divider()
        st.markdown("### 🛒 Carrinho")
        if not df_estoque.empty:
            df_estoque['Menu'] = df_estoque.apply(lambda x: f"{x['Nome']} (Estoque: {x['Estoque']})", axis=1)
            prod_sel = st.selectbox("Produto:", ["(Apenas Ponto)"] + df_estoque['Menu'].tolist())
            nome_p_real = prod_sel.split(" (Estoque:")[0] if prod_sel != "(Apenas Ponto)" else "(Apenas Ponto)"
            c_f, c_u = st.columns(2)
            v_f = c_f.selectbox("FARDOS", list(range(0, 11)))
            v_u = c_u.selectbox("UNIDADES", list(range(0, 41)))
            
            if st.button("✅ CONFIRMAR VENDA", type="primary"):
                if n_i:
                    with st.spinner("Registrando..."):
                        if nome_p_real != "(Apenas Ponto)":
                            idx_e = df_estoque[df_estoque['Nome'] == nome_p_real].index[0]
                            row_p = df_estoque.iloc[idx_e]
                            # CORREÇÃO KEYERROR: Fallback caso Qtd_Fardo não exista
                            try: ref_f = int(ler_numero_input(row_p['Qtd_Fardo']))
                            except: ref_f = 12
                            
                            total_b = (v_f * ref_f) + v_u
                            est_at = int(ler_numero_input(row_p['Estoque']))
                            if est_at >= total_b:
                                sheet_estoque.update_cell(idx_e + 2, 6, est_at - total_b)
                                total_mon = total_b * ler_numero_input(row_p['Venda'])
                                sheet_hist_est.append_row([pegar_data_hora(), nome_p_real, "VENDA", total_b, float_para_sheets(total_mon), f"Cli: {n_i}"])
                            else: st.error("Sem estoque!"); st.stop()
                        
                        # FIDELIDADE (Evita duplicar)
                        df_clientes['tel_l'] = df_clientes['telefone'].apply(limpar_telefone)
                        match = df_clientes[df_clientes['tel_l'] == t_limpo]
                        if not match.empty:
                            pts = int(ler_numero_input(match.iloc[0]['compras'])) + 1
                            sheet_clientes.update_cell(int(match.index[0] + 2), 3, pts)
                        else:
                            pts = 1
                            sheet_clientes.append_row([n_i, t_i, 1, date.today().strftime('%d/%m/%Y')])
                        
                        msg, btn = gerar_mensagem_zap(n_i, pts)
                        st.session_state.link_zap_atual = f"https://api.whatsapp.com/send?phone=55{t_limpo}&text={urllib.parse.quote(msg)}"
                        st.session_state.msg_zap_btn = btn
                        st.session_state.venda_sucesso = True
                        st.rerun()
        else: st.warning("Estoque vazio.")

# ==========================================
# 👥 GERENCIAR CLIENTES
# ==========================================
elif menu == "👥 Gerenciar Clientes":
    st.title("👥 Clientes")
    df_c = pd.DataFrame(sheet_clientes.get_all_records())
    if not df_c.empty:
        df_c['Display'] = df_c['nome'] + " - " + df_c['telefone'].astype(str)
        sel = st.selectbox("Escolha:", ["Selecione..."] + df_c['Display'].tolist())
        if sel != "Selecione...":
            idx = df_c[df_c['Display'] == sel].index[0]
            linha_s = idx + 2
            with st.form("form_edit_cli"):
                n_n = st.text_input("Nome", value=df_c.iloc[idx]['nome'])
                n_t = st.text_input("Tel", value=df_c.iloc[idx]['telefone'])
                n_p = st.number_input("Pontos", value=int(ler_numero_input(df_c.iloc[idx]['compras'])))
                if st.form_submit_button("Salvar"):
                    sheet_clientes.update_cell(linha_s, 1, n_n)
                    sheet_clientes.update_cell(linha_s, 2, n_t)
                    sheet_clientes.update_cell(linha_s, 3, n_p)
                    st.rerun()
                if st.form_submit_button("🗑️ EXCLUIR CLIENTE"):
                    sheet_clientes.delete_rows(int(linha_s))
                    st.rerun()

# ==========================================
# 📊 RELATÓRIOS
# ==========================================
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios")
    st.write("Estoque")
    try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True)
    except: st.write("Vazio")
    st.write("Fidelidade")
    try: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True)
    except: st.write("Vazio")
