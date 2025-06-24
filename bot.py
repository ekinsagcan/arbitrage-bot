import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ✅ Coin butonları burada tanımlanır
POPULAR_COINS = [
    ("Bitcoin", "bitcoin"),
    ("Ethereum", "ethereum"),
    ("Solana", "solana"),
    ("Dogecoin", "dogecoin"),
    ("BNB", "binancecoin"),
    ("Pepe", "pepe")
]

# CoinGecko'dan fiyat verisi çeker
def get_prices(symbol="bitcoin"):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/tickers?per_page=100&page=1"
    response = requests.get(url)

    if response.status_code == 404:
        raise Exception(f"❌ Coin '{symbol}' not found.")
    if response.status_code != 200:
        raise Exception("❌ Failed to retrieve data from CoinGecko.")

    data = response.json()
    if "tickers" not in data or not data["tickers"]:
        raise Exception("⚠️ No price data available.")

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

# /start komutu - tanıtım + butonlar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Welcome! I'm your *Crypto Arbitrage Bot*.\n\n"
        "📊 I scan 100+ exchanges and show where to buy low & sell high.\n\n"
        "💡 Select a coin below to see arbitrage opportunities:"
    )

    # Butonları oluştur
    buttons = [
        [InlineKeyboardButton(name, callback_data=symbol)]
        for name, symbol in POPULAR_COINS
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

# Butona basıldığında çalışır
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data

    try:
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

        await query.edit_message_text(text=message, parse_mode="Markdown")

    except Exception as e:
        await query.edit_message_text(f"⚠️ Error: {str(e)}")

# Ana program
if __name__ == "__main__":
    TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
