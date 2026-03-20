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

ICON_URL = "https://splendid-plum-mslpekoeqx.edgeone.app/cerveja.png"
st.set_page_config(page_title="Adega do Barão", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
    div.stButton > button {{ background-color: #008CBA; color: white; font-weight: bold; border-radius: 10px; height: 3em; width: 100%; border: none; }}
    div.stButton > button[kind="primary"] {{ background-color: #FF0000 !important; }}
    .estoque-info {{ padding: 15px; background-color: #e3f2fd; border-left: 5px solid #2196f3; border-radius: 5px; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }}
    .big-btn {{ display: block; background-color: #25D366; color: white; font-weight: bold; text-align: center; padding: 14px; border-radius: 10px; text-decoration: none; font-size: 18px; margin-top: 10px; }}
    </style>
    <link rel="shortcut icon" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
""", unsafe_allow_html=True)

# ==========================================
# 🔒 CONSTANTES
# ==========================================

TIPOS_PRODUTO = ["GARRAFA 600ML", "LATA", "LITRÃO", "LONG NECK", "OUTROS"]
VOLUMES_ML    = ["200ml", "210ml", "269ml", "300ml", "330ml", "350ml", "473ml", "550ml", "600ml", "950ml", "1 Litro", "Outros"]
FORNECEDORES  = ["Ambev", "Daterra", "Jurerê", "Mix Matheus", "Zé Delivery", "Outros"]
PONTOS_PREMIO = 10

# ==========================================
# 🔑 LOGIN
# ==========================================

SENHA_DO_SISTEMA = st.secrets.get("SENHA_DO_SISTEMA", "adega123")

if "logado"   not in st.session_state: st.session_state.logado   = False
if "carrinho" not in st.session_state: st.session_state.carrinho = []

if not st.session_state.logado:
    st.markdown("<br><br><h1 style='text-align: center;'>🔒 Adega do Barão</h1>", unsafe_allow_html=True)

    # JavaScript para submeter o form ao pressionar Enter no campo de senha
    st.markdown("""
        <script>
        const waitField = setInterval(() => {
            const inputs = window.parent.document.querySelectorAll('input[type=password]');
            if (inputs.length > 0) {
                inputs[0].addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        const btns = window.parent.document.querySelectorAll('button[kind=primaryFormSubmit], button[data-testid=baseButton-secondaryFormSubmit], button');
                        for (const btn of btns) {
                            if (btn.innerText.includes('ACESSAR')) { btn.click(); break; }
                        }
                    }
                });
                clearInterval(waitField);
            }
        }, 300);
        </script>
    """, unsafe_allow_html=True)

    _, col_centro, _ = st.columns([1, 2, 1])
    with col_centro:
        with st.form("login_form"):
            senha = st.text_input("Senha de Acesso:", type="password", placeholder="Digite e aperte Enter ↵")
            if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True, type="primary"):
                if senha == SENHA_DO_SISTEMA:
                    st.success("✅ Senha Correta!")
                    with st.spinner("Acessando Adega..."):
                        time.sleep(1)
                        st.session_state.logado = True
                        st.rerun()
                else:
                    st.error("🚫 Senha incorreta!")
    st.stop()

# ==========================================
# 📡 CONEXÃO COM GOOGLE SHEETS
# ==========================================

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Fidelidade")

    # Mapeamento: chave interna → possíveis nomes na planilha (em ordem de preferência)
    NOMES_ABAS = {
        "clientes": ["Página1", "Pagina1", "página1", "pagina1", "Clientes", "clientes"],
        "estoque":  ["Estoque", "estoque", "Stock"],
        "hist_est": ["Historico_Estoque", "Histórico_Estoque", "Hist_Estoque", "hist_estoque", "Histórico Estoque"],
        "hist_cli": ["Historico", "Histórico", "histórico", "historico", "Hist_Clientes"],
    }

    # Cabeçalhos padrão para criação automática de abas
    HEADERS_ABAS = {
        "clientes": ["nome", "telefone", "compras", "data_cadastro"],
        "estoque":  ["Nome", "Tipo", "Fornecedor", "Custo", "Venda", "Estoque", "Data Compra", "Qtd_Fardo", "ML"],
        "hist_est": ["Data", "Produto", "Tipo", "Qtd", "Valor"],
        "hist_cli": ["Data", "Nome", "Telefone", "Pontos", "Valor_Pago"],
    }

    abas_existentes = {ws.title for ws in planilha.worksheets()}

    def obter_ou_criar_aba(chave):
        """Tenta encontrar a aba por vários nomes possíveis. Se não achar, cria com o nome padrão."""
        for nome in NOMES_ABAS[chave]:
            if nome in abas_existentes:
                return planilha.worksheet(nome)
        # Não encontrou — cria a aba com o nome padrão (primeiro da lista)
        nome_novo = NOMES_ABAS[chave][0]
        nova_aba  = planilha.add_worksheet(title=nome_novo, rows=1000, cols=20)
        nova_aba.append_row(HEADERS_ABAS[chave])
        st.toast(f"✅ Aba '{nome_novo}' criada automaticamente na planilha.", icon="📋")
        return nova_aba

    sheets = {
        "clientes": obter_ou_criar_aba("clientes"),
        "estoque":  obter_ou_criar_aba("estoque"),
        "hist_est": obter_ou_criar_aba("hist_est"),
        "hist_cli": obter_ou_criar_aba("hist_cli"),
    }

    def garantir_cabecalhos():
        headers_padrao = ["Nome", "Tipo", "Fornecedor", "Custo", "Venda", "Estoque", "Data Compra", "Qtd_Fardo", "ML"]
        try:
            atuais = sheets["estoque"].row_values(1)
            if not atuais or len(atuais) < 9:
                for i, h in enumerate(headers_padrao):
                    sheets["estoque"].update_cell(1, i + 1, h)
        except Exception as e:
            st.warning(f"Não foi possível verificar os cabeçalhos da planilha: {e}")

    @st.cache_data(ttl=10)
    def carregar_dados_estoque():
        try:
            return pd.DataFrame(sheets["estoque"].get_all_records())
        except Exception as e:
            st.warning(f"Erro ao carregar estoque: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=10)
    def carregar_dados_clientes():
        try:
            return pd.DataFrame(sheets["clientes"].get_all_records())
        except Exception as e:
            st.warning(f"Erro ao carregar clientes: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=10)
    def carregar_historico_cli():
        try:
            return pd.DataFrame(sheets["hist_cli"].get_all_records())
        except Exception as e:
            st.warning(f"Erro ao carregar histórico de clientes: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=10)
    def carregar_historico_est():
        try:
            return pd.DataFrame(sheets["hist_est"].get_all_records())
        except Exception as e:
            st.warning(f"Erro ao carregar histórico de estoque: {e}")
            return pd.DataFrame()

    def limpar_cache():
        carregar_dados_estoque.clear()
        carregar_dados_clientes.clear()
        carregar_historico_cli.clear()
        carregar_historico_est.clear()

    garantir_cabecalhos()

except Exception as e:
    st.error(f"Erro de conexão com o Google Sheets: {e}")
    st.stop()

# ==========================================
# 🛠️ FUNÇÕES UTILITÁRIAS
# ==========================================

def converter_para_numero(valor):
    """Converte string monetária brasileira para float."""
    if not valor:
        return 0.0
    v = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except:
        return 0.0

def para_real_visual(valor):
    """Formata float para R$ no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def salvar_com_ponto(valor):
    """Formata float com ponto decimal para salvar na planilha."""
    return "{:.2f}".format(valor)

def limpar_tel(telefone):
    """Remove tudo que não é dígito do telefone."""
    return re.sub(r'\D', '', str(telefone))

def calc_fisico(total, ref_fardo):
    """Retorna string legível da quantidade em fardos e unidades."""
    if ref_fardo == 0:
        ref_fardo = 12
    fardos, unidades = divmod(int(total), int(ref_fardo))
    txt = ""
    if fardos > 0:   txt += f"📦 {fardos} fardo(s) "
    if unidades > 0: txt += f"🍺 {unidades} un"
    return txt if txt else "Zerado"

def montar_nome_exibicao(df):
    """Centraliza a criação da coluna Nome_Exibicao."""
    if df.empty:
        return df
    if 'ML'   not in df.columns: df['ML']   = "-"
    if 'Tipo' not in df.columns: df['Tipo'] = "-"
    df['Nome_Exibicao'] = (
        df['Nome'].astype(str) + " - " +
        df['Tipo'].astype(str) + " (" +
        df['ML'].astype(str) + ")"
    )
    return df

def gerar_mensagem(nome_cliente, pontos):
    """Gera mensagem de WhatsApp de acordo com os pontos do cliente."""
    import random
    nome   = nome_cliente.split()[0].capitalize()
    faltam = PONTOS_PREMIO - pontos

    # --- 1º ponto: boas-vindas ---
    if pontos == 1:
        return (
            f"Oi, {nome}! 🍺 Seja bem-vindo à família Adega do Barão!\n"
            f"Seu cartão fidelidade está aberto e o primeiro ponto já foi carimbado. "
            f"A cada {PONTOS_PREMIO} compras você ganha um prêmio especial.\n"
            f"Fico feliz em ter você aqui! Se puder nos avaliar no *JA PEDIU*, a gente agradece muito 🙏",
            "Enviar Boas-Vindas 🎉"
        )

    # --- Quase lá: 8 ou 9 pontos ---
    elif pontos >= PONTOS_PREMIO - 2 and pontos < PONTOS_PREMIO:
        return (
            f"Ei, {nome}! 👀 *{pontos} pontos*... falta só {faltam} pro prêmio.\n"
            f"Dá quase pra sentir o cheirinho da recompensa, né? 😏🍻 Até a próxima!\n"
            f"E se ainda não nos avaliou no *JA PEDIU*, aproveita — leva só um segundo ⭐",
            f"Enviar Saldo ({pontos}/{PONTOS_PREMIO}) 📲"
        )

    # --- Meio do caminho: 2–7 pontos ---
    elif 1 < pontos < PONTOS_PREMIO:
        frases_incentivo = [
            "Cada compra tá te deixando mais perto do prêmio!",
            "Você tá indo muito bem, continua assim! 💪",
            "A Adega do Barão tá torcendo por você!",
            "Tamo junto nessa jornada rumo ao prêmio! 🙌",
        ]
        incentivo = random.choice(frases_incentivo)
        return (
            f"Obrigado pela visita, {nome}! 🙏\n"
            f"Mais um ponto no seu cartão — agora você tem *{pontos} de {PONTOS_PREMIO}*.\n"
            f"{incentivo} A Adega do Barão tá sempre te esperando! 🍺\n"
            f"Ah, se ainda não nos avaliou no *JA PEDIU*, aproveita e deixa suas estrelinhas pra gente ⭐",
            f"Enviar Saldo ({pontos}/{PONTOS_PREMIO}) 📲"
        )

    # --- Prêmio conquistado: 10 pontos ---
    else:
        return (
            f"PARABÉNS, {nome}!!! 🎉🏆\n"
            f"Você completou {PONTOS_PREMIO} pontos e conquistou seu prêmio!\n"
            f"Hoje você tem *20% de desconto* na Adega do Barão.\n"
            f"Pode chegar que a gente tá te esperando! 🥳🍷\n"
            f"E se curtiu a experiência, deixa sua avaliação no *JA PEDIU* pra gente 🙏⭐",
            "🏆 ENVIAR PRÊMIO!"
        )

def buscar_linha_real(sheet, nome_busca, coluna_nome=1):
    """
    Busca a linha real na planilha pelo nome do produto (não pelo índice do DataFrame).
    Evita o bug de índice dessincronizado quando o cache está desatualizado.
    Retorna o número da linha (1-based) ou None se não encontrar.
    """
    try:
        cell = sheet.find(nome_busca, in_column=coluna_nome)
        return cell.row if cell else None
    except Exception:
        return None

# ==========================================
# 📱 MENU LATERAL
# ==========================================

with st.sidebar:
    st.title("🔧 Menu Principal")
    menu = st.radio("Navegar:", ["💰 Caixa", "📦 Estoque", "👥 Clientes", "📊 HISTÓRICOS"])
    st.divider()
    if st.button("SAIR 🔴"):
        st.session_state.logado = False
        st.rerun()

# ==========================================
# 📦 ESTOQUE
# ==========================================

if menu == "📦 Estoque":
    st.title("📦 Gerenciamento de Estoque")

    df_est = carregar_dados_estoque()
    df_est = montar_nome_exibicao(df_est)

    aba_estoque = st.radio(
        "Selecione a tela:",
        ["📋 Lista geral", "🆕 Cadastrar Novo", "✏️ Editar/Excluir"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.divider()

    # --- LISTA DETALHADA ---
    if aba_estoque == "📋 Lista geral":
        if not df_est.empty:
            df_vis = df_est.copy()
            df_vis['custo_n'] = df_vis['Custo'].apply(converter_para_numero)
            df_vis['venda_n'] = df_vis['Venda'].apply(converter_para_numero)
            df_vis['Lucro Un.'] = df_vis['venda_n'] - df_vis['custo_n']
            df_vis['Custo (R$)'] = df_vis['custo_n'].apply(para_real_visual)
            df_vis['Venda (R$)'] = df_vis['venda_n'].apply(para_real_visual)
            df_vis['Lucro (R$)'] = df_vis['Lucro Un.'].apply(para_real_visual)
            df_vis['Físico'] = df_vis.apply(
                lambda r: calc_fisico(
                    converter_para_numero(r['Estoque']),
                    converter_para_numero(r.get('Qtd_Fardo', 12))
                ), axis=1
            )
            df_vis = df_vis.sort_values(by='Nome')
            st.dataframe(
                df_vis[['Nome', 'Tipo', 'ML', 'Físico', 'Custo (R$)', 'Venda (R$)', 'Lucro (R$)', 'Fornecedor', 'Data Compra']],
                use_container_width=True
            )
        else:
            st.info("O estoque está vazio.")

    # --- CADASTRAR NOVO ---
    elif aba_estoque == "🆕 Cadastrar Novo":
        st.subheader("Cadastro de Produto")
        with st.form("form_novo_produto", clear_on_submit=True):
            nome_produto = st.text_input("Nome do Produto :red[(Obrigatório)]:").upper()

            c_t1, c_t2 = st.columns(2)
            tipo_produto = c_t1.selectbox("Tipo:", TIPOS_PRODUTO)
            sel_ml       = c_t2.selectbox("Volume (ML):", VOLUMES_ML)
            ml_custom    = c_t2.text_input("Se escolheu 'Outros', digite o ML:")

            c1, c2 = st.columns(2)
            custo_input = c1.text_input("Custo Unitário R$ :red[(Obrigatório)]:", placeholder="0.00")
            venda_input = c2.text_input("Venda Unitária R$ :red[(Obrigatório)]:", placeholder="00.00")

            c3, c4 = st.columns(2)
            sel_forn   = c3.selectbox("Fornecedor :red[(Obrigatório)]:", FORNECEDORES)
            forn_custom = c4.text_input("Se escolheu 'Outros', digite o Fornecedor:")

            data_compra  = st.date_input("Data da Compra", date.today())
            st.divider()

            tipo_compra  = st.radio("Formato da Compra:", ["Fardo Fechado", "Unidades Soltas"], horizontal=True)
            col_a, col_b = st.columns(2)
            ref_fardo    = col_a.number_input("Itens por Fardo (Ref):", value=12)
            qtd_inicial  = col_b.number_input("Qtd Fardos / Unidades:", min_value=0)

            if st.form_submit_button("✅ CADASTRAR PRODUTO", type="primary"):
                fornecedor_final = forn_custom if sel_forn == "Outros" else sel_forn
                ml_final         = ml_custom   if sel_ml  == "Outros" else sel_ml
                qtd_final        = qtd_inicial * ref_fardo if tipo_compra == "Fardo Fechado" else qtd_inicial

                if not nome_produto or not custo_input or not venda_input or not fornecedor_final:
                    st.error("Preencha todos os campos obrigatórios!")
                else:
                    with st.spinner("Cadastrando produto..."):
                        sheets["estoque"].append_row([
                            nome_produto, tipo_produto, fornecedor_final,
                            salvar_com_ponto(converter_para_numero(custo_input)),
                            salvar_com_ponto(converter_para_numero(venda_input)),
                            qtd_final, data_compra.strftime('%d/%m/%Y'), ref_fardo, ml_final
                        ])
                        sheets["hist_est"].append_row([
                            datetime.now().strftime('%d/%m/%Y %H:%M'),
                            nome_produto, "NOVO", qtd_final, fornecedor_final
                        ])
                        limpar_cache()
                    st.success(f"✅ Produto '{nome_produto}' cadastrado com sucesso!")

    # --- EDITAR / EXCLUIR ---
    elif aba_estoque == "✏️ Editar/Excluir":
        if not df_est.empty:
            lista_prods = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            sel_e = st.selectbox("Selecione para Editar:", ["Selecione..."] + lista_prods)

            if sel_e != "Selecione...":
                idx  = df_est[df_est['Nome_Exibicao'] == sel_e].index[0]
                row  = df_est.iloc[idx]

                with st.form(key=f"ed_form_{idx}", clear_on_submit=True):
                    novo_nome = st.text_input("Nome do Produto :red[(Obrigatório)]:", value=str(row['Nome'])).upper()

                    c_tipo, c_ml = st.columns(2)
                    idx_t         = TIPOS_PRODUTO.index(row['Tipo']) if row['Tipo'] in TIPOS_PRODUTO else 0
                    novo_tipo     = c_tipo.selectbox("Tipo:", TIPOS_PRODUTO, index=idx_t)
                    idx_m         = VOLUMES_ML.index(row['ML']) if row['ML'] in VOLUMES_ML else len(VOLUMES_ML) - 1
                    sel_ml_edit   = c_ml.selectbox("Volume (ML):", VOLUMES_ML, index=idx_m)
                    ml_edit_custom = c_ml.text_input("Se 'Outros', digite o ML:", value=row['ML'] if sel_ml_edit == "Outros" else "")

                    c_a, c_b   = st.columns(2)
                    venda_edit = c_a.text_input("Venda (R$):", value=str(row['Venda']))
                    custo_edit = c_b.text_input("Custo (R$):", value=str(row['Custo']))

                    c_f1, c_f2  = st.columns(2)
                    idx_f        = FORNECEDORES.index(row['Fornecedor']) if row['Fornecedor'] in FORNECEDORES else len(FORNECEDORES) - 1
                    sel_forn_edit = c_f1.selectbox("Fornecedor:", FORNECEDORES, index=idx_f)
                    forn_edit_custom = c_f2.text_input("Se 'Outros', fornecedor:", value=row['Fornecedor'] if sel_forn_edit == "Outros" else "")

                    st.write("---")
                    estoque_atual_num = int(converter_para_numero(row['Estoque']))
                    ref_fardo_atual   = int(converter_para_numero(row.get('Qtd_Fardo', 12)))
                    st.info(f"📊 Estoque Atual: {calc_fisico(estoque_atual_num, ref_fardo_atual)} ({estoque_atual_num} unid.)")

                    e1, e2, e3     = st.columns(3)
                    estoque_editado = e1.number_input("Corrigir Total:", value=estoque_atual_num)
                    add_fardos      = e2.number_input("➕ Novo(s) Fardo(s):", min_value=0)
                    add_unidades    = e3.number_input("➕ Nova(s) Unid:", min_value=0)

                    b_sal, b_exc = st.columns(2)

                    if b_sal.form_submit_button("💾 SALVAR"):
                        fornecedor_final = forn_edit_custom if sel_forn_edit == "Outros" else sel_forn_edit
                        ml_final         = ml_edit_custom   if sel_ml_edit  == "Outros" else sel_ml_edit
                        novo_total       = estoque_editado + (add_fardos * ref_fardo_atual) + add_unidades

                        with st.spinner("Salvando alterações..."):
                            # Busca a linha real na planilha para evitar bug de índice dessincronizado
                            linha_real = buscar_linha_real(sheets["estoque"], str(row['Nome']))
                            if linha_real is None:
                                st.error("Produto não encontrado na planilha. Atualize a página e tente novamente.")
                            else:
                                sheets["estoque"].batch_update([
                                    {"range": f"A{linha_real}", "values": [[novo_nome]]},
                                    {"range": f"B{linha_real}", "values": [[novo_tipo]]},
                                    {"range": f"C{linha_real}", "values": [[fornecedor_final]]},
                                    {"range": f"D{linha_real}", "values": [[salvar_com_ponto(converter_para_numero(custo_edit))]]},
                                    {"range": f"E{linha_real}", "values": [[salvar_com_ponto(converter_para_numero(venda_edit))]]},
                                    {"range": f"F{linha_real}", "values": [[novo_total]]},
                                    {"range": f"G{linha_real}", "values": [[date.today().strftime('%d/%m/%Y')]]},
                                    {"range": f"I{linha_real}", "values": [[ml_final]]},
                                ])
                                limpar_cache()
                                st.success("✅ Produto atualizado!")
                                time.sleep(1)
                                st.rerun()

                    # Exclusão com confirmação em 2 cliques
                    if b_exc.form_submit_button("🗑️ EXCLUIR", type="primary"):
                        st.session_state[f"confirmar_exclusao_{idx}"] = True

                # Confirmação fora do form para evitar resubmit
                if st.session_state.get(f"confirmar_exclusao_{idx}"):
                    st.warning(f"⚠️ Tem certeza que deseja excluir **{row['Nome']}**? Esta ação não pode ser desfeita.")
                    c_sim, c_nao = st.columns(2)
                    if c_sim.button("✅ SIM, EXCLUIR", type="primary"):
                        with st.spinner("Excluindo..."):
                            linha_real = buscar_linha_real(sheets["estoque"], str(row['Nome']))
                            if linha_real:
                                sheets["estoque"].delete_rows(linha_real)
                            limpar_cache()
                        st.session_state.pop(f"confirmar_exclusao_{idx}", None)
                        st.rerun()
                    if c_nao.button("❌ Cancelar"):
                        st.session_state.pop(f"confirmar_exclusao_{idx}", None)
                        st.rerun()
        else:
            st.info("Estoque vazio. Cadastre produtos primeiro.")

# ==========================================
# 💰 CAIXA & CARRINHO
# ==========================================

elif menu == "💰 Caixa":
    st.title("💰 Caixa & Fidelidade")

    # Tela pós-venda
    if st.session_state.get("venda_concluida"):
        st.success("✅ Venda Realizada com Sucesso!")
        st.markdown(
            f'<a href="{st.session_state.link_whatsapp}" target="_blank" class="big-btn">'
            f'{st.session_state.botao_texto}</a>',
            unsafe_allow_html=True
        )
        if st.button("🛒 Nova Venda"):
            st.session_state.venda_concluida = False
            st.rerun()

    else:
        df_cli = carregar_dados_clientes()
        df_est = carregar_dados_estoque()
        df_est = montar_nome_exibicao(df_est)

        # Seleção de cliente
        lista_clientes = (
            ["🆕 NOVO"] + sorted((df_cli['nome'].astype(str) + " - " + df_cli['telefone'].astype(str)).tolist())
            if not df_cli.empty else ["🆕 NOVO"]
        )
        sel_cliente = st.selectbox("Cliente:", lista_clientes)
        c1, c2 = st.columns(2)

        if sel_cliente == "🆕 NOVO":
            nome_cliente     = c1.text_input("Nome:").upper()
            telefone_cliente = c2.text_input("Tel:", placeholder="(85) 99999-9999")
        else:
            nome_cliente     = sel_cliente.split(" - ")[0]
            telefone_cliente = sel_cliente.split(" - ")[1]

        # Mostra pontos atuais do cliente selecionado
        if sel_cliente != "🆕 NOVO" and not df_cli.empty:
            tel_limpo   = limpar_tel(telefone_cliente)
            match_atual = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tel_limpo]
            if not match_atual.empty:
                pts_atuais = int(match_atual.iloc[0]['compras'])
                faltam     = PONTOS_PREMIO - pts_atuais
                st.info(f"⭐ {nome_cliente} tem **{pts_atuais}/{PONTOS_PREMIO}** pontos. Faltam {faltam} para o prêmio.")
                if pts_atuais >= PONTOS_PREMIO:
                    st.success("🏆 Cliente com PRÊMIO disponível! Aplicar 20% de desconto.")

        st.divider()

        # Seleção de produto
        if not df_est.empty:
            lista_produtos   = sorted(df_est['Nome_Exibicao'].astype(str).tolist())
            produto_selecionado = st.selectbox("Produto:", ["(Selecione...)"] + lista_produtos, key="p_caixa")

            if produto_selecionado != "(Selecione...)":
                row_produto = df_est[df_est['Nome_Exibicao'] == produto_selecionado].iloc[0]
                preco_unit  = converter_para_numero(row_produto['Venda'])
                estoque_disp = int(converter_para_numero(row_produto['Estoque']))

                st.info(f"💰 Preço: {para_real_visual(preco_unit)} | Estoque: {estoque_disp} unid.")

                q1, q2        = st.columns(2)
                qtd_fardos    = q1.number_input("Fardos:", min_value=0, key="f_caixa")
                qtd_unidades  = q2.number_input("Unid:", min_value=0, key="u_caixa")

                if st.button("➕ ADICIONAR AO CARRINHO"):
                    ref   = int(converter_para_numero(row_produto.get('Qtd_Fardo', 12)))
                    baixa = (qtd_fardos * ref) + qtd_unidades

                    if estoque_disp >= baixa > 0:
                        st.session_state.carrinho.append({
                            "Produto":      produto_selecionado,
                            "nome_produto": row_produto['Nome'],
                            "Qtd":          baixa,
                            "Preço":        preco_unit,
                        })
                        st.rerun()
                    else:
                        st.error("Quantidade inválida ou estoque insuficiente.")
        else:
            st.warning("⚠️ Cadastre produtos no Estoque primeiro!")

        # Carrinho
        if st.session_state.carrinho:
            st.write("---")
            st.subheader("🛒 Carrinho")
            df_car = pd.DataFrame(st.session_state.carrinho)
            st.table(df_car[['Produto', 'Qtd', 'Preço']])

            total_bruto = sum(item['Qtd'] * item['Preço'] for item in st.session_state.carrinho)

            # Verifica se cliente tem prêmio e aplica desconto automaticamente
            cliente_com_premio = False
            if sel_cliente != "🆕 NOVO" and not df_cli.empty:
                tel_limpo   = limpar_tel(telefone_cliente)
                match_atual = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == tel_limpo]
                if not match_atual.empty and int(match_atual.iloc[0]['compras']) >= PONTOS_PREMIO:
                    cliente_com_premio = True

            if cliente_com_premio:
                desconto    = total_bruto * 0.20
                total_final = total_bruto - desconto
                st.success(f"🏆 Desconto de 20% aplicado! De {para_real_visual(total_bruto)} por **{para_real_visual(total_final)}**")
            else:
                total_final = total_bruto

            st.subheader(f"Total: {para_real_visual(total_final)}")

            col_finalizar, col_limpar = st.columns(2)

            if col_limpar.button("🗑️ Limpar Carrinho"):
                st.session_state.carrinho = []
                st.rerun()

            if col_finalizar.button("✅ FINALIZAR VENDA", type="primary"):
                if not nome_cliente or not telefone_cliente:
                    st.error("Informe o nome e telefone do cliente antes de finalizar.")
                else:
                    with st.spinner("Finalizando venda..."):
                        df_est_atual = carregar_dados_estoque()
                        df_est_atual = montar_nome_exibicao(df_est_atual)
                        linhas_hist_est = []
                        erro_estoque    = False

                        for item in st.session_state.carrinho:
                            # Busca segura pelo nome real na planilha
                            linha_real = buscar_linha_real(sheets["estoque"], item['nome_produto'])
                            if linha_real is None:
                                st.error(f"Produto '{item['nome_produto']}' não encontrado na planilha!")
                                erro_estoque = True
                                break

                            # Lê estoque atual diretamente (ignora cache)
                            estoque_cell = sheets["estoque"].cell(linha_real, 6).value
                            est_atual    = int(converter_para_numero(estoque_cell))
                            novo_est     = est_atual - item['Qtd']

                            sheets["estoque"].update_cell(linha_real, 6, novo_est)

                            linhas_hist_est.append([
                                datetime.now().strftime('%d/%m/%Y %H:%M'),
                                item['Produto'], "VENDA",
                                item['Qtd'],
                                salvar_com_ponto(item['Qtd'] * item['Preço'])
                            ])

                        if not erro_estoque:
                            # Salva histórico de estoque em lote (1 chamada só)
                            if linhas_hist_est:
                                sheets["hist_est"].append_rows(linhas_hist_est)

                            # Atualiza pontos do cliente
                            telefone_limpo = limpar_tel(telefone_cliente)
                            pontos = 1

                            if not df_cli.empty:
                                match_cli = df_cli[df_cli['telefone'].astype(str).apply(limpar_tel) == telefone_limpo]
                                if not match_cli.empty:
                                    idx_cli     = match_cli.index[0]
                                    pontos_ant  = int(match_cli.iloc[0]['compras'])
                                    pontos      = pontos_ant + 1

                                    if pontos > PONTOS_PREMIO:
                                        pontos = 1  # Zera após o prêmio

                                    # Busca linha real do cliente para evitar bug de índice
                                    linha_cli = buscar_linha_real(sheets["clientes"], match_cli.iloc[0]['nome'])
                                    if linha_cli:
                                        sheets["clientes"].update_cell(linha_cli, 3, pontos)
                                    else:
                                        sheets["clientes"].append_row([nome_cliente, telefone_limpo, pontos, date.today().strftime('%d/%m/%Y')])
                                else:
                                    sheets["clientes"].append_row([nome_cliente, telefone_limpo, 1, date.today().strftime('%d/%m/%Y')])
                            else:
                                sheets["clientes"].append_row([nome_cliente, telefone_limpo, 1, date.today().strftime('%d/%m/%Y')])

                            sheets["hist_cli"].append_row([
                                datetime.now().strftime('%d/%m/%Y %H:%M'),
                                nome_cliente, telefone_limpo, pontos,
                                salvar_com_ponto(total_final)  # salva o valor real pago
                            ])

                            mensagem, texto_botao = gerar_mensagem(nome_cliente, pontos)
                            st.session_state.carrinho       = []
                            st.session_state.link_whatsapp  = f"https://api.whatsapp.com/send?phone=55{telefone_limpo}&text={urllib.parse.quote(mensagem)}"
                            st.session_state.botao_texto    = texto_botao
                            st.session_state.venda_concluida = True
                            limpar_cache()
                            st.rerun()

# ==========================================
# 👥 CLIENTES
# ==========================================

elif menu == "👥 Clientes":
    st.title("👥 Gerenciar Clientes")
    df_c = carregar_dados_clientes()
    st.metric("Total de Clientes", len(df_c) if not df_c.empty else 0)

    aba_cli1, aba_cli2 = st.tabs(["📋 Lista", "⚙️ Editar"])

    with aba_cli1:
        if not df_c.empty:
            st.dataframe(df_c.sort_values('nome'), use_container_width=True)
        else:
            st.info("Nenhum cliente cadastrado.")

    with aba_cli2:
        if not df_c.empty:
            sel = st.selectbox("Cliente:", ["Selecione..."] + sorted(df_c['nome'].tolist()))
            if sel != "Selecione...":
                idx_cli = df_c[df_c['nome'] == sel].index[0]
                with st.form(f"cli_{idx_cli}"):
                    novo_nome = st.text_input("Nome:", value=str(df_c.iloc[idx_cli]['nome']))
                    novo_tel  = st.text_input("Tel:", value=str(df_c.iloc[idx_cli]['telefone']))
                    novos_pts = st.number_input("Pontos:", value=int(df_c.iloc[idx_cli]['compras']), min_value=0, max_value=PONTOS_PREMIO)
                    if st.form_submit_button("💾 Salvar"):
                        with st.spinner("Salvando..."):
                            linha_cli = buscar_linha_real(sheets["clientes"], str(df_c.iloc[idx_cli]['nome']))
                            if linha_cli:
                                sheets["clientes"].batch_update([
                                    {"range": f"A{linha_cli}", "values": [[novo_nome]]},
                                    {"range": f"B{linha_cli}", "values": [[novo_tel]]},
                                    {"range": f"C{linha_cli}", "values": [[novos_pts]]},
                                ])
                                limpar_cache()
                                st.success("✅ Cliente atualizado!")
                                st.rerun()
                            else:
                                st.error("Cliente não encontrado na planilha.")
        else:
            st.info("Nenhum cliente cadastrado.")

# ==========================================
# 📊 HISTÓRICOS
# ==========================================

elif menu == "📊 HISTÓRICOS":
    st.title("📊 Relatórios e Históricos")
    aba_h1, aba_h2 = st.tabs(["👥 Clientes", "📦 Estoque"])

    with aba_h1:
        df_hc = carregar_historico_cli()
        if not df_hc.empty:
            # Filtro por data para não travar com muitos registros
            st.subheader("Filtrar por período")
            col_d1, col_d2 = st.columns(2)
            data_ini = col_d1.date_input("De:", value=date.today().replace(day=1))
            data_fim = col_d2.date_input("Até:", value=date.today())

            # Tenta filtrar pela coluna de data (primeira coluna)
            try:
                col_data = df_hc.columns[0]
                df_hc[col_data] = pd.to_datetime(df_hc[col_data], dayfirst=True, errors='coerce')
                df_filtrado = df_hc[
                    (df_hc[col_data].dt.date >= data_ini) &
                    (df_hc[col_data].dt.date <= data_fim)
                ]
                st.dataframe(df_filtrado, use_container_width=True)
                st.caption(f"{len(df_filtrado)} registros no período selecionado.")
            except Exception:
                st.dataframe(df_hc.tail(200), use_container_width=True)
                st.caption("Exibindo os 200 registros mais recentes.")
        else:
            st.info("Nenhum histórico de clientes.")

    with aba_h2:
        df_he = carregar_historico_est()
        if not df_he.empty:
            st.subheader("Filtrar por período")
            col_d1, col_d2 = st.columns(2)
            data_ini2 = col_d1.date_input("De:", value=date.today().replace(day=1), key="est_ini")
            data_fim2 = col_d2.date_input("Até:", value=date.today(), key="est_fim")

            try:
                col_data2 = df_he.columns[0]
                df_he[col_data2] = pd.to_datetime(df_he[col_data2], dayfirst=True, errors='coerce')
                df_filtrado2 = df_he[
                    (df_he[col_data2].dt.date >= data_ini2) &
                    (df_he[col_data2].dt.date <= data_fim2)
                ]
                st.dataframe(df_filtrado2, use_container_width=True)
                st.caption(f"{len(df_filtrado2)} registros no período selecionado.")
            except Exception:
                st.dataframe(df_he.tail(200), use_container_width=True)
                st.caption("Exibindo os 200 registros mais recentes.")
        else:
            st.info("Nenhum histórico de estoque.")
