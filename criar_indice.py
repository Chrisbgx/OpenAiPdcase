import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)
from azure.search.documents import SearchClient
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

def extrair_texto(caminho):
    leitor = PdfReader(caminho)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text() + "\n"
    return texto

def criar_indice():
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    campos = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="file_name", type=SearchFieldDataType.String)
    ]
    index = SearchIndex(name=AZURE_SEARCH_INDEX, fields=campos)
    if AZURE_SEARCH_INDEX in [i.name for i in index_client.list_indexes()]:
        index_client.delete_index(AZURE_SEARCH_INDEX)
        print("⚠️ Índice anterior deletado.")
    index_client.create_index(index)
    print("✅ Novo índice criado.")

def enviar_documentos(texto, file_name):
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=AZURE_SEARCH_INDEX, credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    chunks = [texto[i:i+1000] for i in range(0, len(texto), 1000)]
    safe_file_name = file_name.replace('.', '_')
    docs = [{"id": f"{safe_file_name}_doc_{i}", "content": chunk, "file_name": file_name} for i, chunk in enumerate(chunks)]
    resultado = search_client.upload_documents(documents=docs)
    print(f"✅ {len(resultado)} documentos enviados ao índice para {file_name}.")

def indexar_varios_pdfs(pasta):
    for nome_arquivo in os.listdir(pasta):
        if nome_arquivo.lower().endswith('.pdf'):
            caminho_pdf = os.path.join(pasta, nome_arquivo)
            if os.path.getsize(caminho_pdf) == 0:
                print(f"Arquivo vazio ignorado: {nome_arquivo}")
                continue
            print(f"Indexando: {nome_arquivo}")
            texto_extraido = extrair_texto(caminho_pdf)
            enviar_documentos(texto_extraido, nome_arquivo)

if __name__ == "__main__":
    criar_indice()
    indexar_varios_pdfs(".")
