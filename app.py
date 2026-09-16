import streamlit as st
import pandas as pd
from pymongo import MongoClient
import io

# ---------------------------------------------------------
# Configuração da Página e Viewport Mobile
# ---------------------------------------------------------
st.set_page_config(
    page_title="Cardápio Escolar NutriEscola",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="auto"
)

# Estilização CSS responsiva
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .main-header {
        font-size: calc(1.5rem + 1vw);
        color: #2E7D32;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: calc(0.9rem + 0.3vw);
        color: #555555;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .meal-card {
        background-color: #F9FBE7;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 6px solid #81C784;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .meal-title {
        font-weight: 700;
        color: #1B5E20;
        font-size: 1.1rem;
    }
    .meal-content {
        font-size: 0.95rem;
        color: #333333;
        margin-top: 8px;
    }
    @media (max-width: 640px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        .stButton>button {
            width: 100%;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Conexão com MongoDB Atlas (Com Caching)
# ---------------------------------------------------------
@st.cache_resource
def init_connection():
    # Pega a URL salva em st.secrets (seguro)
    mongo_uri = st.secrets["MONGO_URI"]
    return MongoClient(mongo_uri)

try:
    client = init_connection()
    db = client["nutriescola_db"]
    col_alunos = db["contagem_alunos"]
    col_historico = db["historico_presenca"]
    col_cardapio = db["cardapio"]
except Exception as e:
    st.error(f"Erro ao conectar ao MongoDB: {e}")
    st.stop()

# ---------------------------------------------------------
# Carga Inicial de Dados Padrão (se o banco estiver vazio)
# ---------------------------------------------------------
if col_alunos.count_documents({}) == 0:
    dados_iniciais = [
        {"Turma": "Berçário / Maternal", "Total Alunos": 25, "Intolerantes a Lactose": 2, "Celiacos (Glúten)": 1},
        {"Turma": "Infantil II e III", "Total Alunos": 40, "Intolerantes a Lactose": 3, "Celiacos (Glúten)": 0},
        {"Turma": "1º ao 5º Ano (Fundamental I)", "Total Alunos": 120, "Intolerantes a Lactose": 8, "Celiacos (Glúten)": 3},
        {"Turma": "6º ao 9º Ano (Fundamental II)", "Total Alunos": 110, "Intolerantes a Lactose": 5, "Celiacos (Glúten)": 2},
        {"Turma": "Ensino Médio", "Total Alunos": 95, "Intolerantes a Lactose": 4, "Celiacos (Glúten)": 1},
    ]
    col_alunos.insert_many(dados_iniciais)

# Funções auxiliares para ler dados
def carregar_alunos():
    dados = list(col_alunos.find({}, {"_id": 0}))
    return pd.DataFrame(dados)

def carregar_historico():
    dados = list(col_historico.find({}, {"_id": 0}))
    return pd.DataFrame(dados)

CARDAPIO_PADRAO = {
    "Segunda-feira": {"Café da Manhã": "Leite com cacau 100% e pão com manteiga", "Almoço": "Arroz, feijão, carne moída", "Lanche da Tarde": "Banana com aveia", "Alergênicos": "Contém glúten e lactose"},
    "Terça-feira": {"Café da Manhã": "Vitamina de morango", "Almoço": "Arroz, feijão preto, frango grelhado", "Lanche da Tarde": "Maçã assada", "Alergênicos": "Contém lactose"},
    "Quarta-feira": {"Café da Manhã": "Suco de laranja e biscoito polvilho", "Almoço": "Macarrão à bolonhesa", "Lanche da Tarde": "Salada de frutas", "Alergênicos": "Contém glúten"},
    "Quinta-feira": {"Café da Manhã": "Leite e pão de queijo", "Almoço": "Escondidinho de frango", "Lanche da Tarde": "Suco de uva e torrada", "Alergênicos": "Contém lactose"},
    "Sexta-feira": {"Café da Manhã": "Iogurte com mel", "Almoço": "Peixe grelhado e purê", "Lanche da Tarde": "Bolo de cenoura", "Alergênicos": "Contém peixe"}
}

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429982.png", width=80)
    st.title("NutriEscola Cloud")

    etapa_ensino = st.selectbox("🏫 Etapa Escolar:", ["Ensino Infantil", "Ensino Fundamental e Médio"])
    dia_semana = st.select_slider("📅 Dia da Semana:", options=["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"])

    st.divider()

    with st.expander("✍️ Lançar Presença Diária", expanded=False):
        with st.form("form_presenca"):
            data_p = st.date_input("Data")
            turmas_list = list(carregar_alunos()["Turma"].unique()) if not carregar_alunos().empty else []
            turma_p = st.selectbox("Turma:", turmas_list + ["+ Nova Turma..."])
            if turma_p == "+ Nova Turma...":
                turma_p = st.text_input("Nome da Nova Turma:")

            q_presentes = st.number_input("Presentes:", min_value=0, value=30)
            q_lactose = st.number_input("Lactose:", min_value=0, value=0)
            q_gluten = st.number_input("Glúten:", min_value=0, value=0)
            obs = st.text_input("Obs:")

            if st.form_submit_button("📌 Salvar no Banco", use_container_width=True):
                if turma_p.strip():
                    col_alunos.update_one(
                        {"Turma": turma_p},
                        {"$set": {"Turma": turma_p, "Total Alunos": q_presentes, "Intolerantes a Lactose": q_lactose, "Celiacos (Glúten)": q_gluten}},
                        upsert=True
                    )
                    col_historico.insert_one({
                        "Data": data_p.strftime("%d/%m/%Y"),
                        "Turma": turma_p,
                        "Alunos Presentes": q_presentes,
                        "Lactose": q_lactose,
                        "Glúten": q_gluten,
                        "Observações": obs
                    })
                    st.success("Dados salvos no MongoDB!")
                    st.rerun()

# ---------------------------------------------------------
# Corpo Principal
# ---------------------------------------------------------
st.markdown("<div class='main-header'>🍎 Cardápio Escolar NutriEscola</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Sincronizado na Nuvem com MongoDB</div>", unsafe_allow_html=True)

refeicao = CARDAPIO_PADRAO.get(dia_semana, CARDAPIO_PADRAO["Segunda-feira"])

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='meal-card'><div class='meal-title'>🌅 Café da Manhã</div><div class='meal-content'>{refeicao['Café da Manhã']}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='meal-card'><div class='meal-title'>🍽️ Almoço</div><div class='meal-content'>{refeicao['Almoço']}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='meal-card'><div class='meal-title'>🍎 Lanche</div><div class='meal-content'>{refeicao['Lanche da Tarde']}</div></div>", unsafe_allow_html=True)

st.divider()

aba1, aba2 = st.tabs(["👥 Presença e Turmas", "📜 Histórico"])

with aba1:
    df_alunos = carregar_alunos()
    st.subheader("👥 Contagem de Alunos (Salva Automaticamente)")
    st.dataframe(df_alunos, use_container_width=True)

with aba2:
    df_hist = carregar_historico()
    st.subheader("📜 Histórico de Lançamentos")
    st.dataframe(df_hist, use_container_width=True)