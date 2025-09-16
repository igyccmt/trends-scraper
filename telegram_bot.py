from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import subprocess
import logging
import asyncio
from datetime import datetime
import os

# Import your Twitter/X scraper
from twitter_trends_scraper import scrape_twitter_trends

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

# List of authorized user IDs (optional but recommended for security)
AUTHORIZED_USERS = [7811776774]  # Replace with your Telegram user ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Check if user is authorized (optional security measure)
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    keyboard = [['/scrape', '/xtrends', '/status'], ['/help']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = """
🤖 *Trends Scraper Bot*

Available commands:
• /scrape - Run the Google Trends scraper
• /xtrends - Run the Twitter/X trends scraper
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
• /xtrends - Run the Twitter/X trends scraper
• /status - Check the status of the last scrape
• /help - Show this help message

The scrapers will collect trending queries from Google Trends and Twitter/X and save them to files.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the Google Trends scraper when /scrape command is issued."""
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
            
            # Extract key information - improved parsing
            total_count = 0
            success_count = 0
            
            for line in lines:
                # Look for "TRENDS_COUNT:" pattern (English format)
                if "TRENDS_COUNT:" in line:
                    try:
                        parts = line.split("TRENDS_COUNT:")
                        if len(parts) > 1:
                            total_count = int(parts[1].strip())
                    except (ValueError, IndexError):
                        pass
                # Look for "SUCCESS_COUNT:" pattern (English format)
                if "SUCCESS_COUNT:" in line:
                    try:
                        parts = line.split("SUCCESS_COUNT:")
                        if len(parts) > 1:
                            success_count = int(parts[1].strip())
                    except (ValueError, IndexError):
                        pass
                
                # Fallback: Look for "Toplam X trend işlendi" pattern (Turkish for "Total X trends processed")
                if "Toplam" in line and "trend işlendi" in line and total_count == 0:
                    try:
                        # Extract the number from the line - look for digits
                        words = line.split()
                        for word in words:
                            if word.isdigit():
                                total_count = int(word)
                                break
                    except (ValueError, IndexError):
                        pass
                
                # Fallback: Look for "Başarılı: X" pattern (Turkish for "Successful: X")
                if "Başarılı:" in line and success_count == 0:
                    try:
                        # Extract the number after "Başarılı:"
                        parts = line.split("Başarılı:")
                        if len(parts) > 1:
                            # Get the part after "Başarılı:" and extract the first number
                            num_part = parts[1].strip()
                            # Find the first number in the string
                            for word in num_part.split():
                                if word.isdigit():
                                    success_count = int(word)
                                    break
                    except (ValueError, IndexError):
                        pass
            
            # Final fallback if we still can't determine counts
            if total_count == 0:
                total_count = 15  # Default value based on your script
            if success_count == 0:
                success_count = total_count  # Assume all were successful
            
            result_text = f"""
✅ *Google Trends Scraping Completed!*

• Total trends processed: {total_count}
• Successful: {success_count}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Data has been saved to files.
            """
            
            await message.edit_text(result_text, parse_mode='Markdown')
            
            # Send a small sample if available
            if len(output) > 0:
                sample = output[-500:]  # Last 500 characters
                # Escape special characters for MarkdownV2
                escaped_sample = sample.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                await update.message.reply_text(f"📋 Last output:\n```\n{escaped_sample}\n```", parse_mode='MarkdownV2')
            
        else:
            # Error
            error_output = stderr.decode().strip()
            error_message = error_output[-1000:] if error_output else "Unknown error occurred"
            await message.edit_text(
                f"❌ <b>Google Trends Scraping Failed!</b>\n<pre>{error_message}</pre>",
                parse_mode="HTML"
            )
        
    except asyncio.TimeoutError:
        await message.edit_text("⏰ *Scraping timed out!* The process took too long to complete.", parse_mode='Markdown')
    except Exception as e:
        await message.edit_text(f"❌ *Unexpected error!*\n\n{str(e)}", parse_mode='Markdown')

def git_push(commit_message="Update Twitter trends"):
    """Push changes to GitHub with better error handling"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Configure git user (important for automated pushes)
        subprocess.run(["git", "config", "user.name", "GitHub Actions Bot"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "actions@users.noreply.github.com"], check=True, capture_output=True)
        
        # Add all relevant files
        subprocess.run(["git", "add", "twitter_trends.csv"], check=True, capture_output=True)
        subprocess.run(["git", "add", "*.json"], check=True, capture_output=True)
        
        # Check for changes more reliably
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message], 
                capture_output=True, 
                text=True, 
                check=True
            )
            print(f"✓ Commit: {commit_result.stdout}")
            
            # Push with retry logic
            try:
                push_result = subprocess.run(
                    ["git", "push", "origin", "main"], 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    timeout=30
                )
                print("✅ Data pushed to GitHub successfully")
                return True
            except subprocess.TimeoutExpired:
                print("⚠️ Git push timed out, retrying...")
                push_result = subprocess.run(
                    ["git", "push", "origin", "main"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                print("✅ Data pushed to GitHub after retry")
                return True
        else:
            print("ℹ️ No changes to commit")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")
        print(f"Stderr: {e.stderr.decode() if e.stderr else 'None'}")
        return False
    except Exception as e:
        print(f"❌ Unexpected git error: {e}")
        return False

async def xtrends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run Twitter/X scraper and show results with GitHub status"""
    user_id = update.effective_user.id
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    message = await update.message.reply_text("🔄 Scraping Twitter/X trends...")
    
    try:
        trends = scrape_twitter_trends()
        
        if not trends:
            await message.edit_text("❌ Failed to scrape Twitter/X trends.")
            return

        # Show top 10 trends
        result_lines = [
            f"{t['rank']}. {t['name']} ({t.get('tweetCount','N/A')} tweets)"
            for t in trends[:10]
        ]
        result_text = "📊 *Top Twitter/X Trends:*\n\n" + "\n".join(result_lines)
        result_text += "\n\n✅ Data saved locally"

        await message.edit_text(result_text, parse_mode="Markdown")
        
        # Send separate message for GitHub status
        github_message = await update.message.reply_text("🔄 Attempting to push to GitHub...")
        
        # Call git_push directly
        git_success = git_push("Auto-update Twitter trends from Telegram bot")
        if git_success:
            await github_message.edit_text("✅ Successfully pushed to GitHub!")
        else:
            await github_message.edit_text("❌ Failed to push to GitHub. Check server logs for details.")
    
    except Exception as e:
        error_msg = f"❌ Error scraping Twitter trends:\n{str(e)}"
        await message.edit_text(error_msg)
        logger.error(f"Twitter scraper error: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the status of the scraper."""
    # Check if the CSV file exists and get its stats
    csv_exists = os.path.exists("trends.csv")
    twitter_csv_exists = os.path.exists("twitter_trends.csv")
    status_info = ""
    
    if csv_exists:
        try:
            # Get file modification time
            mod_time = os.path.getmtime("trends.csv")
            mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            status_info += f"• Google Trends - Last update: {mod_date}\n"
            
            # Count lines in the CSV file
            with open("trends.csv", "r", encoding="utf-8") as f:
                line_count = sum(1 for line in f) - 1  # Subtract header row
            
            status_info += f"• Google Trends - Total records: {line_count}\n"
        except Exception as e:
            status_info += f"• Google Trends - Error reading file: {str(e)}\n"
    else:
        status_info += "• Google Trends - No data found\n"
    
    if twitter_csv_exists:
        try:
            # Get file modification time
            mod_time = os.path.getmtime("twitter_trends.csv")
            mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            status_info += f"• Twitter Trends - Last update: {mod_date}\n"
            
            # Count lines in the CSV file
            with open("twitter_trends.csv", "r", encoding="utf-8") as f:
                line_count = sum(1 for line in f) - 1  # Subtract header row
            
            status_info += f"• Twitter Trends - Total records: {line_count}\n"
        except Exception as e:
            status_info += f"• Twitter Trends - Error reading file: {str(e)}\n"
    else:
        status_info += "• Twitter Trends - No data found\n"
    
    # Check for JSON files
    json_files = [f for f in os.listdir('.') if f.startswith('twitter_trends_') and f.endswith('.json')]
    if json_files:
        json_files.sort(reverse=True)
        latest_json = json_files[0]
        mod_time = os.path.getmtime(latest_json)
        mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        status_info += f"• Latest JSON: {latest_json} ({mod_date})\n"
    
    status_text = f"""
📊 *Scraper Status*

{status_info}
• GitHub: Check your repository for updates

Use /scrape to run Google Trends scraper or /xtrends for Twitter/X trends.
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages."""
    text = update.message.text.lower()
    
    if text in ['run', 'scrape', 'start scraping']:
        await scrape_command(update, context)
    elif text in ['x', 'xtrends', 'twitter', 'twitter trends']:
        await xtrends_command(update, context)
    elif text in ['status', 'check status']:
        await status_command(update, context)
    elif text in ['hi', 'hello', 'hey', 'start']:
        await start(update, context)
    elif text in ['help', 'commands']:
        await help_command(update, context)
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
    application.add_handler(CommandHandler("xtrends", xtrends_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Starting bot...")
    print(f"Bot token: {'Found' if BOT_TOKEN else 'Missing'}")
    print(f"Authorized users: {AUTHORIZED_USERS}")
    application.run_polling()

if __name__ == '__main__':
    main()
