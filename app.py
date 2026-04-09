import streamlit as st
import pandas as pd
import datetime

# Configuração da página
st.set_page_config(page_title="WMS Professional", layout="wide")

# --- ESTADO DO SISTEMA ---
if 'db_produtos' not in st.session_state:
    st.session_state.db_produtos = pd.DataFrame(columns=[
        'ID', 'Nome', 'Categoria', 'Valor_Unitario', 'Giro', 'Classe_ABC', 
        'Endereco', 'Status', 'Qtd_Estoque'
    ])

if 'liberacoes' not in st.session_state:
    st.session_state.liberacoes = {'expedicao': False, 'distribuicao': False}

# --- LÓGICA DE NEGÓCIO ---
def calcular_abc(df):
    if df.empty: return df
    df['Impacto'] = df['Valor_Unitario'].astype(float) * df['Giro'].astype(float)
    df = df.sort_values(by='Impacto', ascending=False)
    df['Acumulado'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def rotulo_abc(perc):
        if perc <= 0.7: return 'A'
        elif perc <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe_ABC'] = df['Acumulado'].apply(rotulo_abc)
    # Endereçamento estratégico: A próximo à saída, C ao fundo
    df['Endereco'] = df['Classe_ABC'].apply(lambda x: f"RUA-{x}-" + str(datetime.datetime.now().microsecond % 100))
    return df

# --- INTERFACE DE LOGIN ---
with st.sidebar:
    st.header("🔑 Acesso ao Sistema")
    perfil = st.selectbox("Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha", type="password")
    
    # Credenciais fixas
    credenciais = {
        "Administrador": "admin123",
        "Conferente": "conf123"
    }

if senha == credenciais.get(perfil):
    st.success(f"Logado como: {perfil}")
    
    # --- ESPAÇO DO ADMINISTRADOR ---
    if perfil == "Administrador":
        st.title("🛡️ Painel de Controle WMS")
        tab_cad, tab_estoque, tab_controle = st.tabs(["🆕 Cadastro", "📦 Inventário", "🔓 Liberações"])
        
        with tab_cad:
            col1, col2 = st.columns(2)
            with col1:
                with st.form("form_cadastro"):
                    st.subheader("Novo Produto")
                    nome = st.text_input("Descrição do Item")
                    cat = st.selectbox("Categoria", ["Escritório", "Papelaria", "Suprimentos"])
                    val = st.number_input("Preço de Custo (R$)", min_value=0.01)
                    giro = st.number_input("Previsão de Saída Mensal", min_value=1)
                    if st.form_submit_button("Salvar no WMS"):
                        novo_id = len(st.session_state.db_produtos) + 1
                        novo_item = pd.DataFrame([{
                            'ID': novo_id, 'Nome': nome, 'Categoria': cat, 
                            'Valor_Unitario': val, 'Giro': giro, 'Status': 'Ativo', 'Qtd_Estoque': 0
                        }])
                        st.session_state.db_produtos = pd.concat([st.session_state.db_produtos, novo_item], ignore_index=True)
                        st.session_state.db_produtos = calcular_abc(st.session_state.db_produtos)
                        st.toast(f"{nome} Cadastrado!")

        with tab_estoque:
            st.subheader("Posição do Almoxarifado")
            st.dataframe(st.session_state.db_produtos, use_container_width=True)
            
        with tab_controle:
            st.subheader("Gerenciamento de Fluxo")
            st.info("Libere os processos para a equipe de conferência abaixo:")
            col_a, col_b = st.columns(2)
            st.session_state.liberacoes['expedicao'] = col_a.toggle("Liberar Expedição", value=st.session_state.liberacoes['expedicao'])
            
            # Trava de segurança: Distribuição só libera se Expedição estiver ativa
            if st.session_state.liberacoes['expedicao']:
                st.session_state.liberacoes['distribuicao'] = col_b.toggle("Liberar Distribuição", value=st.session_state.liberacoes['distribuicao'])
            else:
                st.session_state.liberacoes['distribuicao'] = False
                col_b.warning("Aguardando Expedição...")

    # --- ESPAÇO DO CONFERENTE ---
    if perfil == "Conferente":
        st.title("📋 Operação de Campo")
        menu = ["📥 Recebimento"]
        
        if st.session_state.liberacoes['expedicao']: menu.append("📤 Expedição")
        if st.session_state.liberacoes['distribuicao']: menu.append("🚚 Distribuição")
        
        op = st.radio("Selecione a tarefa:", menu, horizontal=True)
        st.divider()

        if op == "📥 Recebimento":
            st.subheader("Entrada de Mercadoria")
            if st.session_state.db_produtos.empty:
                st.warning("Aguardando cadastro de produtos pelo ADM.")
            else:
                sel = st.selectbox("Produto p/ Conferência", st.session_state.db_produtos['Nome'].tolist())
                qtd_in = st.number_input("Qtd Conferida", min_value=1)
                if st.button("Gerar Etiqueta e Armazenar"):
                    idx = st.session_state.db_produtos.index[st.session_state.db_produtos['Nome'] == sel].tolist()[0]
                    st.session_state.db_produtos.at[idx, 'Qtd_Estoque'] += qtd_in
                    
                    # Layout da Etiqueta
                    st.success("Item Armazenado com Sucesso!")
                    st.markdown(f"""
                    <div style="border:2px solid black; padding:10px; background-color:white; color:black; width:300px">
                        <h4>ETIQUETA WMS</h4>
                        <p><b>PRODUTO:</b> {sel}<br>
                        <b>CLASSE:</b> {st.session_state.db_produtos.at[idx, 'Classe_ABC']}<br>
                        <b>ENDEREÇO:</b> {st.session_state.db_produtos.at[idx, 'Endereco']}<br>
                        <b>DATA:</b> {datetime.date.today()}</p>
                    </div>
                    """, unsafe_allow_html=True)

        elif op == "📤 Expedição":
            st.subheader("Separação e Checkout")
            st.progress(50, text="Processando pedidos liberados pelo Administrador...")
            st.write("Aguardando leitura de código de barras...")

        elif op == "🚚 Distribuição":
            st.subheader("Carregamento")
            st.success("Fluxo Final Liberado. Pronto para entrega.")

else:
    if senha:
        st.error("Senha incorreta. Verifique com o administrador.")
    else:
        st.info("Insira a senha na barra lateral para começar.")
