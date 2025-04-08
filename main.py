import asyncio
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# Rota fake só pra enganar a Koyeb
@app.get("/")
def read_root():
    return {"status": "Bot está rodando 😎"}

# Aqui entra sua função do bot!
def iniciar_bot():
    import time
    print("🚀 Iniciando Bot Versão 4 Turbo com análise avançada...")
    while True:
        print("🤖 Bot rodando em background...")
        # Aqui você pode chamar sua função principal do bot
        time.sleep(15)  # simula execução contínua a cada 15s

# Roda o bot em thread separada
threading.Thread(target=iniciar_bot, daemon=True).start()

# Inicia o servidor FastAPI
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
