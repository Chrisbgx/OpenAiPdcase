import os
import json
import numpy as np
from datetime import datetime, timedelta
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

load_dotenv()

# Configurações Azure
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Configurações avançadas
CACHE_FILE = "cache_respostas_avancado.json"
CACHE_EXPIRY_HOURS = 48
SIMILARITY_THRESHOLD = 0.85
MAX_CACHE_SIZE = 1000

# Configurações de qualidade
MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0.15"))
TOP_P = float(os.getenv("RAG_TOP_P", "0.92"))
SEARCH_TOP_RESULTS = int(os.getenv("RAG_SEARCH_TOP", "25"))
CONTEXT_MAX_DOCS = int(os.getenv("RAG_CONTEXT_DOCS", "10"))

# Cliente Azure OpenAI será criado quando necessário
azure_openai_client = None

def get_azure_openai_client():
    """Cria cliente Azure OpenAI de forma lazy com tratamento de erro"""
    global azure_openai_client
    
    if azure_openai_client is None:
        try:
            if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT]):
                raise ValueError("Variáveis Azure OpenAI não configuradas no .env")
            
            azure_openai_client = AzureOpenAI(
                api_key=AZURE_OPENAI_KEY,
                api_version="2024-12-01-preview",
                azure_endpoint=AZURE_OPENAI_ENDPOINT
            )
            print("✅ Cliente Azure OpenAI inicializado com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar cliente Azure OpenAI: {e}")
            raise
    
    return azure_openai_client

class CacheAvancado:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.cache = self.carregar_cache()
        self.perguntas_vetorizadas = None
        self._atualizar_vetorizacao()
    
    def carregar_cache(self):
        """Carrega cache do arquivo"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def salvar_cache(self):
        """Salva cache no arquivo"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erro ao salvar cache: {e}")
    
    def _atualizar_vetorizacao(self):
        """Atualiza a vetorização TF-IDF das perguntas em cache"""
        if not self.cache:
            return
        
        perguntas = [entry['pergunta_normalizada'] for entry in self.cache.values()]
        if perguntas:
            try:
                self.perguntas_vetorizadas = self.vectorizer.fit_transform(perguntas)
            except:
                self.perguntas_vetorizadas = None
    
    def normalizar_pergunta(self, pergunta):
        """Normaliza pergunta para comparação"""
        return ' '.join(pergunta.lower().strip().split())
    
    def cache_expirado(self, timestamp):
        """Verifica se entrada está expirada"""
        try:
            cache_time = datetime.fromisoformat(timestamp)
            return datetime.now() - cache_time > timedelta(hours=CACHE_EXPIRY_HOURS)
        except:
            return True
    
    def limpar_cache_expirado(self):
        """Remove entradas expiradas do cache"""
        chaves_expiradas = []
        for chave, entry in self.cache.items():
            if self.cache_expirado(entry['timestamp']):
                chaves_expiradas.append(chave)
        
        for chave in chaves_expiradas:
            del self.cache[chave]
        
        if chaves_expiradas:
            print(f"🧹 Removidas {len(chaves_expiradas)} entradas expiradas do cache")
            self._atualizar_vetorizacao()
    
    def encontrar_pergunta_similar(self, pergunta):
        """Encontra pergunta similar usando similaridade semântica"""
        if not self.cache or self.perguntas_vetorizadas is None:
            return None
        
        self.limpar_cache_expirado()
        pergunta_norm = self.normalizar_pergunta(pergunta)
        
        try:
            pergunta_vec = self.vectorizer.transform([pergunta_norm])
            similaridades = cosine_similarity(pergunta_vec, self.perguntas_vetorizadas)[0]
            
            max_sim_idx = np.argmax(similaridades)
            max_similaridade = similaridades[max_sim_idx]
            
            if max_similaridade >= SIMILARITY_THRESHOLD:
                chaves = list(self.cache.keys())
                chave_similar = chaves[max_sim_idx]
                entry = self.cache[chave_similar]
                
                print(f"💡 Pergunta similar encontrada (similaridade: {max_similaridade:.2f})")
                
                entry['timestamp'] = datetime.now().isoformat()
                entry['uso_count'] = entry.get('uso_count', 0) + 1
                
                return entry['resposta']
                
        except Exception as e:
            print(f"⚠️ Erro na busca por similaridade: {e}")
        
        return None
    
    def adicionar_ao_cache(self, pergunta, resposta):
        """Adiciona nova entrada ao cache"""
        if len(self.cache) >= MAX_CACHE_SIZE:
            chave_mais_antiga = min(self.cache.keys(), 
                                  key=lambda k: self.cache[k]['timestamp'])
            del self.cache[chave_mais_antiga]
        
        chave = f"q_{len(self.cache)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.cache[chave] = {
            'pergunta_original': pergunta,
            'pergunta_normalizada': self.normalizar_pergunta(pergunta),
            'resposta': resposta,
            'timestamp': datetime.now().isoformat(),
            'uso_count': 1
        }
        
        self._atualizar_vetorizacao()
        self.salvar_cache()
        print(f"💾 Nova resposta adicionada ao cache (total: {len(self.cache)})")

class DeduplicadorContexto:
    @staticmethod
    def calcular_similaridade_jaccard(texto1, texto2):
        """Calcula similaridade Jaccard entre dois textos"""
        palavras1 = set(texto1.lower().split())
        palavras2 = set(texto2.lower().split())
        
        intersecao = palavras1 & palavras2
        uniao = palavras1 | palavras2
        
        return len(intersecao) / len(uniao) if uniao else 0
    
    @staticmethod
    def remover_duplicatas_inteligente(documentos):
        """Remove duplicatas considerando chunks e páginas"""
        if not documentos:
            return []
        
        documentos_ordenados = sorted(
            documentos, 
            key=lambda x: (
                -x.get('score', 0),
                x.get('page', 9999),
                x.get('chunk_id', 9999)
            )
        )
        
        documentos_unicos = []
        chunks_utilizados = set()
        
        for doc in documentos_ordenados:
            content = doc['content']
            filename = doc['filename']
            page = doc.get('page', 'N/A')
            chunk_id = doc.get('chunk_id', 'N/A')
            
            chunk_identifier = f"{filename}_{page}_{chunk_id}"
            
            if chunk_identifier in chunks_utilizados:
                continue
                
            eh_duplicata = False
            for unico in documentos_unicos:
                sim_jaccard = DeduplicadorContexto.calcular_similaridade_jaccard(content, unico['content'])
                
                mesmo_arquivo = filename == unico['filename']
                paginas_proximas = False
                
                if page != 'N/A' and unico.get('page') != 'N/A':
                    try:
                        diff_pagina = abs(int(page) - int(unico.get('page', 0)))
                        paginas_proximas = diff_pagina <= 1
                    except:
                        pass
                
                threshold_jaccard = 0.85 if mesmo_arquivo and paginas_proximas else 0.75
                
                if sim_jaccard > threshold_jaccard:
                    eh_duplicata = True
                    break
            
            if not eh_duplicata:
                documentos_unicos.append(doc)
                chunks_utilizados.add(chunk_identifier)
        
        print(f"🧠 Deduplicação: {len(documentos)} → {len(documentos_unicos)} chunks únicos")
        return documentos_unicos

def agrupar_por_documento(documentos):
    """Agrupa chunks do mesmo documento para melhor apresentação"""
    if not documentos:
        return []
    
    grupos_arquivo = {}
    for doc in documentos:
        filename = doc['filename']
        if filename not in grupos_arquivo:
            grupos_arquivo[filename] = []
        grupos_arquivo[filename].append(doc)
    
    documentos_agrupados = []
    for filename, chunks in grupos_arquivo.items():
        chunks_ordenados = sorted(
            chunks,
            key=lambda x: (
                x.get('page', 9999) if x.get('page') != 'N/A' else 9999,
                x.get('chunk_id', 9999) if x.get('chunk_id') != 'N/A' else 9999
            )
        )
        
        if len(chunks_ordenados) <= 2:
            documentos_agrupados.extend(chunks_ordenados)
        else:
            chunks_por_score = sorted(chunks_ordenados, key=lambda x: -x.get('score', 0))
            documentos_agrupados.extend(chunks_por_score[:2])
    
    resultado_final = sorted(documentos_agrupados, key=lambda x: -x.get('score', 0))
    
    print(f"📚 Agrupamento: {len(documentos)} → {len(resultado_final)} chunks de {len(grupos_arquivo)} arquivos")
    return resultado_final

# Instâncias globais
cache_manager = CacheAvancado()
deduplicador = DeduplicadorContexto()

def buscar_documentos(pergunta):
    """Busca documentos com metadata rica e deduplicação avançada"""
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT,
                                 index_name=AZURE_SEARCH_INDEX,
                                 credential=AzureKeyCredential(AZURE_SEARCH_KEY))
    
    try:
        try:
            resultados_busca = search_client.search(
                pergunta, 
                top=SEARCH_TOP_RESULTS,
                select=[
                    "content", 
                    "file_name", 
                    "filename", 
                    "page_number", 
                    "chunk_id", 
                    "total_pages", 
                    "file_type"
                ],
                search_fields=["content"],
                highlight_fields="content",
                query_type="semantic" if hasattr(search_client, 'semantic_search') else "simple",
                order_by=["search.score() desc"]
            )
            resultados = list(resultados_busca)
            print(f"🎯 Busca realizada com {len(resultados)} resultados")
            
        except Exception as sort_error:
            print(f"⚠️ Problema na ordenação: {sort_error}")
            resultados_busca = search_client.search(
                pergunta, 
                top=SEARCH_TOP_RESULTS,
                select=[
                    "content", 
                    "file_name", 
                    "filename", 
                    "page_number", 
                    "chunk_id", 
                    "total_pages", 
                    "file_type"
                ],
                search_fields=["content"],
                highlight_fields="content"
            )
            resultados = list(resultados_busca)
        
    except Exception as e:
        print(f"⚠️ Erro na busca, tentando busca básica: {e}")
        try:
            resultados_busca = search_client.search(
                pergunta, 
                top=SEARCH_TOP_RESULTS,
                select=["content", "file_name", "filename", "page_number"],
                search_fields=["content"]
            )
            resultados = list(resultados_busca)
        except Exception as e2:
            print(f"⚠️ Usando fallback simples: {e2}")
            resultados_busca = search_client.search(pergunta, top=SEARCH_TOP_RESULTS)
            resultados = list(resultados_busca)
    
    # Estrutura dados com metadata rica
    documentos_estruturados = []
    for doc in resultados:
        documento = {
            'content': doc.get('content', ''),
            'filename': doc.get('filename', doc.get('file_name', 'Documento')),
            'page': doc.get('page_number', 'N/A'),
            'chunk_id': doc.get('chunk_id', 'N/A'),
            'total_pages': doc.get('total_pages', 'N/A'),
            'file_type': doc.get('file_type', 'PDF'),
            'score': getattr(doc, '@search.score', 0.0)
        }
        documentos_estruturados.append(documento)
    
    documentos_unicos = deduplicador.remover_duplicatas_inteligente(documentos_estruturados)
    documentos_agrupados = agrupar_por_documento(documentos_unicos)
    
    return documentos_agrupados[:CONTEXT_MAX_DOCS]

def formatar_contexto_otimizado(documentos):
    """Formata contexto com metadata rica para máxima qualidade"""
    if not documentos:
        return "Nenhum contexto relevante encontrado."
    
    contexto_formatado = []
    arquivos_vistos = {}
    
    for i, doc in enumerate(documentos, 1):
        filename = doc.get('filename', 'N/A')
        page = doc.get('page', 'N/A')
        chunk_id = doc.get('chunk_id', 'N/A')
        total_pages = doc.get('total_pages', 'N/A')
        file_type = doc.get('file_type', 'PDF')
        score = doc.get('score', 0.0)
        
        if filename not in arquivos_vistos:
            arquivos_vistos[filename] = []
        arquivos_vistos[filename].append(page)
        
        arquivo_info = f"📁 **{filename}** ({file_type})"
        if total_pages != 'N/A':
            arquivo_info += f" - {total_pages} páginas"
        
        localizacao_info = ""
        if page != 'N/A':
            localizacao_info = f"📖 Página {page}"
            if chunk_id != 'N/A':
                localizacao_info += f" (Seção {chunk_id})"
        
        score_info = ""
        if score > 0:
            if score >= 1.0:
                indicator = "🎯"
            elif score >= 0.7:
                indicator = "🔥"
            elif score >= 0.5:
                indicator = "✅"
            else:
                indicator = "📋"
            score_info = f"{indicator} Score: {score:.3f}"
        
        documento_fmt = f"""📄 **Documento {i}** | {score_info}
{arquivo_info}
{localizacao_info}

📝 **Conteúdo:**
{doc['content'].strip()}

---"""
        contexto_formatado.append(documento_fmt)
    
    resumo_arquivos = []
    for arquivo, paginas in arquivos_vistos.items():
        paginas_unicas = sorted(set(p for p in paginas if p != 'N/A'))
        if paginas_unicas:
            resumo_arquivos.append(f"• {arquivo}: páginas {', '.join(map(str, paginas_unicas))}")
        else:
            resumo_arquivos.append(f"• {arquivo}")
    
    cabecalho = f"""📚 **FONTES CONSULTADAS** ({len(arquivos_vistos)} arquivos, {len(documentos)} seções):
{chr(10).join(resumo_arquivos)}

{'='*60}

"""
    
    return cabecalho + "\n".join(contexto_formatado)

def perguntar_ao_modelo(pergunta):
    """Função principal com cache avançado e prompt otimizado"""
    resposta_cache = cache_manager.encontrar_pergunta_similar(pergunta)
    if resposta_cache:
        return resposta_cache
    
    documentos = buscar_documentos(pergunta)
    contexto_formatado = formatar_contexto_otimizado(documentos)
    
    system_message = """Você é um especialista técnico sênior especializado em análise de documentação corporativa. Você tem acesso a um sistema de busca avançado que fornece contexto rico com páginas específicas e seções de documentos.

**SUA MISSÃO:**
- Fornecer respostas precisas, detalhadas e acionáveis baseadas nos documentos fornecidos
- Aproveitar a metadata rica (páginas, seções, scores) para dar respostas mais precisas
- Referenciar SEMPRE as páginas específicas dos documentos quando aplicável
- Estruturar respostas de forma profissional e técnica
- Incluir procedimentos práticos passo-a-passo quando disponíveis
- Priorizar informações de documentos com maior score de relevância

**FORMATO DE RESPOSTA OBRIGATÓRIO:**
1. **🎯 Resumo Executivo:** Resposta direta e objetiva (1-2 frases)
2. **🔧 Detalhamento Técnico:** Explicação completa baseada nos documentos
3. **✅ Procedimentos:** Lista numerada de passos quando aplicável
4. **⚠️ Observações Importantes:** Considerações, limitações ou alertas
5. **📚 Referências:** Citação específica dos documentos (arquivo e páginas)

**REGRAS CRÍTICAS:**
- Use APENAS informações dos documentos fornecidos
- Cite sempre "Documento X (página Y)" nas referências
- Se informação não estiver disponível, declare explicitamente
- Priorize documentos com scores mais altos (🎯 e 🔥)"""

    user_message = f"""**CONTEXTO ENRIQUECIDO COM METADATA:**
{contexto_formatado}

**PERGUNTA DO USUÁRIO:**
{pergunta}

**INSTRUÇÃO ESPECÍFICA:**
Analise cuidadosamente todos os documentos fornecidos acima, considerando seus scores de relevância e localização específica (páginas/seções). Forneça uma resposta estruturada usando o formato obrigatório, citando precisamente as fontes consultadas."""

    try:
        client = get_azure_openai_client()
        
        resposta = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=TOP_P,
            frequency_penalty=0.1,
            presence_penalty=0.1
        )
        
        resposta_texto = resposta.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erro na chamada Azure OpenAI: {e}")
        
        if "DeploymentNotFound" in error_msg:
            return """❌ **ERRO: Deployment não encontrado**

🔧 **SOLUÇÃO:**
1. Execute: `python verificar_azure.py` para listar deployments disponíveis
2. Atualize a variável `AZURE_OPENAI_DEPLOYMENT` no arquivo .env
3. Use o nome exato de um deployment ativo

⚠️ **Deployment configurado pode estar incorreto ou não existir no Azure OpenAI.**"""
        
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return """❌ **ERRO: Credenciais inválidas**

🔧 **SOLUÇÃO:**
1. Verifique `AZURE_OPENAI_KEY` no arquivo .env
2. Confirme se a chave está correta no Azure Portal
3. Verifique se o recurso Azure OpenAI está ativo"""
        
        elif "403" in error_msg or "Forbidden" in error_msg:
            return """❌ **ERRO: Acesso negado**

🔧 **SOLUÇÃO:**
1. Verifique permissões no Azure OpenAI
2. Confirme se a subscription está ativa
3. Verifique cotas de uso do serviço"""
        
        else:
            return f"""❌ **ERRO na geração de resposta**

**Detalhes técnicos:** {error_msg}

🔧 **SOLUÇÃO:**
Execute `python verificar_azure.py` para diagnosticar o problema."""
    
    cache_manager.adicionar_ao_cache(pergunta, resposta_texto)
    
    arquivos_unicos = set(doc.get('filename', 'N/A') for doc in documentos)
    paginas_processadas = [doc.get('page') for doc in documentos if doc.get('page') != 'N/A']
    
    stats_msg = f"✅ Resposta gerada ({len(resposta_texto)} chars)"
    stats_msg += f" | {len(documentos)} chunks de {len(arquivos_unicos)} arquivos"
    if paginas_processadas:
        stats_msg += f" | páginas: {', '.join(map(str, sorted(set(paginas_processadas))))}"
    
    print(stats_msg)
    return resposta_texto

def estatisticas_cache():
    """Mostra estatísticas do cache"""
    cache = cache_manager.cache
    total = len(cache)
    
    if total == 0:
        print("📊 Cache vazio")
        return
    
    usos = [entry.get('uso_count', 1) for entry in cache.values()]
    
    print(f"📊 Estatísticas do Cache:")
    print(f"   Total de entradas: {total}")
    print(f"   Uso médio: {sum(usos)/len(usos):.1f}")
    print(f"   Entrada mais usada: {max(usos)} vezes")
    print(f"   Economia estimada: {sum(usos) - total} consultas ao modelo")

def mostrar_configuracoes_qualidade():
    """Mostra configurações atuais de qualidade otimizadas"""
    print("⚙️ Configurações RAG:")
    print(f"   🎯 Max Tokens: {MAX_TOKENS}")
    print(f"   🌡️ Temperature: {TEMPERATURE}")
    print(f"   📊 Top P: {TOP_P}")
    print(f"   🔍 Resultados Busca: {SEARCH_TOP_RESULTS}")
    print(f"   📄 Docs no Contexto: {CONTEXT_MAX_DOCS}")
    print(f"   💾 Similaridade Threshold: {SIMILARITY_THRESHOLD}")

if __name__ == "__main__":
    print("🧠 Sistema RAG Otimizado - Cache Inteligente")
    mostrar_configuracoes_qualidade()
    
    pergunta = input("\nDigite sua pergunta: ")
    resposta = perguntar_ao_modelo(pergunta)
    print("\n📘 Resposta do modelo:\n", resposta)
    print("\n" + "="*50)
    estatisticas_cache() 