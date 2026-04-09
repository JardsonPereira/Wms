import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NexLOG Papelaria | WMS Pro", layout="wide")

# Estilização para Interface Profissional
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
if 'db_papelaria' not in st.session_state:
    st.session_state.db_papelaria = pd.DataFrame(columns=[
        'SKU', 'Produto', 'Categoria', 'Preco_Custo', 'Giro_Mensal', 'Classe_ABC', 
        'Zona_Endereco', 'Estoque_Atual', 'Status'
    ])

if 'fluxo_ativo' not in st.session_state:
    st.session_state.fluxo_ativo = {'expedicao': False, 'distribuicao': False}

# --- MOTOR LOGÍSTICO (CURVA ABC & ZONAS) ---
def inteligência_estoque(df):
    if df.empty: return df
    # ABC baseado em Valor x Giro (Impacto Financeiro)
    df['Impacto'] = df['Preco_Custo'].astype(float) * df['Giro_Mensal'].astype(float)
    df = df.sort_values(by='Impacto', ascending=False)
    df['Soma_Acum'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def definir_abc(p):
        if p <= 0.7: return 'A'
        elif p <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe_ABC'] = df['Soma_Acum'].apply(definir_abc)
    
    # Endereçamento por Zonas da Papelaria
    # Zona 1: Frente (Itens A), Zona 2: Meio (Itens B), Zona 3: Fundo (Itens C)
    df['Zona_Endereco'] = df['Classe_ABC'].apply(
        lambda x: f"ZONA-0{ord(x)-64}-PRAT-{datetime.datetime.now().microsecond % 20:02d}"
    )
    return df

# --- LOGIN E SEGURANÇA ---
with st.sidebar:
    st.title("📦 WMS Papelaria")
    st.image("https://cdn-icons-png.flaticon.com/512/2611/2611152.png", width=80)
    st.divider()
    st.write("**Acessos do Sistema:**")
    st.code("ADM: admin123\nCONF: conf123")
    
    perfil = st.selectbox("Escolha o Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha de Acesso", type="password")

# Autenticação
if (perfil == "Administrador" and senha == "admin123") or (perfil == "Conferente" and senha == "conf123"):
    
    # --- ÁREA DO ADMINISTRADOR (ESTRATÉGIA) ---
    if perfil == "Administrador":
        st.title("🛡️ Painel de Gestão - Papelaria")
        
        # KPIs em tempo real
        k1, k2, k3 = st.columns(3)
        total_skus = len(st.session_state.db_papelaria)
        valor_inv = (st.session_state.db_papelaria['Estoque_Atual'] * st.session_state.db_papelaria['Preco_Custo']).sum()
        
        k1.metric("Total de Itens (SKUs)", total_skus)
        k2.metric("Valor em Estoque", f"R$ {valor_inv:,.2f}")
        k3.metric("Status Operacional", "LIBERADO" if st.session_state.fluxo_ativo['expedicao'] else "AGUARDANDO")

        tab_cad, tab_bi, tab_config = st.tabs(["📝 Cadastro de Itens", "📊 BI & Curva ABC", "🔐 Liberação de Fluxo"])

        with tab_cad:
            with st.form("form_papelaria"):
                col1, col2 = st.columns(2)
                nome_p = col1.text_input("Descrição do Produto (Ex: Caderno 10 Matérias)")
                cat_p = col1.selectbox("Categoria", ["Escrita", "Papéis", "Escolar", "Escritório", "Presentes"])
                custo_p = col2.number_input("Preço de Custo (R$)", min_value=0.01)
                giro_p = col2.number_input("Previsão de Vendas/Mês", min_value=1)
                
                if st.form_submit_button("Cadastrar e Gerar Endereço"):
                    novo_item = pd.DataFrame([{
                        'SKU': f"PAP-{len(st.session_state.db_papelaria)+1:03d}",
                        'Produto': nome_p, 'Categoria': cat_p, 'Preco_Custo': custo_p,
                        'Giro_Mensal': giro_p, 'Estoque_Atual': 0, 'Status': 'Ativo'
                    }])
                    st.session_state.db_papelaria = pd.concat([st.session_state.db_papelaria, novo_item], ignore_index=True)
                    st.session_state.db_papelaria = inteligência_estoque(st.session_state.db_papelaria)
                    st.success(f"Produto {nome_p} registrado com sucesso!")

        with tab_bi:
            if not st.session_state.db_papelaria.empty:
                st.dataframe(st.session_state.db_papelaria[['SKU', 'Produto', 'Classe_ABC', 'Zona_Endereco', 'Estoque_Atual']], use_container_width=True)
                fig = px.pie(st.session_state.db_papelaria, names='Classe_ABC', title="Composição Curva ABC (Valor x Giro)", hole=0.5)
                st.plotly_chart(fig)
            else:
                st.info("Aguardando cadastro de produtos.")

        with tab_config:
            st.subheader("Controle de Segurança da Equipe")
            st.session_state.fluxo_ativo['expedicao'] = st.toggle("Ativar Módulo de Expedição", st.session_state.fluxo_ativo['expedicao'])
            st.session_state.fluxo_ativo['distribuicao'] = st.toggle("Ativar Módulo de Distribuição", st.session_state.fluxo_ativo['distribuicao'], 
                                                                    disabled=not st.session_state.fluxo_ativo['expedicao'])

    # --- ÁREA DO CONFERENTE (OPERAÇÃO) ---
    if perfil == "Conferente":
        st.title("📋 Terminal de Operação")
        
        menus = ["📥 Recebimento", "🔍 Conferência", "🏷️ Endereçamento", "📦 Armazenamento"]
        if st.session_state.fluxo_ativo['expedicao']: menus.append("📤 Expedição")
        if st.session_state.fluxo_ativo['distribuicao']: menus.append("🚚 Distribuição")
        
        tarefa = st.sidebar.radio("Selecione a Operação:", menus)

        if tarefa == "📥 Recebimento":
            st.header("Entrada de Mercadoria")
            if st.session_state.db_papelaria.empty: st.warning("Nenhum item cadastrado.")
            else:
                sel = st.selectbox("Selecione o Item Chegando", st.session_state.db_papelaria['Produto'])
                st.number_input("Qtd conforme Nota Fiscal", min_value=1)
                st.button("Registrar Chegada na Doca")

        elif tarefa == "🔍 Conferência":
            st.header("Conferência Cega")
            st.info("Abra as caixas e conte os itens individualmente.")
            st.selectbox("Item em conferência", st.session_state.db_papelaria['Produto'])
            st.number_input("Quantidade Contada", min_value=0)
            if st.button("Validar Contagem"): st.success("Conferência finalizada!")

        elif tarefa == "🏷️ Endereçamento":
            st.header("Etiquetagem de Produto")
            item_etq = st.selectbox("Gerar Etiqueta para:", st.session_state.db_papelaria['Produto'])
            idx = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == item_etq][0]
            
            # Etiqueta visual de ponta
            st.markdown(f"""
            <div style="background-color:white; border:5px solid black; padding:20px; color:black; text-align:center; font-family:monospace">
                <p style="margin:0">WMS PAPELARIA - ETIQUETA INTERNA</p>
                <h1 style="margin:10px 0">{st.session_state.db_papelaria.at[idx, 'Zona_Endereco']}</h1>
                <p style="font-size:20px"><b>{item_etq}</b></p>
                <p>SKU: {st.session_state.db_papelaria.at[idx, 'SKU']} | CLASSE: {st.session_state.db_papelaria.at[idx, 'Classe_ABC']}</p>
            </div>
            """, unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.header("Put-away (Guardar no Estoque)")
            sel_arm = st.selectbox("Confirmar Guardada:", st.session_state.db_papelaria['Produto'])
            qtd_arm = st.number_input("Quantidade que está indo para prateleira", min_value=1)
            if st.button("Confirmar e Atualizar Saldo"):
                idx = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_arm][0]
                st.session_state.db_papelaria.at[idx, 'Estoque_Atual'] += qtd_arm
                st.success(f"Estoque atualizado! Saldo atual de {sel_arm}: {st.session_state.db_papelaria.at[idx, 'Estoque_Atual']}")

        elif tarefa == "📤 Expedição":
            st.header("Picking e Checkout")
            sel_exp = st.selectbox("Item para Pedido de Cliente", st.session_state.db_papelaria['Produto'])
            qtd_exp = st.number_input("Quantidade a retirar", min_value=1)
            idx_exp = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_exp][0]
            
            if st.button("Confirmar Saída"):
                if st.session_state.db_papelaria.at[idx_exp, 'Estoque_Atual'] >= qtd_exp:
                    st.session_state.db_papelaria.at[idx_exp, 'Estoque_Atual'] -= qtd_exp
                    st.success("Saída confirmada! Pedido enviado para embalagem.")
                else:
                    st.error("ERRO: Saldo insuficiente em estoque!")

        elif tarefa == "🚚 Distribuição":
            st.header("Despacho e Logística")
            st.info("Aguardando coleta da transportadora ou motoboy...")

else:
    if senha: st.error("Acesso Negado. Senha incorreta.")
    else: st.info("Seja bem-vindo. Por favor, faça o login no menu lateral.")
