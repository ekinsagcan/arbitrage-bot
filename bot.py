import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"

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
    "Bitfinex": "https://api.bitfinex.com/v1/pubticker/",
    "Poloniex": "https://api.poloniex.com/markets/ticker24h",
    "Bitstamp": "https://www.bitstamp.net/api/v2/ticker/",
    "Coinbase": "https://api.exchange.coinbase.com/products/{pair}/ticker"
}

def normalize_symbol(symbol):
    return symbol.replace("-", "").replace("_", "").replace("/", "").upper()

async def fetch_all_prices():
    coins_by_exchange = {}
    for name, url in EXCHANGES.items():
        try:
            coins = {}
            if name == "Binance":
                data = requests.get(url).json()
                if isinstance(data, list):
                    for item in data:
                        symbol = item.get("symbol", "").upper()
                        price = item.get("price")
                        if price:
                            coins[symbol] = float(price)

            elif name == "OKX":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    raw_price = item.get("last")
                    if raw_price:
                        symbol = normalize_symbol(item.get("instId", ""))
                        coins[symbol] = float(raw_price)

            elif name == "KuCoin":
                data = requests.get(url).json().get("data", {}).get("ticker", [])
                for item in data:
                    raw_price = item.get("last")
                    if raw_price:
                        symbol = normalize_symbol(item.get("symbol", ""))
                        coins[symbol] = float(raw_price)

            elif name == "Bybit":
                response = requests.get(url)
                if response.headers.get("Content-Type", "").startswith("application/json"):
                    data = response.json().get("result", {}).get("list", [])
                    for item in data:
                        raw_price = item.get("lastPrice")
                        if raw_price:
                            symbol = item.get("symbol", "").upper()
                            coins[symbol] = float(raw_price)

            elif name == "MEXC":
                data = requests.get(url).json()
                for item in data:
                    raw_price = item.get("price")
                    if raw_price:
                        symbol = item.get("symbol", "").upper()
                        coins[symbol] = float(raw_price)

            elif name == "Bitget":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    raw_price = item.get("last")
                    if raw_price:
                        symbol = normalize_symbol(item.get("symbol", ""))
                        coins[symbol] = float(raw_price)

            elif name == "CoinEx":
                data = requests.get(url).json().get("data", {})
                for symbol, item in data.items():
                    raw_price = item.get("last")
                    if raw_price:
                        coins[symbol.upper()] = float(raw_price)

            elif name == "LBank":
                data = requests.get(url).json().get("data", [])
                for item in data:
                    raw_price = item.get("ticker", {}).get("latest")
                    if raw_price:
                        symbol = item.get("symbol", "").upper()
                        coins[symbol] = float(raw_price)

            elif name == "Gate.io":
                try:
                    data = requests.get(url, verify=False).json()
                    for symbol, item in data.items():
                        raw_price = item.get("last")
                        if raw_price:
                            coins[symbol.upper()] = float(raw_price)
                except Exception as e:
                    print(f"[SSL Error] Gate.io: {e}")

            elif name == "Bitfinex":
                for pair in ["btcusd", "ethusd", "solusd"]:
                    try:
                        full_url = url + pair
                        data = requests.get(full_url).json()
                        price = data.get("last_price")
                        if price:
                            symbol = pair.upper()
                            coins[symbol] = float(price)
                    except:
                        continue

            elif name == "Poloniex":
                data = requests.get(url).json()
                for item in data:
                    raw_price = item.get("last")
                    if raw_price:
                        symbol = normalize_symbol(item.get("symbol", ""))
                        coins[symbol] = float(raw_price)

            elif name == "Bitstamp":
                for pair in ["btcusd", "ethusd"]:
                    try:
                        full_url = url + pair + "/"
                        data = requests.get(full_url).json()
                        price = data.get("last")
                        if price:
                            coins[pair.upper()] = float(price)
                    except:
                        continue

            elif name == "Coinbase":
                for pair in ["BTC-USD", "ETH-USD"]:
                    try:
                        full_url = url.replace("{pair}", pair)
                        data = requests.get(full_url).json()
                        price = data.get("price")
                        if price:
                            coins[pair.replace("-", "").upper()] = float(price)
                    except:
                        continue

            coins_by_exchange[name] = coins
        except Exception as e:
            print(f"Error fetching from {name}: {e}")
    return coins_by_exchange

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

