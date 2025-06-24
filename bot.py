import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Function to fetch prices for a given coin
def get_prices(symbol="bitcoin"):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/tickers?per_page=100&page=1"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Failed to retrieve data from CoinGecko.")

    data = response.json()

    if "tickers" not in data or not data["tickers"]:
        raise Exception("No price data available for this coin.")

    prices = []
    for ticker in data["tickers"]:
        market = ticker.get("market", {}).get("name", "Unknown")
        base = ticker.get("base", "")
        target = ticker.get("target", "")
        pair = f"{base}/{target}"
        price = ticker.get("last", 0.0)

        if price:
            prices.append((market, pair, price))

    return prices

# /start command: teach the user how to use the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Hello! I'm your *Crypto Arbitrage Opportunity Bot*. 📊\n\n"
        "Here's what I can do:\n"
        "🟢 Use `/arbitrage coinname` to find arbitrage opportunities.\n"
        "   Example: `/arbitrage bitcoin` or `/arbitrage ethereum`\n\n"
        "🔍 I check over 100 exchanges and show you:\n"
        "   - The cheapest exchange\n"
        "   - The most expensive exchange\n"
        "   - The profit percentage if you buy low & sell high 💰\n\n"
        "Try it now with a popular coin like `/arbitrage dogecoin` or `/arbitrage solana`."
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# /arbitrage command handler
async def arbitrage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Please enter a coin name. Example: /arbitrage bitcoin")
            return

        symbol = context.args[0].lower()
        prices = get_prices(symbol)

        prices_sorted = sorted(prices, key=lambda x: x[2])
        lowest = prices_sorted[0]
        highest = prices_sorted[-1]

        diff = highest[2] - lowest[2]
        percent = (diff / lowest[2]) * 100

        message = (
            f"📈 *Arbitrage Opportunity for {symbol.upper()}*:\n\n"
            f"🔻 Lowest Price: {lowest[0]} - {lowest[2]:.4f} ({lowest[1]})\n"
            f"🔺 Highest Price: {highest[0]} - {highest[2]:.4f} ({highest[1]})\n\n"
            f"📊 Difference: {diff:.4f} ({percent:.2f}%)"
        )
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# Main bot loop
if __name__ == "__main__":
    TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"  # Replace with your actual bot token
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("arbitrage", arbitrage))
    app.run_polling()
