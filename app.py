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

    page_title="Super Adega 11.0",

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

            st.error("⏳ Sessão expirada.")

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

        st.session_state.ultima_atividade = time.time()

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



# --- FUNÇÕES AUXILIARES DE LIMPEZA E FORMATO ---

def limpar_telefone(tel): return re.sub(r'\D', '', str(tel))

def pegar_data_hora(): return datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')



def ler_numero_input(valor):

    """Lê o que o usuário digitou (4,49) e vira float python (4.49) para cálculo"""

    if not valor or str(valor).strip() == "": return 0.0

    val_str = str(valor).replace("R$", "").strip()

    if "," in val_str:

        val_str = val_str.replace(".", "").replace(",", ".")

    try: return float(val_str)

    except: return 0.0



def float_para_sheets(valor):

    """

    O SEGREDO: Transforma float (4.49) em STRING BRASILEIRA ("4,49") 

    para o Google Sheets não bugar e criar milhões.

    """

    return f"{valor:.2f}".replace(".", ",")



def formatar_moeda_visual(v):

    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")



# --- MENSAGEM WHATSAPP (EXATAMENTE A SUA) ---

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

    

    # --- ABA 1: ENTRADA ---

    with aba_cad:

        st.subheader("Registrar Compra")

        lista_nomes = df_estoque['Nome'].unique().tolist() if not df_estoque.empty else []

        modo_cadastro = st.radio("Produto:", ["Selecionar Existente", "Cadastrar Novo"], horizontal=True)

        

        nome_final = ""

        qtd_fardo_ref = 12 

        

        if modo_cadastro == "Selecionar Existente":

            if lista_nomes:

                nome_selecionado = st.selectbox("Escolha o Item:", lista_nomes)

                nome_final = nome_selecionado

                item_dados = df_estoque[df_estoque['Nome'] == nome_selecionado].iloc[0]

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

            st.write("Como você comprou?")

            forma_compra = st.radio("Formato:", ["Fardo Fechado", "Unidades Soltas"])

            data_compra = st.date_input("Data da Compra", date.today())

            fornecedor = st.text_input("Fornecedor", placeholder="Ex: Atacadão")



        with col_vals:

            custo_unitario_novo = 0.0

            qtd_total_adicionada = 0

            

            # --- CAMPOS VAZIOS PARA NÃO PRECISAR APAGAR (Input como string) ---

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

                                estoque_antigo = int(ler_numero_input(row['Estoque']))

                                custo_antigo = ler_numero_input(row['Custo'])

                                

                                # Proteção contra o erro antigo dos milhões

                                if custo_antigo > 1000: custo_antigo = custo_unitario_novo

                                

                                valor_antigo = estoque_antigo * custo_antigo

                                valor_novo = qtd_total_adicionada * custo_unitario_novo

                                novo_total = estoque_antigo + qtd_total_adicionada

                                

                                if novo_total > 0:

                                    novo_custo = (valor_antigo + valor_novo) / novo_total

                                else:

                                    novo_custo = custo_unitario_novo

                                

                                # ENVIA COMO TEXTO "4,49" PARA NÃO BUGAR NA PLANILHA

                                sheet_estoque.update_cell(idx_planilha + i, 6, novo_total)

                                sheet_estoque.update_cell(idx_planilha + i, 4, float_para_sheets(novo_custo))

                                sheet_estoque.update_cell(idx_planilha + i, 5, float_para_sheets(preco_venda))

                                sheet_estoque.update_cell(idx_planilha + i, 3, fornecedor)

                                sheet_estoque.update_cell(idx_planilha + i, 7, data_compra.strftime('%d/%m/%Y'))

                                try: sheet_estoque.update_cell(idx_planilha + i, 8, qtd_fardo_ref)

                                except: pass

                                encontrado = True

                                break

                    

                    if not encontrado:

                        # CRIA NOVO - TUDO COMO STRING FORMATADA

                        sheet_estoque.append_row([

                            nome_final, 

                            "Geral", 

                            fornecedor, 

                            float_para_sheets(custo_unitario_novo), 

                            float_para_sheets(preco_venda), 

                            qtd_total_adicionada, 

                            data_compra.strftime('%d/%m/%Y'), 

                            qtd_fardo_ref

                        ])

                    

                    sheet_hist_est.append_row([pegar_data_hora(), nome_final, "COMPRA", qtd_total_adicionada, float_para_sheets(qtd_total_adicionada*custo_unitario_novo), f"Forn: {fornecedor}"])

                    st.success(f"✅ {qtd_total_adicionada}x {nome_final} Salvo! (Custo Un: R$ {float_para_sheets(custo_unitario_novo)})")

                    time.sleep(2)

                    st.rerun()

            else: st.error("Preencha valores e quantidades.")



    # --- ABA 2: EDITAR E EXCLUIR ITEM ---

    with aba_edit:

        st.subheader("✏️ Editar/Excluir")

        if not df_estoque.empty:

            prod_edit = st.selectbox("Selecione:", ["Selecione..."] + df_estoque['Nome'].unique().tolist())

            

            if prod_edit != "Selecione...":

                idx_edit = df_estoque[df_estoque['Nome'] == prod_edit].index[0]

                row_edit = df_estoque.iloc[idx_edit]

                linha_sheet = idx_edit + 2

                

                with st.form("form_edit_estoque"):

                    st.info(f"Editando: {prod_edit}")

                    c1, c2, c3 = st.columns(3)

                    

                    # Traz valores atuais para os campos (aqui sim precisa value, pois é edição)

                    val_venda_atual = float_para_sheets(ler_numero_input(row_edit['Venda']))

                    val_custo_atual = float_para_sheets(ler_numero_input(row_edit['Custo']))

                    val_estoque_atual = int(ler_numero_input(row_edit['Estoque']))

                    

                    # Inputs como texto para aceitar vírgula na edição

                    novo_venda_str = c1.text_input("Venda (R$)", value=val_venda_atual)

                    novo_custo_str = c2.text_input("Custo Médio (R$)", value=val_custo_atual)

                    novo_estoque = c3.number_input("Estoque (Qtd)", value=val_estoque_atual, step=1)

                    

                    col_save, col_del = st.columns(2)

                    if col_save.form_submit_button("💾 Salvar Correção"):

                        sheet_estoque.update_cell(linha_sheet, 5, novo_venda_str)

                        sheet_estoque.update_cell(linha_sheet, 4, novo_custo_str)

                        sheet_estoque.update_cell(linha_sheet, 6, novo_estoque)

                        st.success("Dados corrigidos!")

                        time.sleep(1)

                        st.rerun()

                    

                    if col_del.form_submit_button("🗑️ EXCLUIR ITEM"):

                        sheet_estoque.delete_rows(int(linha_sheet))

                        st.warning("Excluído.")

                        time.sleep(1.5)

                        st.rerun()

        else: st.warning("Sem produtos.")



    # --- ABA 3: VER ESTOQUE ---

    with aba_ver:

        if not df_estoque.empty:

            busca = st.text_input("🔍 Buscar:", placeholder="Nome...").upper()

            if busca: df_estoque = df_estoque[df_estoque['Nome'].str.contains(busca, case=False)]

            

            df_display = df_estoque.copy()

            # Converte para float para calcular

            df_display['Custo_Num'] = df_display['Custo'].apply(ler_numero_input)

            df_display['Venda_Num'] = df_display['Venda'].apply(ler_numero_input)

            df_display['Lucro Un.'] = df_display['Venda_Num'] - df_display['Custo_Num']

            

            # Formata para visualização

            df_display['Custo Médio'] = df_display['Custo_Num'].apply(formatar_moeda_visual)

            df_display['Preço Venda'] = df_display['Venda_Num'].apply(formatar_moeda_visual)

            df_display['Lucro Real'] = df_display['Lucro Un.'].apply(formatar_moeda_visual)

            

            if 'Qtd_Fardo' in df_display.columns:

                df_display['Visual Estoque'] = df_display.apply(lambda x: f"{int(ler_numero_input(x['Estoque'])//(ler_numero_input(x['Qtd_Fardo']) or 12))} Fardos + {int(ler_numero_input(x['Estoque'])%(ler_numero_input(x['Qtd_Fardo']) or 12))} Un", axis=1)

            else: df_display['Visual Estoque'] = df_display['Estoque']



            st.dataframe(

                df_display[['Nome', 'Visual Estoque', 'Venda', 'Custo', 'Lucro Un.']],

                use_container_width=True, hide_index=True,

                column_config={

                    "Venda": st.column_config.NumberColumn("Venda", format="R$ %.2f"),

                    "Custo": st.column_config.NumberColumn("Custo Médio", format="R$ %.2f"),

                    "Lucro Un.": st.column_config.NumberColumn("Lucro Real", format="R$ %.2f"),

                }

            )

        else: st.info("Vazio.")



# ==========================================

# 💰 FIDELIDADE & CAIXA

# ==========================================

elif menu == "💰 Fidelidade & Caixa":

    st.title("💰 Caixa & Fidelidade")

    

    if st.session_state.venda_sucesso:

        st.balloons()

        st.success("✅ VENDA REGISTRADA COM SUCESSO!")

        st.markdown(f"""<a href="{st.session_state.link_zap_atual}" target="_blank" class="big-btn">📱 {st.session_state.msg_zap_btn}</a>""", unsafe_allow_html=True)

        st.divider()

        if st.button("🔄 NOVA VENDA", type="primary"):

            st.session_state.venda_sucesso = False

            st.rerun()

            

    else:

        df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

        df_estoque = pd.DataFrame(sheet_estoque.get_all_records())

        

        st.markdown("### 👤 Cliente")

        lista_clientes_display = ["🆕 NOVO CLIENTE"]

        dict_clientes = {}

        

        if not df_clientes.empty:

            df_clientes['tel_limpo'] = df_clientes['telefone'].apply(limpar_telefone)

            df_clientes['Display'] = df_clientes['nome'] + " - " + df_clientes['telefone'].astype(str)

            lista_clientes_display += df_clientes['Display'].tolist()

            for idx, row in df_clientes.iterrows():

                dict_clientes[row['Display']] = row['telefone']

                

        cliente_selecionado = st.selectbox("Selecione:", lista_clientes_display)

        col_nome, col_tel = st.columns(2)

        is_new_client = False

        

        if cliente_selecionado == "🆕 NOVO CLIENTE":

            is_new_client = True

            nome_input = col_nome.text_input("Nome:", placeholder="Digite o nome...").strip().upper()

            tel_input = col_tel.text_input("Telefone:", placeholder="88999990000")

        else:

            dados_nome = cliente_selecionado.split(" - ")[0]

            dados_tel = dict_clientes.get(cliente_selecionado, "")

            nome_input = col_nome.text_input("Nome:", value=dados_nome, disabled=True)

            tel_input = col_tel.text_input("Telefone:", value=dados_tel, disabled=True)

            

        tel_input_limpo = limpar_telefone(tel_input)

        st.divider()



        st.markdown("### 🛒 Carrinho")

        if not df_estoque.empty:

            df_estoque['Menu'] = df_estoque.apply(lambda x: f"{x['Nome']} (Estoque: {x['Estoque']})", axis=1)

            lista_prod = ["(Apenas Pontuar - Sem Produto)"] + df_estoque['Menu'].tolist()

            prod_escolhido_menu = st.selectbox("Produto:", lista_prod)

            

            nome_produto_real = prod_escolhido_menu.split(" (Estoque:")[0] if prod_escolhido_menu != "(Apenas Pontuar - Sem Produto)" else "(Apenas Pontuar - Sem Produto)"



            c_fardo, c_unid = st.columns(2)

            qtd_fardos_venda = c_fardo.selectbox("FARDOS", list(range(0, 11)))

            qtd_soltas_venda = c_unid.selectbox("UNIDADES", list(range(0, 41)))

            

            tamanho_fardo_real = 12

            if nome_produto_real != "(Apenas Pontuar - Sem Produto)":

                item_data = df_estoque[df_estoque['Nome'] == nome_produto_real].iloc[0]

                try: tamanho_fardo_real = int(ler_numero_input(item_data['Qtd_Fardo']))

                except: tamanho_fardo_real = 12

                

            total_unidades_venda = (qtd_fardos_venda * tamanho_fardo_real) + qtd_soltas_venda

            if total_unidades_venda > 0: st.info(f"🧾 Baixando: **{total_unidades_venda} garrafas**")

        else:

            st.warning("Estoque vazio.")

            nome_produto_real = "(Apenas Pontuar - Sem Produto)"

            total_unidades_venda = 0



        st.divider()

        if st.button("✅ CONFIRMAR VENDA", type="primary"):

            erro = False

            if not nome_input: st.error("Falta nome."); erro = True

            

            if not erro:

                with st.spinner("Registrando..."):

                    if nome_produto_real != "(Apenas Pontuar - Sem Produto)" and total_unidades_venda > 0:

                        idx_est = -1

                        est_atual = 0

                        for i, r in df_estoque.iterrows():

                            if r['Nome'] == nome_produto_real:

                                idx_est = i + 2

                                est_atual = int(ler_numero_input(r['Estoque']))

                                venda_val = ler_numero_input(r['Venda'])

                                break

                        if idx_est != -1:

                            if est_atual >= total_unidades_venda:

                                sheet_estoque.update_cell(idx_est, 6, est_atual - total_unidades_venda)

                                total_monetario = total_unidades_venda * venda_val

                                sheet_hist_est.append_row([pegar_data_hora(), nome_produto_real, "VENDA", total_unidades_venda, float_para_sheets(total_monetario), f"Cli: {nome_input}"])

                            else:

                                st.error(f"Estoque insuficiente!"); st.stop()

                    elif nome_produto_real != "(Apenas Pontuar - Sem Produto)" and total_unidades_venda == 0:

                        nome_produto_real = f"Visita ({nome_produto_real})"

                    

                    cliente_ja_existe = False

                    row_cli = -1

                    pts_old = 0

                    if not df_clientes.empty:

                        match = df_clientes[df_clientes['tel_limpo'] == tel_input_limpo]

                        if not match.empty:

                            cliente_ja_existe = True

                            row_cli = match.index[0] + 2

                            pts_old = int(ler_numero_input(match.iloc[0]['compras']))

                    

                    if cliente_ja_existe:

                        novos_pts = pts_old + 1

                        sheet_clientes.update_cell(row_cli, 3, novos_pts)

                        sheet_clientes.update_cell(row_cli, 4, pegar_data_hora())

                        if is_new_client: sheet_clientes.update_cell(row_cli, 1, nome_input)

                    else:

                        novos_pts = 1

                        sheet_clientes.append_row([nome_input, tel_input, 1, pegar_data_hora()])

                    

                    sheet_hist_cli.append_row([pegar_data_hora(), nome_input, tel_input, f"Venda: {nome_produto_real}"])

                    

                    msg, btn_txt = gerar_mensagem_zap(nome_input, novos_pts)

                    link = f"https://api.whatsapp.com/send?phone={tel_input_limpo}&text={urllib.parse.quote(msg)}"

                    

                    st.session_state.venda_sucesso = True

                    st.session_state.link_zap_atual = link

                    st.session_state.msg_zap_btn = btn_txt

                    st.rerun()



# ==========================================

# 👥 GERENCIAR CLIENTES

# ==========================================

elif menu == "👥 Gerenciar Clientes":

    st.title("👥 Gerenciar Clientes")

    try: df_cli_edit = pd.DataFrame(sheet_clientes.get_all_records())

    except: df_cli_edit = pd.DataFrame()



    if not df_cli_edit.empty:

        df_cli_edit['Display'] = df_cli_edit['nome'] + " - " + df_cli_edit['telefone'].astype(str)

        escolha_edit = st.selectbox("Buscar:", ["Selecione..."] + df_cli_edit['Display'].tolist())

        

        if escolha_edit != "Selecione...":

            idx_edit = df_cli_edit[df_cli_edit['Display'] == escolha_edit].index[0]

            row_edit = df_cli_edit.iloc[idx_edit]

            linha_sheet_edit = idx_edit + 2

            

            with st.form("form_edicao"):

                c1, c2, c3 = st.columns(3)

                novo_nome = c1.text_input("Nome", value=row_edit['nome'])

                novo_tel = c2.text_input("Telefone", value=row_edit['telefone'])

                novos_pts = c3.number_input("Pontos", value=int(ler_numero_input(row_edit['compras'])), step=1)

                

                col_save, col_del = st.columns(2)

                if col_save.form_submit_button("💾 Salvar"):

                    sheet_clientes.update_cell(linha_sheet_edit, 1, novo_nome)

                    sheet_clientes.update_cell(linha_sheet_edit, 2, novo_tel)

                    sheet_clientes.update_cell(linha_sheet_edit, 3, novos_pts)

                    st.success("Atualizado!")

                    st.rerun()

                

                if col_del.form_submit_button("🗑️ EXCLUIR CLIENTE"):

                    sheet_clientes.delete_rows(int(linha_sheet_edit))

                    st.warning("Excluído!")

                    st.rerun()

    else: st.warning("Sem dados.")



# ==========================================

# 📊 RELATÓRIOS

# ==========================================

elif menu == "📊 Relatórios":

    st.title("📊 Relatórios")

    c1, c2 = st.columns(2)

    with c1: 

        st.subheader("Estoque")

        try: st.dataframe(pd.DataFrame(sheet_hist_est.get_all_records()), use_container_width=True, hide_index=True)

        except: st.write("Vazio")

    with c2:

        st.subheader("Fidelidade")

        try: st.dataframe(pd.DataFrame(sheet_hist_cli.get_all_records()), use_container_width=True, hide_index=True)

        except: st.write("Vazio")
