import ccxt
import pandas as pd
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from ta.momentum import RSIIndicator
from ta.trend import MACD

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

PAIR_LIST = ["DOGE/USDT", "SHIB/USDT"]
ORDER_AMOUNT = 6
STOP_LOSS = 0.005
TAKE_PROFIT = 0.01

profit_tracker = {pair: 0 for pair in PAIR_LIST}


def send_email_report():
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = 'Relatório Diário do Bot Cripto V3'

    body = "\n".join([f"{pair}: {profit_tracker[pair]:.2f} USDT" for pair in PAIR_LIST])
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
            print("Relatório diário enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar email: {e}")


def get_ohlcv(pair, timeframe='1m', limit=100):
    data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df


def analyze(pair):
    df = get_ohlcv(pair)
    df['rsi'] = RSIIndicator(df['close']).rsi()
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma20'] = df['close'].rolling(20).mean()

    return df


def get_balance(symbol='USDT'):
    balance = exchange.fetch_balance()
    return balance['free'][symbol]


def place_order(pair, side):
    try:
        price = exchange.fetch_ticker(pair)['last']
        amount = ORDER_AMOUNT / price
        order = exchange.create_market_order(pair, side, amount)
        return price, amount
    except Exception as e:
        print(f"Erro ao executar ordem {side} para {pair}: {e}")
        return None, None


def trade_logic(pair):
    in_position = False
    entry_price = 0
    amount = 0

    while True:
        try:
            df = analyze(pair)
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Condição de entrada
            if not in_position:
                if (
                    current['macd'] > current['macd_signal'] and
                    current['close'] > current['sma20']
                ):
                    price, amount = place_order(pair, 'buy')
                    if price:
                        entry_price = price
                        in_position = True
                        print(f"[{pair}] Comprado a {entry_price:.4f} com {amount:.4f} unidades")

            # Condição de saída
            elif in_position:
                price = exchange.fetch_ticker(pair)['last']
                profit_percent = (price - entry_price) / entry_price

                rsi_value = current['rsi']

                # Evita vender se RSI < 15
                if rsi_value < 15:
                    print(f"[{pair}] RSI ({rsi_value:.2f}) muito baixo, evitando venda...")
                    time.sleep(60)
                    continue

                if (
                    profit_percent >= TAKE_PROFIT or
                    profit_percent <= -STOP_LOSS or
                    rsi_value > 80
                ):
                    _, _ = place_order(pair, 'sell')
                    pnl = (price - entry_price) * amount
                    profit_tracker[pair] += pnl
                    print(f"[{pair}] Vendido a {price:.4f}, lucro: {pnl:.4f} USDT")
                    in_position = False
                    entry_price = 0
                    amount = 0

        except Exception as e:
            print(f"[{pair}] Erro na lógica de trade: {e}")

        time.sleep(60)


def start_bot():
    for pair in PAIR_LIST:
        thread = threading.Thread(target=trade_logic, args=(pair,))
        thread.start()

    # Agendamento do envio de email diário
    while True:
        now = time.localtime()
        if now.tm_hour == 23 and now.tm_min == 59:
            send_email_report()
            time.sleep(60)
        time.sleep(30)


if __name__ == "__main__":
    print("Bot Versão 3 iniciado com DOGE e SHIB. Operando 24h por dia 🔥")
    start_bot()
