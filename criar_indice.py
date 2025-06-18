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

# Configuração da pasta dos PDFs
PDF_FOLDER = "kbs_confluence"

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

def indexar_varios_pdfs():
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ Erro: A pasta {PDF_FOLDER} não existe!")
        return

    total_pdfs = 0
    pdfs_processados = 0
    
    # Conta o total de PDFs
    for nome_arquivo in os.listdir(PDF_FOLDER):
        if nome_arquivo.lower().endswith('.pdf'):
            total_pdfs += 1
    
    print(f"\n📚 Total de PDFs encontrados: {total_pdfs}")
    
    for nome_arquivo in os.listdir(PDF_FOLDER):
        if nome_arquivo.lower().endswith('.pdf'):
            caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
            if os.path.getsize(caminho_pdf) == 0:
                print(f"⚠️ Arquivo vazio ignorado: {nome_arquivo}")
                continue
                
            pdfs_processados += 1
            print(f"\n[{pdfs_processados}/{total_pdfs}] Indexando: {nome_arquivo}")
            
            try:
                texto_extraido = extrair_texto(caminho_pdf)
                enviar_documentos(texto_extraido, nome_arquivo)
            except Exception as e:
                print(f"❌ Erro ao processar {nome_arquivo}: {str(e)}")

def validar_configuracao():
    variaveis_requeridas = {
        "AZURE_SEARCH_ENDPOINT": AZURE_SEARCH_ENDPOINT,
        "AZURE_SEARCH_KEY": AZURE_SEARCH_KEY,
        "AZURE_SEARCH_INDEX": AZURE_SEARCH_INDEX
    }
    
    variaveis_faltantes = [var for var, valor in variaveis_requeridas.items() if not valor]
    
    if variaveis_faltantes:
        print("❌ Erro: As seguintes variáveis de ambiente estão faltando no arquivo .env:")
        for var in variaveis_faltantes:
            print(f"  - {var}")
        return False
    return True

if __name__ == "__main__":
    if not validar_configuracao():
        exit(1)
        
    print("🚀 Iniciando indexação dos PDFs...")
    criar_indice()
    indexar_varios_pdfs()
    print("\n✅ Processamento concluído!")
