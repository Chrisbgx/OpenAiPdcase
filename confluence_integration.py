import os
import requests
from dotenv import load_dotenv
import time
import hashlib

load_dotenv()

# Carregando todas as variáveis do arquivo .env
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

# Configuração da pasta para salvar os PDFs
PDF_FOLDER = "kbs_confluence"
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

def calcular_hash_arquivo(caminho_arquivo):
    """Calcula o hash MD5 de um arquivo."""
    hash_md5 = hashlib.md5()
    with open(caminho_arquivo, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def verificar_kb_existente(page_id, title):
    """Verifica se o KB já existe na pasta e retorna o caminho se existir."""
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    pdf_filename = f"KB_{page_id}_{safe_title}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
    
    if os.path.exists(pdf_path):
        return pdf_path
    return None

def buscar_paginas_confluence():
    # URL específica para buscar páginas do espaço
    url = f"{CONFLUENCE_URL}/rest/api/content"
    all_pages = []
    start = 0
    limit = 100  # Número de páginas por requisição
    
    while True:
        params = {
            'spaceKey': CONFLUENCE_SPACE_KEY,
            'type': 'page',
            'limit': limit,
            'start': start
        }
        
        headers = {
            'Accept': 'application/json'
        }
        
        auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        
        try:
            response = requests.get(url, params=params, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()
            
            # Adiciona as páginas encontradas à lista
            pages = data.get('results', [])
            all_pages.extend(pages)
            
            # Verifica se há mais páginas para buscar
            if len(pages) < limit:
                break
                
            # Atualiza o índice inicial para a próxima página
            start += limit
            
            print(f"📥 Baixadas {len(all_pages)} páginas até agora...")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar páginas: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Resposta do servidor: {e.response.text}")
            break
    
    return all_pages

def baixar_pdf_confluence(page_id, title):
    try:
        # Verifica se o KB já existe
        pdf_path = verificar_kb_existente(page_id, title)
        if pdf_path:
            print(f"📄 KB já existe: {os.path.basename(pdf_path)}")
            return True

        # URL para download direto do PDF
        url = f"{CONFLUENCE_URL}/spaces/flyingpdf/pdfpageexport.action?pageId={page_id}"
        
        # Configuração da autenticação
        auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        
        # Faz o download do PDF
        response = requests.get(url, auth=auth, stream=True)
        response.raise_for_status()
        
        # Verifica se o conteúdo é realmente um PDF
        if 'application/pdf' not in response.headers.get('content-type', '').lower():
            print(f"⚠️ A resposta não é um PDF para a página {title}")
            return False
        
        # Cria nome do arquivo PDF
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        pdf_filename = f"KB_{page_id}_{safe_title}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
        
        # Salva o PDF
        with open(pdf_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"✅ PDF baixado: {pdf_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao baixar PDF da página {title}: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Resposta do servidor: {e.response.text}")
        return False

def processar_paginas_confluence():
    pages = buscar_paginas_confluence()
    pdfs_baixados = []
    pdfs_existentes = []
    
    print(f"\n📁 Salvando PDFs na pasta: {PDF_FOLDER}")
    print(f"📚 Total de páginas encontradas: {len(pages)}")
    
    for i, page in enumerate(pages, 1):
        page_id = page['id']
        title = page['title']
        
        print(f"\n[{i}/{len(pages)}] Processando: {title}")
        
        # Verifica se o KB já existe
        pdf_path = verificar_kb_existente(page_id, title)
        if pdf_path:
            pdfs_existentes.append(title)
            continue
        
        if baixar_pdf_confluence(page_id, title):
            pdfs_baixados.append(title)
            # Pequena pausa para não sobrecarregar o servidor
            time.sleep(1)
    
    return pdfs_baixados, pdfs_existentes

def validar_configuracao():
    variaveis_requeridas = {
        "CONFLUENCE_URL": CONFLUENCE_URL,
        "CONFLUENCE_USERNAME": CONFLUENCE_USERNAME,
        "CONFLUENCE_API_TOKEN": CONFLUENCE_API_TOKEN,
        "CONFLUENCE_SPACE_KEY": CONFLUENCE_SPACE_KEY
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
        
    print("🚀 Iniciando download dos PDFs do Confluence...")
    pdfs_baixados, pdfs_existentes = processar_paginas_confluence()
    
    print(f"\n✅ Processamento concluído!")
    print(f"📥 PDFs baixados: {len(pdfs_baixados)}")
    print(f"📄 PDFs já existentes: {len(pdfs_existentes)}")
    
    if pdfs_baixados:
        print("\n📝 Novos PDFs baixados:")
        for pdf in pdfs_baixados:
            print(f"- {pdf}")
    
    if pdfs_existentes:
        print("\n📝 PDFs já existentes:")
        for pdf in pdfs_existentes:
            print(f"- {pdf}") 