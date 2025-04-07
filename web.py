from flask import Flask
import threading
from bot import bot_loop  # importamos o loop do bot

app = Flask(__name__)

@app.route('/')
def health():
    return 'OK', 200

# Iniciar o bot em thread separada
threading.Thread(target=bot_loop, daemon=True).start()

# Iniciar o servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

