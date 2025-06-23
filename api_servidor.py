import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carrega configurações
load_dotenv()

# Sistema RAG com cache inteligente
from engine_rag import perguntar_ao_modelo, cache_manager

print("🧠 Sistema RAG com cache inteligente carregado")

app = FastAPI(
    title="Sistema RAG API - Cache Inteligente",
    description="API de Retrieval Augmented Generation com cache semântico avançado",
    version="3.0.0"
)

# Permitir acesso de qualquer origem (útil para testes locais com OpenWebUI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Sistema RAG API - Cache Inteligente",
        "cache_type": "Cache Inteligente (Similaridade Semântica)",
        "version": "3.0.0",
        "features": [
            "Similaridade semântica",
            "Deduplicação de contexto", 
            "Estatísticas detalhadas",
            "Auto-expiração inteligente"
        ],
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
            "health": "/health",
            "stats": "/stats"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "cache_system": "intelligent",
        "intelligent_caching": True
    }

@app.get("/stats")
async def get_stats():
    """Retorna estatísticas detalhadas do cache inteligente"""
    try:
        cache = cache_manager.cache
        total = len(cache)
        
        if total == 0:
            return {"cache_entries": 0, "message": "Cache vazio", "cache_type": "intelligent"}
        
        usos = [entry.get('uso_count', 1) for entry in cache.values()]
        
        return {
            "cache_entries": total,
            "average_usage": round(sum(usos) / len(usos), 2),
            "max_usage": max(usos),
            "total_cache_hits": sum(usos) - total,
            "cache_efficiency": round((sum(usos) - total) / sum(usos) * 100, 1) if sum(usos) > 0 else 0,
            "cache_type": "intelligent",
            "memory_optimization": "Ativa",
            "semantic_detection": "Ativa"
        }
    except Exception as e:
        return {"error": f"Erro ao obter estatísticas: {e}", "cache_type": "intelligent"}

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "rag-azure-intelligent",
                "object": "model",
                "created": 0,
                "owned_by": "sistema-rag",
                "cache_type": "intelligent",
                "intelligent_caching": True,
                "features": [
                    "semantic_similarity",
                    "context_deduplication", 
                    "auto_expiration",
                    "detailed_stats"
                ]
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        data = await request.json()
        
        # Validação básica
        if "messages" not in data or not data["messages"]:
            return JSONResponse(
                status_code=400,
                content={"error": "Campo 'messages' é obrigatório"}
            )
        
        # Pega a última mensagem do usuário
        user_message = data["messages"][-1]["content"]
        
        if not user_message.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Mensagem não pode estar vazia"}
            )
        
        # Chama o modelo RAG
        resposta = perguntar_ao_modelo(user_message)
        
        return JSONResponse({
            "object": "chat.completion",
            "model": "rag-azure-intelligent",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": resposta
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "cache_type": "intelligent",
                "intelligent_caching": True
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro interno: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando API RAG com cache inteligente")
    uvicorn.run(app, host="0.0.0.0", port=8000) 