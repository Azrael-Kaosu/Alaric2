import ccxt
import time
import pandas as pd
from datetime import datetime
import pytz

# Configuração da Binance
exchange = ccxt.binance({
    'apiKey': 'SUA_API_KEY',
    'secret': 'SUA_SECRET_KEY',
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

# Parâmetros
symbols = ['DOGE/USDT', 'SHIB/USDT']
order_size = 6  # USD por ordem
take_profit_pct = 0.01
stop_loss_pct = 0.005
interval = '1m'
limit = 100

# Armazena posições abertas
positions = {}

def get_data(symbol):
    candles = exchange.fetch_ohlcv(symbol, interval, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_indicators(df):
    df['ema12'] = df['close'].ewm(span=12).mean()
    df['ema26'] = df['close'].ewm(span=26).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9).mean()
    df['rsi'] = compute_rsi(df['close'], 14)
    df['ma20'] = df['close'].rolling(window=20).mean()
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def log(msg):
    agora = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M:%S")
    print(f"[{agora}] {msg}")

def trade():
    for symbol in symbols:
        try:
            df = get_data(symbol)
            df = calculate_indicators(df)

            last = df.iloc[-1]
            previous = df.iloc[-2]
            price = last['close']
            rsi = last['rsi']
            macd = last['macd']
            signal = last['signal']
            ma20 = last['ma20']

            # Checar se já temos uma posição aberta
            position = positions.get(symbol)

            # CONDIÇÃO DE COMPRA
            if not position:
                if macd > signal and previous['macd'] <= previous['signal'] and price > ma20:
                    if rsi < 15:
                        log(f"🎯 RSI favorável para entrada (RSI = {rsi:.2f})")
                    amount = order_size / price
                    # exchange.create_market_buy_order(symbol, amount)
                    positions[symbol] = {
                        'entry_price': price,
                        'amount': amount
                    }
                    log(f"[{symbol}] Comprado a {price:.4f} com {amount:.4f} unidades")

            # CONDIÇÃO DE VENDA
            if position:
                entry = position['entry_price']
                amount = position['amount']
                change = (price - entry) / entry

                if rsi < 15:
                    log(f"🔒 RSI abaixo de 15 — evitando venda (RSI = {rsi:.2f})")
                elif change >= take_profit_pct:
                    # exchange.create_market_sell_order(symbol, amount)
                    log(f"[{symbol}] Take profit: Vendido a {price:.4f} com lucro de {change*100:.2f}%")
                    del positions[symbol]
                elif change <= -stop_loss_pct:
                    # exchange.create_market_sell_order(symbol, amount)
                    log(f"[{symbol}] Stop loss: Vendido a {price:.4f} com prejuízo de {change*100:.2f}%")
                    del positions[symbol]
                elif rsi > 80:
                    # exchange.create_market_sell_order(symbol, amount)
                    log(f"[{symbol}] RSI > 80: Vendido a {price:.4f} mesmo sem atingir TP/SL")
                    del positions[symbol]

        except Exception as e:
            log(f"Erro em {symbol}: {e}")

# Loop infinito
log("🤖 Bot Versão 3 com proteção contra ordens duplicadas iniciado.")
while True:
    trade()
    time.sleep(60)
