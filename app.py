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
ICON_URL = "https://cdn-icons-png.flaticon.com/512/3175/3175199.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #0047AB; color: white !important;
        border-radius: 10px 10px 0px 0px; padding: 10px 20px; font-weight: bold;
    }}
    .stTabs [aria-selected="true"] {{ background-color: #002D6E !important; }}
    div.stButton > button {{
        background-color: #008CBA; color: white; font-weight: bold;
        border-radius: 10px; height: 3em; width: 100%; border: none;
    }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{
        padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3;
        border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px;
    }}
    </style>
    <link rel="shortcut icon" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
    """, unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN
# ==========================================
SENHA_DO_SISTEMA = "adega123"

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>🔒 Adega do Barão</h1>", unsafe_allow_html=True)
    c_a, c_b, c_c = st.columns([1, 2, 1])
    with c_b:
        with st.form("login_form"):
            senha = st.text_input("Senha:", type="password", placeholder="Digite e aperte Enter ↵")
            if st.form_submit_button("ACESSAR"):
                if senha == SENHA_DO_SISTEMA:
                    st.success("Sucesso! Entrando...")
                    st.image("https://media1.tenor.com/m/5-2_9lK2mY8AAAAC/cheers-beer.gif", use_container_width=True)
                    time.sleep(2)
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
    st.stop()

# ==========================================
# 📡 CONEXÃO OTIMIZADA (COM CACHE)
# ==========================================
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Fidelidade")
    
    # Define as planilhas
    sheet_clientes = planilha.worksheet("Página1") 
    sheet_estoque = planilha.worksheet("Estoque") 
    sheet_hist_est = planilha.worksheet("Historico_Estoque")
    sheet_hist_cli = planilha.worksheet("Historico")

    # --- FUNÇÃO DE AUTO-REPARO ---
    def garantir_cabecalhos():
        headers_padrao = ["Nome", "Tipo", "Fornecedor", "Custo", "Venda", "Estoque", "Data Compra", "Qtd_Fardo", "ML"]
        try:
            atuais = sheet_estoque.row_values(1)
            if not atuais or len(atuais) < 9:
                for i, h in enumerate(headers_padrao):
                    sheet_estoque.update_cell(1, i+1, h)
        except: pass

    # --- SISTEMA DE CACHE INTELIGENTE (RESOLVE O ERRO 429) ---
    # TTL=5 significa: Lê os dados e guarda por 5 segundos. 
    # Se você clicar 100 vezes nesse tempo, ele não incomoda o Google.
    
    @st.cache_data(ttl=5)
    def carregar_dados_estoque():
        try: return pd.DataFrame(sheet_estoque.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_dados_clientes():
        try: return pd.DataFrame(sheet_clientes.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_historico_cli():
        try: return pd.DataFrame(sheet_hist_cli.get_all_records())
        except: return pd.DataFrame()

    @st.cache_data(ttl=5)
    def carregar_historico_est():
        try: return pd.DataFrame(sheet_hist_est.get_all_records())
        except: return pd.DataFrame()

    # Função para limpar o cache quando salvamos algo novo (para atualizar na hora)
    def limpar_cache():
        carregar_dados_estoque.clear()
        carregar_dados_clientes.clear()
        carregar_historico_cli.clear()
        carregar_historico_est.clear()

    garantir_cabecalhos() 

except Exception as e:
    st.error(f"Erro de conexão. Aguarde 1 minuto e recarregue a página. ({e})")
    st.stop()

# --- FUNÇÕES ÚTEIS ---
def cvt_num(valor): 
    if not valor: return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v: v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

def fmt_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def save_str(valor): return "{:.2f}".format(valor)
def clean_tel(t): return re.sub(r'\D', '', str(t))

def calc_fisico(total, ref):
    if ref == 0: ref = 12
    f, u = divmod(total, ref)
    txt = ""
    if f > 0: txt += f"📦 {f} fardos "
    if u > 0: txt += f"🍺 {u} un"
    return txt if txt else "Zerado"

def msg_zap(nome, pts):
    n = nome.split()[0].capitalize()
    if pts == 1:
        return f"Oi, {n}! ✨\nObrigado pela compra! Abri seu Cartão Fidelidade. Garantiu 1 ponto! 🍷", "Enviar Boas-Vindas 🎉"
    elif 1 < pts < 10:
        return f"Oi, {n}! 👊\nCompra registrada! Você tem *{pts} pontos*. Faltam {10-pts}! 🍻", f"Enviar Saldo ({pts}) 📲"
    else:
        return f"PARABÉNS, {n}!!! ✨🏆\nCompletou 10 pontos! Ganhou **20% OFF** hoje! 🥳", "🏆 ENVIAR PRÊMIO!"

# ==========================================
# 📱 MENU
# ==========================================
with st.sidebar:
    st.image(ICON_URL, width=80)
    st.title("Menu")
    menu = st.radio("Ir para:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 Históricos"])
    st.divider()
    if st.button("SAIR"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 ESTOQUE
# ==========================================
if menu == "📦 Estoque":
    st.title("📦 Gestão de Estoque")
    
    # Usa o Cache para carregar
    df_est = carregar_dados_estoque()

    t1, t2, t3 = st.tabs(["📋 Lista", "🆕 Novo", "✏️ Editar"])

    # --- LISTA ---
    with t1:
        if not df_est.empty:
            if 'ML' not in df_est.columns: df_est['ML'] = "-"
            
            df_est['custo_n'] = df_est['Custo'].apply(cvt_num)
            df_est['venda_n'] = df_est['Venda'].apply(cvt_num)
            df_est['Lucro (R$)'] = (df_est['venda_n'] - df_est['custo_n']).apply(fmt_reais)
            df_est['Custo (R$)'] = df_est['custo_n'].apply(fmt_reais)
            df_est['Venda (R$)'] = df_est['venda_n'].apply(fmt_reais)
            df_est['Físico'] = df_est.apply(lambda r: calc_fisico(int(cvt_num(r['Estoque'])), int(cvt_num(r.get('Qtd_Fardo', 12)))), axis=1)
            
            st.dataframe(df_est[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']], use_container_width=True)
        else:
            st.info("Estoque vazio.")

    # --- NOVO ---
    with t2:
        st.subheader("Novo Produto")
        nome = st.text_input("Nome:").upper()
        c_t, c_m = st.columns(2)
        tipo = c_t.selectbox("Tipo:", ["LATA", "LONG NECK", "GARRAFA 600ML", "LITRÃO", "OUTROS"])
        
        lista_ml = ["269ml", "330ml", "350ml", "473ml", "550ml", "600ml", "1 Litro", "Outros"]
        sel_ml = c_m.selectbox("ML:", lista_ml)
        ml_final = c_m.text_input("Digite o ML:") if sel_ml == "Outros" else sel_ml

        c1, c2 = st.columns(2)
        custo = c1.text_input("Custo (R$):", placeholder="Ex: 3,50")
        venda = c2.text_input("Venda (R$):", placeholder="Ex: 5,00")
        
        c3, c4 = st.columns(2)
        forn = c3.text_input("Fornecedor:")
        dt = c4.date_input("Data:", date.today())
        
        st.markdown("---")
        modo = st.radio("Comprou como?", ["Fardo Fechado", "Unidade Solta"], horizontal=True)
        c5, c6 = st.columns(2)
        ref = c5.number_input("Itens no Fardo:", value=12)
        qtd_ini = c6.number_input("Qtd Fardos:" if modo == "Fardo Fechado" else "Qtd Unidades:", min_value=0)
        
        total_ini = qtd_ini * ref if modo == "Fardo Fechado" else qtd_ini

        if st.button("✅ CADASTRAR", type="primary"):
            if not nome or not custo or not venda:
                st.warning("Preencha Nome e Preços!")
            else:
                sheet_estoque.append_row([
                    nome, tipo, forn, 
                    save_str(cvt_num(custo)), save_str(cvt_num(venda)), 
                    int(total_ini), dt.strftime('%d/%m/%Y'), int(ref), str(ml_final)
                ])
                sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), nome, "NOVO", int(total_ini), forn])
                
                limpar_cache() # Força atualização
                st.success("Salvo!"); time.sleep(1); st.rerun()

    # --- EDITAR ---
    with t3:
        if not df_est.empty:
            sel = st.selectbox("Editar:", ["Selecione..."] + df_est['Nome'].tolist())
            if sel != "Selecione...":
                idx = df_est[df_est['Nome'] == sel].index[0]
                row = df_est.iloc[idx]
                
                st.info(f"Editando: {sel}")
                ml_db = str(row.get('ML', '350ml'))
                idx_ml = lista_ml.index(ml_db) if ml_db in lista_ml else lista_ml.index("Outros")
                
                c_a, c_b = st.columns(2)
                novo_ml_sel = c_a.selectbox("ML:", lista_ml, index=idx_ml, key="ed_ml")
                novo_ml_txt = c_b.text_input("ML Personalizado:", value=ml_db if novo_ml_sel == "Outros" else "", disabled=(novo_ml_sel != "Outros"))
                ml_save = novo_ml_txt if novo_ml_sel == "Outros" else novo_ml_sel

                c_c, c_d = st.columns(2)
                n_venda = c_c.text_input("Venda:", value=str(row['Venda']))
                n_custo = c_d.text_input("Custo:", value=str(row['Custo']))
                
                st.write("➕ **Adicionar Estoque:**")
                f1, f2 = st.columns(2)
                add_f = f1.number_input("Add Fardos:", min_value=0)
                add_u = f2.number_input("Add Unidades:", min_value=0)
                
                col_save, col_del = st.columns(2)
                
                if col_save.button("💾 SALVAR ALTERAÇÕES"):
                    ref = int(cvt_num(row.get('Qtd_Fardo', 12)))
                    atual = int(cvt_num(row['Estoque']))
                    novo_total = atual + (add_f * ref) + add_u
                    
                    sheet_estoque.update_cell(idx+2, 4, save_str(cvt_num(n_custo)))
                    sheet_estoque.update_cell(idx+2, 5, save_str(cvt_num(n_venda)))
                    sheet_estoque.update_cell(idx+2, 6, int(novo_total))
                    sheet_estoque.update_cell(idx+2, 9, str(ml_save))
                    
                    if (add_f * ref) + add_u > 0:
                         sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), sel, "ENTRADA", (add_f * ref) + add_u, "Ajuste Manual"])
                    
                    limpar_cache() # Força atualização
                    st.success("Atualizado!"); time.sleep(1); st.rerun()

                if col_del.button("🗑️ EXCLUIR PRODUTO"):
                    sheet_estoque.delete_rows(int(idx + 2))
                    limpar_cache() # Força atualização
                    st.warning("Excluído!"); time.sleep(1); st.rerun()

# ==========================================
# 💰 CAIXA
# ==========================================
elif menu == "💰 Caixa":
    st.title("💰 Caixa")
    
    if 'v_suc' in st.session_state and st.session_state.v_suc:
        st.success("Venda Feita!")
        st.markdown(f'<a href="{st.session_state.link}" target="_blank" class="big-btn">{st.session_state.btn_txt}</a>', unsafe_allow_html=True)
        if st.button("Nova Venda"): 
            st.session_state.v_suc = False
            st.rerun()
    else:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()

        sel_cli = st.selectbox("Cliente:", ["🆕 NOVO"] + (df_cli['nome'] + " - " + df_cli['telefone'].astype(str)).tolist() if not df_cli.empty else ["🆕 NOVO"])
        
        c1, c2 = st.columns(2)
        if sel_cli == "🆕 NOVO":
            nm = c1.text_input("Nome:").upper()
            tl = c2.text_input("Tel:")
        else:
            nm = sel_cli.split(" - ")[0]
            tl = sel_cli.split(" - ")[1]

        st.divider()
        if not df_est.empty:
            prod = st.selectbox("Produto:", ["(Selecione...)"] + df_est['Nome'].tolist())
            if prod != "(Selecione...)":
                idx_p = df_est[df_est['Nome'] == prod].index[0]
                row_p = df_est.iloc[idx_p]
                st.markdown(f'<div class="estoque-info">Em Estoque: {calc_fisico(int(cvt_num(row_p["Estoque"])), int(cvt_num(row_p.get("Qtd_Fardo", 12))))}</div>', unsafe_allow_html=True)
            
            q1, q2 = st.columns(2)
            q_f = q1.number_input("Fardos:", min_value=0)
            q_u = q2.number_input("Unidades:", min_value=0)

            if st.button("✅ FINALIZAR VENDA"):
                tel_clean = clean_tel(tl)
                if prod != "(Selecione...)":
                    ref = int(cvt_num(df_est.iloc[idx_p].get('Qtd_Fardo', 12)))
                    baixa = (q_f * ref) + q_u
                    atual = int(cvt_num(df_est.iloc[idx_p]['Estoque']))
                    
                    if atual < baixa:
                        st.error("Estoque Insuficiente!"); st.stop()
                    
                    sheet_estoque.update_cell(idx_p+2, 6, int(atual - baixa))
                    vlr = cvt_num(df_est.iloc[idx_p]['Venda'])
                    sheet_hist_est.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), prod, "VENDA", baixa, save_str(baixa*vlr)])

                # Fidelidade
                match = df_cli[df_cli['telefone'].astype(str).apply(clean_tel) == tel_clean] if not df_cli.empty else pd.DataFrame()
                if not match.empty:
                    pts = int(match.iloc[0]['compras']) + 1
                    sheet_clientes.update_cell(int(match.index[0]+2), 3, pts)
                else:
                    pts = 1
                    sheet_clientes.append_row([nm, tel_clean, 1, date.today().strftime('%d/%m/%Y')])
                
                sheet_hist_cli.append_row([datetime.now().strftime('%d/%m/%Y %H:%M'), nm, tel_clean, pts])
                msg, btn = msg_zap(nm, pts)
                
                limpar_cache() # Força atualização geral
                
                st.session_state.link = f"https://api.whatsapp.com/send?phone=55{tel_clean}&text={urllib.parse.quote(msg)}"
                st.session_state.btn_txt = btn
                st.session_state.v_suc = True
                st.rerun()

# ==========================================
# 👥 CLIENTES E 📊 HISTÓRICOS
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Clientes")
    st.dataframe(carregar_dados_clientes(), use_container_width=True)

elif menu == "📊 Históricos":
    st.title("📊 Relatórios")
    t1, t2 = st.tabs(["Vendas", "Estoque"])
    with t1: st.dataframe(carregar_historico_cli(), use_container_width=True)
    with t2: st.dataframe(carregar_historico_est(), use_container_width=True)
