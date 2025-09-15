from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import json
import time
import random
import csv
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_driver():
    """Setup Chrome driver with options"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]

    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Uncomment to run headless
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument("--user-data-dir=selenium_profile")  # persistent session

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver

def automated_login(driver):
    """Automated login to Twitter using credentials from .env"""
    try:
        username = os.getenv('TWITTER_USERNAME')
        password = os.getenv('TWITTER_PASSWORD')
        email = os.getenv('TWITTER_EMAIL', username)

        if not username or not password:
            print("Error: Twitter credentials not found in .env file")
            return False

        print("Navigating to Twitter login page...")
        driver.get("https://twitter.com/i/flow/login")

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "text")))
        username_field = driver.find_element(By.NAME, "text")
        username_field.clear()
        username_field.send_keys(email)

        driver.find_element(By.XPATH, "//span[contains(text(), 'Next')]").click()

        # Sometimes Twitter asks for username verification
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Verify')]"))
            )
            verify_field = driver.find_element(By.NAME, "text")
            verify_field.clear()
            verify_field.send_keys(username)
            driver.find_element(By.XPATH, "//span[contains(text(), 'Next')]").click()
        except:
            pass

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password")))
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        driver.find_element(By.XPATH, "//span[contains(text(), 'Log in')]").click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//a[@data-testid='AppTabBar_Home_Link']"))
        )
        print("Login successful!")
        return True
    except Exception as e:
        print(f"Automated login failed: {e}")
        driver.save_screenshot("login_error.png")
        return False

def check_logged_in(driver):
    """Check if we're already logged in to Twitter"""
    try:
        driver.get("https://twitter.com/home")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[@data-testid='AppTabBar_Home_Link']"))
        )
        return True
    except:
        return False

def parse_trend_block(block, rank):
    """Extract label, name, posts, count, url from a trend block"""
    trend = {
        "rank": rank, "label": None, "name": None,
        "posts": None, "tweetCount": 0, "url": None
    }

    # Label (contains 'Trending')
    try:
        trend["label"] = block.find_element(
            By.XPATH, ".//span[contains(text(),'Trending')]"
        ).text
    except:
        pass

    # Posts (contains 'posts')
    try:
        posts_text = block.find_element(
            By.XPATH, ".//span[contains(text(),'posts')]"
        ).text
        trend["posts"] = posts_text
        numbers = re.sub(r"[^\d]", "", posts_text)
        if numbers.isdigit():
            trend["tweetCount"] = int(numbers)
    except:
        pass

    # Name (first span that’s not label or posts)
    # Name (skip ranks like "1", "2", "·")
    try:
        spans = block.find_elements(By.XPATH, ".//span")
        for s in spans:
            txt = s.text.strip()
            if not txt:
                continue
            if txt in {trend["label"], trend["posts"]}:
                continue
            if txt.isdigit() or txt == "·":
                continue  # skip rank numbers / separators
            # this should be the actual trend name
            trend["name"] = txt
            break
    except:
        pass

    # Build search URL
    if trend["name"]:
        q = trend["name"].replace("#", "%23").replace(" ", "%20")
        trend["url"] = f"https://twitter.com/search?q={q}"

    return trend

def scrape_twitter_trends():
    """Scrape Twitter trending topics using Selenium"""
    print("Scraping Twitter trends using Selenium...")
    driver, trends = None, []

    try:
        driver = setup_driver()

        if not check_logged_in(driver):
            print("Not logged in. Attempting login...")
            if not automated_login(driver):
                return []

        print("Navigating to trends page...")
        driver.get("https://twitter.com/explore/tabs/trending")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='trend']"))
        )

        trend_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='trend']")
        if not trend_elements:
            print("No trends found. Saving page source for debugging...")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("trends_page.png")
            return []

        for i, element in enumerate(trend_elements[:50], start=1):
            try:
                trend = parse_trend_block(element, i)
                if trend["name"]:
                    trends.append(trend)
            except Exception as e:
                print(f"Error parsing trend {i}: {e}")
                continue

        print(f"Successfully extracted {len(trends)} trends")
        return trends
    finally:
        if driver:
            driver.quit()

def save_twitter_trends(trends, filename=None):
    """Save Twitter trends to JSON file"""
    if not filename:
        filename = f"twitter_trends_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    data = {"scraped_at": datetime.now().isoformat(), "source": "Twitter Web", "trends": trends}
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename

def save_to_csv(trends, filename="twitter_trends.csv"):
    """Save Twitter trends to CSV file"""
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "rank", "label", "name", "posts", "tweet_count", "url"])
        for trend in trends:
            writer.writerow([
                datetime.now().isoformat(),
                trend.get("rank", 0),
                trend.get("label", ""),
                trend.get("name", ""),
                trend.get("posts", ""),
                trend.get("tweetCount", 0),
                trend.get("url", "")
            ])
    return filename

if __name__ == "__main__":
    print("=" * 60)
    print("TWITTER TRENDS SCRAPER (SELENIUM)")
    print("=" * 60)

    if not os.getenv('TWITTER_USERNAME') or not os.getenv('TWITTER_PASSWORD'):
        print("⚠️ Warning: Missing Twitter credentials in .env")

    trends = scrape_twitter_trends()
    if trends:
        json_file = save_twitter_trends(trends)
        print(f"✓ Trends saved to {json_file}")
        csv_file = save_to_csv(trends)
        print(f"✓ Trends appended to {csv_file}")

        print(f"\nTop {min(10, len(trends))} Twitter trends:")
        for t in trends[:10]:
            print(f"{t['rank']}. {t['name']} ({t.get('tweetCount','N/A')} tweets)")
    else:
        print("❌ No trends found or error occurred")

