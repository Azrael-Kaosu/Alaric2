import time
import ccxt
from threading import Lock
from config import API_KEY, API_SECRET, VALOR_BR, STOP_LOSS, TAKE_PROFIT

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})

symbol = 'USDT/BRL'
operation_lock = Lock()
cooldown = 60  # segundos
ultimo_preco = None

def pegar_preco():
    ticker = exchange.fetch_ticker(symbol)
    return round(ticker['last'], 3)

def comprar(valor_brl):
    try:
        preco = pegar_preco()
        quantidade = round(valor_brl / preco, 2)
        order = exchange.create_market_buy_order(symbol, quantidade)
        print(f"✔️ Compra executada a {preco} BRL")
    except Exception as e:
        print(f"❌ Erro na compra: {e}")

def vender(valor_usdt):
    try:
        preco = pegar_preco()
        order = exchange.create_market_sell_order(symbol, valor_usdt)
        print(f"✔️ Venda executada a {preco} BRL")
    except Exception as e:
        print(f"❌ Erro na venda: {e}")

def executar_operacao():
    if operation_lock.locked():
        print("⚠️ Operação em andamento. Ignorando.")
        return

    with operation_lock:
        preco = pegar_preco()
        global ultimo_preco
        if preco != ultimo_preco:
            print(f"Preço atual: {preco} BRL")
            ultimo_preco = preco

        # Exemplo: simulação de lógica
        if preco < 5.87:
            print(f"💰 Iniciando COMPRA de {VALOR_BR} BRL")
            comprar(VALOR_BR)
        elif preco > 5.88:
            saldo = exchange.fetch_balance()
            usdt_disp = saldo['total']['USDT']
            if usdt_disp > 5:
                print(f"💰 Iniciando VENDA de {round(usdt_disp, 2)} USDT")
                vender(round(usdt_disp, 2))

def iniciar_bot():
    while True:
        try:
            executar_operacao()
        except Exception as e:
            print(f"❌ Erro geral: {e}")
        time.sleep(cooldown)
