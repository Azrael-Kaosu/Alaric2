import ccxt
import time

# Configuração da API da Binance
api_key = "MsyHcLLcfEVaYxSYHKz4sRep4cB7dLtkkySi0fn1wgXvde0F788RkWdjrXleZmIY"
api_secret = "LnzMvpPBSqWTt1gvni0pnISGkFzUVsDWcPcWXzZI6BsEr3FKnzQpNWFWXy27lvhk"

symbol = "USDT/BRL"  # Par de trade
percent = 0.003  # Alvo de lucro de 0.3%
stop_loss_percent = 0.02  # Stop-loss de 2%
trade_amount_brl = 60  # Compra com R$60
wait_time = 600  # Tempo de espera: 10 minutos
cooldown_time = 5 * 60 * 60  # Pausa após stop-loss: 5 horas

# Inicializa a Binance
binance = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'},
})

binance.load_markets()

last_buy_price = None
last_sell_price = None
position = None  # "bought", "sold" ou None
stop_loss_activated = False

market = binance.market(symbol)
min_notional = market['limits']['cost']['min']

while True:
    try:
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        print(f"\nPreço atual: {price:.2f} BRL")

        if stop_loss_activated:
            print("Stop-loss ativado! Esperando 5 horas...")
            time.sleep(cooldown_time)
            stop_loss_activated = False
            position = None
            continue

        if position == "bought":
            time.sleep(wait_time)
            current_price = binance.fetch_ticker(symbol)['last']

            if current_price >= last_buy_price * (1 + percent):
                balance = binance.fetch_balance()
                usdt_available = balance['total']['USDT']
                if usdt_available > 0:
                    print(f"🎯 VENDENDO {usdt_available:.2f} USDT por {current_price:.2f} BRL")
                    binance.create_market_sell_order(symbol, usdt_available)
                    last_sell_price = current_price
                    position = "sold"

            elif current_price <= last_buy_price * (1 - stop_loss_percent):
                print("⚠️ STOP-LOSS acionado na compra!")
                stop_loss_activated = True

        elif position == "sold":
            time.sleep(wait_time)
            current_price = binance.fetch_ticker(symbol)['last']

            if current_price <= last_sell_price * (1 - percent):
                brl_balance = binance.fetch_balance()['total']['BRL']
                if brl_balance >= trade_amount_brl and trade_amount_brl >= min_notional:
                    print(f"🟢 COMPRANDO {trade_amount_brl} BRL em USDT a {current_price:.2f} BRL")
                    binance.create_market_buy_order(symbol, trade_amount_brl / current_price)
                    last_buy_price = current_price
                    position = "bought"

            elif current_price >= last_sell_price * (1 + stop_loss_percent):
                print("⚠️ STOP-LOSS acionado na venda!")
                stop_loss_activated = True

        elif position is None:
            print("Fazendo primeira tentativa de compra/venda...")

            try:
                balance = binance.fetch_balance()
                brl_balance = balance['total']['BRL']
                usdt_available = balance['total']['USDT']

                if brl_balance >= trade_amount_brl and trade_amount_brl >= min_notional:
                    print(f"💰 Iniciando com COMPRA de {trade_amount_brl} BRL")
                    binance.create_market_buy_order(symbol, trade_amount_brl / price)
                    last_buy_price = price
                    position = "bought"

                elif usdt_available > 0:
                    print(f"💰 Iniciando com VENDA de {usdt_available:.2f} USDT")
                    binance.create_market_sell_order(symbol, usdt_available)
                    last_sell_price = price
                    position = "sold"

                else:
                    print("Sem saldo suficiente para iniciar operações.")

            except Exception as e:
                print("Erro na primeira operação:", e)

        time.sleep(10)

    except Exception as e:
        print("Erro geral:", e)
        time.sleep(10)
