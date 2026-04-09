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
    st.session_state.nfs_liberadas = {} 

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

if (perfil == "Administrador" and senha == "admin123") or (perfil == "Conferente" and senha == "conf123"):
    
    # --- ÁREA DO ADMINISTRADOR ---
    if perfil == "Administrador":
        st.title("🛡️ Gestão de Recebimento")
        tab_cad, tab_recebe, tab_bi = st.tabs(["📝 Cadastro", "📑 Bipar NF", "📊 Inventário"])

        with tab_cad:
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
                    st.success(f"{nome} cadastrado!")

        with tab_recebe:
            chave_nf = st.text_input("⚡ Bipar Chave da NF")
            if chave_nf:
                num_skus = st.number_input("Qtd de SKUs na nota", min_value=1, step=1)
                itens_nf = []
                for i in range(num_skus):
                    col_a, col_b = st.columns(2)
                    sku_sel = col_a.selectbox(f"SKU {i+1}", st.session_state.db_papelaria['Produto'].tolist(), key=f"sku_{i}")
                    qtd_item = col_b.number_input(f"Qtd {sku_sel}", min_value=1, key=f"qtd_{i}")
                    itens_nf.append({'item': sku_sel, 'qtd_esperada': qtd_item, 'validado': False})
                
                if st.button("🚀 Liberar para Conferência"):
                    st.session_state.nfs_liberadas[chave_nf] = {'status': 'Pendente', 'itens': itens_nf}
                    st.success("Nota enviada ao Conferente!")

        with tab_bi:
            st.dataframe(st.session_state.db_papelaria, use_container_width=True)

    # --- ÁREA DO CONFERENTE ---
    if perfil == "Conferente":
        st.title("📋 Terminal Operacional")
        tarefa = st.sidebar.radio("Tarefa:", ["🔍 Conferência", "🏷️ Endereçamento", "📦 Armazenamento"])

        if tarefa == "🔍 Conferência":
            st.header("Notas para Contagem")
            
            # Filtra apenas notas que ainda possuem itens não validados
            nfs_ativas = {k: v for k, v in st.session_state.nfs_liberadas.items() if any(not i['validado'] for i in v['itens'])}
            
            if not nfs_ativas:
                st.info("✅ Tudo limpo! Nenhuma nota pendente de conferência.")
            else:
                for chave, dados in nfs_ativas.items():
                    with st.expander(f"📦 NF: ...{chave[-6:]}", expanded=True):
                        for i, item in enumerate(dados['itens']):
                            # O item só aparece se ainda não foi validado
                            if not item['validado']:
                                st.write(f"👉 **Contar:** {item['item']}")
                                col1, col2 = st.columns([2, 1])
                                qtd_c = col1.number_input(f"Qtd Real de {item['item']}", min_value=0, key=f"c_{chave}_{i}")
                                if col2.button("Validar", key=f"b_{chave}_{i}"):
                                    if qtd_c == item['qtd_esperada']:
                                        item['validado'] = True
                                        st.rerun() # Atualiza a tela para remover o item validado
                                    else:
                                        st.error("Divergência detectada!")

        elif tarefa == "🏷️ Endereçamento":
            st.header("Etiquetas Pendentes")
            # Só permite endereçar itens que já foram validados na conferência
            itens_prontos = []
            for nf in st.session_state.nfs_liberadas.values():
                for i in nf['itens']:
                    if i['validado']: itens_prontos.append(i['item'])
            
            if not itens_prontos:
                st.warning("Nenhum item validado para endereçamento.")
            else:
                sel_e = st.selectbox("Gerar Etiqueta:", list(set(itens_prontos)))
                idx_e = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_e][0]
                st.markdown(f"""<div style="background:white; border:4px solid black; padding:15px; color:black; text-align:center">
                    <h2>{st.session_state.db_papelaria.at[idx_e, 'Zona_Endereco']}</h2><p>{sel_e}</p></div>""", unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.header("Guardar no Estoque")
            sel_a = st.selectbox("Produto para Armazenar:", st.session_state.db_papelaria['Produto'])
            qtd_a = st.number_input("Qtd Guardada", min_value=1)
            if st.button("Finalizar Ciclo"):
                idx_a = st.session_state.db_papelaria.index[st.session_state.db_papelaria['Produto'] == sel_a][0]
                st.session_state.db_papelaria.at[idx_a, 'Estoque_Atual'] += qtd_a
                st.success(f"{sel_a} agora está disponível no saldo real!")

else:
    st.warning("Por favor, faça o login.")
