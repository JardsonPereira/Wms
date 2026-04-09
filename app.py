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

if 'nfs_liberadas' not in st.session_state:
    st.session_state.nfs_liberadas = {} # Dicionário para armazenar Notas e seus itens

if 'fluxo_ativo' not in st.session_state:
    st.session_state.fluxo_ativo = {'conferencia': False, 'expedicao': False, 'distribuicao': False}

# --- MOTOR LOGÍSTICO ---
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
    st.info("**Credenciais:**\n\nADM: `admin123` | CONF: `conf123` ")
    perfil = st.selectbox("Perfil", ["Conferente", "Administrador"])
    senha = st.text_input("Senha", type="password")

# Autenticação
if (perfil == "Administrador" and senha == "admin123") or (perfil == "Conferente" and senha == "conf123"):
    
    # --- ÁREA DO ADMINISTRADOR ---
    if perfil == "Administrador":
        st.title("🛡️ Painel de Gestão Estratégica")
        
        tab_cad, tab_recebe, tab_bi, tab_config = st.tabs([
            "📝 Cadastro de SKU", "📑 Recebimento (Bipar NF)", "📊 Dashboards", "🔐 Liberações"
        ])

        with tab_cad:
            st.subheader("Novo Produto no Mestre")
            with st.form("form_cad"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Descrição do Produto")
                cat = c1.selectbox("Categoria", ["Escrita", "Papéis", "Escolar", "Escritório"])
                custo = c2.number_input("Custo Unitário", min_value=0.01)
                giro = c2.number_input("Previsão Mensal", min_value=1)
                if st.form_submit_button("Cadastrar SKU"):
                    novo = pd.DataFrame([{
                        'SKU': f"PAP-{len(st.session_state.db_papelaria)+1:03d}",
                        'Produto': nome, 'Categoria': cat, 'Preco_Custo': custo,
                        'Giro_Mensal': giro, 'Estoque_Atual': 0, 'Status': 'Ativo'
                    }])
                    st.session_state.db_papelaria = pd.concat([st.session_state.db_papelaria, novo], ignore_index=True)
                    st.session_state.db_papelaria = inteligência_estoque(st.session_state.db_papelaria)
                    st.success(f"SKU {nome} pronto para receber estoque.")

        with tab_recebe:
            st.subheader("Entrada e Auditoria de NF")
            
            # Simulação de Bipagem da Chave de Acesso
            chave_nf = st.text_input("⚡ Bipar Chave de Acesso da NF (44 dígitos)")
            
            if chave_nf:
                st.divider()
                st.markdown(f"**NF Detectada:** `{chave_nf[-10:]}`")
                
                num_skus = st.number_input("Quantos SKUs diferentes nesta nota?", min_value=1, step=1)
                
                itens_nf = []
                for i in range(num_skus):
                    st.markdown(f"--- **Item {i+1}** ---")
                    col_a, col_b = st.columns(2)
                    sku_sel = col_a.selectbox(f"Selecionar SKU {i+1}", st.session_state.db_papelaria['Produto'].tolist(), key=f"sku_{i}")
                    qtd_item = col_b.number_input(f"Qtd para {sku_sel}", min_value=1, key=f"qtd_{i}")
                    itens_nf.append({'item': sku_sel, 'qtd_esperada': qtd_item})
                
                if st.button("🚀 Liberar Nota para Conferência"):
                    st.session_state.nfs_liberadas[chave_nf] = {
                        'status': 'Pendente',
                        'data': datetime.date.today(),
                        'itens': itens_nf
                    }
                    st.session_state.fluxo_ativo['conferencia'] = True
                    st.success("Nota enviada para o coletor do conferente!")

        with tab_bi:
            if not st.session_state.db_papelaria.empty:
                st.dataframe(st.session_state.db_papelaria, use_container_width=True)
                fig = px.bar(st.session_state.db_papelaria, x='Produto', y='Estoque_Atual', color='Classe_ABC', title="Saldo Real por SKU")
                st.plotly_chart(fig)

        with tab_config:
            st.subheader("Cadeados Operacionais")
            st.session_state.fluxo_ativo['expedicao'] = st.toggle("Liberar Expedição", value=st.session_state.fluxo_ativo['expedicao'])
            st.session_state.fluxo_ativo['distribuicao'] = st.toggle("Liberar Distribuição", value=st.session_state.fluxo_ativo['distribuicao'], disabled=not st.session_state.fluxo_ativo['expedicao'])

    # --- ÁREA DO CONFERENTE ---
    if perfil == "Conferente":
        st.title("📋 Terminal de Campo")
        
        opcoes = []
        if st.session_state.fluxo_ativo['conferencia']: opcoes.append("🔍 Conferência")
        opcoes.extend(["🏷️ Endereçamento", "📦 Armazenamento"])
        
        if st.session_state.fluxo_ativo['expedicao']: opcoes.append("📤 Expedição")
        if st.session_state.fluxo_ativo['distribuicao']: opcoes.append("🚚 Distribuição")
        
        tarefa = st.sidebar.radio("Tarefa:", opcoes)

        if tarefa == "🔍 Conferência":
            st.header("Notas Aguardando Contagem")
            if not st.session_state.nfs_liberadas:
                st.info("Nenhuma nota bipada pelo Administrador.")
            else:
                for chave, dados in st.session_state.nfs_liberadas.items():
                    with st.expander(f"NF: ...{chave[-6:]} - Status: {dados['status']}"):
                        for i, item in enumerate(dados['itens']):
                            st.write(f"**{item['item']}** | Esperado: {item['qtd_esperada']}")
                            qtd_contada = st.number_input(f"Contagem Real de {item['item']}", min_value=0, key=f"conf_{chave}_{i}")
                            
                            if st.button(f"Validar {item['item']}", key=f"btn_{chave}_{i}"):
                                if qtd_contada == item['qtd_esperada']:
                                    st.success("Bateu! Prossiga para etiquetagem.")
                                else:
                                    st.error(f"Divergência! Avisar ADM. (Faltam/Sobram {abs(qtd_contada - item['qtd_esperada'])} un)")

        elif tarefa == "🏷️ Endereçamento":
            st.header("Etiquetagem")
            sel_e = st.selectbox("Gerar Etiqueta:", st.session_state.db_papelaria['Produto'])
            idx_e = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_e][0]
            st.markdown(f"""
            <div style="background:white; border:4px solid black; padding:15px; color:black; text-align:center">
                <h2>{st.session_state.db_papelaria.at[idx_e, 'Zona_Endereco']}</h2>
                <p>{sel_e}</p>
            </div>
            """, unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.header("Confirmar Guardada")
            sel_a = st.selectbox("Produto Finalizado:", st.session_state.db_papelaria['Produto'])
            qtd_a = st.number_input("Qtd Guardada no Box", min_value=1)
            if st.button("Atualizar Estoque Real"):
                idx_a = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_a][0]
                st.session_state.db_papelaria.at[idx_a, 'Estoque_Atual'] += qtd_a
                st.success("Produto disponível para venda!")

        # Módulos de Expedição e Distribuição seguem a lógica anterior...
        elif tarefa == "📤 Expedição":
            st.subheader("Picking")
            st.info("Siga as orientações de retirada conforme o pedido.")

else:
    if senha: st.error("Acesso Negado.")
