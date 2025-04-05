from fastapi import FastAPI
import threading
from bot import iniciar_bot

app = FastAPI()

@app.on_event("startup")
def start_bot():
    print("🚀 Iniciando bot de trade...")
    thread = threading.Thread(target=iniciar_bot)
    thread.start()

@app.get("/")
def root():
    return {"status": "bot rodando"}
