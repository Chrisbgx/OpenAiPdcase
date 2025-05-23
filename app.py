import streamlit as st
from meu_script_rag import perguntar_ao_modelo, buscar_documentos
from dotenv import load_dotenv
import os

# Configuração da página
st.set_page_config(
    page_title="Sistema RAG - Documentos Técnicos",
    page_icon="📚",
    layout="wide"
)

# Carregar variáveis de ambiente
load_dotenv()

# Título e descrição
st.title("📚 Sistema RAG - Documentos Técnicos")
st.write(
    "Este sistema permite fazer perguntas sobre documentos técnicos usando IA. "
    "Digite sua pergunta abaixo e continue a conversa normalmente."
)

# Inicializar histórico na sessão
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Layout principal
with st.container():
    pergunta = st.text_area("Digite sua pergunta:", height=80)
    col1, col2 = st.columns([1, 5])
    with col1:
        enviar = st.button("Enviar Pergunta", use_container_width=True)
    st.write("")  # Espaço

    if enviar and pergunta.strip():
        with st.spinner("Buscando resposta..."):
            trechos = buscar_documentos(pergunta)
            resposta = perguntar_ao_modelo(pergunta)
        # Salvar pergunta e resposta no histórico
        st.session_state.chat_history.append({
            "pergunta": pergunta,
            "resposta": resposta,
            "file_name": trechos[0].get("file_name", None) if trechos and isinstance(trechos[0], dict) else None
        })

# Exibir histórico de chat
for chat in st.session_state.chat_history:
    st.markdown(f"**Você:** {chat['pergunta']}")
    if chat["file_name"] and os.path.exists(chat["file_name"]):
        with st.expander(f"Ver PDF do contexto encontrado: {chat['file_name']}"):
            st.pdf(chat["file_name"])
    st.markdown("**Resposta:**")
    st.markdown(chat["resposta"])
    st.markdown("---")

st.divider()
with st.expander("ℹ️ Sobre o Sistema"):
    st.markdown("""
    - **RAG (Retrieval Augmented Generation)**: Busca e gera respostas com base nos documentos indexados.
    - **Azure Cognitive Search**: Indexação e busca dos documentos.
    - **Azure OpenAI**: Geração de respostas com IA.
    """)
