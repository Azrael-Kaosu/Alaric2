import os
import ccxt
import time
import threading
import statistics
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================
# 🔐 Configurações da Binance
# ==========================
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True
})

# ==========================
# ⚙️ Configurações gerais
# ==========================
pares = {
    "DOGE/USDT": {"quantidade": 6},
    "SHIB/USDT": {"quantidade": 6}
}

take_profit_percent = 1.01  # 1%
stop_loss_percent = 0.995   # -0.5%
rsi_buy_threshold = 15
rsi_sell_threshold = 80
rsi_protege_venda = True

intervalo = '1m'
limite_candles = 100

# Armazenar ordens ativas
ordens_ativas = {}

# ==========================
# 🔍 Funções Técnicas
# ==========================

def obter_dados_mercado(par):
    ohlcv = exchange.fetch_ohlcv(par, timeframe=intervalo, limit=limite_candles)
    return [x[4] for x in ohlcv]

def calcular_rsi(precos, periodo=14):
    ganhos = []
    perdas = []

    for i in range(1, periodo + 1):
        delta = precos[-i] - precos[-i - 1]
        if delta > 0:
            ganhos.append(delta)
        else:
            perdas.append(abs(delta))

    if not ganhos:
        return 0
    if not perdas:
        return 100

    media_ganhos = sum(ganhos) / periodo
    media_perdas = sum(perdas) / periodo
    rs = media_ganhos / media_perdas
    return 100 - (100 / (1 + rs))

def calcular_macd(precos):
    def ema(prices, period):
        return statistics.mean(prices[-period:])

    ema12 = ema(precos, 12)
    ema26 = ema(precos, 26)
    macd = ema12 - ema26
    signal = ema(precos[-9:], 9)
    return macd, signal

# ==========================
# 🤖 Execução de Ordens
# ==========================

def executar_bot(par):
    global ordens_ativas

    while True:
        try:
            precos = obter_dados_mercado(par)
            media_20 = statistics.mean(precos[-20:])
            preco_atual = precos[-1]
            rsi = calcular_rsi(precos)
            macd, signal = calcular_macd(precos)
            simbolo_formatado = par.replace("/", "")

            posicao_aberta = ordens_ativas.get(par, None)

            if not posicao_aberta:
                if macd > signal and preco_atual > media_20:
                    if rsi < rsi_buy_threshold:
                        print(f"[{par}] RSI < {rsi_buy_threshold}. Compra permitida, mas com cautela.")

                    quantidade = pares[par]["quantidade"] / preco_atual
                    order = exchange.create_market_buy_order(par, quantidade)
                    ordens_ativas[par] = {
                        "preco_compra": preco_atual,
                        "quantidade": quantidade,
                        "hora": datetime.now()
                    }
                    print(f"[{par}] ✅ COMPRA realizada a {preco_atual:.4f}")
            else:
                preco_compra = ordens_ativas[par]["preco_compra"]
                if preco_atual >= preco_compra * take_profit_percent:
                    if rsi < rsi_buy_threshold and rsi_protege_venda:
                        print(f"[{par}] RSI < {rsi_buy_threshold}, venda ignorada mesmo com lucro.")
                    else:
                        exchange.create_market_sell_order(par, ordens_ativas[par]["quantidade"])
                        print(f"[{par}] ✅ VENDA (lucro) realizada a {preco_atual:.4f}")
                        ordens_ativas.pop(par)
                elif preco_atual <= preco_compra * stop_loss_percent:
                    if rsi < rsi_buy_threshold and rsi_protege_venda:
                        print(f"[{par}] RSI < {rsi_buy_threshold}, venda ignorada mesmo com prejuízo.")
                    else:
                        exchange.create_market_sell_order(par, ordens_ativas[par]["quantidade"])
                        print(f"[{par}] ❌ VENDA (stop-loss) realizada a {preco_atual:.4f}")
                        ordens_ativas.pop(par)

        except Exception as e:
            print(f"[{par}] Erro: {e}")

        time.sleep(10)

# ==========================
# 🌐 Servidor de Health Check
# ==========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot esta vivo!")

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


# ==========================
# 🚀 Inicialização
# ==========================

def iniciar_bot():
    print("[🔥] Bot Versão 3 com proteção contra ordens duplicadas iniciado.")

      # Iniciar bot para cada par
    for par in pares:
        threading.Thread(target=executar_bot, args=(par,), daemon=True).start()



