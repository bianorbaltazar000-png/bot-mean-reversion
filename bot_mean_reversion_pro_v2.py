import time
import csv
import pandas as pd
from binance.client import Client
import matplotlib.pyplot as plt

# ================= CONFIG =================

API_KEY = "rd6E8StpKmMbuEUwk5CyfiGzrvz8UPjwwxr8cArskwNJdrDdNVIEoCrWdwFTt5Gs"
API_SECRET = "fZjbYCh7ESBZGe8DrkVh8OsBcFM7ny9ANHai23P5hivCQga4JKjnATjce8Mz8Fxf"

REAL_MODE = False   # <<< mude para True SOMENTE quando for real

symbol = "BNBUSDT"
interval = Client.KLINE_INTERVAL_1MINUTE

saldo = 100.0              # saldo inicial (simulado)
risk_pct = 0.05           # 5% do saldo por trade (realista)
stop_pct = 0.003          # 0.3%
take_pct = 0.004          # 0.4%
trail_pct = 0.002         # 0.2%

# ====== PROTEÇÕES ======
max_daily_loss_pct = 0.03   # 3% por dia
max_trades_day = 20

daily_start_balance = saldo
trading_enabled = True

# ================= CONEXÃO =================
if REAL_MODE:
    client = Client(API_KEY, API_SECRET)
    print("🚨 MODO REAL ATIVO")
else:
    client = Client(API_KEY, API_SECRET, testnet=True)
    print("🧪 TESTNET ATIVO")

# ================= VARIÁVEIS =================
posicao = False
entrada = 0.0
stop = 0.0
take = 0.0
trail = 0.0

trades = 0
wins = 0
equity = [saldo]
cooldown = 0

# ================= CSV =================
csvfile = open("trades.csv", "w", newline="")
writer = csv.writer(csvfile)
writer.writerow(["Entrada","Saida","Resultado_%","Saldo"])

# ================= GRÁFICO =================
plt.ion()
fig, ax = plt.subplots()

print("🤖 MEAN REVERSION PRO V2")

# ================= LOOP =================
while True:

    klines = client.get_klines(symbol=symbol, interval=interval, limit=150)

    df = pd.DataFrame(klines, columns=[
        "t","o","h","l","c","v","ct","q","n","tb","tq","i"
    ])

    df["c"] = df["c"].astype(float)

    # RSI
    delta = df["c"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"] = 100 - (100/(1+rs))

    # Bollinger
    mid = df["c"].rolling(20).mean()
    std = df["c"].rolling(20).std()
    df["bb_low"] = mid - std*2
    df["bb_up"] = mid + std*2

    preco = df["c"].iloc[-1]
    rsi = df["rsi"].iloc[-1]
    bb_low = df["bb_low"].iloc[-1]
    bb_up = df["bb_up"].iloc[-1]

    print(f"Preço: {preco:.2f} | RSI: {rsi:.1f}")

    # ===== VERIFICA PROTEÇÕES =====
    daily_loss = (saldo - daily_start_balance) / daily_start_balance

    if daily_loss <= -max_daily_loss_pct:
        print("🛑 LIMITE DE PERDA DIÁRIA ATINGIDO — BOT PARADO")
        trading_enabled = False

    if trades >= max_trades_day:
        print("🛑 LIMITE DE TRADES ATINGIDO — BOT PARADO")
        trading_enabled = False

    if cooldown > 0:
        cooldown -= 1

    # ================= BUY =================
    if trading_enabled and not posicao and cooldown == 0 and preco <= bb_low and rsi < 30:

        entrada = preco
        size = saldo * risk_pct

        stop = entrada * (1 - stop_pct)
        take = entrada * (1 + take_pct)
        trail = entrada * (1 - trail_pct)

        posicao = True
        trades += 1
        cooldown = 2

        print("🟢 BUY", round(entrada,2), "| Size:", round(size,2))

        # (em REAL você colocaria create_order aqui)

    # ================= TRAILING =================
    if posicao:
        novo_trail = preco * (1 - trail_pct)
        if novo_trail > trail:
            trail = novo_trail

    # ================= SELL =================
    if posicao and (preco >= take or preco <= trail or rsi > 55):

        resultado = (preco - entrada) / entrada
        saldo += saldo * resultado
        equity.append(saldo)

        if resultado > 0:
            wins += 1

        writer.writerow([round(entrada,2), round(preco,2), round(resultado*100,2), round(saldo,2)])

        posicao = False
        cooldown = 2

        print("🔴 FECHOU", round(preco,2))
        print("Saldo:", round(saldo,2))

    # ================= STATS =================
    winrate = wins/trades*100 if trades > 0 else 0
    print(f"Trades:{trades} | Winrate:{round(winrate,1)}% | Equity:{round(saldo,2)}")
    print("-"*40)

    # ================= GRÁFICO =================
    ax.clear()
    ax.plot(equity)
    ax.set_title("Equity Curve")
    plt.pause(0.01)

    time.sleep(60)
