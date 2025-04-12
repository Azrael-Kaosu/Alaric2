import ccxt
import time
import itertools

# Configuração da API
api_key = 'D0DiV60UucDChy9heZaDjo65Gli9s1Q4xyfEbUlAiWt718iYuqMVotlGd0GsG8Zz'
api_secret = 'PtTCQXFQ9VQkJaTdIfPAA53xBV4LYdq3SaS0VzATIAT5mD6geQxk7sGjxBJYtbN3'

binance = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',
    }
})

# Parâmetros de arbitragem
taxa = 0.001  # Taxa de 0.1% por transação
min_lucro_percentual = 0.5  # Só executa se lucro líquido > 0.5%
valor_entrada = 6  # Mínimo para ordens de mercado na Binance

# Moedas envolvidas
moedas = ['USDT', 'BTC', 'ETH', 'DOGE', 'SHIB', 'SOL']

def obter_saldo(moeda):
    try:
        balance = binance.fetch_balance()
        return float(balance['free'].get(moeda, 0))
    except Exception as e:
        print(f"Erro ao obter saldo de {moeda}: {e}")
        return 0

def obter_preco(par):
    try:
        ticker = binance.fetch_ticker(par)
        if not ticker or 'ask' not in ticker or 'bid' not in ticker:
            print(f"Erro ao obter o ticker de {par}. Dados incompletos.")
            return None
        return ticker
    except Exception as e:
        print(f"Erro ao obter preço de {par}: {e}")
        return None

def gerar_triangulos(moedas):
    triangulos = []
    for caminho in itertools.permutations(moedas, 3):
        if caminho[0] == 'USDT' and caminho[2] == 'USDT':
            triangulos.append(caminho)
    return triangulos

def calcular_lucro_triangulo(caminho, capital_inicial):
    moeda1, moeda2, moeda3 = caminho
    par1 = f"{moeda2}/{moeda1}"  # Ex: BTC/USDT
    par2 = f"{moeda3}/{moeda2}"  # Ex: ETH/BTC
    par3 = f"{moeda3}/{moeda1}"  # Ex: ETH/USDT

    ticker1 = obter_preco(par1)
    ticker2 = obter_preco(par2)
    ticker3 = obter_preco(par3)

    if not ticker1 or not ticker2 or not ticker3:
        print(f"Erro: Não foi possível obter preços para {caminho}")
        return None, f"Erro ao obter preço de uma das ordens para {caminho}."

    # Etapa 1: moeda1 → moeda2
    quantia_moeda2 = (capital_inicial / ticker1['ask']) * (1 - taxa)
    preco_compra1 = ticker1['ask']
    preco_venda1 = ticker1['bid']

    # Etapa 2: moeda2 → moeda3
    quantia_moeda3 = (quantia_moeda2 / ticker2['ask']) * (1 - taxa)
    preco_compra2 = ticker2['ask']
    preco_venda2 = ticker2['bid']

    # Etapa 3: moeda3 → moeda1
    capital_final = quantia_moeda3 * ticker3['bid'] * (1 - taxa)
    preco_compra3 = ticker3['ask']
    preco_venda3 = ticker3['bid']

    lucro = capital_final - capital_inicial
    lucro_percentual = (lucro / capital_inicial) * 100

    # Exibindo detalhes para depuração
    print(f"🔍 Calculando arbitragem para {caminho}")
    print(f"    Etapa 1 ({par1}): Preço compra: {preco_compra1}, Preço venda: {preco_venda1}")
    print(f"    Etapa 2 ({par2}): Preço compra: {preco_compra2}, Preço venda: {preco_venda2}")
    print(f"    Etapa 3 ({par3}): Preço compra: {preco_compra3}, Preço venda: {preco_venda3}")
    print(f"    Lucro bruto: {lucro:.4f} USDT | Lucro percentual: {lucro_percentual:.2f}%")

    if lucro_percentual < min_lucro_percentual:
        return None, f"Lucro insuficiente: {lucro_percentual:.2f}% (mínimo: {min_lucro_percentual}%)"

    return {
        'caminho': caminho,
        'capital_final': capital_final,
        'lucro': lucro,
        'lucro_percentual': lucro_percentual,
        'ordens': [par1, par2, par3],
        'precos': [(preco_compra1, preco_venda1), (preco_compra2, preco_venda2), (preco_compra3, preco_venda3)],
    }, None

def executar_orden_triangulo(caminho, valor_usdt):
    print("🚀 Executando arbitragem:", caminho)
    moeda1, moeda2, moeda3 = caminho

    # Ordem 1: USDT → moeda2
    par1 = f"{moeda2}/USDT"
    ticker1 = obter_preco(par1)
    quantia_moeda2 = (valor_usdt / ticker1['ask']) * (1 - taxa)
    binance.create_market_buy_order(par1, quantia_moeda2)

    # Ordem 2: moeda2 → moeda3
    par2 = f"{moeda3}/{moeda2}"
    ticker2 = obter_preco(par2)
    quantia_moeda3 = (quantia_moeda2 / ticker2['ask']) * (1 - taxa)
    binance.create_market_buy_order(par2, quantia_moeda3)

    # Ordem 3: moeda3 → USDT
    par3 = f"{moeda3}/USDT"
    ticker3 = obter_preco(par3)
    binance.create_market_sell_order(par3, quantia_moeda3)

    print("✅ Arbitragem executada com sucesso!")

def verificar_todas_rotas():
    saldo_usdt = obter_saldo('USDT')
    if saldo_usdt < valor_entrada:
        print(f"⚠️ Saldo insuficiente ({saldo_usdt:.2f} USDT). Esperando...\n")
        return

    triangulos = gerar_triangulos(moedas)

    print("🔍 Verificando rotas...\n")
    for caminho in triangulos:
        resultado, erro = calcular_lucro_triangulo(caminho, valor_entrada)
        
        if erro:
            print(f"❌ Erro ao processar {caminho}: {erro}\n")
        elif resultado:
            lucro = resultado['lucro']
            perc = resultado['lucro_percentual']
            ordens = resultado['ordens']
            precos = resultado['precos']

            # Log detalhado para ajudar a depurar
            print(f"⏱ Tentando arbitragem: {caminho}")
            for i, ordem in enumerate(ordens):
                preco_compra, preco_venda = precos[i]
                print(f"    {ordem} - Preço de compra: {preco_compra:.4f} | Preço de venda: {preco_venda:.4f}")

            print(f"    Lucro bruto: {lucro:.4f} USDT ({perc:.2f}%)")

            if perc >= min_lucro_percentual:
                print(f"💰 OPORTUNIDADE: {caminho} | Lucro: {lucro:.4f} USDT ({perc:.2f}%)")
                executar_orden_triangulo(caminho, valor_entrada)
                return  # Espera a próxima rodada
            else:
                print(f"📉 Rota: {caminho} | Lucro insuficiente: {lucro:.4f} USDT ({perc:.2f}%)\n")

def monitorar():
    while True:
        verificar_todas_rotas()
        time.sleep(5)

monitorar()
