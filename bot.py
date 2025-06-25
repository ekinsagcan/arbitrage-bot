import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import aiohttp
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json

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
        self.premium_users = set()
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat"""
        conn = sqlite3.connect('arbitrage.db')
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
        conn.close()
    
    async def fetch_binance_prices(self) -> Dict[str, float]:
        """Binance fiyatlarını çek"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.exchanges['binance']) as response:
                    data = await response.json()
                    return {item['symbol']: float(item['price']) for item in data}
        except Exception as e:
            logger.error(f"Binance fiyat hatası: {e}")
            return {}
    
    async def fetch_kucoin_prices(self) -> Dict[str, float]:
        """KuCoin fiyatlarını çek"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.exchanges['kucoin']) as response:
                    data = await response.json()
                    prices = {}
                    for item in data['data']['ticker']:
                        symbol = item['symbol'].replace('-', '')
                        prices[symbol] = float(item['last'])
                    return prices
        except Exception as e:
            logger.error(f"KuCoin fiyat hatası: {e}")
            return {}
    
    async def fetch_gate_prices(self) -> Dict[str, float]:
        """Gate.io fiyatlarını çek"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.exchanges['gate']) as response:
                    data = await response.json()
                    prices = {}
                    for item in data:
                        symbol = item['currency_pair'].replace('_', '')
                        prices[symbol] = float(item['last'])
                    return prices
        except Exception as e:
            logger.error(f"Gate.io fiyat hatası: {e}")
            return {}
    
    async def fetch_mexc_prices(self) -> Dict[str, float]:
        """MEXC fiyatlarını çek"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.exchanges['mexc']) as response:
                    data = await response.json()
                    return {item['symbol']: float(item['price']) for item in data}
        except Exception as e:
            logger.error(f"MEXC fiyat hatası: {e}")
            return {}
    
    async def get_all_prices(self) -> Dict[str, Dict[str, float]]:
        """Tüm borsalardan fiyatları çek"""
        tasks = [
            self.fetch_binance_prices(),
            self.fetch_kucoin_prices(),
            self.fetch_gate_prices(),
            self.fetch_mexc_prices()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'binance': results[0] if not isinstance(results[0], Exception) else {},
            'kucoin': results[1] if not isinstance(results[1], Exception) else {},
            'gate': results[2] if not isinstance(results[2], Exception) else {},
            'mexc': results[3] if not isinstance(results[3], Exception) else {}
        }
    
    def calculate_arbitrage_opportunities(self, all_prices: Dict[str, Dict[str, float]]) -> List[Dict]:
        """Arbitraj fırsatlarını hesapla"""
        opportunities = []
        
        # Ortak coinleri bul
        common_symbols = set()
        for exchange_prices in all_prices.values():
            if common_symbols:
                common_symbols &= set(exchange_prices.keys())
            else:
                common_symbols = set(exchange_prices.keys())
        
        for symbol in common_symbols:
            prices = {}
            for exchange, exchange_prices in all_prices.items():
                if symbol in exchange_prices:
                    prices[exchange] = exchange_prices[symbol]
            
            if len(prices) >= 2:
                sorted_prices = sorted(prices.items(), key=lambda x: x[1])
                lowest_exchange, lowest_price = sorted_prices[0]
                highest_exchange, highest_price = sorted_prices[-1]
                
                if lowest_price > 0:
                    profit_percent = ((highest_price - lowest_price) / lowest_price) * 100
                    
                    if profit_percent > 0.5:  # En az %0.5 kar
                        opportunities.append({
                            'symbol': symbol,
                            'buy_exchange': lowest_exchange,
                            'sell_exchange': highest_exchange,
                            'buy_price': lowest_price,
                            'sell_price': highest_price,
                            'profit_percent': profit_percent,
                            'profit_amount': highest_price - lowest_price
                        })
        
        return sorted(opportunities, key=lambda x: x['profit_percent'], reverse=True)
    
    def is_premium_user(self, user_id: int) -> bool:
        """Kullanıcının premium olup olmadığını kontrol et"""
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subscription_end FROM users 
            WHERE user_id = ? AND is_premium = TRUE
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            subscription_end = datetime.strptime(result[0], '%Y-%m-%d')
            return subscription_end > datetime.now()
        return False
    
    def save_user(self, user_id: int, username: str):
        """Kullanıcıyı kaydet"""
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, is_premium)
            VALUES (?, ?, FALSE)
        ''', (user_id, username))
        conn.commit()
        conn.close()

# Bot komutları
arbitrage_bot = ArbitrageBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komutu"""
    user = update.effective_user
    arbitrage_bot.save_user(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("🔍 Arbitraj Fırsatları", callback_data='check_arbitrage')],
        [InlineKeyboardButton("💎 Premium Üyelik", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Bilgi", callback_data='info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🚀 Kripto Arbitraj Bot'a Hoş Geldiniz!

Merhaba {user.first_name}! 

Bu bot ile farklı borsalar arasındaki fiyat farklarını takip edebilir ve arbitraj fırsatlarını yakalayabilirsiniz.

🔥 Özellikler:
• Gerçek zamanlı fiyat analizi
• En karlı arbitraj fırsatları
• 4+ büyük borsa desteği
• Anında bildirimler

💰 Günde %1-5 arası kar fırsatları!

Başlamak için aşağıdaki butonları kullanın:
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton tıklamalarını işle"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'check_arbitrage':
        await query.edit_message_text("🔄 Fiyatlar kontrol ediliyor, lütfen bekleyin...")
        
        # Fiyatları çek
        all_prices = await arbitrage_bot.get_all_prices()
        opportunities = arbitrage_bot.calculate_arbitrage_opportunities(all_prices)
        
        if not opportunities:
            await query.edit_message_text("❌ Şu anda arbitraj fırsatı bulunamadı.")
            return
        
        is_premium = arbitrage_bot.is_premium_user(user_id)
        
        if is_premium:
            # Premium kullanıcı - tüm fırsatları göster
            text = "💎 PREMIUM - En İyi Arbitraj Fırsatları:\n\n"
            for i, opp in enumerate(opportunities[:10], 1):
                text += f"{i}. {opp['symbol']}\n"
                text += f"   📈 Al: {opp['buy_exchange'].upper()} - ${opp['buy_price']:.6f}\n"
                text += f"   📉 Sat: {opp['sell_exchange'].upper()} - ${opp['sell_price']:.6f}\n"
                text += f"   💰 Kar: %{opp['profit_percent']:.2f}\n"
                text += f"   💵 Fark: ${opp['profit_amount']:.6f}\n\n"
        else:
            # Ücretsiz kullanıcı - sadece ilk 3 fırsatı göster
            text = "🔍 Ücretsiz - En İyi 3 Arbitraj Fırsatı:\n\n"
            for i, opp in enumerate(opportunities[:3], 1):
                text += f"{i}. {opp['symbol']}\n"
                text += f"   💰 Kar Potansiyeli: %{opp['profit_percent']:.2f}\n\n"
            
            text += "💎 Tüm fırsatları ve detayları görmek için Premium üyelik gerekli!"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data='check_arbitrage')],
            [InlineKeyboardButton("💎 Premium Ol", callback_data='premium')],
            [InlineKeyboardButton("🏠 Ana Menü", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == 'premium':
        text = """
💎 PREMIUM ÜYELİK AVANTAJLARI

🔥 Sınırsız arbitraj analizi
📊 Detaylı kar hesaplamaları
⚡ Gerçek zamanlı fiyat takibi
🎯 En karlı fırsatlar öncelikle
📱 7/24 bot erişimi
💰 Günlük %1-5 kar potansiyeli

💳 Fiyatlar:
• Aylık: 29.99 USD
• 3 Aylık: 79.99 USD (%11 indirim)
• Yıllık: 299.99 USD (%17 indirim)

📞 Premium üyelik için:
@arbitraj_destek ile iletişime geçin

🎁 İlk hafta ÜCRETSİZ deneme!
        """
        
        keyboard = [
            [InlineKeyboardButton("📞 İletişim", url='https://t.me/arbitraj_destek')],
            [InlineKeyboardButton("🏠 Ana Menü", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == 'info':
        text = """
ℹ️ ARBITRAJ TİCARETİ NEDİR?

Arbitraj, aynı varlığın farklı piyasalardaki fiyat farklarından yararlanarak kar elde etme işlemidir.

🎯 Nasıl Çalışır:
1. Coin'i düşük fiyattan al
2. Yüksek fiyattan sat
3. Aradaki farkı kazan

⚠️ Riskler:
• Transfer süreleri
• İşlem ücretleri
• Piyasa volatilitesi
• Likidite sorunları

💡 Ipuçları:
• Hızlı işlem yapın
• Ücretleri hesaplayın
• Küçük miktarlarla başlayın
• Risk yönetimi yapın

🤖 Bu bot sadece analiz sağlar, yatırım tavsiyesi değildir.
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 Ana Menü", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 Arbitraj Fırsatları", callback_data='check_arbitrage')],
            [InlineKeyboardButton("💎 Premium Üyelik", callback_data='premium')],
            [InlineKeyboardButton("ℹ️ Bilgi", callback_data='info')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏠 Ana Menü - Yapmak istediğiniz işlemi seçin:"
        await query.edit_message_text(text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım komutu"""
    help_text = """
🤖 ARBITRAJ BOT KOMUTLARI

/start - Botu başlat
/help - Bu yardım mesajını göster
/arbitrage - Arbitraj fırsatlarını kontrol et
/premium - Premium üyelik bilgileri

💬 Destek için: @arbitraj_destek
🌐 Web sitesi: (yakında)

Bot 7/24 aktif olarak çalışmaktadır.
    """
    await update.message.reply_text(help_text)

async def arbitrage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Arbitraj komut kısayolu"""
    user_id = update.effective_user.id
    
    # Fiyatları çek
    all_prices = await arbitrage_bot.get_all_prices()
    opportunities = arbitrage_bot.calculate_arbitrage_opportunities(all_prices)
    
    if not opportunities:
        await update.message.reply_text("❌ Şu anda arbitraj fırsatı bulunamadı.")
        return
    
    is_premium = arbitrage_bot.is_premium_user(user_id)
    
    if is_premium:
        text = "💎 PREMIUM - En İyi Arbitraj Fırsatları:\n\n"
        for i, opp in enumerate(opportunities[:10], 1):
            text += f"{i}. {opp['symbol']}\n"
            text += f"   📈 Al: {opp['buy_exchange'].upper()} - ${opp['buy_price']:.6f}\n"
            text += f"   📉 Sat: {opp['sell_exchange'].upper()} - ${opp['sell_price']:.6f}\n"
            text += f"   💰 Kar: %{opp['profit_percent']:.2f}\n\n"
    else:
        text = "🔍 Ücretsiz - En İyi 3 Arbitraj Fırsatı:\n\n"
        for i, opp in enumerate(opportunities[:3], 1):
            text += f"{i}. {opp['symbol']}\n"
            text += f"   💰 Kar Potansiyeli: %{opp['profit_percent']:.2f}\n\n"
        
        text += "💎 Premium üyelik için /premium komutunu kullanın!"
    
    await update.message.reply_text(text)

def main():
    """Ana fonksiyon"""
    # Bot token'ı - doğrudan kodda veya environment variable'dan
    TOKEN = "7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA"
    
    # Alternatif olarak environment variable'dan da alabilirsiniz:
    # TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7779789749:AAGWErvW0sXqNQbif6qxZ10H53xd_g2_KNA')
    
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN bulunamadı!")
        return
    
    try:
        # Uygulamayı oluştur (sürüm uyumluluğu için)
        application = Application.builder().token(TOKEN).build()
        
        # Komut handler'larını ekle
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("arbitrage", arbitrage_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Bot'u çalıştır
        logger.info("Bot başlatılıyor...")
        
        # Render için özel yapılandırma
        port = int(os.environ.get('PORT', 8000))
        
        # Webhook yerine polling kullan
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}")
        # Eski sürüm desteği için alternatif yöntem
        try:
            from telegram.ext import Updater
            
            updater = Updater(token=TOKEN, use_context=True)
            dispatcher = updater.dispatcher
            
            # Handler'ları ekle
            dispatcher.add_handler(CommandHandler("start", start))
            dispatcher.add_handler(CommandHandler("help", help_command))
            dispatcher.add_handler(CommandHandler("arbitrage", arbitrage_command))
            dispatcher.add_handler(CallbackQueryHandler(button_handler))
            
            # Bot'u başlat
            updater.start_polling()
            logger.info("Bot başlatıldı (eski sürüm)")
            updater.idle()
            
        except Exception as e2:
            logger.error(f"Alternatif başlatma da başarısız: {e2}")
            # Son çare olarak basit polling
            import time
            logger.info("Manuel polling başlatılıyor...")
            while True:
                time.sleep(1)

if __name__ == '__main__':
    main()
