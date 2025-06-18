import os
import requests
from dotenv import load_dotenv
import base64

load_dotenv()

def testar_conexao():
    try:
        # Obtém as credenciais do arquivo .env
        confluence_url = os.getenv("CONFLUENCE_URL")
        confluence_username = os.getenv("CONFLUENCE_USERNAME")
        confluence_token = os.getenv("CONFLUENCE_API_TOKEN")

        # Verifica se as variáveis de ambiente estão configuradas
        if not all([confluence_url, confluence_username, confluence_token]):
            print("❌ Erro: Algumas variáveis de ambiente estão faltando!")
            print("Verifique se você configurou:")
            print("- CONFLUENCE_URL")
            print("- CONFLUENCE_USERNAME")
            print("- CONFLUENCE_API_TOKEN")
            return

        # URL para testar a conexão
        url = f"{confluence_url}/rest/api/content"
        params = {
            'spaceKey': 'HELPDESK',
            'type': 'page',
            'limit': 100
        }

        # Configuração da autenticação básica
        auth = (confluence_username, confluence_token)
        
        # Headers necessários
        headers = {
            'Accept': 'application/json'
        }

        # Faz a requisição
        response = requests.get(url, params=params, auth=auth, headers=headers)
        
        # Verifica se a requisição foi bem sucedida
        response.raise_for_status()
        
        # Processa a resposta
        data = response.json()
        
        print("✅ Conexão bem sucedida!")
        print(f"📊 Total de páginas encontradas: {len(data.get('results', []))}")
        
        # Mostra algumas informações das primeiras páginas
        print("\n📑 Primeiras páginas encontradas:")
        for page in data.get('results', [])[:5]:
            print(f"- {page['title']} (ID: {page['id']})")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar ao Confluence: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Resposta do servidor: {e.response.text}")
        print("\nDicas de solução:")
        print("1. Verifique se a URL do Confluence está correta")
        print("2. Confirme se o token de API é válido")
        print("3. Verifique se o usuário tem permissões adequadas")
        print("4. Certifique-se de que o arquivo .env está no diretório correto")
        print("5. Verifique se você está usando o token de API e não a senha")

if __name__ == "__main__":
    testar_conexao() 