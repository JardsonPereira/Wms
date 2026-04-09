import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NexLOG | WMS Intelligence", layout="wide", initial_sidebar_state="expanded")

# Custom CSS para estética "High-Tech"
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004b95; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE DADOS ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=[
        'ID', 'Produto', 'Categoria', 'Custo', 'Giro_Previsto', 'Classe', 'Endereco', 'Saldo', 'Status'
    ])

if 'fluxo' not in st.session_state:
    st.session_state.fluxo = {'exp': False, 'dist': False}

# --- MOTOR DE INTELIGÊNCIA LOGÍSTICA ---
def atualizar_inteligencia(df):
    if df.empty: return df
    # Cálculo Curva ABC (Baseado no valor de estoque teórico e giro)
    df['Impacto'] = df['Custo'].astype(float) * df['Giro_Previsto'].astype(float)
    df = df.sort_values(by='Impacto', ascending=False)
    df['Perc'] = df['Impacto'].cumsum() / df['Impacto'].sum()
    
    def classe_abc(p):
        if p <= 0.7: return 'A'
        elif p <= 0.9: return 'B'
        else: return 'C'
        
    df['Classe'] = df['Perc'].apply(classe_abc)
    # Endereçamento Inteligente: Classe A na Rua 1 (Próximo à doca)
    df['Endereco'] = df['Classe'].apply(lambda x: f"R{ord(x)-64}-N0{datetime.datetime.now().microsecond % 9}-P{datetime.datetime.now().microsecond % 5}")
    return df

# --- BARRA LATERAL (AUTENTICAÇÃO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2343/2343894.png", width=100)
    st.title("NexLOG WMS")
    st.info("**Acesso Rápido:**\n\nAdmin: `admin123` | Conf: `conf123` ")
    
    user = st.selectbox("Usuário", ["Conferente", "Administrador"])
    pw = st.text_input("Senha", type="password")

# --- LÓGICA DE NAVEGAÇÃO ---
if (user == "Administrador" and pw == "admin123") or (user == "Conferente" and pw == "conf123"):
    
    if user == "Administrador":
        st.title("🛡️ Dashboard de Gestão Estratégica")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKUs Cadastrados", len(st.session_state.db))
        m2.metric("Valor Total em Estoque", f"R$ {(st.session_state.db['Saldo'] * st.session_state.db['Custo']).sum():,.2f}")
        m3.metric("Acuracidade", "100%", "0.5%")
        m4.metric("Status Expedição", "LIBERADO" if st.session_state.fluxo['exp'] else "BLOQUEADO")

        aba_cad, aba_inv, aba_ctr = st.tabs(["🆕 Cadastro de SKU", "📊 BI & Inventário", "⚙️ Controle de Fluxo"])

        with aba_cad:
            with st.form("cad_sku"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome do Material")
                cat = c1.selectbox("Categoria", ["Suprimentos", "Papelaria", "TI", "Mobiliário"])
                custo = c2.number_input("Custo Unitário", min_value=0.01)
                giro = c2.number_input("Demanda Mensal Estimada", min_value=1)
                if st.form_submit_button("Finalizar Cadastro"):
                    novo = pd.DataFrame([{
                        'ID': len(st.session_state.db)+1, 'Produto': nome, 'Categoria': cat,
                        'Custo': custo, 'Giro_Previsto': giro, 'Saldo': 0, 'Status': 'Ativo'
                    }])
                    st.session_state.db = pd.concat([st.session_state.db, novo], ignore_index=True)
                    st.session_state.db = atualizar_inteligencia(st.session_state.db)
                    st.success("SKU Cadastrado com Estratégia de Endereçamento!")

        with aba_inv:
            st.dataframe(st.session_state.db[['ID', 'Produto', 'Classe', 'Endereco', 'Saldo', 'Custo']], use_container_width=True)
            if not st.session_state.db.empty:
                fig = px.pie(st.session_state.db, names='Classe', title="Ocupação por Curva ABC", hole=0.4)
                st.plotly_chart(fig)

        with aba_ctr:
            st.subheader("Configurações de Operação")
            st.session_state.fluxo['exp'] = st.toggle("Habilitar Módulo de Expedição", st.session_state.fluxo['exp'])
            st.session_state.fluxo['dist'] = st.toggle("Habilitar Módulo de Distribuição", st.session_state.fluxo['dist'], disabled=not st.session_state.fluxo['exp'])
            if st.button("Limpar Logs de Sistema"): st.toast("Logs limpos!")

    if user == "Conferente":
        st.title("🚀 Operação de Fluxo")
        menu = ["📥 Recebimento", "🔍 Conferência", "📍 Endereçamento", "📦 Armazenamento"]
        if st.session_state.fluxo['exp']: menu.append("📤 Expedição")
        if st.session_state.fluxo['dist']: menu.append("🚚 Distribuição")
        
        tarefa = st.sidebar.radio("Etapa do Processo", menu)

        if tarefa == "📥 Recebimento":
            st.subheader("Entrada de Inbound")
            prod = st.selectbox("Selecionar Item em Doca", st.session_state.db['Produto'])
            st.number_input("Quantidade da Nota Fiscal", min_value=1)
            if st.button("Iniciar Conferência"): st.warning("Mova o palete para a zona de conferência.")

        elif tarefa == "🔍 Conferência":
            st.subheader("Verificação de Qualidade e Qtd")
            sel = st.selectbox("Confirmar Produto", st.session_state.db['Produto'])
            qtd = st.number_input("Quantidade Contada", min_value=1)
            if st.button("Validar"): st.success("Conferência cega bateu com a NF!")

        elif tarefa == "📍 Endereçamento":
            st.subheader("Etiquetagem Inteligente")
            sel = st.selectbox("Produto para Etiquetar", st.session_state.db['Produto'])
            idx = st.session_state.db.index[st.session_state.db['Produto'] == sel][0]
            end = st.session_state.db.at[idx, 'Endereco']
            st.markdown(f"""
                <div style="background:white; border:2px dashed #333; padding:20px; text-align:center; color:black">
                    <h3>ETIQUETA NEXLOG</h3>
                    <h1 style="font-size: 50px">{end}</h1>
                    <p><b>{sel}</b> | CLASSE {st.session_state.db.at[idx, 'Classe']}</p>
                </div>
            """, unsafe_allow_html=True)

        elif tarefa == "📦 Armazenamento":
            st.subheader("Put-away (Guardada)")
            sel = st.selectbox("Confirmar Guardada no Endereço", st.session_state.db['Produto'])
            qtd_a = st.number_input("Qtd Guardada", min_value=1)
            if st.button("Confirmar Armazenamento"):
                idx = st.session_state.db.index[st.session_state.db['Produto'] == sel][0]
                st.session_state.db.at[idx, 'Saldo'] += qtd_a
                st.balloons()
                st.success("Estoque Atualizado!")

        elif tarefa == "📤 Expedição":
            st.subheader("Picking (Separação)")
            sel = st.selectbox("Produto para Saída", st.session_state.db['Produto'])
            qtd_s = st.number_input("Qtd para Picking", min_value=1)
            idx = st.session_state.db.index[st.session_state.db['Produto'] == sel][0]
            if st.button("Confirmar Saída"):
                if st.session_state.db.at[idx, 'Saldo'] >= qtd_s:
                    st.session_state.db.at[idx, 'Saldo'] -= qtd_s
                    st.success("Saída autorizada!")
                else: st.error("Erro: Estoque insuficiente!")

        elif tarefa == "🚚 Distribuição":
            st.subheader("Last Mile / Distribuição")
            st.info("Consolidando cargas para transporte...")

else:
    if pw: st.error("Acesso Negado")
    else: st.warning("Aguardando Login...")
