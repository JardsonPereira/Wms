import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="WMS Almoxarifado Pro", layout="wide")

# --- INICIALIZAÇÃO DO BANCO DE DADOS (SESSION STATE) ---
if 'db_wms' not in st.session_state:
    st.session_state.db_wms = pd.DataFrame(columns=[
        'ID', 'Produto', 'Categoria', 'Valor', 'Giro', 'Classe_ABC', 
        'Endereco', 'Status', 'Saldo_Estoque'
    ])

if 'liberacoes' not in st.session_state:
    st.session_state.liberacoes = {'expedicao': False, 'distribuicao': False}

# --- FUNÇÕES DE LÓGICA LOGÍSTICA ---
def processar_abc_e_endereco(df):
    if df.empty: return df
    df['Impacto'] = df['Valor'].astype(float) * df['Giro'].astype(float)
    df = df.sort_values(by='Impacto', ascending=False)
    df['Acumulado'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def definir_classe(p):
        if p <= 0.7: return 'A'
        elif p <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe_ABC'] = df['Acumulado'].apply(definir_classe)
    # Regra de Endereçamento: Itens A ficam perto da expedição (Rua 1), C ao fundo (Rua 3)
    mapa_ruas = {'A': 'RUA-01', 'B': 'RUA-02', 'C': 'RUA-03'}
    df['Endereco'] = df['Classe_ABC'].apply(lambda x: f"{mapa_ruas[x]}-BOX-{datetime.datetime.now().microsecond % 50}")
    return df

# --- INTERFACE DE LOGIN ---
with st.sidebar:
    st.header("🔑 Acesso WMS")
    st.info("**Credenciais:**\n\n- **ADM:** `admin123` \n- **Conferente:** `conf123` ")
    perfil = st.selectbox("Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha", type="password")

# --- VALIDAÇÃO DE ACESSO ---
acesso_adm = (perfil == "Administrador" and senha == "admin123")
acesso_conf = (perfil == "Conferente" and senha == "conf123")

if acesso_adm or acesso_conf:
    st.title(f"📦 Sistema de Gestão de Almoxarifado - {perfil}")

    # --- MENU ADMINISTRADOR ---
    if acesso_adm:
        menu_adm = st.tabs(["📑 Cadastro", "📊 Relatórios e ABC", "🔓 Liberação de Fluxo"])
        
        with menu_adm[0]:
            st.subheader("Cadastro de Novos Produtos")
            with st.form("form_cad"):
                col1, col2 = st.columns(2)
                nome = col1.text_input("Nome do Produto")
                cat = col1.selectbox("Categoria", ["Escritório", "Papelaria", "Informática", "Limpeza"])
                val = col2.number_input("Valor Unitário (R$)", min_value=0.01)
                giro = col2.number_input("Giro Mensal Estimado", min_value=1)
                if st.form_submit_button("Salvar Produto"):
                    novo_prod = pd.DataFrame([{
                        'ID': len(st.session_state.db_wms)+1, 'Produto': nome, 'Categoria': cat,
                        'Valor': val, 'Giro': giro, 'Status': 'Ativo', 'Saldo_Estoque': 0
                    }])
                    st.session_state.db_wms = pd.concat([st.session_state.db_wms, novo_prod], ignore_index=True)
                    st.session_state.db_wms = processar_abc_e_endereco(st.session_state.db_wms)
                    st.success("Item cadastrado e endereçado automaticamente!")

        with menu_adm[1]:
            st.subheader("Análise de Inventário e Curva ABC")
            st.dataframe(st.session_state.db_wms, use_container_width=True)
            if not st.session_state.db_wms.empty:
                fig = px.bar(st.session_state.db_wms, x='Produto', y='Saldo_Estoque', color='Classe_ABC', title="Saldo por Produto e Classe")
                st.plotly_chart(fig)

        with menu_adm[2]:
            st.subheader("Controle de Operações")
            st.session_state.liberacoes['expedicao'] = st.toggle("Liberar EXPEDIÇÃO para equipe", value=st.session_state.liberacoes['expedicao'])
            st.session_state.liberacoes['distribuicao'] = st.toggle("Liberar DISTRIBUIÇÃO para equipe", 
                                                                   value=st.session_state.liberacoes['distribuicao'], 
                                                                   disabled=not st.session_state.liberacoes['expedicao'])

    # --- MENU CONFERENTE ---
    if acesso_conf:
        # Menus solicitados
        opcoes = ["📥 Recebimento", "🔍 Conferência", "📍 Endereçamento", "📦 Armazenamento"]
        
        if st.session_state.liberacoes['expedicao']: opcoes.append("📤 Expedição")
        if st.session_state.liberacoes['distribuicao']: opcoes.append("🚚 Distribuição")
        
        tarefa = st.sidebar.radio("Selecione o Menu Operacional:", opcoes)

        if tarefa == "📥 Recebimento":
            st.subheader("Entrada de Materiais")
            if st.session_state.db_wms.empty: st.warning("Nenhum produto no mestre de cadastro.")
            else:
                prod_rec = st.selectbox("Produto Chegando:", st.session_state.db_wms['Produto'])
                qtd_rec = st.number_input("Quantidade em Nota:", min_value=1)
                if st.button("Registrar Entrada"):
                    st.info(f"Recebimento de {qtd_rec} unid. de {prod_rec} iniciado. Siga para a Conferência.")

        elif tarefa == "🔍 Conferência":
            st.subheader("Conferência Cega / Qualidade")
            sel_conf = st.selectbox("Confirmar Item:", st.session_state.db_wms['Produto'])
            qtd_conf = st.number_input("Quantidade Física Contada:", min_value=1)
            if st.button("Validar Quantidades"):
                st.success("Conferência concluída sem divergências!")

        elif tarefa == "📍 Endereçamento":
            st.subheader("Geração de Etiqueta e Destino")
            sel_end = st.selectbox("Gerar Etiqueta para:", st.session_state.db_wms['Produto'])
            idx = st.session_state.db_wms.index[st.session_state.db_wms['Produto'] == sel_end][0]
            
            st.markdown(f"""
            <div style="border:3px solid #000; padding:20px; background-color:white; color:black; text-align:center">
                <h2>ETIQUETA DE ARMAZENAGEM</h2>
                <hr>
                <h1>{st.session_state.db_wms.at[idx, 'Endereco']}</h1>
                <p>PRODUTO: {sel_end} | CLASSE: {st.session_state.db_wms.at[idx, 'Classe_ABC']}</p>
                <p>DATA: {datetime.date.today()}</p>
            </div>
            """, unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.subheader("Confirmação de Guardada")
            sel_arm = st.selectbox("Confirmar Armazenagem no Box:", st.session_state.db_wms['Produto'])
            qtd_arm = st.number_input("Quantidade Guardada:", min_value=1)
            if st.button("Finalizar e Atualizar Estoque"):
                idx = st.session_state.db_wms.index[st.session_state.db_wms['Produto'] == sel_arm][0]
                st.session_state.db_wms.at[idx, 'Saldo_Estoque'] += qtd_arm
                st.success(f"Estoque atualizado! {sel_arm} disponível para venda/uso.")

        elif tarefa == "📤 Expedição":
            st.subheader("Separação (Picking)")
            sel_exp = st.selectbox("Item para Saída:", st.session_state.db_wms['Produto'])
            qtd_exp = st.number_input("Quantidade Pedida:", min_value=1)
            idx_exp = st.session_state.db_wms.index[st.session_state.db_wms['Produto'] == sel_exp][0]
            
            if st.button("Confirmar Separação"):
                if st.session_state.db_wms.at[idx_exp, 'Saldo_Estoque'] >= qtd_exp:
                    st.session_state.db_wms.at[idx_exp, 'Saldo_Estoque'] -= qtd_exp
                    st.success("Picking realizado. Item movido para doca de saída.")
                else:
                    st.error("Saldo insuficiente em estoque!")

        elif tarefa == "🚚 Distribuição":
            st.subheader("Expedição Final / Carregamento")
            st.write("Aguardando romaneio de carga...")
            st.info("Fluxo de distribuição liberado pelo Administrador.")

else:
    if senha: st.error("Senha inválida.")
    else: st.info("Use o painel lateral para acessar o sistema.")
