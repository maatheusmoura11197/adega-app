import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 
import re 
from datetime import datetime
import pytz 

# --- 🔗 LINK DA SUA PLANILHA ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/SEU_ID_DA_PLANILHA_AQUI" 

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Fidelidade Adega", page_icon="🍷", layout="centered")
st.title("🍷 Fidelidade Adega Online")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Menu Rápido")
    if "docs.google.com" in URL_PLANILHA:
        st.link_button("📂 Abrir Planilha Google", URL_PLANILHA)
    st.info("💡 Dica: Agora ao excluir um cliente, o histórico dele também é apagado automaticamente.")

# --- CONEXÃO COM O GOOGLE SHEETS ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    
    # ABAS
    sheet_resumo = client.open("Fidelidade").worksheet("Página1") 
    try:
        sheet_historico = client.open("Fidelidade").worksheet("Historico")
    except:
        st.error("⚠️ Crie uma aba chamada 'Historico' na planilha!")
        st.stop()
    conexao = True
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")
    conexao = False

# --- FUNÇÕES ÚTEIS ---
def limpar_telefone(tel_completo):
    return re.sub(r'\D', '', tel_completo)

def pegar_data_hora():
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

def registrar_historico(nome, telefone, acao, valor=0.0):
    data = pegar_data_hora()
    # Adicionando o valor na coluna 5
    sheet_historico.append_row([data, nome, telefone, acao, valor])

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

# --- ESTADO DA SESSÃO ---
if 'confirmacao' not in st.session_state: st.session_state.confirmacao = False
if 'dados_temp' not in st.session_state: st.session_state.dados_temp = {}
if 'sucesso_msg' not in st.session_state: st.session_state.sucesso_msg = None
if 'nome_auto' not in st.session_state: st.session_state.nome_auto = ""
if 'tel_auto' not in st.session_state: st.session_state.tel_auto = ""

# --- CARREGAR DADOS ---
if conexao:
    todos_dados = sheet_resumo.get_all_records()
    df = pd.DataFrame(todos_dados)
else:
    df = pd.DataFrame()

# ==========================================
# 📊 PAINEL DO PATRÃO
# ==========================================
if not df.empty and conexao:
    st.markdown("### 📊 Visão Geral")
    col1, col2, col3 = st.columns(3)
    
    total_clientes = len(df)
    try:
        total_pontos = df['compras'].sum()
        # Tenta calcular faturamento se a coluna existir
        total_faturado = df['total_gasto'].sum() if 'total_gasto' in df.columns else 0.0
    except:
        total_pontos = 0
        total_faturado = 0.0

    col1.metric("Clientes", total_clientes)
    col2.metric("Pontos Dados", total_pontos)
    col3.metric("Faturamento", f"R$ {total_faturado:,.2f}")
    st.divider()

# ==========================================
# 📋 IMPORTADOR
# ==========================================
with st.expander("📋 Importar do Pedido (Copiar e Colar)"):
    texto_pedido = st.text_area("Cole aqui o texto do pedido:", height=80)
    if st.button("🔍 Extrair Dados"):
        if texto_pedido:
            # Busca Telefone
            candidatos = re.findall(r'[\d\+\(\)\-\s]{8,20}', texto_pedido)
            telefone_achado = ""
            for item in candidatos:
                apenas_nums = re.sub(r'\D', '', item)
                if 10 <= len(apenas_nums) <= 13:
                    telefone_achado = apenas_nums[-11:] # Pega sempre DDD+9+Num
                    if len(apenas_nums) >= 11: break 
            
            if telefone_achado: st.session_state.tel_auto = telefone_achado
            
            # Busca Nome
            linhas = texto_pedido.split('\n')
            nome_achado = ""
            for linha in linhas:
                if "Cliente:" in linha or "Nome:" in linha:
                    nome_achado = linha.replace("Cliente:", "").replace("Nome:", "").strip().upper()
                    break
            if not nome_achado:
                for linha in linhas:
                    if len(linha.strip()) > 3 and not linha.strip().isdigit():
                        nome_achado = linha.strip().upper()
                        break
            if nome_achado: st.session_state.nome_auto = nome_achado
            st.rerun()

# ==========================================
# 📝 REGISTRO DE VENDA
# ==========================================
st.subheader("📝 Novo Registro")
nome_inicial = st.session_state.nome_auto
tel_inicial = st.session_state.tel_auto

nome = st.text_input("Nome do Cliente", value=nome_inicial).strip().upper()

st.write("📞 Telefone")
col_ddi, col_num = st.columns([0.2, 0.8])
with col_ddi: st.text_input("DDI", value="+55", disabled=True, label_visibility="collapsed")

if tel_inicial and len(tel_inicial) == 11:
    tel_visual = f"{tel_inicial[:2]} {tel_inicial[2:7]}-{tel_inicial[7:]}"
else:
    tel_visual = tel_inicial

with col_num:
    numero_digitado = st.text_input("Número", value=tel_visual, placeholder="88 99999-0000", label_visibility="collapsed")

# CAMPO DE VALOR (NOVO)
valor_compra = st.number_input("Valor da Compra (R$)", min_value=0.0, step=1.0, format="%.2f")

# Limpeza
num_limpo = limpar_telefone(numero_digitado)
if num_limpo.startswith("55") and len(num_limpo) > 11: num_limpo = num_limpo[2:]
tel_salvar = "55" + num_limpo

if st.button("Verificar e Registar", type="primary"):
    valido = len(num_limpo) >= 10
    if (nome or valido) and conexao:
        st.session_state.sucesso_msg = None 
        cli_encontrado = pd.DataFrame()

        if not df.empty:
            df['telefone'] = df['telefone'].astype(str)
            if valido:
                match = df[df['telefone'].str.endswith(num_limpo)]
                if not match.empty: cli_encontrado = match
            if cli_encontrado.empty and nome:
                match = df[df['nome'] == nome]
                if not match.empty: cli_encontrado = match

        if not cli_encontrado.empty:
            # JÁ EXISTE
            dados = cli_encontrado.iloc[0]
            idx = cli_encontrado.index[0]
            # Pega gasto antigo (trata erro se coluna nao existir)
            gasto_ant = float(dados['total_gasto']) if 'total_gasto' in dados else 0.0
            
            st.session_state.dados_temp = {
                'indice': idx,
                'nome_antigo': dados['nome'],
                'nome_novo': nome if nome else dados['nome'],
                'telefone': str(dados['telefone']),
                'compras_atuais': dados['compras'],
                'gasto_atual': gasto_ant,
                'novo_valor': valor_compra
            }
            st.session_state.confirmacao = True
            st.rerun()
        else:
            # NOVO
            if valido and nome:
                data = pegar_data_hora()
                # Colunas: Nome | Tel | Compras | Data | Total Gasto
                sheet_resumo.append_row([nome, tel_salvar, 1, data, valor_compra])
                registrar_historico(nome, tel_salvar, "Cadastro + Compra", valor_compra)
                
                msg, btn = gerar_mensagem_zap(nome, 1)
                link = f"https://api.whatsapp.com/send?phone={tel_salvar}&text={urllib.parse.quote(msg)}"
                st.session_state.sucesso_msg = {'texto': f"🎉 {nome} cadastrado!", 'link': link, 'btn_label': btn}
                st.rerun()
            else:
                st.warning("Preencha Nome e Telefone para novos.")

# --- CONFIRMAÇÃO ---
if st.session_state.confirmacao:
    d = st.session_state.dados_temp
    st.divider()
    st.warning(f"🚨 **CLIENTE ENCONTRADO:** {d['nome_antigo']}")
    st.info(f"Adicionar compra de R$ {d['novo_valor']:.2f}?")
    
    c1, c2 = st.columns(2)
    if c1.button("✅ SIM"):
        with st.spinner('Atualizando...'):
            linha = int(d['indice']) + 2
            novo_total = int(d['compras_atuais']) + 1
            novo_gasto = d['gasto_atual'] + d['novo_valor']
            data = pegar_data_hora()
            
            sheet_resumo.update_cell(linha, 1, d['nome_novo'])
            sheet_resumo.update_cell(linha, 3, novo_total)
            sheet_resumo.update_cell(linha, 4, data)
            sheet_resumo.update_cell(linha, 5, novo_gasto) # Atualiza dinheiro
            
            registrar_historico(d['nome_novo'], d['telefone'], f"Compra (+1)", d['novo_valor'])
            
            msg, btn = gerar_mensagem_zap(d['nome_novo'], novo_total)
            link = f"https://api.whatsapp.com/send?phone={d['telefone']}&text={urllib.parse.quote(msg)}"
            st.session_state.sucesso_msg = {'texto': f"✅ Atualizado!", 'link': link, 'btn_label': btn, 'salao_festa': (novo_total>=10)}
            
            if novo_total >= 10:
                registrar_historico(d['nome_novo'], d['telefone'], "🏆 PRÉMIO LIBERADO", 0)
            
            st.session_state.confirmacao = False
            st.rerun()
    
    if c2.button("❌ Não"):
        st.session_state.confirmacao = False
        st.rerun()

# --- SUCESSO ---
if st.session_state.sucesso_msg:
    r = st.session_state.sucesso_msg
    st.divider()
    st.success(r['texto'])
    if r.get('salao_festa'): st.balloons()
    st.markdown(f"""<a href="{r['link']}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">{r['btn_label']}</div></a>""", unsafe_allow_html=True)
    if st.button("🔄 Novo Atendimento"):
        st.session_state.sucesso_msg = None
        st.rerun()

# ==========================================
# 🛠️ GESTÃO & EXCLUSÃO (COM LIMPEZA TOTAL)
# ==========================================
st.markdown("---")
st.subheader("🛠️ Gerenciar Clientes")

if not df.empty and conexao:
    df['rotulo'] = df['nome'] + " - " + df['telefone'].astype(str)
    
    # Busca por texto para facilitar encontrar na lista
    busca_cli = st.text_input("Filtrar cliente na lista:", placeholder="Digite o nome...")
    
    lista_filtrada = df['rotulo'].tolist()
    if busca_cli:
        lista_filtrada = [c for c in lista_filtrada if busca_cli.upper() in c.upper()]
        
    cliente_selecionado = st.selectbox("Selecione o Cliente:", [""] + lista_filtrada)

    if cliente_selecionado:
        idx = df[df['rotulo'] == cliente_selecionado].index[0]
        dados_cli = df.iloc[idx]
        linha_sheet = int(idx) + 2 
        
        st.info(f"Editando: **{dados_cli['nome']}** | Pontos: {dados_cli['compras']}")
        
        with st.form("form_edicao"):
            c1, c2 = st.columns(2)
            novo_nome = c1.text_input("Nome", value=dados_cli['nome'])
            novo_pts = c2.number_input("Pontos", value=int(dados_cli['compras']))
            
            st.markdown("### 🚫 Área de Perigo")
            senha = st.text_input("Senha para Excluir", type="password")
            
            col_s, col_d = st.columns(2)
            salvar = col_s.form_submit_button("💾 Salvar")
            excluir = col_d.form_submit_button("🗑️ EXCLUIR TUDO", type="primary")

        if salvar:
            sheet_resumo.update_cell(linha_sheet, 1, novo_nome.upper())
            sheet_resumo.update_cell(linha_sheet, 3, novo_pts)
            st.success("Salvo!")
            st.rerun()

        if excluir:
            if senha == "1234": # SENHA DO PATRÃO
                st.session_state.exclusao_pendente = {
                    'linha': linha_sheet,
                    'nome': dados_cli['nome'],
                    'tel': str(dados_cli['telefone'])
                }
                st.rerun()
            else:
                st.error("Senha incorreta.")

    # CONFIRMAÇÃO DE EXCLUSÃO TOTAL
    if 'exclusao_pendente' in st.session_state:
        dados_del = st.session_state.exclusao_pendente
        st.error(f"⚠️ ATENÇÃO: Isso vai apagar {dados_del['nome']} do cadastro E TODO O HISTÓRICO DELE.")
        
        c1, c2 = st.columns(2)
        if c1.button("SIM, APAGAR TUDO"):
            with st.spinner("Apagando rastros..."):
                # 1. Apaga do Resumo (Principal)
                sheet_resumo.delete_rows(dados_del['linha'])
                
                # 2. Apaga do Histórico (Varredura Completa)
                # Baixa tudo do histórico, filtra quem NÃO é esse telefone e sobe de volta
                try:
                    todos_hist = sheet_historico.get_all_records()
                    # Mantém apenas os registros que tem telefone DIFERENTE do excluído
                    novo_historico = [h for h in todos_hist if str(h['Telefone']) != dados_del['tel']]
                    
                    # Limpa a aba histórico inteira
                    sheet_historico.clear()
                    # Recoloca o cabeçalho
                    sheet_historico.append_row(['Data', 'Nome', 'Telefone', 'Ação', 'Valor'])
                    # Recoloca os dados filtrados
                    if novo_historico:
                        # Prepara lista de listas para subir rápido
                        lista_upload = [[h['Data'], h['Nome'], h['Telefone'], h['Ação'], h.get('Valor', 0)] for h in novo_historico]
                        sheet_historico.append_rows(lista_upload)
                        
                except Exception as e:
                    st.error(f"Erro ao limpar histórico: {e}")

                st.success("Cliente removido completamente.")
                del st.session_state.exclusao_pendente
                st.rerun()
                
        if c2.button("Cancelar"):
            del st.session_state.exclusao_pendente
            st.rerun()

# ==========================================
# 📂 HISTÓRICO ORGANIZADO (SANFONA)
# ==========================================
st.markdown("---")
st.subheader("📂 Histórico por Cliente")

# Botão para atualizar a visualização
if st.button("🔄 Atualizar Lista de Histórico"):
    st.rerun()

try:
    # Baixa o histórico completo
    dados_h = sheet_historico.get_all_records()
    df_h = pd.DataFrame(dados_h)
    
    if not df_h.empty:
        # Garante que as colunas existem
        df_h['Telefone'] = df_h['Telefone'].astype(str)
        
        # Pega a lista de nomes únicos no histórico
        nomes_unicos = df_h['Nome'].unique()
        
        # Para cada nome, cria uma "Sanfona" (Expander)
        for nome_cli in sorted(nomes_unicos):
            # Filtra as compras desse cliente
            compras_cli = df_h[df_h['Nome'] == nome_cli]
            qtd_compras = len(compras_cli)
            
            # O Titulo da sanfona mostra o resumo
            with st.expander(f"👤 {nome_cli} ({qtd_compras} registros)"):
                # Mostra a tabela limpa
                st.dataframe(
                    compras_cli[['Data', 'Ação', 'Valor']], 
                    hide_index=True, 
                    use_container_width=True
                )
    else:
        st.info("Histórico vazio.")
        
except Exception as e:
    st.warning("Ainda não há histórico ou ocorreu um erro na leitura.")
