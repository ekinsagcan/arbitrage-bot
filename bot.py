import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CryptoArbitrageBot:
    def __init__(self):
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
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

    async def fetch_coin_prices(self, coin_ids: List[str]) -> Dict[str, float]:
        """Fetch prices from CoinGecko API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.coingecko_api}/simple/price"
                params = {
                    'ids': ','.join(coin_ids),
                    'vs_currencies': 'usd',
                    'include_last_updated_at': 'true'
                }
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return {coin_id: coin_data['usd'] for coin_id, coin_data in data.items()}
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
            return {}

    async def get_top_market_coins(self, limit: int = 100) -> List[Dict]:
        """Get top coins by market cap"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.coingecko_api}/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': limit,
                    'page': 1,
                    'sparkline': 'false'
                }
                async with session.get(url, params=params) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Market data error: {e}")
            return []

    async def calculate_arbitrage(self, coin_ids: List[str]) -> List[Dict]:
        """Calculate arbitrage opportunities"""
        prices = await self.fetch_coin_prices(coin_ids)
        opportunities = []
        
        # In a real implementation, you would compare prices across exchanges
        # This is a simplified version using CoinGecko's aggregated data
        for coin_id, price in prices.items():
            # Simulate price differences (real implementation would compare actual exchanges)
            simulated_diff = price * 0.02  # 2% simulated arbitrage opportunity
            if simulated_diff > 0:
                opportunities.append({
                    'coin_id': coin_id,
                    'price': price,
                    'profit_percent': 2.0,
                    'simulated': True  # Flag for demo purposes
                })
        
        return sorted(opportunities, key=lambda x: x['profit_percent'], reverse=True)

    def is_premium_user(self, user_id: int) -> bool:
        """Check if user has active premium subscription"""
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

# Bot instance
bot = CryptoArbitrageBot()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🔍 Check Arbitrage", callback_data='check_arbitrage')],
        [InlineKeyboardButton("💎 Premium Membership", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Info", callback_data='info')]
    ]
    
    await update.message.reply_text(
        f"🚀 Welcome to Crypto Arbitrage Bot, {user.first_name}!\n\n"
        "Discover price differences across exchanges and profit opportunities.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_arbitrage_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle arbitrage check requests"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("🔄 Analyzing market data...")
    
    # Get top 50 coins by market cap
    top_coins = await bot.get_top_market_coins(50)
    coin_ids = [coin['id'] for coin in top_coins][:20]  # Limit to top 20 for demo
    
    opportunities = await bot.calculate_arbitrage(coin_ids)
    user_id = query.from_user.id
    
    if not opportunities:
        await query.edit_message_text("❌ No significant arbitrage opportunities found.")
        return
    
    is_premium = bot.is_premium_user(user_id)
    
    if is_premium:
        text = "💎 Premium Arbitrage Opportunities:\n\n"
        for opp in opportunities[:10]:
            text += f"• {opp['coin_id'].upper()}\n"
            text += f"  💵 Price: ${opp['price']:,.4f}\n"
            text += f"  📈 Potential Profit: {opp['profit_percent']:.2f}%\n\n"
    else:
        text = "🔍 Top Arbitrage Opportunities (Free Tier):\n\n"
        for opp in opportunities[:3]:
            text += f"• {opp['coin_id'].upper()}\n"
            text += f"  📈 Potential Profit: {opp['profit_percent']:.2f}%\n\n"
        text += "💎 Upgrade to Premium for full details and more opportunities!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data='check_arbitrage')],
        [InlineKeyboardButton("💎 Go Premium", callback_data='premium')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium membership information"""
    query = update.callback_query
    await query.answer()
    
    text = """💎 Premium Membership Benefits:

• Unlimited arbitrage analysis
• Real-time price alerts
• Detailed profit calculations
• Priority support
• Exchange-specific data

💰 Pricing:
• Monthly: $29.99
• Annual: $299 (save 15%)

📞 Contact @premium_support for inquiries"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Contact Support", url='https://t.me/premium_support')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    """Start the bot"""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_arbitrage_check, pattern='^check_arbitrage$'))
    app.add_handler(CallbackQueryHandler(show_premium_info, pattern='^premium$'))
    
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
