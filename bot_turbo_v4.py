import ccxt
import time
import datetime
import numpy as np
import os

# Configurações
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
symbol_list = ['DOGE/USDT', 'SHIB/USDT']
capital_por_ordem = 6  # USDT por operação
intervalo = 15  # segundos entre análises
take_profit = 0.01  # 1%
stop_loss = 0.005  # 0.5%
rsi_topo = 80
rsi_fundo = 15
explosao_threshold = 0.015  # 1.5% de variação repentina
trailing_delta = 0.0025  # 0.25%

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(False)

# Dicionário com trades abertos e controle do topo
abertas = {}  # {symbol: {'compra': preco, 'tempo': timestamp, 'topo': preco}}

def calcular_indicadores(precos):
    closes = np.array(precos)

    # Média móvel
    media = np.mean(closes[-20:])

    # RSI
    diffs = np.diff(closes)
    ganhos = np.maximum(diffs, 0)
    perdas = np.maximum(-diffs, 0)
    avg_gain = np.mean(ganhos[-14:])
    avg_loss = np.mean(perdas[-14:])
    rs = avg_gain / avg_loss if avg_loss != 0 else 1e10
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = np.mean(closes[-12:])
    ema26 = np.mean(closes[-26:])
    macd = ema12 - ema26
    signal = np.mean(closes[-9:])
    
    return media, rsi, macd, signal

def pegar_precos(symbol, limit=50):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
    closes = [x[4] for x in ohlcv]
    return closes

def comprar(symbol, preco):
    print(f"[🟢] Comprando {symbol} a {preco:.6f}")
    exchange.create_market_buy_order(symbol, capital_por_ordem / preco)
    abertas[symbol] = {'compra': preco, 'tempo': time.time(), 'topo': preco}

def vender(symbol, preco, motivo):
    print(f"[🔴] Vendendo {symbol} a {preco:.6f} | Motivo: {motivo}")
    amount = capital_por_ordem / abertas[symbol]['compra']
    exchange.create_market_sell_order(symbol, amount)
    del abertas[symbol]

def analisar():
    for symbol in symbol_list:
        try:
            precos = pegar_precos(symbol)
            atual = precos[-1]
            media, rsi, macd, signal = calcular_indicadores(precos)

            explosao = (precos[-1] - precos[-4]) / precos[-4] > explosao_threshold

            if symbol not in abertas:
                if macd > signal and atual > media and rsi < rsi_topo:
                    comprar(symbol, atual)
            else:
                preco_compra = abertas[symbol]['compra']
                topo = abertas[symbol]['topo']
                lucro = (atual - preco_compra) / preco_compra

                # Atualiza topo se preço subir
                if atual > topo:
                    abertas[symbol]['topo'] = atual

                trailing_stop = abertas[symbol]['topo'] * (1 - trailing_delta)

                if rsi > rsi_topo and not explosao:
                    vender(symbol, atual, 'RSI > topo')
                elif atual <= trailing_stop:
                    vender(symbol, atual, 'Trailing Stop')
                elif lucro >= take_profit and not explosao:
                    vender(symbol, atual, 'Take Profit')
                elif lucro <= -stop_loss and rsi > rsi_fundo:
                    vender(symbol, atual, 'Stop Loss')

        except Exception as e:
            print(f"[⚠️] Erro ao analisar {symbol}: {e}")

print("🚀 Iniciando Bot V4 Turbo com Trailing Stop 0.25%...\n")
while True:
    analisar()
    time.sleep(intervalo)
