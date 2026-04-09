import streamlit as st
import pandas as pd
import datetime
import plotly.express as px # Necessário adicionar 'plotly' no requirements.txt

# Configuração da página
st.set_page_config(page_title="WMS Logística Pro", layout="wide")

# --- ESTADO DO SISTEMA (Banco de dados temporário) ---
if 'db_produtos' not in st.session_state:
    st.session_state.db_produtos = pd.DataFrame(columns=[
        'ID', 'Nome', 'Categoria', 'Valor_Unitario', 'Giro', 'Classe_ABC', 
        'Endereco', 'Status', 'Qtd_Estoque'
    ])

if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=['Data/Hora', 'Usuário', 'Ação', 'Produto', 'Qtd'])

if 'liberacoes' not in st.session_state:
    st.session_state.liberacoes = {'expedicao': False, 'distribuicao': False}

# --- FUNÇÕES DE APOIO ---
def registrar_log(usuario, acao, produto="-", qtd=0):
    novo_log = pd.DataFrame([{
        'Data/Hora': datetime.datetime.now().strftime("%d/%m %H:%M"),
        'Usuário': usuario, 'Ação': acao, 'Produto': produto, 'Qtd': qtd
    }])
    st.session_state.logs = pd.concat([novo_log, st.session_state.logs], ignore_index=True)

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
    df['Endereco'] = df['Classe_ABC'].apply(lambda x: f"RUA-{x}-" + str(datetime.datetime.now().microsecond % 100))
    return df

# --- INTERFACE DE LOGIN ---
with st.sidebar:
    st.header("🔑 Acesso ao Sistema")
    st.info("**Usuários e Senhas:**\n\n- **Administrador:** `admin123` \n- **Conferente:** `conf123` ")
    
    perfil = st.selectbox("Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha", type="password")

if senha == ("admin123" if perfil == "Administrador" else "conf123"):
    
    # --- ÁREA DO ADMINISTRADOR ---
    if perfil == "Administrador":
        st.title("🛡️ Gestão de Almoxarifado (ADM)")
        tab_cad, tab_estoque, tab_fluxo, tab_relatorios = st.tabs(["🆕 Cadastro", "📦 Inventário", "🔓 Liberações", "📊 Dashboards"])
        
        with tab_cad:
            with st.form("cadastro"):
                col1, col2 = st.columns(2)
                nome = col1.text_input("Nome do Produto")
                cat = col1.selectbox("Categoria", ["Escritório", "Papelaria", "Informática"])
                val = col2.number_input("Custo Unitário (R$)", min_value=0.1)
                giro = col2.number_input("Giro Mensal Previsto", min_value=1)
                if st.form_submit_button("Cadastrar Item"):
                    novo_item = pd.DataFrame([{
                        'ID': len(st.session_state.db_produtos)+1, 'Nome': nome, 'Categoria': cat, 
                        'Valor_Unitario': val, 'Giro': giro, 'Status': 'Ativo', 'Qtd_Estoque': 0
                    }])
                    st.session_state.db_produtos = pd.concat([st.session_state.db_produtos, novo_item], ignore_index=True)
                    st.session_state.db_produtos = calcular_abc(st.session_state.db_produtos)
                    registrar_log("ADM", "Cadastrou Produto", nome)
                    st.success("Produto registrado!")

        with tab_estoque:
            st.dataframe(st.session_state.db_produtos, use_container_width=True)

        with tab_fluxo:
            st.subheader("Controle de Permissões")
            st.session_state.liberacoes['expedicao'] = st.toggle("Permitir Expedição", value=st.session_state.liberacoes['expedicao'])
            st.session_state.liberacoes['distribuicao'] = st.toggle("Permitir Distribuição", value=st.session_state.liberacoes['distribuicao'], disabled=not st.session_state.liberacoes['expedicao'])
            
            st.divider()
            st.subheader("Histórico de Movimentação")
            st.table(st.session_state.logs.head(10))

        with tab_relatorios:
            if not st.session_state.db_produtos.empty:
                fig = px.pie(st.session_state.db_produtos, names='Classe_ABC', title="Distribuição Curva ABC")
                st.plotly_chart(fig)
            else: st.write("Sem dados para exibir.")

    # --- ÁREA DO CONFERENTE ---
    if perfil == "Conferente":
        st.title("📋 Operação e Conferência")
        op = st.sidebar.radio("Tarefa", ["Recebimento", "Expedição", "Distribuição"])

        if op == "Recebimento":
            st.subheader("📥 Entrada de Materiais")
            if st.session_state.db_produtos.empty: st.warning("Nenhum produto cadastrado.")
            else:
                sel = st.selectbox("Selecione o Item", st.session_state.db_produtos['Nome'])
                qtd = st.number_input("Quantidade", min_value=1)
                if st.button("Confirmar Entrada"):
                    idx = st.session_state.db_produtos.index[st.session_state.db_produtos['Nome'] == sel][0]
                    st.session_state.db_produtos.at[idx, 'Qtd_Estoque'] += qtd
                    registrar_log("Conferente", "Recebimento", sel, qtd)
                    st.success(f"Estoque atualizado! Endereço: {st.session_state.db_produtos.at[idx, 'Endereco']}")

        elif op == "Expedição":
            if st.session_state.liberacoes['expedicao']:
                st.subheader("📤 Conferência de Saída")
                sel_exp = st.selectbox("Item para Saída", st.session_state.db_produtos['Nome'])
                qtd_exp = st.number_input("Qtd para Enviar", min_value=1)
                
                idx_exp = st.session_state.db_produtos.index[st.session_state.db_produtos['Nome'] == sel_exp][0]
                estoque_atual = st.session_state.db_produtos.at[idx_exp, 'Qtd_Estoque']
                
                if st.button("Validar Saída"):
                    if estoque_atual >= qtd_exp:
                        st.session_state.db_produtos.at[idx_exp, 'Qtd_Estoque'] -= qtd_exp
                        registrar_log("Conferente", "Expedição", sel_exp, qtd_exp)
                        st.success("Saída autorizada!")
                    else:
                        st.error(f"Estoque Insuficiente! Disponível: {estoque_atual}")
            else:
                st.error("❌ Módulo de Expedição bloqueado pelo Administrador.")

        elif op == "Distribuição":
            if st.session_state.liberacoes['distribuicao']:
                st.subheader("🚚 Fluxo de Distribuição")
                st.info("Aguardando carregamento dos veículos...")
            else:
                st.error("❌ Módulo de Distribuição bloqueado ou aguardando Expedição.")
else:
    if senha: st.error("Senha incorreta!")
