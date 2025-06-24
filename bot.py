import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# CoinGecko API'den canlı fiyat verilerini çeker
def get_prices(symbol="bitcoin"):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/tickers"
    res = requests.get(url)
    data = res.json()

    prices = []
    for ticker in data["tickers"]:
        market = ticker["market"]["name"]
        pair = ticker["base"] + "/" + ticker["target"]
        price = ticker["last"]
        prices.append((market, pair, price))

    return prices

# Telegram'da /arbitraj komutu çalıştığında burası çalışır
async def arbitraj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = " ".join(context.args).lower() or "bitcoin"
        prices = get_prices(symbol)

        prices_sorted = sorted(prices, key=lambda x: x[2])
        en_ucuza = prices_sorted[0]
        en_pahalisi = prices_sorted[-1]

        fark = en_pahalisi[2] - en_ucuza[2]
        yuzde = (fark / en_ucuza[2]) * 100

        mesaj = (
            f"📊 {symbol.upper()} arbitraj fırsatı:\n\n"
            f"💰 En ucuz: {en_ucuza[0]} - {en_ucuza[2]:.4f} ({en_ucuza[1]})\n"
            f"💸 En pahalı: {en_pahalisi[0]} - {en_pahalisi[2]:.4f} ({en_pahalisi[1]})\n\n"
            f"🔁 Fiyat farkı: {fark:.4f} ({yuzde:.2f}%)"
        )

        await update.message.reply_text(mesaj)
    except Exception as e:
        await update.message.reply_text("Hata oluştu: " + str(e))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Arbitraj fırsatlarını görmek için /arbitraj coinadi yaz (örn: /arbitraj bitcoin)")

if __name__ == "__main__":
    TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("arbitraj", arbitraj))
    app.run_polling()
