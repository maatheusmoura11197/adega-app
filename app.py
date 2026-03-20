importar streamlit como st
import pandas as pd
importar gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
importar re
from datetime import datetime, date
tempo de importação

# ==========================================
# âš™ï¸ CONFIGURAÃ‡ÃƒO E ESTILO
# ==========================================

ICON_URL = "https://splendid-plum-mslpekoeqx.edgeone.app/cerveja.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
    div.stButton > botão {{ background-color: #008CBA; color: white; font-weight: bold; border-radius: 10px; height: 3em; width: 100%; border: none; }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{ padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3; border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }}
    </style>
    <link rel="shortcut icon" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
    "", unsafe_allow_html=True)

# ==========================================
# ðŸ”' CONSTANTES — Centralizadas aqui, fáceis de manter
# ==========================================

TIPOS_PRODUTO = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
VOLUMES_ML = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
FORNECEDORES = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
PONTOS_PREMIO = 10

# ==========================================
# ðŸ” LOGIN & VARIÁVEIS DE SESSÃO
# ==========================================

#MELHORIA: Senha lida do secrets, não hardcoded no código
SENHA_DO_SISTEMA = st.secrets.get("SENHA_DO_SISTEMA", "adega123")

Se "logado" não estiver em st.session_state: st.session_state.logado = False
se "carrinho" não estiver em st.session_state: st.session_state.carrinho = []

se não st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>ðŸ”' Adega do Barão</h1>", unsafe_allow_html=True)
    _, col_centro, _ = st.columns([1, 2, 1])
    com col_centro:
        com st.form("login_form"):
            senha = st.text_input("Senha de Acesso:", type="password", placeholder="Digite e aperte Enter â†µ")
            if st.form_submit_button("ACESSAR SISTEMA"):
                se senha == SENHA_DO_SISTEMA:
                    st.success("âœ…Senha Correta!")
                    with st.spinner("Acessando Adega..."):
                        tempo.dormir(1)
                        st.session_state.logado = True
                        st.rerun()
                outro:
                    st.error("ðŸš«Senha incorreta!")
    st.stop()

# ==========================================
# ðŸ“¡ CONEXÃO COM GOOGLE SHEETS
# ==========================================

tentar:
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open("Fidelidade")
    planilha_clientes = planilha.worksheet("Página1")
    planilha_estoque = planilha.worksheet("Estoque")
    planilha_hist_est = planilha.worksheet("Histórico_Estoque")
    planilha_hist_cli = planilha.worksheet("Histórico")

    def garantir_cabecalhos():
        headers_padrao = ["Nome", "Tipo", "Fornecedor", "Custo", "Venda", "Estoque", "Dados Compra", "Qtd_Fardo", "ML"]
        tentar:
            atuais = sheet_estoque.row_values(1)
            se não atual ou len(atuais) < 9:
                para i, h em enumerate(headers_padrao):
                    sheet_estoque.update_cell(1, i + 1, h)
        exceto Exception como e:
            #MELHORIA: Erro visível em vez de passe silencioso
            st.warning(f"Não foi possível verificar os cabeços da planilha: {e}")

    @st.cache_data(ttl=15)
    def carregar_dados_estoque():
        tentar:
            retornar pd.DataFrame(sheet_estoque.get_all_records())
        exceto Exception como e:
            st.warning(f"Erro ao carregar estoque: {e}")
            retornar pd.DataFrame()

    @st.cache_data(ttl=15)
    def carregar_dados_clientes():
        tentar:
            retornar pd.DataFrame(sheet_clientes.get_all_records())
        exceto Exception como e:
            st.warning(f"Erro ao carregar clientes: {e}")
            retornar pd.DataFrame()

    @st.cache_data(ttl=15)
    def carregando_historico_cli():
        tentar:
            retornar pd.DataFrame(sheet_hist_cli.get_all_records())
        exceto Exception como e:
            st.warning(f"Erro ao carregar histórico de clientes: {e}")
            retornar pd.DataFrame()

    @st.cache_data(ttl=15)
    def carregando_historico_est():
        tentar:
            retornar pd.DataFrame(sheet_hist_est.get_all_records())
        exceto Exception como e:
            st.warning(f"Erro ao carregar histórico de estoque: {e}")
            retornar pd.DataFrame()

    def limpar_cache():
        carregar_dados_estoque.clear()
        carregar_dados_clientes.clear()
        carregar_historico_cli.clear()
        carregar_historico_est.clear()

    garantir_cabecalhos()

exceto Exception como e:
    st.error(f"Erro de conexão com o Planilhas Google: {e}")
    st.stop()

# ==========================================
# ðŸ› ï¸ FUNÃ‡Ã•ES UTILITÃ RIAS
# ==========================================

def conversor_para_numero(valor):
    """Converter string de valor monetário brasileiro para float."""
    se não for valor:
        retornar 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    se "," em v:
        v = v.replace(".", "").replace(",", ".")
    tentar:
        retornar float(v)
    exceto:
        retornar 0.0

def para_real_visual(valor):
    """Formato float para string no padrão R$ brasileiro."""
    retornar f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def salvar_com_ponto(valor):
    """Formato float com ponto decimal para salvar na planilha."""
    retornar "{:.2f}".format(valor)

def limpar_tel(telefone):
    """Remova tudo que não é para o dígito do telefone."""
    retornar re.sub(r'\D', '', str(telefone))

def calc_físico(total, ref_fardo):
    """Retorna string legível da quantidade em fardos e unidades."""
    se ref_fardo == 0:
        ref_fardo = 12
    fardos, unidades = divmod(total, ref_fardo)
    txt = ""
    se fardos > 0: txt += f"ðŸ“¦ {fardos} fardos "
    se unidades > 0: txt += f"ðŸ º {unidades} un"
    retornar txt se txt senão "Zerado"

def montar_nome_exibicao(df):
    """
    MELHORIA: Centraliza a criação da coluna Nome_Exibicao.
    Antes era repetido em 3 lugares diferentes no código.
    """
    se df.vazio:
        retornar df
    Se 'ML' não estiver em df.columns: df['ML'] = "-"
    Se 'Tipo' não estiver em df.columns: df['Tipo'] = "-"
    df['Nome_Exibicao'] = (
        df['Nome'].astype(str) + " - " +
        df['Tipo'].astype(str) + " (" +
        df['ML'].astype(str) + ")"
    )
    retornar df

def gerar_mensagem(nome_cliente, pontos):
    """Gera mensagem de WhatsApp de acordo com os pontos do cliente."""
    nome = nome_cliente.split()[0].capitalize()
    se pontos == 1:
        retornar (
            f"Oi, {nome}! âœ¨\nObrigado por comprar na Adega do Barão! "
            f"Já abriu seu Cartão Fidelidade. A cada {PONTOS_PREMIO} compras você ganha um prêmio!"
            f"Você garantiu o seu 1º ponto. Ah e não esquece de avaliar a gente no *JA PEDIU* ðŸ ·",
            "Enviar Boas-Vindas ðŸŽ‰"
        )
    elif 1 < pontos < PONTOS_PREMIO:
        retornar (
            f"E aÃ, {nome}! ðŸ'Š\nCompra registrada! Agora você tem *{pontos} pontos*. âœ¨\n"
            f"Faltam só {PONTOS_PREMIO - pontos} para o prêmio! Tamo junto! ðŸ »",
            f"Enviar Saldo ({pontos}/{PONTOS_PREMIO}) ðŸ“²"
        )
    outro:
        retornar (
            f"PARABÃ‰NS, {nome}!!! âœ¨ðŸ †\nVocê completou {PONTOS_PREMIO} pontos e ganhou um "
            f"**DESCONTO DE 20%** hoje! Aproveite! ðŸ¥³ðŸ ·",
            "ðŸ † ENVIAR PRÃŠMIO!"
        )

# ==========================================
# ðŸ“± MENU LATERAL
# ==========================================

com st.sidebar:
    st.title("ðŸ”§ Menu Principal")
    menu = st.radio("Navegar:", ["ðŸ'° Caixa", "ðŸ“¦ Estoque", "ðŸ'¥ Clientes", "ðŸ“Š HISTÓRICOS"])
    st.divider()
    se st.button("SAIR ðŸ“´"):
        st.session_state.logado = Falso
        st.rerun()

# ==========================================
# ðŸ“¦ ESTOQUE
# ==========================================

if menu == "ðŸ“¦ Estoque":
    st.title("ðŸ“¦ Gerenciamento de Estoque")

    df_est = carregar_dados_estoque()
    df_est = montar_nome_exibicao(df_est) # MELHORIA: função centralizada

    aba_estoque = st.radio(
        "Selecione a tela:",
        ["ðŸ“‹ Lista superior", "ðŸ†• Cadastrar Novo", "âœ ï¸ Editar/Excluir"],
        horizontal=Verdadeiro,
        visibilidade_do_rótulo="recolhido"
    )
    st.divider()

    # --- LISTA DETALHADA ---
    if aba_estoque == "ðŸ“‹ Lista superior":
        se df_est não estiver vazio:
            df_vis = df_est.copy()
            df_vis['custo_n'] = df_vis['Custo'].apply(converter_para_numero)
            df_vis['venda_n'] = df_vis['Venda'].apply(converter_para_numero)
            df_vis['Lucro Un.'] = df_vis['venda_n'] - df_vis['custo_n']
            df_vis['Custo (R$)'] = df_vis['custo_n'].apply(para_real_visual)
            df_vis['Venda (R$)'] = df_vis['venda_n'].apply(para_real_visual)
            df_vis['Lucro (R$)'] = df_vis['Lucro Un.'].apply(para_real_visual)
            df_vis['Físico'] = df_vis.apply(
                lambda r: calc_físico(
                    int(converter_para_numero(r['Estoque'])),
                    int(converter_para_numero(r.get('Qtd_Fardo', 12)))
                ), eixo=1
            )
            df_vis = df_vis.sort_values(by='Nome')
            st.dataframe(
                df_vis[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']],
                use_container_width=True
            )
        outro:
            st.info("O estoque está vazio.")

    # --- CADASTRAR NOVO ---
    elif aba_estoque == "ðŸ†• Cadastrar Novo":
        st.subheader("Cadastro Produto")
        com st.form("form_novo_produto", clear_on_submit=True):
            nome_produto = st.text_input("Nome do Produto :red[(Obrigatório)]:").upper()

            c_t1, c_t2 = st.columns(2)
            tipo_produto = c_t1.selectbox("Tipo:", TIPOS_PRODUTO) # MELHORIA: usa constante
            sel_ml = c_t2.selectbox("Volume (ML):", VOLUMES_ML) # MELHORIA: usa constante
            ml_custom = c_t2.text_input("Se escolheu 'Outros', digite o ML :red[(Obrigatório)]:")

            c1, c2 = st.columns(2)
            custo_input = c1.text_input("Custo Unitário R$ :red[(Obrigatório)]:", placeholder="0.00")
            text_input("Venda Unitária R$ :red[(Obrigatório)]:", placeholder="00.00")

            c3, c4 = st.columns(2)
            sel_forn = c3.selectbox("Fornecedor :red[(Obrigatório)]:", FORNECEDORES) # MELHORIA: usa constante
            forn_custom = c4.text_input("Se escolheu 'Outros', digite o Fornecedor :red[(Obrigatório)]:")

            data_compra = st.date_input("Dados Compra", date.today())
            st.divider()

            tipo_compra = st.radio("Formato da Compra:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
            col_a, col_b = st.columns(2)
            ref_fardo = col_a.number_input("Itens por Fardo (Ref):", valor=12)
            qtd_inicial = col_b.number_input("Qtd Fardos / Unidades:", min_value=0)

            if st.form_submit_button("âœ… PRODUTO CADASTRAR", type="primary"):
                fornecedor_final = forn_custom if sel_forn == "Outros" else sel_forn
                ml_final = ml_custom if sel_ml == "Outros" else sel_ml
                qtd_final = qtd_inicial * ref_fardo if tipo_compra == "Fardo Fechado" else qtd_inicial

                se não nome_produto ou não custo_input ou não_face_input ou não fornecedor_final:
                    st.error("Preencha todos os campos obrigatórios!")
                outro:
                    sheet_estoque.append_row([
                        nome_produto, tipo_produto, fornecedor_final,
                        salvar_com_ponto(converter_para_numero(custo_input)),
                        salvar_com_ponto(converter_para_numero(venda_input)),
                        qtd_final, data_compra.strftime('%d/%m/%Y'), ref_fardo, ml_final
                    ])
                    sheet_hist_est.append_row([
                        datetime.now().strftime('%d/%m/%Y %H:%M'),
                        nome_produto, "NOVO", qtd_final, fornecedor_final
                    ])
                    limpar_cache()
                    st.success(f"âœ… Produto '{nome_produto}' cadastrado!")

    # --- EDITAR / EXCLUIR ---
    elif aba_estoque == "âœ ï¸ Editar/Excluir":
        se df_est não estiver vazio:
            lista_prods = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            sel_e = st.selectbox("Seleção para Editar:", ["Seleção..."] + lista_prods)

            se sel_e != "Selecione...":
                idx = df_est[df_est['Nome_Exibicao'] == sel_e].index[0]
                linha = df_est.iloc[idx]

                com st.form(key=f"ed_form_{idx}", clear_on_submit=True):
                    novo_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:", value=str(row['Nome'])).upper()

                    c_tipo, c_ml = st.columns(2)
                    idx_t = TIPOS_PRODUTO.index(row['Tipo']) if row['Tipo'] em TIPOS_PRODUTO else 1
                    novo_tipo = c_tipo.selectbox("Tipo:", TIPOS_PRODUTO, index=idx_t) # MELHORIA: usa constante

                    idx_m = VOLUMES_ML.index(row['ML']) se row['ML'] estiver em VOLUMES_ML senão len(VOLUMES_ML) - 1
                    sel_ml_edit = c_ml.selectbox("Volume (ML):", VOLUMES_ML, index=idx_m) # MELHORIA: usa constante
                    ml_edit_custom = c_ml.text_input("Se 'Outros', digite o ML:", value=row['ML'] if sel_ml_edit == "Outros" else "")

                    c_a, c_b = st.columns(2)
                    text_input("Venda (R$):", valor=str(linha['Venda']))
                    custo_edit = c_b.text_input("Custo (R$):", value=str(row['Custo']))

                    c_f1, c_f2 = st.columns(2)
                    idx_f = FORNECEDORES.index(row['Fornecedor']) if row['Fornecedor'] em FORNECEDORES else len(FORNECEDORES) - 1
                    sel_forn_edit = c_f1.selectbox("Fornecedor:", FORNECEDORES, index=idx_f) # MELHORIA: usa constante
                    forn_edit_custom = c_f2.text_input("Se 'Outros', digite o Fornecedor:", value=row['Fornecedor'] if sel_forn_edit == "Outros" else "")

                    st.write("---")
                    estoque_atual_num = int(converter_para_numero(row['Estoque']))
                    ref_fardo_atual = int(converter_para_numero(row.get('Qtd_Fardo', 12)))
                    st.info(f"ðŸ“Š Estoque Atual: {calc_fisico(estoque_atual_num, ref_fardo_atual)} ({estoque_atual_num} unid.)")

                    e1, e2, e3 = st.columns(3)
                    estoque_editado = e1.number_input("Corrigir Total:", valor=estoque_atual_num)
                    adicionar_fardos = e2.number_input("âž• Novo Fardo:", min_value=0)
                    add_unidades = e3.number_input("âž• Nova Unid:", min_value=0)

                    b_sal, b_exc = st.columns(2)

                    if b_sal.form_submit_button("ðŸ'¾ SALVAR"):
                        fornecedor_final = forn_edit_custom if sel_forn_edit == "Outros" else sel_forn_edit
                        ml_final = ml_edit_custom if sel_ml_edit == "Outros" else sel_ml_edit
                        novo_total = estoque_editado + (add_fardos * ref_fardo_atual) + add_unidades

                        # MELHORIA: batch_update em vez de múltiplas chamadas update_cell
                        sheet_estoque.batch_update([
                            {"intervalo": f"A{idx+2}", "valores": [[novo_nome]]},
                            {"intervalo": f"B{idx+2}", "valores": [[novo_tipo]]},
                            {"range": f"C{idx+2}", "values": [[fornecedor_final]]},
                            {"intervalo": f"D{idx+2}", "valores": [[salvar_com_ponto(converter_para_numero(custo_edit))]]},
                            {"intervalo": f"E{idx+2}", "valores": [[salvar_com_ponto(converter_para_numero(venda_edit))]]},
                            {"range": f"F{idx+2}", "values": [[novo_total]]},
                            {"range": f"G{idx+2}", "values": [[date.today().strftime('%d/%m/%Y')]]},
                            {"range": f"I{idx+2}", "values": [[ml_final]]},
                        ])
                        limpar_cache()
                        st.success("Atualizado!")
                        tempo.dormir(1)
                        st.rerun()

                    if b_exc.form_submit_button("ðŸ—'ï¸ EXCLUIR", type="primary"):
                        planilha_estoque.delete_rows(int(idx + 2))
                        limpar_cache()
                        st.rerun()

# ==========================================
# ðŸ'° CAIXA & CARRINHO
# ==========================================

elif menu == "ðŸ'° Caixa":
    st.title("ðŸ'° Caixa & Fidelidade")

    # Tela pós-venda
    if st.session_state.get("venda_concluida"):
        st.success("Venda Realizada!")
        st.markdown(
            f'<a href="{st.session_state.link_whatsapp}" target="_blank" class="big-btn">'
            f'{st.session_state.botao_texto}</a>',
            unsafe_allow_html=True
        )
        se st.button("Nova Venda"):
            st.session_state.venda_concluida = Falso
            st.rerun()

    outro:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()
        df_est = montar_nome_exibicao(df_est) # MELHORIA: função centralizada

        # Seleção de cliente
        lista_clientes = (
            ["ðŸ†• NOVO"] + sorted((df_cli['nome'].astype(str) + " - " + df_cli['telefone'].astype(str)).tolist())
            se não df_cli.empty senão ["ðŸ†• NOVO"]
        )
        sel_cliente = st.selectbox("Cliente:", lista_clientes)
        c1, c2 = st.columns(2)

        if sel_cliente == "ðŸ†• NOVO":
            nome_cliente = c1.text_input("Nome:").upper()
            telefone_cliente = c2.text_input("Tel:")
        outro:
            nome_cliente = sel_cliente.split(" - ")[0]
            telefone_cliente = sel_cliente.split(" - ")[1]

        st.divider()

        # Seleção de produto
        se df_est não estiver vazio:
            lista_produtos = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            produto_selecionado = st.selectbox("Produto:", ["(Seleção...)"] + lista_produtos, key="p_caixa")

            if produto_selecionado != "(Seleção...)":
                row_produto = df_est[df_est['Nome_Exibicao'] == produto_selecionado].iloc[0]

                st.info(f"ðŸ'° Preço: {para_real_visual(converter_para_numero(row_produto['Venda']))} | Estoque: {row_produto['Estoque']}")

                q1, q2 = st.columns(2)
                qtd_fardos = q1.number_input("Fardos:", min_value=0, key="f_caixa")
                qtd_unidades = q2.number_input("Unid:", min_value=0, key="u_caixa")

                if st.button("➾ ADICIONAR"):
                    ref = int(converter_para_numero(row_produto.get('Qtd_Fardo', 12)))
                    baixa = (qtd_fardos * ref) + qtd_unidades

                    if int(row_produto['Estoque']) >= baixa > 0:
                        # MELHORIA: salva o nome do produto em vez do índice — evita bug de índice desincronizado
                        st.session_state.carrinho.append({
                            "Produto": produto_selecionado,
                            "nome_produto": row_produto['Nome'], # chave segura para busca na finalização
                            "Qtd": baixa,
                            "Preço": converter_para_numero(row_produto['Venda']),
                        })
                        st.rerun()
                    outro:
                        st.error("Qtd inválido ou estoque insuficiente.")
        outro:
            st.warning("âš ï¸ Cadastro de produtos no Estoque primeiro!")

        # Carrinho
        se st.session_state.carrinho:
            st.write("---")
            st.subheader("ðŸ› ï¸ Carrinho")
            df_car = pd.DataFrame(st.session_state.carrinho)
            st.table(df_car[['Produto', 'Qtd', 'Preço']])

            total = soma(item['Qtd'] * item['Preço'] para item em st.session_state.carrinho)
            st.subheader(f"Total: {para_real_visual(total)}")

            col_finalizar, col_limpar = st.columns(2)

            if col_limpar.button("Limpar Carrinho"):
                st.estado_sessão.carrinho = []
                st.rerun()

            if col_finalizar.button("âœ… FINALIZAR VENDA", type="primary"):
                with st.spinner("Finalizando..."):

                    # MELHORIA: busca produto pelo nome (seguro) e acumula linhas para lote
                    df_est_atual = carregar_dados_estoque()
                    df_est_atual = montar_nome_exibicao(df_est_atual)
                    linhas_hist_est = []

                    para item em st.session_state.carrinho:
                        # MELHORIA: busca segura pelo nome, não pelo índice
                        correspondências = df_est_atual[df_est_atual['Nome'] == item['nome_produto']]
                        se matches.empty:
                            st.error(f"Produto '{item['nome_produto']}' não encontrado na planilha!")
                            st.stop()

                        idx_prod = matches.index[0]
                        prod_row = matches.iloc[0]
                        novo_est = int(prod_row['Estoque']) - item['Qtd']

                        # MELHORIA: batch_update para atualizar estoque em 1 chamada por produto
                        planilha_estoque.update_cell(int(idx_prod + 2), 6, novo_est)

                        linhas_hist_est.append([
                            datetime.now().strftime('%d/%m/%Y %H:%M'),
                            item['Produto'], "VENDA",
                            item['Qtd'],
                            salvar_com_ponto(item['Qtd'] * item['Preço'])
                        ])

                    # MELHORIA: append_rows em vez de append_row em loop — 1 chamada só
                    sheet_hist_est.append_rows(linhas_hist_est)

                    # Atualiza pontos do cliente
                    telefone_limpo = limpar_tel(telefone_cliente)
                    pontos = 1

                    se df_cli não estiver vazio:
                        match_cli = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == telefone_limpo]
                        se não match_cli.empty:
                            idx_cli = match_cli.index[0]
                            pontos = int(match_cli.iloc[0]['compras']) + 1

                            se pontos > PONTOS_PREMIO:
                                # MELHORIA: zera após atingir prêmio, evita acúmulo infinito
                                pontos = 1

                            sheet_clientes.update_cell(int(idx_cli + 2), 3, pontos)
                        outro:
                            sheet_clientes.append_row([nome_cliente, telefone_limpo, 1, date.today().strftime('%d/%m/%Y')])
                    outro:
                        sheet_clientes.append_row([nome_cliente, telefone_limpo, 1, date.today().strftime('%d/%m/%Y')])

                    sheet_hist_cli.append_row([
                        datetime.now().strftime('%d/%m/%Y %H:%M'),
                        nome_cliente, telefone_limpo, pontos
                    ])

                    mensagem, texto_botao = gerar_mensagem(nome_cliente, pontos)
                    st.estado_sessão.carrinho = []
                    st.session_state.link_whatsapp = f"https://api.whatsapp.com/send?phone=55{telefone_limpo}&text={urllib.parse.quote(mensagem)}"
                    st.session_state.botao_texto = texto_botao # MELHORIA: nome claro
                    st.session_state.venda_concluida = Verdadeiro # MELHORIA: nome claro
                    limpar_cache()
                    st.rerun()

# ==========================================
# ðŸ'¥ CLIENTES
# ==========================================

menu elif == "ðŸ'¥ Clientes":
    st.title("ðŸ'¥ Gerenciar Clientes")
    df_c = carregar_dados_clientes()
    st.metric("Total de Clientes", len(df_c) if not df_c.empty else 0)

    aba_cli1, aba_cli2 = st.tabs(["ðŸ“‹ Lista", "âš™ï¸ Editar"])

    com aba_cli1:
        se df_c não estiver vazio:
            st.dataframe(df_c.sort_values('nome'), use_container_width=True)
        outro:
            st.info("Nenhum cliente cadastrado.")

    com aba_cli2:
        se df_c não estiver vazio:
            sel = st.selectbox("Cliente:", ["Seleção..."] + sorted(df_c['nome'].tolist()))
            se sel != "Selecione...":
                idx_cli = df_c[df_c['nome'] == sel].index[0]
                com st.form(f"cli_{idx_cli}"):
                    novo_nome = st.text_input("Nome:", valor=df_c.iloc[idx_cli]['nome'])
                    novo_tel = st.text_input("Tel:", value=str(df_c.iloc[idx_cli]['telefone']))
                    novos_pts = st.number_input("Pontos:", value=int(df_c.iloc[idx_cli]['compras']))
                    if st.form_submit_button("ðŸ'¾ Salvar"):
                        # MELHORIA: batch_update em vez de 3 update_cell separados
                        sheet_clientes.batch_update([
                            {"intervalo": f"A{idx_cli+2}", "valores": [[novo_nome]]},
                            {"range": f"B{idx_cli+2}", "values": [[novo_tel]]},
                            {"range": f"C{idx_cli+2}", "values": [[novos_pts]]},
                        ])
                        limpar_cache()
                        st.rerun()
        outro:
            st.info("Nenhum cliente cadastrado.")

# ==========================================
# ðŸ“Š HISTÓRICOS
# ==========================================

elif menu == "ðŸ“Š HISTÓRICOS":
    st.title("ðŸ“Š Relatórios")
    aba_h1, aba_h2 = st.tabs(["Clientes", "Estoque"])
    com aba_h1:
        st.dataframe(carregar_historico_cli(), use_container_width=True)
    com aba_h2:
        st.dataframe(carregar_historico_est(), use_container_width=True)
