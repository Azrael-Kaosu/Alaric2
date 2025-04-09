import ccxt
import time
import numpy as np

# === CONFIGURAÇÕES ===
API_KEY = 'D0DiV60UucDChy9heZaDjo65Gli9s1Q4xyfEbUlAiWt718iYuqMVotlGd0GsG8Zz'
API_SECRET = 'PtTCQXFQ9VQkJaTdIfPAA53xBV4LYdq3SaS0VzATIAT5mD6geQxk7sGjxBJYtbN3'
symbol = 'BTC/USDT'  # usa algo seguro e com volume

capital_por_ordem = 10  # em USDT
intervalo = 15  # segundos
rsi_topo = 70
rsi_fundo = 30

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(False)

# === FUNÇÕES ===
def pegar_precos(symbol, limit=50):
    try:
        print(f"📈 Pegando preços de {symbol}", flush=True)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
        closes = [x[4] for x in ohlcv]
        return closes
    except Exception as e:
        print(f"⚠️ Erro ao pegar preços: {e}", flush=True)
        return []

def calcular_rsi(closes, period=14):
    deltas = np.diff(closes)
    ganhos = np.maximum(deltas, 0)
    perdas = np.maximum(-deltas, 0)
    avg_gain = np.mean(ganhos[-period:])
    avg_loss = np.mean(perdas[-period:])
    rs = avg_gain / avg_loss if avg_loss != 0 else 1e10
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analisar():
    precos = pegar_precos(symbol)
    if len(precos) < 20:
        print("❌ Dados insuficientes", flush=True)
        return

    rsi = calcular_rsi(precos)
    atual = precos[-1]
    media = np.mean(precos[-20:])

    print(f"💹 Preço atual: {atual:.2f} | Média: {media:.2f} | RSI: {rsi:.2f}", flush=True)

    if rsi < rsi_fundo:
        print("🟢 RSI indica sobrevenda! (possível compra)", flush=True)
    elif rsi > rsi_topo:
        print("🔴 RSI indica sobrecompra! (possível venda)", flush=True)
    else:
        print("⏸️ Mercado neutro", flush=True)

# === LOOP DO BOT ===
print("🤖 Iniciando Alaric V4 Modo Debug...\n")
while True:
    try:
        analisar()
    except Exception as e:
        print(f"❌ Erro no loop: {e}", flush=True)
    time.sleep(intervalo)
