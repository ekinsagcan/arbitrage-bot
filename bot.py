import os
import asyncio
import logging
from datetime import datetime
import aiohttp
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ArbitrageBot:
    def __init__(self):
        self.exchanges = {
            'binance': 'https://api.binance.com/api/v3/ticker/price',
            'kucoin': 'https://api.kucoin.com/api/v1/market/allTickers',
            'gate': 'https://api.gateio.ws/api/v4/spot/tickers',
            'mexc': 'https://api.mexc.com/api/v3/ticker/price'
        }
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat"""
        with sqlite3.connect('arbitrage.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscription_end DATE,
                    is_premium BOOLEAN DEFAULT FALSE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arbitrage_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    exchange1 TEXT,
                    exchange2 TEXT,
                    price1 REAL,
                    price2 REAL,
                    profit_percent REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    async def fetch_prices(self, exchange: str) -> Dict[str, float]:
        """Borsa fiyatlarını çek"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.exchanges[exchange]) as response:
                    data = await response.json()
                    
                    if exchange == 'binance':
                        return {item['symbol']: float(item['price']) for item in data}
                    elif exchange == 'kucoin':
                        return {item['symbol'].replace('-', ''): float(item['last']) for item in data['data']['ticker']}
                    elif exchange == 'gate':
                        return {item['currency_pair'].replace('_', ''): float(item['last']) for item in data}
                    elif exchange == 'mexc':
                        return {item['symbol']: float(item['price']) for item in data}
        except Exception as e:
            logger.error(f"{exchange} fiyat hatası: {str(e)}")
            return {}
    
    async def get_all_prices(self) -> Dict[str, Dict[str, float]]:
        """Tüm borsalardan fiyatları çek"""
        tasks = [self.fetch_prices(exchange) for exchange in self.exchanges]
        results = await asyncio.gather(*tasks)
        return dict(zip(self.exchanges.keys(), results))
    
    def calculate_arbitrage(self, all_prices: Dict[str, Dict[str, float]]) -> List[Dict]:
        """Arbitraj fırsatlarını hesapla"""
        opportunities = []
        
        # Tüm borsalarda ortak olan sembolleri bul
        common_symbols = set.intersection(*[set(prices.keys()) for prices in all_prices.values() if prices])
        
        for symbol in common_symbols:
            prices = {ex: all_prices[ex][symbol] for ex in all_prices if symbol in all_prices[ex]}
            
            if len(prices) >= 2:
                sorted_prices = sorted(prices.items(), key=lambda x: x[1])
                lowest_ex, lowest_price = sorted_prices[0]
                highest_ex, highest_price = sorted_prices[-1]
                
                if lowest_price > 0:
                    profit_percent = ((highest_price - lowest_price) / lowest_price) * 100
                    
                    if profit_percent > 0.5:  # Minimum %0.5 kar
                        opportunities.append({
                            'symbol': symbol,
                            'buy_exchange': lowest_ex,
                            'sell_exchange': highest_ex,
                            'buy_price': lowest_price,
                            'sell_price': highest_price,
                            'profit_percent': profit_percent
                        })
        
        return sorted(opportunities, key=lambda x: x['profit_percent'], reverse=True)
    
    def is_premium_user(self, user_id: int) -> bool:
        """Premium kullanıcı kontrolü"""
        with sqlite3.connect('arbitrage.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT subscription_end FROM users 
                WHERE user_id = ? AND is_premium = TRUE
            ''', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return datetime.strptime(result[0], '%Y-%m-%d') > datetime.now()
            return False
    
    def save_user(self, user_id: int, username: str):
        """Kullanıcıyı veritabanına kaydet"""
        with sqlite3.connect('arbitrage.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))
            conn.commit()

# Global bot instance
bot = ArbitrageBot()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot.save_user(user.id, user.username or "")
    
    keyboard = [
        [InlineKeyboardButton("🔍 Arbitraj Kontrol", callback_data='check')],
        [InlineKeyboardButton("💎 Premium", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Yardım", callback_data='help')]
    ]
    
    await update.message.reply_text(
        f"Merhaba {user.first_name}!\nKripto arbitraj botuna hoş geldiniz.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'check':
        await handle_arbitrage_check(query)
    elif query.data == 'premium':
        await show_premium_info(query)
    elif query.data == 'help':
        await show_help(query)
    elif query.data == 'back':
        await start(update, context)

async def handle_arbitrage_check(query):
    await query.edit_message_text("🔄 Fiyatlar kontrol ediliyor...")
    
    prices = await bot.get_all_prices()
    opportunities = bot.calculate_arbitrage(prices)
    user_id = query.from_user.id
    
    if not opportunities:
        await query.edit_message_text("❌ Şu an arbitraj fırsatı yok")
        return
    
    is_premium = bot.is_premium_user(user_id)
    text = "💎 Premium Arbitraj Fırsatları:\n\n" if is_premium else "🔍 Ücretsiz Arbitraj Fırsatları:\n\n"
    
    max_opps = 10 if is_premium else 3
    for opp in opportunities[:max_opps]:
        text += f"• {opp['symbol']}\n"
        text += f"  ⬇️ {opp['buy_exchange']}: ${opp['buy_price']:.6f}\n"
        text += f"  ⬆️ {opp['sell_exchange']}: ${opp['sell_price']:.6f}\n"
        text += f"  💰 %{opp['profit_percent']:.2f} kar\n\n"
    
    if not is_premium:
        text += "\n💎 Daha fazlası için premium üye olun!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Yenile", callback_data='check')],
        [InlineKeyboardButton("💎 Premium", callback_data='premium')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='back')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_premium_info(query):
    text = """💎 Premium Üyelik Avantajları:
    
• Sınırsız arbitraj kontrolü
• Detaylı fiyat analizleri
• Öncelikli bildirimler
• VIP destek hattı

💰 Aylık: $29.99
📞 İletişim: @premium_destek"""
    
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data='back')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_help(query):
    text = """ℹ️ Bot Kullanım Kılavuzu:

/start - Botu başlat
/arbitrage - Arbitraj kontrolü
/premium - Üyelik bilgileri

📞 Destek: @bot_destek"""
    
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data='back')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN bulunamadı!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Bot başlatılıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
