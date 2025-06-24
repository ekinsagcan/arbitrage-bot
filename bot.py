import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================
# CONFIGURATION
# ======================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Replace with your actual token
COMMON_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]

# ======================
# EXCHANGE ENDPOINTS
# ======================
EXCHANGES = {
    "Binance": "https://api.binance.com/api/v3/ticker/price",
    "OKX": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
    "KuCoin": "https://api.kucoin.com/api/v1/market/allTickers",
    "Bybit": "https://api.bybit.com/v5/market/tickers?category=spot",
    "MEXC": "https://api.mexc.com/api/v3/ticker/price",
    "Bitget": "https://api.bitget.com/api/spot/v1/market/tickers",
    "Gate.io": "https://api.gate.io/api2/1/tickers",
    "CoinEx": "https://api.coinex.com/v1/market/ticker/all",
    "LBank": "https://api.lbank.info/v2/ticker.do?symbol=all"
}

# ======================
# FETCH PRICE FUNCTIONS
# ======================
async def fetch_prices(symbol):
    symbol = symbol.upper()
    prices = []

    for name, url in EXCHANGES.items():
        try:
            if name == "Binance":
                r = requests.get(url)
                data = r.json()
                for item in data:
                    if item["symbol"] == symbol:
                        prices.append((name, float(item["price"])))

            elif name == "OKX":
                r = requests.get(url)
                data = r.json()["data"]
                for item in data:
                    if item["instId"].replace("-", "") == symbol:
                        prices.append((name, float(item["last"])))

            elif name == "KuCoin":
                r = requests.get(url)
                data = r.json()["data"]["ticker"]
                for item in data:
                    if item["symbol"].replace("-", "") == symbol:
                        prices.append((name, float(item["last"])))

            elif name == "Bybit":
                r = requests.get(url)
                data = r.json()["result"]["list"]
                for item in data:
                    if item["symbol"] == symbol:
                        prices.append((name, float(item["lastPrice"])))

            elif name == "MEXC":
                r = requests.get(url)
                data = r.json()
                for item in data:
                    if item["symbol"] == symbol:
                        prices.append((name, float(item["price"])))

            elif name == "Bitget":
                r = requests.get(url)
                data = r.json()["data"]
                for item in data:
                    if item["symbol"].replace("_", "") == symbol:
                        prices.append((name, float(item["last"])))

            elif name == "Gate.io":
                r = requests.get(url)
                data = r.json()
                if symbol in data:
                    prices.append((name, float(data[symbol]["last"])))

            elif name == "CoinEx":
                r = requests.get(url)
                data = r.json()["data"]
                if symbol in data:
                    prices.append((name, float(data[symbol]["last"])))

            elif name == "LBank":
                r = requests.get(url)
                data = r.json()["data"]
                for item in data:
                    if item["symbol"].upper() == symbol:
                        prices.append((name, float(item["ticker"]["latest"])))

        except Exception as e:
            print(f"Error fetching from {name}: {e}")

    return prices

# ======================
# BOT COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(pair, callback_data=pair)]
        for pair in COMMON_PAIRS
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    text = (
        "👋 Welcome to the Multi-Exchange Arbitrage Bot!\n\n"
        "Select a trading pair below to see real-time arbitrage opportunities across major crypto exchanges."
    )
    await update.message.reply_text(text, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data

    prices = await fetch_prices(symbol)
    if not prices:
        await query.edit_message_text(f"❌ No data found for {symbol}")
        return

    prices.sort(key=lambda x: x[1])
    lowest = prices[0]
    highest = prices[-1]
    diff = highest[1] - lowest[1]
    percent = (diff / lowest[1]) * 100 if lowest[1] else 0

    message = (
        f"📊 *Arbitrage Report for {symbol}*\n\n"
        f"🔻 Lowest: {lowest[0]} - {lowest[1]:.4f}\n"
        f"🔺 Highest: {highest[0]} - {highest[1]:.4f}\n\n"
        f"💰 Difference: {diff:.4f} ({percent:.2f}%)"
    )
    await query.edit_message_text(message, parse_mode="Markdown")

# ======================
# BOT SETUP
# ======================
if __name__ == "__main__":
    app = ApplicationBuilder().token("7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
