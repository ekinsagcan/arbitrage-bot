import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ======================
# CONFIGURATION
# ======================
BOT_TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"

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
    "LBank": "https://api.lbank.info/v2/ticker.do?symbol=all",
    "Gate.io": "https://api.gate.io/api2/1/tickers",
    "Bitfinex": "https://api-pub.bitfinex.com/v2/tickers?symbols=ALL",
    "Poloniex": "https://api.poloniex.com/markets/ticker24h",
    "Bitstamp_products": "https://www.bitstamp.net/api/v2/trading-pairs-info/",
    "Bitstamp_ticker_base": "https://www.bitstamp.net/api/v2/ticker/",
    "Coinbase_products": "https://api.exchange.coinbase.com/products"
}

# ======================
# FETCH ALL PRICES
# ======================
async def fetch_all_prices():
    coins_by_exchange = {}

    for name, url in EXCHANGES.items():
        try:
            coins = {}

            if name == "Binance":
                data = requests.get(url).json()
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["price"])
                    coins[symbol] = price

            elif name == "OKX":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    symbol = item["instId"].replace("-", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "KuCoin":
                data = requests.get(url).json().get("data", {}).get("ticker", [])
                for item in data:
                    symbol = item["symbol"].replace("-", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "Bybit":
                data = requests.get(url).json().get("result", {}).get("list", [])
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["lastPrice"])
                    coins[symbol] = price

            elif name == "MEXC":
                data = requests.get(url).json()
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["price"])
                    coins[symbol] = price

            elif name == "Bitget":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    symbol = item["symbol"].replace("_", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "CoinEx":
                data = requests.get(url).json().get("data", {})
                for symbol, item in data.items():
                    symbol = symbol.upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "LBank":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    symbol = item["symbol"].upper()
                    price = float(item["ticker"]["latest"])
                    coins[symbol] = price

            elif name == "Gate.io":
                data = requests.get(url).json()
                for symbol, item in data.items():
                    symbol = symbol.upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "Bitfinex":
                data = requests.get(url).json()
                for item in data:
                    symbol_raw = item[0]  # örn: "tBTCUSD"
                    if symbol_raw.startswith("t") and len(symbol_raw) > 1:
                        symbol = symbol_raw[1:].upper()
                        price = float(item[7])  # last price index 7
                        coins[symbol] = price

            elif name == "Poloniex":
                data = requests.get(url).json()
                for item in data:
                    symbol = item["symbol"].replace("/", "").upper()
                    price = float(item["last"])
                    coins[symbol] = price

            elif name == "Bitstamp_products":
                # Bu endpoint sadece ürün listesi, fiyat için aşağıya geçilecek
                coins_by_exchange["Bitstamp_products"] = url

            elif name == "Bitstamp_ticker_base":
                # Burada döngüyle ürünlerden fiyat çekilecek, ama önce ürünleri almalı
                # Bu fonksiyon çağrısı içinde ayrı ele alınacak
                coins_by_exchange["Bitstamp_ticker_base"] = url

            elif name == "Coinbase_products":
                # Benzer şekilde ürünler listesi alınacak, fiyatlar ayrı alınacak
                coins_by_exchange["Coinbase_products"] = url

        except Exception as e:
            print(f"Error fetching from {name}: {e}")

    # Bitstamp için ürün listesini çek ve fiyatları al
    try:
        products_url = coins_by_exchange.get("Bitstamp_products")
        ticker_base_url = coins_by_exchange.get("Bitstamp_ticker_base")
        if products_url and ticker_base_url:
            products = requests.get(products_url).json()
            coins = {}
            for product in products:
                symbol = product['name'].replace("/", "").upper()
                ticker_url = f"{ticker_base_url}{product['url_symbol']}/"
                ticker_data = requests.get(ticker_url).json()
                price = float(ticker_data.get("last", 0))
                coins[symbol] = price
            coins_by_exchange["Bitstamp"] = coins
            del coins_by_exchange["Bitstamp_products"]
            del coins_by_exchange["Bitstamp_ticker_base"]
    except Exception as e:
        print(f"Error fetching Bitstamp tickers: {e}")

    # Coinbase için ürünleri çek ve fiyatları al
    try:
        products_url = coins_by_exchange.get("Coinbase_products")
        if products_url:
            products = requests.get(products_url).json()
            coins = {}
            for product in products:
                if product['quote_currency'] == "USD":
                    symbol = (product['base_currency'] + product['quote_currency']).upper()
                    ticker_url = f"https://api.exchange.coinbase.com/products/{product['id']}/ticker"
                    ticker_data = requests.get(ticker_url).json()
                    price = float(ticker_data.get("price", 0))
                    coins[symbol] = price
            coins_by_exchange["Coinbase"] = coins
            del coins_by_exchange["Coinbase_products"]
    except Exception as e:
        print(f"Error fetching Coinbase tickers: {e}")

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
            f"{i}. {symbol} → {low[0]}: {low[1]:.6f} → {high[0]}: {high[1]:.6f} → Diff: {diff:.6f} ({percent:.2f}%)\n"
        )
    await update.message.reply_text(message)

# ======================
# BOT SETUP
# ======================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.run_polling()
