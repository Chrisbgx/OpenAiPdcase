import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import openai
from dotenv import load_dotenv

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # ex: https://pocpdcase.openai.azure.com/
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # ex: gpt-35-turbo ou outro nome de deployment

def buscar_documentos(pergunta):
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT,
                                 index_name=AZURE_SEARCH_INDEX,
                                 credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    resultados = search_client.search(pergunta)
    trechos = [doc['content'] for doc in resultados]
    return trechos  # retorna lista de trechos

def perguntar_ao_modelo(pergunta):
    contexto = buscar_documentos(pergunta)
    
    prompt = f"""Você é um assistente especializado em documentos técnicos. Use o contexto abaixo para responder com precisão e objetividade.

Contexto:
{contexto}

Pergunta: {pergunta}
Resposta:"""

    openai.api_type = "azure"
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_version = "2024-12-01-preview"
    openai.api_key = AZURE_OPENAI_KEY

    resposta = openai.ChatCompletion.create(
        engine=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500
    )

    return resposta["choices"][0]["message"]["content"]

if __name__ == "__main__":
    pergunta = input("Digite sua pergunta: ")
    resposta = perguntar_ao_modelo(pergunta)
    print("\n📘 Resposta do modelo:\n", resposta)
