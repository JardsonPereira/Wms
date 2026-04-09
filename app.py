import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NexLOG Papelaria | WMS Pro", layout="wide")

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
if 'db_papelaria' not in st.session_state:
    st.session_state.db_papelaria = pd.DataFrame(columns=[
        'SKU', 'Produto', 'Categoria', 'Preco_Custo', 'Giro_Mensal', 'Classe_ABC', 
        'Zona_Endereco', 'Estoque_Atual', 'Status'
    ])

if 'recebimentos_pendentes' not in st.session_state:
    st.session_state.recebimentos_pendentes = []

if 'fluxo_ativo' not in st.session_state:
    st.session_state.fluxo_ativo = {'conferencia': False, 'expedicao': False, 'distribuicao': False}

# --- INTELIGÊNCIA LOGÍSTICA ---
def inteligência_estoque(df):
    if df.empty: return df
    df['Impacto'] = df['Preco_Custo'].astype(float) * df['Giro_Mensal'].astype(float)
    df = df.sort_values(by='Impacto', ascending=False)
    df['Soma_Acum'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def definir_abc(p):
        if p <= 0.7: return 'A'
        elif p <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe_ABC'] = df['Soma_Acum'].apply(definir_abc)
    df['Zona_Endereco'] = df['Classe_ABC'].apply(
        lambda x: f"ZONA-0{ord(x)-64}-PRAT-{datetime.datetime.now().microsecond % 20:02d}"
    )
    return df

# --- LOGIN E SEGURANÇA ---
with st.sidebar:
    st.title("📦 WMS Papelaria")
    st.divider()
    st.write("**Credenciais:**\n\nADM: `admin123` | CONF: `conf123` ")
    perfil = st.selectbox("Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha", type="password")

# Autenticação
if (perfil == "Administrador" and senha == "admin123") or (perfil == "Conferente" and senha == "conf123"):
    
    # --- ÁREA DO ADMINISTRADOR ---
    if perfil == "Administrador":
        st.title("🛡️ Painel de Gestão Estratégica")
        
        tab_cad, tab_recebe, tab_bi, tab_config = st.tabs([
            "📝 Cadastro de SKU", "📄 Recebimento (NF)", "📊 Dashboards", "🔐 Liberações"
        ])

        with tab_cad:
            with st.form("form_cad"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Descrição do Produto")
                cat = c1.selectbox("Categoria", ["Escrita", "Papéis", "Escolar", "Escritório"])
                custo = c2.number_input("Custo Unitário", min_value=0.01)
                giro = c2.number_input("Previsão Mensal", min_value=1)
                if st.form_submit_button("Cadastrar"):
                    novo = pd.DataFrame([{
                        'SKU': f"PAP-{len(st.session_state.db_papelaria)+1:03d}",
                        'Produto': nome, 'Categoria': cat, 'Preco_Custo': custo,
                        'Giro_Mensal': giro, 'Estoque_Atual': 0, 'Status': 'Ativo'
                    }])
                    st.session_state.db_papelaria = pd.concat([st.session_state.db_papelaria, novo], ignore_index=True)
                    st.session_state.db_papelaria = inteligência_estoque(st.session_state.db_papelaria)
                    st.success(f"{nome} cadastrado!")

        with tab_recebe:
            st.subheader("Entrada de Nota Fiscal")
            if st.session_state.db_papelaria.empty:
                st.info("Cadastre um produto antes de receber uma nota.")
            else:
                nf_num = st.text_input("Número da Nota Fiscal")
                item_nf = st.selectbox("Produto na Nota", st.session_state.db_papelaria['Produto'])
                qtd_nf = st.number_input("Quantidade em Nota", min_value=1)
                
                if st.button("Validar NF e Liberar Conferência"):
                    st.session_state.recebimentos_pendentes.append({'nf': nf_num, 'item': item_nf, 'qtd': qtd_nf})
                    st.session_state.fluxo_ativo['conferencia'] = True
                    st.success(f"NF {nf_num} validada! O Conferente já pode iniciar a contagem.")

        with tab_bi:
            if not st.session_state.db_papelaria.empty:
                st.dataframe(st.session_state.db_papelaria, use_container_width=True)
                fig = px.pie(st.session_state.db_papelaria, names='Classe_ABC', title="Curva ABC")
                st.plotly_chart(fig)

        with tab_config:
            st.subheader("Controle de Cadeado Logístico")
            st.session_state.fluxo_ativo['expedicao'] = st.toggle("Liberar Expedição", value=st.session_state.fluxo_ativo['expedicao'])
            st.session_state.fluxo_ativo['distribuicao'] = st.toggle("Liberar Distribuição", value=st.session_state.fluxo_ativo['distribuicao'], disabled=not st.session_state.fluxo_ativo['expedicao'])

    # --- ÁREA DO CONFERENTE ---
    if perfil == "Conferente":
        st.title("📋 Terminal de Campo")
        
        # O menu Recebimento foi removido daqui conforme solicitado
        opcoes = []
        if st.session_state.fluxo_ativo['conferencia']: opcoes.append("🔍 Conferência")
        opcoes.extend(["🏷️ Endereçamento", "📦 Armazenamento"])
        
        if st.session_state.fluxo_ativo['expedicao']: opcoes.append("📤 Expedição")
        if st.session_state.fluxo_ativo['distribuicao']: opcoes.append("🚚 Distribuição")
        
        tarefa = st.sidebar.radio("Selecione a Operação:", opcoes)

        if tarefa == "🔍 Conferência":
            st.header("Conferência de Carga Liberada")
            if not st.session_state.recebimentos_pendentes:
                st.info("Nenhuma Nota Fiscal liberada pelo ADM para conferência no momento.")
            else:
                for idx, r in enumerate(st.session_state.recebimentos_pendentes):
                    st.write(f"**NF:** {r['nf']} | **Item:** {r['item']} | **Qtd Esperada:** {r['qtd']}")
                    if st.button(f"Confirmar Contagem de {r['item']}", key=idx):
                        st.success("Item conferido e movido para etapa de Endereçamento!")

        elif tarefa == "🏷️ Endereçamento":
            st.header("Impressão de Etiquetas")
            sel_e = st.selectbox("Item para Etiquetar", st.session_state.db_papelaria['Produto'])
            idx_e = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_e][0]
            st.markdown(f"""
            <div style="background:white; border:4px solid black; padding:15px; color:black; text-align:center">
                <h3>{st.session_state.db_papelaria.at[idx_e, 'Zona_Endereco']}</h3>
                <p><b>{sel_e}</b><br>CLASSE {st.session_state.db_papelaria.at[idx_e, 'Classe_ABC']}</p>
            </div>
            """, unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.header("Put-away")
            sel_a = st.selectbox("Guardar Produto:", st.session_state.db_papelaria['Produto'])
            qtd_a = st.number_input("Qtd Guardada", min_value=1)
            if st.button("Confirmar e Atualizar Estoque"):
                idx_a = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_a][0]
                st.session_state.db_papelaria.at[idx_a, 'Estoque_Atual'] += qtd_a
                st.success("Saldo atualizado no sistema!")

        elif tarefa == "📤 Expedição":
            st.header("Picking")
            sel_ex = st.selectbox("Saída de Produto:", st.session_state.db_papelaria['Produto'])
            qtd_ex = st.number_input("Qtd Saída", min_value=1)
            if st.button("Validar Checkout"):
                idx_ex = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_ex][0]
                if st.session_state.db_papelaria.at[idx_ex, 'Estoque_Atual'] >= qtd_ex:
                    st.session_state.db_papelaria.at[idx_ex, 'Estoque_Atual'] -= qtd_ex
                    st.success("Saída realizada!")
                else: st.error("Sem estoque!")

        elif tarefa == "🚚 Distribuição":
            st.subheader("Despacho Final")
            st.info("Aguardando coleta externa...")

else:
    if senha: st.error("Acesso Negado.")
