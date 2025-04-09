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

# Dicionário com trades abertos
abertas = {}  # {symbol: {'compra': preco, 'tempo': timestamp, 'topo': preco}}

def log(msg, tipo='INFO'):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    prefix = {
        'INFO': '[ℹ️]',
        'COMPRA': '[🟢]',
        'VENDA': '[🔴]',
        'ERRO': '[⚠️]',
        'WARNING': '[🟡]'
    }.get(tipo, '[ℹ️]')
    print(f"[{timestamp}] {prefix} {msg}")

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

def pegar_precos(symbol, limit=50):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
    closes = [x[4] for x in ohlcv]
    return closes

def comprar(symbol, preco):
    log(f"Comprando {symbol} a {preco:.6f}", 'COMPRA')
    exchange.create_market_buy_order(symbol, capital_por_ordem / preco)
    abertas[symbol] = {'compra': preco, 'tempo': time.time(), 'topo': preco}

def vender(symbol, preco, motivo):
    log(f"Vendendo {symbol} a {preco:.6f} | Motivo: {motivo}", 'VENDA')
    amount = capital_por_ordem / abertas[symbol]['compra']
    exchange.create_market_sell_order(symbol, amount)
    del abertas[symbol]

def analisar():
    for symbol in symbol_list:
        try:
            log(f"Analisando {symbol}...", 'INFO')
            precos = pegar_precos(symbol)
            atual = precos[-1]
            media, rsi, macd, signal = calcular_indicadores(precos)

            explosao = (precos[-1] - precos[-4]) / precos[-4] > explosao_threshold
            log(f"Preço atual: {atual:.6f} | RSI: {rsi:.2f} | MACD: {macd:.6f} | Signal: {signal:.6f}", 'INFO')

            if symbol not in abertas:
                if macd > signal and atual > media and rsi < rsi_topo:
                    log(f"📈 Sinal de compra detectado para {symbol}", 'INFO')
                    comprar(symbol, atual)
                else:
                    log(f"⚪ Nenhum sinal forte de compra para {symbol}", 'INFO')
            else:
                preco_compra = abertas[symbol]['compra']
                topo = abertas[symbol]['topo']
                lucro = (atual - preco_compra) / preco_compra

                if atual > topo:
                    abertas[symbol]['topo'] = atual
                    log(f"📈 Novo topo atingido para {symbol}: {atual:.6f}", 'INFO')

                trailing_stop = abertas[symbol]['topo'] * (1 - trailing_delta)
                log(f"Lucro atual: {lucro*100:.2f}% | Trailing Stop: {trailing_stop:.6f}", 'INFO')

                if rsi > rsi_topo and not explosao:
                    vender(symbol, atual, 'RSI > topo')
                elif atual <= trailing_stop:
                    vender(symbol, atual, 'Trailing Stop')
                elif lucro >= take_profit and not explosao:
                    vender(symbol, atual, 'Take Profit')
                elif lucro <= -stop_loss and rsi > rsi_fundo:
                    vender(symbol, atual, 'Stop Loss')
                else:
                    log(f"🔄 Mantendo posição aberta para {symbol}", 'INFO')

        except Exception as e:
            log(f"Erro ao analisar {symbol}: {e}", 'ER
