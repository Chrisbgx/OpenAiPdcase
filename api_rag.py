from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from meu_script_rag import perguntar_ao_modelo
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permitir acesso de qualquer origem (útil para testes locais com OpenWebUI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "rag-azure",
                "object": "model",
                "created": 0,
                "owned_by": "owner"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    # Pega a última mensagem do usuário
    user_message = data["messages"][-1]["content"]
    resposta = perguntar_ao_modelo(user_message)
    return JSONResponse({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": resposta
            }
        }]
    }) 