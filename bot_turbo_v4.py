import ccxt
import time
import numpy as np
import os
import threading
from fastapi import FastAPI

# === CONFIGURAÇÕES ===
API_KEY = 'D0DiV60UucDChy9heZaDjo65Gli9s1Q4xyfEbUlAiWt718iYuqMVotlGd0GsG8Zz'
API_SECRET = 'PtTCQXFQ9VQkJaTdIfPAA53xBV4LYdq3SaS0VzATIAT5mD6geQxk7sGjxBJYtbN3'
symbol_list = ['DOGE/USDT', 'SHIB/USDT']
capital_por_ordem = 6  # USDT por operação
intervalo = 15  # segundos entre análises
take_profit = 0.01  # 1%
stop_loss = 0.005  # 0.5%
rsi_topo = 80
rsi_fundo = 15
explosao_threshold = 0.015  # 1.5%
trailing_delta = 0.0025  # 0.25%

# === API Exchange ===
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(False)

# === Bot State ===
abertas = {}  # {symbol: {'compra': preco, 'tempo': timestamp, 'topo': preco}}

# === Funções ===
def pegar_precos(symbol, limit=50):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
    closes = [x[4] for x in ohlcv]
    return closes

def calcular_indicadores(precos):
    closes = np.array(precos)

    media = np.mean(closes[-20:])
    diffs = np.diff(closes)
    ganhos = np.maximum(diffs, 0)
    perdas = np.maximum(-diffs, 0)
    avg_gain = np.mean(ganhos[-14:])
    avg_loss = np.mean(perdas[-14:])
    rs = avg_gain / avg_loss if avg_loss != 0 else 1e10
    rsi = 100 - (100 / (1 + rs))

    ema12 = np.mean(closes[-12:])
    ema26 = np.mean(closes[-26:])
    macd = ema12 - ema26
    signal = np.mean(closes[-9:])

    return media, rsi, macd, signal

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

            print(f"[🔍] {symbol} | Preço: {atual:.6f} | Média: {media:.6f} | RSI: {rsi:.2f} | MACD: {macd:.6f} | Signal: {signal:.6f}")

            if symbol not in abertas:
                if macd > signal and atual > media and rsi < rsi_topo:
                    print(f"[📈] Sinal de compra detectado para {symbol}")
                    comprar(symbol, atual)
            else:
                preco_compra = abertas[symbol]['compra']
                topo = abertas[symbol]['topo']
                lucro = (atual - preco_compra) / preco_compra

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

# === FASTAPI ===
app = FastAPI()

@app.on_event("startup")
def iniciar_bot_em_background():
    thread = threading.Thread(target=loop_bot)
    thread.daemon = True
    thread.start()

def loop_bot():
    print("🚀 Iniciando Alaric V4.1 com Debug + Trailing Stop...\n")
    while True:
        analisar()
        time.sleep(intervalo)
