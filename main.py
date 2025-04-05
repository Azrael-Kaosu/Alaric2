import time
import ccxt
import threading

# Configurações
quantidade_brl = 60
stop_loss = 0.02
take_profit = 0.003
intervalo = 10  # segundos

# Variáveis de controle
position = None  # 'long', 'short' ou None
entry_price = None
cooldown_until = 0  # timestamp para cooldown
cooldown_time = 60  # tempo de espera após erro

# Inicializa a Binance
binance = ccxt.binance({
    'apiKey': 'SUA_API_KEY',
    'secret': 'SEU_API_SECRET',
})
binance.set_sandbox_mode(False)  # ou True pra testes

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
                # Verificar stop-loss e take-profit
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

# Iniciar o monitoramento em thread
threading.Thread(target=monitorar).start()

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
