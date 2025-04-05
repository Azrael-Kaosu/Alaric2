from fastapi import FastAPI
import threading
import time
import ccxt

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Alaric2 online"}

def start_bot():
    api_key = "SUA_API_KEY"
    api_secret = "SEU_API_SECRET"

    symbol = "USDT/BRL"
    percent = 0.003
    stop_loss = 0.02
    trade_amount_brl = 60
    wait_time = 600

    binance = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'},
    })

    binance.load_markets()
    market = binance.market(symbol)
    min_notional = market['limits']['cost']['min']

    last_buy_price = None
    last_sell_price = None
    position = None
    stop_triggered = False
    stop_time = 0

    while True:
        try:
            price = binance.fetch_ticker(symbol)['last']
            print(f"Preço atual: {price} BRL")

            if stop_triggered:
                if time.time() - stop_time >= 5 * 3600:
                    print("Saindo do modo de espera após stop-loss.")
                    stop_triggered = False
                else:
                    print("Modo stop-loss ativo. Aguardando...")
                    time.sleep(60)
                    continue

            if position == "bought":
                time.sleep(wait_time)
                current = binance.fetch_ticker(symbol)['last']
                if current >= last_buy_price * (1 + percent):
                    usdt = binance.fetch_balance()['total']['USDT']
                    if usdt > 0:
                        print(f"Vendendo {usdt:.2f} USDT por {current} BRL")
                        binance.create_market_sell_order(symbol, usdt)
                        last_sell_price = current
                        position = "sold"
                elif current <= last_buy_price * (1 - stop_loss):
                    print("STOP-LOSS ATIVADO!")
                    stop_triggered = True
                    stop_time = time.time()
                    position = None

            elif position == "sold":
                time.sleep(wait_time)
                current = binance.fetch_ticker(symbol)['last']
                if current <= last_sell_price * (1 - percent):
                    brl = binance.fetch_balance()['total']['BRL']
                    if brl >= trade_amount_brl and trade_amount_brl >= min_notional:
                        print(f"Comprando com {trade_amount_brl} BRL a {current} BRL")
                        binance.create_market_buy_order(symbol, trade_amount_brl / current)
                        last_buy_price = current
                        position = "bought"
                elif current >= last_sell_price * (1 + stop_loss):
                    print("STOP-LOSS ATIVADO!")
                    stop_triggered = True
                    stop_time = time.time()
                    position = None

            elif position is None:
                print("Primeira tentativa de compra...")
                brl = binance.fetch_balance()['total']['BRL']
                if brl >= trade_amount_brl and trade_amount_brl >= min_notional:
                    binance.create_market_buy_order(symbol, trade_amount_brl / price)
                    last_buy_price = price
                    position = "bought"
                else:
                    print("Sem BRL suficiente. Aguardando saldo para vender.")
                    position = "sold"

            time.sleep(10)

        except Exception as e:
            print("Erro:", e)
            time.sleep(15)

# Inicia o bot em paralelo
threading.Thread(target=start_bot).start()
