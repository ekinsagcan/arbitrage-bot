import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ======================
# CONFIGURATION
# ======================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Replace with your actual token

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
    "CoinEx": "https://api.coinex.com/v1/market/ticker/all",
    "LBank": "https://api.lbank.info/v2/ticker.do?symbol=all"
}

# ======================
# FETCH ALL PRICES
# ======================
async def fetch_all_prices():
    coins_by_exchange = {}
    for name, url in EXCHANGES.items():
        try:
            r = requests.get(url)
            data = r.json()
            coins = {}

            if name == "Binance":
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["price"])
                    coins[symbol] = price

            elif name == "OKX":
                for item in data.get("data", []):
                    symbol = item["instId"].replace("-", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "KuCoin":
                for item in data.get("data", {}).get("ticker", []):
                    symbol = item["symbol"].replace("-", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "Bybit":
                for item in data.get("result", {}).get("list", []):
                    symbol = item["symbol"].upper()
                    price = float(item["lastPrice"])
                    coins[symbol] = price

            elif name == "MEXC":
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["price"])
                    coins[symbol] = price

            elif name == "Bitget":
                for item in data.get("data", []):
                    symbol = item["symbol"].replace("_", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "CoinEx":
                for symbol, item in data.get("data", {}).items():
                    symbol = symbol.upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "LBank":
                for item in data.get("data", []):
                    symbol = item["symbol"].upper()
                    price = float(item["ticker"]["latest"])
                    coins[symbol] = price

            coins_by_exchange[name] = coins
        except Exception as e:
            print(f"Error fetching from {name}: {e}")
    return coins_by_exchange

# ======================
# FIND TOP OPPORTUNITIES
# ======================
def find_top_arbitrage_opportunities(coins_by_exchange, top_n=5):
    merged = {}
    for exchange, coins in coins_by_exchange.items():
        for symbol, price in coins.items():
            if symbol not in merged:
                merged[symbol] = []
            merged[symbol].append((exchange, price))

    opportunities = []
    for symbol, prices in merged.items():
        if len(prices) < 2:
            continue
        prices.sort(key=lambda x: x[1])
        low = prices[0]
        high = prices[-1]
        diff = high[1] - low[1]
        percent = (diff / low[1]) * 100 if low[1] else 0
        opportunities.append((symbol, low, high, diff, percent))

    opportunities.sort(key=lambda x: x[4], reverse=True)
    return opportunities[:top_n]

# ======================
# BOT COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /top to see the top arbitrage opportunities.")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching data, please wait...")
    coins_by_exchange = await fetch_all_prices()
    top_opps = find_top_arbitrage_opportunities(coins_by_exchange)

    if not top_opps:
        await update.message.reply_text("No arbitrage opportunities found.")
        return

    message = "\U0001F4CA Top Arbitrage Opportunities:\n\n"
    for i, (symbol, low, high, diff, percent) in enumerate(top_opps, start=1):
        message += (
            f"{i}. {symbol} → {low[0]}: {low[1]:.4f} → {high[0]}: {high[1]:.4f} → Diff: {diff:.4f} ({percent:.2f}%)\n"
        )
    await update.message.reply_text(message)

# ======================
# BOT SETUP
# ======================
if __name__ == "__main__":
    app = ApplicationBuilder().token("7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.run_polling()
