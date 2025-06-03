# Sistema RAG - Documentos Técnicos

Este é um sistema de RAG (Retrieval Augmented Generation) que permite fazer perguntas sobre documentos técnicos usando IA. O sistema utiliza Azure Cognitive Search para indexação e busca de documentos, e Azure OpenAI para geração de respostas.

## Pré-requisitos

- Python 3.8 ou superior
- Conta no Azure com acesso a:
  - Azure Cognitive Search
  - Azure OpenAI Service
- PDFs técnicos para indexação

## Configuração do Ambiente

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
cd [NOME_DO_DIRETORIO]
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```env
AZURE_SEARCH_ENDPOINT=sua_url_do_azure_search
AZURE_SEARCH_KEY=sua_chave_do_azure_search
AZURE_SEARCH_INDEX=nome_do_seu_indice

AZURE_OPENAI_ENDPOINT=sua_url_do_azure_openai
AZURE_OPENAI_KEY=sua_chave_do_azure_openai
AZURE_OPENAI_DEPLOYMENT=nome_do_seu_deployment
```

## Indexação dos Documentos

1. Coloque seus arquivos PDF na raiz do projeto

2. Execute o script de criação do índice:
```bash
python criar_indice.py
```

Este script irá:
- Criar um novo índice no Azure Cognitive Search
- Extrair o texto dos PDFs
- Dividir o texto em chunks
- Enviar os chunks para o índice

## Executando a Aplicação

1. Inicie a aplicação Streamlit:
```bash
streamlit run app.py
```

2. Acesse a interface web através do navegador (geralmente em http://localhost:8501)

## Funcionalidades

- Interface web amigável para fazer perguntas sobre os documentos
- Visualização dos PDFs relacionados às respostas
- Histórico de conversas
- Sistema RAG que combina busca semântica com geração de respostas

## Estrutura do Projeto

- `app.py`: Interface web usando Streamlit
- `meu_script_rag.py`: Lógica principal do sistema RAG
- `criar_indice.py`: Script para indexação dos documentos
- `requirements.txt`: Dependências do projeto
- `.env`: Configurações do ambiente (não versionado)

## Observações

- O sistema utiliza o modelo GPT-3.5 Turbo da Azure OpenAI
- Os documentos são divididos em chunks de 1000 caracteres para melhor processamento
- A temperatura do modelo está configurada em 0.3 para respostas mais precisas
- O sistema mantém um histórico das conversas durante a sessão

## Suporte

Para problemas ou dúvidas, abra uma issue no repositório. 
