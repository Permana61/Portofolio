import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes


BOT_TOKEN = "8407060260:AAFZzq35nnwisNYIXHr6gWX3Ciji7wXayPw"

# ----------------------- CoinGecko API -----------------------
def valid_token_id(token_id: str) -> bool:

    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=10)
        r.raise_for_status()
        coins = r.json()
        ids = [c['id'] for c in coins]
        return token_id.lower() in ids
    except:
        return False

def get_price(token_id: str) -> float:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        r = requests.get(url, params={"ids": token_id, "vs_currencies": "usd"}, timeout=10)
        r.raise_for_status()
        return float(r.json()[token_id]["usd"])
    except:
        return None

def get_historical(token_id: str, days: int = 60) -> pd.Series:
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
        r = requests.get(url, params={"vs_currency":"usd","days":days}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "prices" not in data or not data["prices"]:
            return pd.Series([])
        prices = [p[1] for p in data["prices"]]
        return pd.Series(prices)
    except:
        return pd.Series([])

# ----------------------- Indicators -----------------------
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    roll_up = pd.Series(gain).ewm(alpha=1/period, adjust=False).mean()
    roll_down = pd.Series(loss).ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    return 100 - (100 / (1 + rs))

def ema_cross_signal(series: pd.Series, fast: int = 50, slow: int = 200):
    efast = ema(series, fast)
    eslow = ema(series, slow)
    cross = efast - eslow
    if len(cross) < 2:
        return "none"
    prev, last = cross.iloc[-2], cross.iloc[-1]
    if prev <= 0 and last > 0:
        return "golden"
    elif prev >= 0 and last < 0:
        return "death"
    return "none"

# ----------------------- Telegram Handlers -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Aku bot analisis crypto.\n\n"
        "Perintah:\n"
        "/price <token> - harga USD\n"
        "/rsi <token> - RSI terakhir\n"
        "/ma <token> <fast> <slow> - EMA crossover\n"
        "/signal <token> - signal EMA + RSI\n"
        "/chart <token> - chart candlestick + EMA + RSI"
    )

async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /price bitcoin")
        return
    token = context.args[0].lower()
    if not valid_token_id(token):
        await update.message.reply_text(f"Token '{token}' tidak valid di CoinGecko")
        return
    price = get_price(token)
    if price is None:
        await update.message.reply_text(f"Gagal mengambil harga {token}")
        return
    await update.message.reply_text(f"${price:,.2f}")

async def rsi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /rsi bitcoin")
        return
    token = context.args[0].lower()
    if not valid_token_id(token):
        await update.message.reply_text(f"Token '{token}' tidak valid")
        return
    prices = get_historical(token, 30)
    if prices.empty:
        await update.message.reply_text(f"Gagal mengambil data historis {token}")
        return
    val = rsi(prices).iloc[-1]
    tag = "Neutral"
    if val >= 70: tag = "Overbought"
    elif val <= 30: tag = "Oversold"
    await update.message.reply_text(f"RSI(14) {token} = {val:.2f} ({tag})")

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Contoh: /ma bitcoin 10 30")
        return
    token = context.args[0].lower()
    if not valid_token_id(token):
        await update.message.reply_text(f"Token '{token}' tidak valid")
        return
    fast, slow = int(context.args[1]), int(context.args[2])
    prices = get_historical(token, max(fast, slow)*2)
    if prices.empty:
        await update.message.reply_text(f"Gagal mengambil data historis {token}")
        return
    cross = ema_cross_signal(prices, fast, slow)
    await update.message.reply_text(f"EMA{fast}/{slow} crossover {token}: {cross.upper()}")

async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /signal bitcoin")
        return
    token = context.args[0].lower()
    if not valid_token_id(token):
        await update.message.reply_text(f"Token '{token}' tidak valid")
        return
    prices = get_historical(token, 60)
    if prices.empty:
        await update.message.reply_text(f"Gagal mengambil data historis {token}")
        return
    cross = ema_cross_signal(prices)
    rsi_val = rsi(prices).iloc[-1]
    signal = "HOLD"
    if cross == "golden" and 40 <= rsi_val <= 70:
        signal = "BUY"
    elif cross == "death" and 30 <= rsi_val <= 60:
        signal = "SELL"
    await update.message.reply_text(
        f"{token} signal: {signal}\nRSI={rsi_val:.2f}\nEMA50/200 crossover={cross.upper()}\nIni bukan nasihat finansial."
    )

async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /chart bitcoin")
        return
    token = context.args[0].lower()
    if not valid_token_id(token):
        await update.message.reply_text(f"Token '{token}' tidak valid")
        return
    prices = get_historical(token, 60)
    if prices.empty:
        await update.message.reply_text(f"Gagal mengambil data historis untuk {token}")
        return

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(prices, label="Price", color="blue")
    ax.plot(ema(prices, 10), label="EMA10", color="green")
    ax.plot(ema(prices, 30), label="EMA30", color="red")
    ax.set_title(f"{token.title()} Candlestick + EMA")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price USD")
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    await update.message.reply_photo(photo=InputFile(buf, filename=f"{token}.png"))
    plt.close(fig)

# ----------------------- Main -----------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("rsi", rsi_cmd))
    app.add_handler(CommandHandler("ma", ma_cmd))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CommandHandler("chart", chart_cmd))

    print("Bot running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
