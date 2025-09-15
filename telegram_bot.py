from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import subprocess
import logging
import asyncio
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found in environment variables")
    exit(1)

# Replace with your actual token

# List of authorized user IDs (optional but recommended for security)
AUTHORIZED_USERS = [7811776774]  # Replace with your Telegram user ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Check if user is authorized (optional security measure)
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    keyboard = [['/scrape', '/status'], ['/help']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = """
🤖 *Trends Scraper Bot*

Available commands:
• /scrape - Run the Google Trends scraper
• /status - Check scraper status
• /help - Show this help message

Click the buttons below or type commands directly.
    """
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = """
📋 *Available Commands*

• /start - Start the bot and show main menu
• /scrape - Run the Google Trends scraper
• /status - Check the status of the last scrape
• /help - Show this help message

The scraper will collect trending queries from Google Trends and save them to GitHub.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the scraper when /scrape command is issued."""
    user_id = update.effective_user.id
    
    # Authorization check
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    # Send initial message
    message = await update.message.reply_text("🔄 Starting Google Trends scraper...")
    
    try:
        # Run the scraper script
        process = await asyncio.create_subprocess_exec(
            'python3', 'scraped_and_saved.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for completion with timeout (10 minutes)
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        
        # Check results
        if process.returncode == 0:
            # Success
            output = stdout.decode().strip()
            lines = output.split('\n')
            
            # Extract key information
            success_count = 0
            total_count = 0
            for line in lines:
                if "Toplam" in line and "trend işlendi" in line:
                    total_count = int(line.split()[1])
                if "Başarılı" in line:
                    success_count = int(line.split()[1])
            
            result_text = f"""
✅ *Scraping Completed Successfully!*

• Total trends processed: {total_count}
• Successful: {success_count}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Data has been pushed to GitHub.
            """
            
            await message.edit_text(result_text, parse_mode='Markdown')
            
            # Send a small sample if available
            if len(output) > 0:
                sample = output[-500:]  # Last 500 characters
                await update.message.reply_text(f"📋 Last output:\n```\n{sample}\n```", parse_mode='MarkdownV2')
            
            else:
            # Error
                error_output = stderr.decode().strip()
                await message.edit_text(
                    f"❌ <b>Scraping Failed!</b>\n<pre>{error_output[-1000:]}</pre>",
                    parse_mode="HTML"
            )
        
 
    except asyncio.TimeoutError:
        await message.edit_text("⏰ *Scraping timed out!* The process took too long to complete.", parse_mode='Markdown')
    except Exception as e:
        await message.edit_text(f"❌ *Unexpected error!*\n\n{str(e)}", parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the status of the scraper."""
    status_text = """
📊 *Scraper Status*

• Last run: Check your trends.csv file
• GitHub: https://github.com/igyccmt/trends-scraper
• Next scheduled run: Based on your cron job

Use /scrape to run the scraper manually.
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages."""
    text = update.message.text.lower()
    
    if text in ['run', 'scrape', 'start scraping']:
        await scrape_command(update, context)
    elif text in ['hi', 'hello', 'hey']:
        await update.message.reply_text("Hello! Use /scrape to run the trends scraper. 👋")
    else:
        await update.message.reply_text("I don't understand that command. Use /help to see available commands.")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scrape", scrape_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
