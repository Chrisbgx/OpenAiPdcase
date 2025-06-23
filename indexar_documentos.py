import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)
from azure.search.documents import SearchClient
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

PDF_FOLDER = "kbs_confluence"

def extrair_texto_com_paginas(caminho):
    """Extrai texto e mantém informação da página"""
    leitor = PdfReader(caminho)
    paginas_texto = []
    
    for num_pagina, pagina in enumerate(leitor.pages, 1):
        texto_pagina = pagina.extract_text()
        if texto_pagina.strip():
            paginas_texto.append({
                'texto': texto_pagina,
                'pagina': num_pagina
            })
    
    return paginas_texto

def sanitizar_nome(nome):
    """Remove acentos e caracteres especiais"""
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'[^a-zA-Z0-9_\-=]', '_', nome)

def criar_indice_melhorado():
    """Cria índice com campos de metadata aprimorados"""
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    
    campos = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="file_name", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, sortable=True, filterable=True),
        SimpleField(name="chunk_id", type=SearchFieldDataType.Int32, sortable=True, filterable=True),
        SimpleField(name="total_pages", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="file_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="created_date", type=SearchFieldDataType.DateTimeOffset, sortable=True, filterable=True),
    ]
    
    index = SearchIndex(name=AZURE_SEARCH_INDEX, fields=campos)
    
    if AZURE_SEARCH_INDEX in [i.name for i in index_client.list_indexes()]:
        index_client.delete_index(AZURE_SEARCH_INDEX)
        print("⚠️ Índice anterior deletado.")
    
    index_client.create_index(index)
    print("✅ Novo índice melhorado criado com metadata rica.")

def enviar_documentos_melhorado(paginas_texto, file_name):
    """Envia documentos com metadata rica"""
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, 
                               index_name=AZURE_SEARCH_INDEX, 
                               credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    
    safe_file_name = sanitizar_nome(file_name)
    total_paginas = len(paginas_texto)
    docs = []
    
    chunk_counter = 0
    for pagina_info in paginas_texto:
        texto_pagina = pagina_info['texto']
        num_pagina = pagina_info['pagina']
        
        chunk_size = 1200
        overlap = 200
        
        if len(texto_pagina) <= chunk_size:
            doc = {
                "id": f"{safe_file_name}_p{num_pagina}_c{chunk_counter}",
                "content": texto_pagina,
                "file_name": file_name,
                "filename": file_name,
                "page_number": num_pagina,
                "chunk_id": chunk_counter,
                "total_pages": total_paginas,
                "file_type": "PDF",
                "created_date": "2024-01-01T00:00:00Z"
            }
            docs.append(doc)
            chunk_counter += 1
        else:
            for i in range(0, len(texto_pagina), chunk_size - overlap):
                chunk = texto_pagina[i:i + chunk_size]
                if chunk.strip():
                    doc = {
                        "id": f"{safe_file_name}_p{num_pagina}_c{chunk_counter}",
                        "content": chunk,
                        "file_name": file_name,
                        "filename": file_name,
                        "page_number": num_pagina,
                        "chunk_id": chunk_counter,
                        "total_pages": total_paginas,
                        "file_type": "PDF", 
                        "created_date": "2024-01-01T00:00:00Z"
                    }
                    docs.append(doc)
                    chunk_counter += 1
    
    batch_size = 50
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        search_client.upload_documents(documents=batch)
        
    print(f"✅ {len(docs)} chunks enviados ao índice para {file_name} ({total_paginas} páginas).")

def indexar_pdf_melhorado(nome_arquivo):
    """Indexa PDF com metadata rica"""
    caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
    
    if os.path.getsize(caminho_pdf) == 0:
        print(f"⚠️ Arquivo vazio ignorado: {nome_arquivo}")
        return 'vazio', nome_arquivo
    
    try:
        paginas_texto = extrair_texto_com_paginas(caminho_pdf)
        if not paginas_texto:
            print(f"⚠️ Nenhum texto extraído de: {nome_arquivo}")
            return 'vazio', nome_arquivo
            
        enviar_documentos_melhorado(paginas_texto, nome_arquivo)
        return 'indexado', nome_arquivo
    except Exception as e:
        print(f"❌ Erro ao processar {nome_arquivo}: {str(e)}")
        return 'erro', nome_arquivo

def indexar_varios_pdfs_melhorado():
    """Indexa múltiplos PDFs com processamento paralelo"""
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ Erro: A pasta {PDF_FOLDER} não existe!")
        return

    pdfs = [nome for nome in os.listdir(PDF_FOLDER) if nome.lower().endswith('.pdf')]
    total_pdfs = len(pdfs)
    print(f"\n📚 Total de PDFs encontrados: {total_pdfs}")

    resultados = {'indexado': [], 'vazio': [], 'erro': []}
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_nome = {executor.submit(indexar_pdf_melhorado, nome): nome for nome in pdfs}
        for i, future in enumerate(as_completed(future_to_nome), 1):
            status, nome_arquivo = future.result()
            resultados[status].append(nome_arquivo)
            print(f"[{i}/{total_pdfs}] {status.upper()}: {nome_arquivo}")

    print(f"\n✅ PDFs indexados: {len(resultados['indexado'])}")
    print(f"⚠️ PDFs vazios: {len(resultados['vazio'])}")  
    print(f"❌ PDFs com erro: {len(resultados['erro'])}")

def validar_configuracao():
    """Valida variáveis de ambiente necessárias"""
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
    
    print("🚀 Iniciando criação de índice MELHORADO com metadata rica...")
    print("⚠️ ATENÇÃO: Isso irá RECRIAR completamente o índice!")
    
    confirmacao = input("Deseja continuar? (s/N): ").lower().strip()
    if confirmacao not in ['s', 'sim', 'y', 'yes']:
        print("❌ Operação cancelada pelo usuário.")
        exit(0)
    
    criar_indice_melhorado()
    indexar_varios_pdfs_melhorado()
    print("\n✅ Índice melhorado criado com sucesso!")
    print("🎯 Agora o sistema RAG terá metadata rica (página, chunks, etc.)") 