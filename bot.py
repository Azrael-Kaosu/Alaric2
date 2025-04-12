import ccxt
import time
import datetime
import numpy as np

# === CONFIGURAÇÕES ===
API_KEY = 'D0DiV60UucDChy9heZaDjo65Gli9s1Q4xyfEbUlAiWt718iYuqMVotlGd0GsG8Zz'
API_SECRET = 'PtTCQXFQ9VQkJaTdIfPAA53xBV4LYdq3SaS0VzATIAT5mD6geQxk7sGjxBJYtbN3'
symbol_list = ['DOGE/USDT', 'SHIB/USDT']
capital_por_ordem = 5.5
intervalo = 20
take_profit = 0.01
stop_loss = 0.005
trailing_delta = 0.0025
rsi_gatilho = 10
max_prejuizos = 3
pausa_em_minutos = 60

usar_adx = True
usar_volume_candle = True
usar_divergencia_rsi = True
usar_backtest_rapido = True

# === CONEXÃO ===
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(False)

abertas = {}
prejuizos = 0
ultima_pausa = 0

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def indicadores(precos):
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
    std = np.std(closes[-20:])
    upper = media + 2 * std
    lower = media - 2 * std
    return media, rsi, macd, signal, upper, lower

def pegar_precos(symbol, limit=50):
    ohlcv = exchange.fetch_ohlcv(symbol, '1m', limit=limit)
    return ohlcv, [x[4] for x in ohlcv]

def comprar(symbol, preco):
    log(f"🟢 COMPRA {symbol} a {preco:.6f}")
    exchange.create_market_buy_order(symbol, capital_por_ordem / preco)
    abertas[symbol] = {'compra': preco, 'topo': preco, 'tempo': time.time()}

def vender(symbol, preco, motivo):
    global prejuizos, ultima_pausa
    entrada = abertas[symbol]['compra']
    lucro = (preco - entrada) / entrada
    log(f"🔴 VENDA {symbol} a {preco:.6f} | Motivo: {motivo} | Lucro: {lucro*100:.2f}%")
    amount = capital_por_ordem / entrada
    exchange.create_market_sell_order(symbol, amount)
    if lucro < 0:
        prejuizos += 1
        if prejuizos >= max_prejuizos:
            log(f"⚠️ Atingiu {max_prejuizos} prejuízos. Pausando por {pausa_em_minutos} minutos.")
            ultima_pausa = time.time()
    else:
        prejuizos = 0
    del abertas[symbol]

def calcular_adx(ohlcv, periodo=14):
    highs = np.array([c[2] for c in ohlcv])
    lows = np.array([c[3] for c in ohlcv])
    closes = np.array([c[4] for c in ohlcv])
    plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]), highs[1:] - highs[:-1], 0)
    minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]), lows[:-1] - lows[1:], 0)
    tr = np.maximum(highs[1:], closes[:-1]) - np.minimum(lows[1:], closes[:-1])
    atr = np.convolve(tr, np.ones(periodo), 'valid') / periodo
    plus_di = 100 * (np.convolve(plus_dm, np.ones(periodo), 'valid') / atr)
    minus_di = 100 * (np.convolve(minus_dm, np.ones(periodo), 'valid') / atr)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = np.mean(dx[-periodo:])
    return adx

def detectar_candle_verde_e_volume(ohlcv):
    open_price, close_price = ohlcv[-1][1], ohlcv[-1][4]
    volume = ohlcv[-1][5]
    avg_volume = np.mean([x[5] for x in ohlcv[-21:-1]])
    return close_price > open_price and volume > avg_volume

def detectar_divergencia_rsi(precos):
    precos_np = np.array(precos)
    rsi_vals = []
    for i in range(14, len(precos_np)):
        diff = np.diff(precos_np[:i])
        ganhos = np.maximum(diff, 0)
        perdas = np.maximum(-diff, 0)
        avg_gain = np.mean(ganhos[-14:])
        avg_loss = np.mean(perdas[-14:])
        rs = avg_gain / avg_loss if avg_loss != 0 else 1e10
        rsi = 100 - (100 / (1 + rs))
        rsi_vals.append(rsi)
    return precos[-1] < precos[-2] and rsi_vals[-1] > rsi_vals[-2]

def backtest_rapido(ohlcv):
    resultado = []
    for i in range(-30, -5, 5):
        entrada = ohlcv[i][4]
        saida = ohlcv[i+4][4]
        resultado.append((saida - entrada) / entrada)
    ganhos = [r for r in resultado if r > 0]
    return len(ganhos) >= 3

def analisar():
    global ultima_pausa
    if time.time() - ultima_pausa < pausa_em_minutos * 60:
        log("⏸️ Bot em pausa por prejuízos.")
        return

    for symbol in symbol_list:
        try:
            ohlcv, precos = pegar_precos(symbol)
            atual = precos[-1]
            media, rsi, macd, signal, upper, lower = indicadores(precos)
            log(f"🔍 {symbol} | Preço: {atual:.6f} | RSI: {rsi:.2f}")

            if symbol not in abertas:
                entrar = False
                if detectar_candle_verde_e_volume(ohlcv):
                    entrar = True
                elif rsi < rsi_gatilho:
                    entrar = True
                elif atual < lower and macd > signal and atual > media:
                    entrar = True

                if entrar:
                    confirmacoes = []

                    if usar_adx:
                        adx = calcular_adx(ohlcv)
                        confirmacoes.append(adx > 20)

                    if usar_volume_candle:
                        confirmacoes.append(detectar_candle_verde_e_volume(ohlcv))

                    if usar_divergencia_rsi:
                        confirmacoes.append(detectar_divergencia_rsi(precos))

                    if usar_backtest_rapido:
                        confirmacoes.append(backtest_rapido(ohlcv))

                    if all(confirmacoes):
                        comprar(symbol, atual)
                    else:
                        log(f"❌ Entrada negada por confirmações em {symbol}")
            else:
                preco_compra = abertas[symbol]['compra']
                topo = abertas[symbol]['topo']
                lucro = (atual - preco_compra) / preco_compra

                if atual > topo:
                    abertas[symbol]['topo'] = atual

                trailing_stop = abertas[symbol]['topo'] * (1 - trailing_delta)

                if lucro >= take_profit:
                    vender(symbol, atual, 'Take Profit')
                elif lucro <= -stop_loss:
                    vender(symbol, atual, 'Stop Loss')
                elif atual <= trailing_stop:
                    vender(symbol, atual, 'Trailing Stop')

        except Exception as e:
            log(f"⚠️ Erro em {symbol}: {e}")

log("🤖 Alaric V6 com confirmações inteligentes iniciado...\n")
while True:
    analisar()
    time.sleep(intervalo)
