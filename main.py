from fastapi import FastAPI
import uvicorn
import asyncio

app = FastAPI()

@app.get("/")
def healthcheck():
    return {"status": "alive"}

async def start_bot():
    await asyncio.sleep(1)  # Espera só pra garantir que a API subiu
    print("🔁 Bot iniciado!")
    # chama sua função principal de trade aqui
    # await sua_funcao_main()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
