import time
import ccxt
import threading
from fastapi import FastAPI
import uvicorn

# Configurações
quantidade_brl = 60
stop_loss = 0.02
take_profit = 0.003
intervalo = 10  # segundos

# Variáveis de controle
position = None  # 'long', 'short' ou None
entry_price = None
cooldown_until = 0
cooldown_time = 60

# Inicializa a Binance
binance = ccxt.binance({
    'apiKey': 'MsyHcLLcfEVaYxSYHKz4sRep4cB7dLtkkySi0fn1wgXvde0F788RkWdjrXleZmIY',
    'secret': 'LnzMvpPBSqWTt1gvni0pnISGkFzUVsDWcPcWXzZI6BsEr3FKnzQpNWFWXy27lvhk',
})
binance.set_sandbox_mode(False)

symbol = 'USDT/BRL'

def obter_preco_atual():
    ticker = binance.fetch_ticker(symbol)
    return ticker['last']

def verificar_saldos():
    saldo = binance.fetch_balance()
    brl = saldo['total'].get('BRL', 0)
    usdt = saldo['total'].get('USDT', 0)
    return brl, usdt

def comprar_usdt(valor_brl):
    preco = obter_preco_atual()
    quantidade = round(valor_brl / preco, 2)
    order = binance.create_market_buy_order(symbol, quantidade)
    return preco

def vender_usdt(quantidade):
    order = binance.create_market_sell_order(symbol, quantidade)
    return obter_preco_atual()

def monitorar():
    global position, entry_price, cooldown_until

    while True:
        try:
            preco_atual = obter_preco_atual()
            print(f"Preço atual: {preco_atual} BRL")

            if time.time() < cooldown_until:
                print("⏳ Em cooldown. Aguardando próxima tentativa.")
                time.sleep(intervalo)
                continue

            if position is None:
                print("Fazendo primeira tentativa de compra/venda...")
                brl, usdt = verificar_saldos()

                if brl >= quantidade_brl:
                    print(f"💰 Iniciando com COMPRA de {quantidade_brl} BRL")
                    try:
                        entry_price = comprar_usdt(quantidade_brl)
                        position = 'long'
                        print(f"✔️ Compra executada a {entry_price} BRL")
                    except Exception as e:
                        print(f"❌ Erro na compra: {e}")
                        cooldown_until = time.time() + cooldown_time
                elif usdt >= 10:
                    print(f"💰 Iniciando com VENDA de {round(usdt, 2)} USDT")
                    try:
                        entry_price = preco_atual
                        vender_usdt(round(usdt, 2))
                        position = 'short'
                        print(f"✔️ Venda executada a {entry_price} BRL")
                    except Exception as e:
                        print(f"❌ Erro na venda: {e}")
                        cooldown_until = time.time() + cooldown_time
                else:
                    print("⚠️ Saldo insuficiente para iniciar.")
            else:
                diferenca = preco_atual - entry_price
                variacao = diferenca / entry_price

                if position == 'long':
                    if variacao <= -stop_loss or variacao >= take_profit:
                        print(f"📉 Fechando posição LONG com lucro/prejuízo de {round(variacao*100, 2)}%")
                        usdt = verificar_saldos()[1]
                        vender_usdt(round(usdt, 2))
                        position = None
                        entry_price = None
                elif position == 'short':
                    if variacao >= stop_loss or variacao <= -take_profit:
                        print(f"📈 Fechando posição SHORT com lucro/prejuízo de {round(variacao*100, 2)}%")
                        brl = verificar_saldos()[0]
                        comprar_usdt(brl)
                        position = None
                        entry_price = None

        except Exception as e:
            print(f"Erro inesperado: {e}")
            cooldown_until = time.time() + cooldown_time

        time.sleep(intervalo)

# 🧠 BOT EM THREAD
threading.Thread(target=monitorar, daemon=True).start()

# 🌀 FASTAPI WEB PARA KOYEB
app = FastAPI()

@app.get("/")
def status():
    return {"status": "bot ativo", "posição": position, "preço_entrada": entry_price}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
