import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO INICIAL E ESTADO DO SISTEMA ---
if 'db_produtos' not in st.session_state:
    st.session_state.db_produtos = pd.DataFrame(columns=[
        'ID', 'Nome', 'Categoria', 'Valor_Unitario', 'Giro', 'Classe_ABC', 
        'Endereco', 'Status', 'Qtd_Estoque'
    ])

if 'liberacoes' not in st.session_state:
    st.session_state.liberacoes = {'expedicao': False, 'distribuicao': False}

# --- FUNÇÕES AUXILIARES ---
def calcular_abc(df):
    if df.empty: return df
    df['Impacto'] = df['Valor_Unitario'] * df['Giro']
    df = df.sort_values(by='Impacto', ascending=False)
    df['Acumulado'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def rotulo_abc(perc):
        if perc <= 0.7: return 'A'
        elif perc <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe_ABC'] = df['Acumulado'].apply(rotulo_abc)
    # Lógica de Endereçamento Simples baseada na Classe
    df['Endereco'] = df['Classe_ABC'].apply(lambda x: f"ZONA-{x}-" + str(datetime.datetime.now().microsecond % 100))
    return df

# --- INTERFACE DE LOGIN ---
st.sidebar.title("WMS Login")
perfil = st.sidebar.selectbox("Selecione o Perfil", ["Conferente", "Administrador"])
senha = st.sidebar.text_input("Senha", type="password")

# Simulação de autenticação simples
auth = False
if perfil == "Administrador" and senha == "admin123":
    auth = True
elif perfil == "Conferente" and senha == "conf123":
    auth = True

if auth:
    st.title(f"Sistema WMS - Portal do {perfil}")
    
    # --- VISÃO ADMINISTRADOR ---
    if perfil == "Administrador":
        tab1, tab2, tab3 = st.tabs(["Cadastro e ABC", "Gestão de Estoque", "Liberações e Relatórios"])
        
        with tab1:
            st.header("Cadastro de Produtos")
            with st.form("cadastro_form"):
                nome = st.text_input("Nome do Produto")
                cat = st.selectbox("Categoria", ["Papelaria", "Escritório", "Informática"])
                valor = st.number_input("Valor Unitário", min_value=0.0)
                giro = st.number_input("Previsão de Giro (Saídas/Mês)", min_value=0)
                if st.form_submit_button("Cadastrar e Gerar Endereçamento"):
                    novo_id = len(st.session_state.db_produtos) + 1
                    novo_item = pd.DataFrame([{
                        'ID': novo_id, 'Nome': nome, 'Categoria': cat, 
                        'Valor_Unitario': valor, 'Giro': giro, 'Status': 'Recebido', 'Qtd_Estoque': 0
                    }])
                    st.session_state.db_produtos = pd.concat([st.session_state.db_produtos, novo_item], ignore_index=True)
                    st.session_state.db_produtos = calcular_abc(st.session_state.db_produtos)
                    st.success(f"Produto {nome} cadastrado com sucesso!")

        with tab2:
            st.header("Inventário Geral")
            st.dataframe(st.session_state.db_produtos)

        with tab3:
            st.header("Controle de Fluxo")
            col1, col2 = st.columns(2)
            st.session_state.liberacoes['expedicao'] = col1.checkbox("Liberar Expedição para Conferente", value=st.session_state.liberacoes['expedicao'])
            st.session_state.liberacoes['distribuicao'] = col2.checkbox("Liberar Distribuição para Conferente", value=st.session_state.liberacoes['distribuicao'])
            
            st.divider()
            st.subheader("Relatório de Ocupação")
            if not st.session_state.db_produtos.empty:
                st.bar_chart(st.session_state.db_produtos['Classe_ABC'].value_counts())

    # --- VISÃO CONFERENTE ---
    if perfil == "Conferente":
        menu_conf = ["Recebimento & Etiqueta"]
        if st.session_state.liberacoes['expedicao']: menu_conf.append("Expedição")
        if st.session_state.liberacoes['distribuicao']: menu_conf.append("Distribuição")
        
        escolha = st.radio("Operação", menu_conf)

        if escolha == "Recebimento & Etiqueta":
            st.header("Recebimento de Mercadoria")
            if st.session_state.db_produtos.empty:
                st.warning("Nenhum produto cadastrado pelo Administrador.")
            else:
                prod_ref = st.selectbox("Selecione o produto chegando", st.session_state.db_produtos['Nome'].tolist())
                qtd = st.number_input("Quantidade Recebida", min_value=1)
                if st.button("Confirmar Recebimento"):
                    # Gera "Etiqueta" visual
                    st.success("Recebimento Confirmado!")
                    st.code(f"""
                    -----------------------------------
                    ETIQUETA DE PRODUTO WMS
                    PRODUTO: {prod_ref}
                    QTD: {qtd}
                    ENDEREÇO: {st.session_state.db_produtos.loc[st.session_state.db_produtos['Nome']==prod_ref, 'Endereco'].values[0]}
                    COD: {datetime.datetime.now().strftime('%Y%m%d%H%M')}
                    -----------------------------------
                    """, language="markdown")
                    # Atualiza estoque
                    idx = st.session_state.db_produtos.index[st.session_state.db_produtos['Nome'] == prod_ref].tolist()[0]
                    st.session_state.db_produtos.at[idx, 'Qtd_Estoque'] += qtd

        elif escolha == "Expedição":
            st.header("Conferência de Saída (Expedição)")
            st.write("Acesso liberado pelo Administrador.")
            # Lógica de conferência aqui

        elif escolha == "Distribuição":
            st.header("Distribuição de Cargas")
            st.info("Fluxo final: Produto pronto para transporte.")

else:
    st.error("Acesso negado. Verifique suas credenciais no painel lateral.")