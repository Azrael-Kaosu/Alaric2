import threading
import bot_binance  # seu script normal
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Alaric bot online"}

# Roda o bot em uma thread separada
def run_bot():
    bot_binance.start()  # ou o nome da função principal do seu script

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
