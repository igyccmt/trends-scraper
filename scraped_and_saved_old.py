from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import json
import time
import random
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

def scrape_trends_from_mz3ric():
    """Scrape first 50 Google Trends daily searches (query + volume)"""

    print("mZ3RIc classından trendler alınıyor...")

    # User agents to avoid bot detection
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'--user-agent={random.choice(user_agents)}')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://trends.google.com/trends/trendingsearches/daily?geo=TR&hl=tr")

    # Wait until at least one trend loads
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.mZ3RIc"))
        )
    except:
        print("⚠️ Trends page didn’t load properly")
        driver.quit()
        return []

    trends = []
    seen = set()
    scrolls = 0

    while len(trends) < 50 and scrolls < 20:
        # Scroll to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Collect all queries + volumes separately
        queries = [el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, "div.mZ3RIc") if el.text.strip()]
        volumes = [el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, "div.lqv0Cb") if el.text.strip()]

        # Pair queries and volumes by index
        for idx, query in enumerate(queries):
            if query not in seen:
                seen.add(query)
                volume = volumes[idx] if idx < len(volumes) else ""
                trends.append({"query": query, "volume": volume})
                if len(trends) >= 50:
                    break

        scrolls += 1

    driver.quit()

    print(f"Toplam {len(trends)} trend bulundu.")
    # Debug preview
    for t in trends[:10]:
        print(f"{t['query']} | {t['volume']}")

    return trends[:50]


def clean_trends_data(trends_list):
    """Clean and filter the scraped trends (keep query + volume)"""
    cleaned = []
    seen = set()
    
    for trend in trends_list:
        query = trend["query"]
        volume = trend.get("volume", "")
        if not query:
            continue

        clean_query = query.strip()
        clean_query = re.sub(r'\s+', ' ', clean_query)
        clean_query = re.sub(r'^\d+\.\s*', '', clean_query)

        if (len(clean_query) > 3 and 
            len(clean_query) < 100 and
            not any(word in clean_query.lower() for word in [
                'google', 'trends', 'keşfet', 'oturum', 'ara', 'search', 
                'maps', '●', 'saat önce', 'dakika önce'
            ]) and
            clean_query not in seen):

            cleaned.append({"query": clean_query, "volume": volume})
            seen.add(clean_query)

    return cleaned

def parse_volume(volume_text: str) -> int:
    """Convert Google Trends volume string into an integer"""
    if not volume_text:
        return 0

    volume_text = volume_text.lower().replace("arama", "").replace("+", "").strip()

    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000
    }

    try:
        if volume_text[-1] in multipliers:
            num = float(volume_text[:-1])
            return int(num * multipliers[volume_text[-1]])
        return int(volume_text)
    except:
        return 0


def generate_related_queries(trend, volume_text=""):
    """Generate related queries for a given trend, scaled by volume"""
    expansions = {
        'spor': ['maç', 'skor', 'sonuç', 'haber', 'lig', 'takım'],
        'maç': ['özet', 'gol', 'iddaa', 'canlı', 'izle', 'sonuç'],
        'basket': ['nba', 'basketbol', 'maç', 'skor', 'oyuncu'],
        'futbol': ['transfer', 'süper lig', 'haber', 'analiz'],
        'sonuç': ['açıklandı', 'sorgulama', 'öğrenme', 'e-devlet'],
        'ne zaman': ['saat kaçta', 'tarih', 'yeri', 'bilet'],
        'alım': ['iş', 'kariyer', 'başvuru', 'sınav', 'memur'],
        'adliye': ['mahkeme', 'dava', 'avukat', 'hukuk'],
        'cuma': ['mesaj', 'kutlama', 'resimli', 'dua', 'hutbe'],
        'oyuncu': ['film', 'dizi', 'rol', 'set', 'fragman']
    }

    # Parse volume
    base_volume = parse_volume(volume_text)
    if base_volume == 0:
        base_volume = 1000  # fallback

    related_data = {'top': [], 'rising': []}
    top_queries = set()
    words = trend.lower().split()

    # Generate top queries
    for word in words:
        if word in expansions:
            for expansion in expansions[word][:3]:
                top_queries.add(f"{trend} {expansion}")
                top_queries.add(f"{expansion} {trend}")

    # Add time-based variations
    time_vars = ['son dakika', 'güncel', 'canlı', 'bugün', '2025']
    for time_var in time_vars[:2]:
        top_queries.add(f"{trend} {time_var}")

    # Scale values based on base volume
    related_data['top'] = [
        {"query": q, "value": int(base_volume * random.uniform(0.4, 0.8))}
        for q in list(top_queries)[:5]
    ]

    # Rising queries (more specific variations)
    rising_queries = set()
    for word in words:
        if word in expansions:
            for expansion in expansions[word][3:6]:
                rising_queries.add(f"{trend} {expansion} son dakika")
                rising_queries.add(f"{expansion} {trend} haberleri")

    related_data['rising'] = [
        {"query": q, "value": int(base_volume * random.uniform(0.8, 1.2))}
        for q in list(rising_queries)[:5]
    ]

    return related_data

# Main execution
print("=" * 60)
print("GOOGLE TRENDS mZ3RIc CLASS SCRAPER")
print("=" * 60)

# Scrape trends from mZ3RIc class
print("1. mZ3RIc classından trendler alınıyor...")
raw_trends = scrape_trends_from_mz3ric()

print(f"2. Ham trend verisi ({len(raw_trends)}):")
for i, trend in enumerate(raw_trends[:10], 1):
    print(f"   {i:2d}. {trend}")

# Clean the trends
print("\n3. Trendler temizleniyor...")
cleaned_trends = clean_trends_data(raw_trends)

print(f"4. Temizlenmiş trendler ({len(cleaned_trends)}):")
for i, trend in enumerate(cleaned_trends, 1):
    print(f"   {i:2d}. {trend}")

# Generate related queries
print("\n5. İlgili aramalar oluşturuluyor...")
all_trends_data = []

for i, trend in enumerate(cleaned_trends[:15], 1):  # Process first 15 trends
    try:
        print(f"   ({i:2d}/{min(15, len(cleaned_trends))}) '{trend}' işleniyor...")
        
        related_queries = generate_related_queries(trend["query"], trend["volume"])
 
        all_trends_data.append({
            "query": trend,
            "related_queries": related_queries,
            "timestamp": datetime.now().isoformat(),
            "success": True
        })
        
        # Small delay
        time.sleep(0.5)
        
    except Exception as e:
        print(f"   ✗ '{trend}' hatası: {e}")
        all_trends_data.append({
            "query": trend,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "success": False
        })

# Save results
filename = f"trends_data_mZ3RIc_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
try:
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_trends_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n6. SONUÇ:")
    print(f"   ✓ Toplam {len(all_trends_data)} trend işlendi")
    print(f"   ✓ Başarılı: {sum(1 for x in all_trends_data if x.get('success'))}")
    print(f"   ✓ Veriler kaydedildi: {filename}")
    
except Exception as e:
    print(f"   ✗ Dosya yazma hatası: {e}")

# Show sample results
successful_entries = [entry for entry in all_trends_data if entry.get('success')]
if successful_entries:
    print(f"\n7. ÖRNEK SONUÇLAR:")
    for i, entry in enumerate(successful_entries[:3], 1):
        print(f"\n   {i}. {entry['query']}:")
        if entry['related_queries'].get('top'):
            print(f"      Top: {[q['query'] for q in entry['related_queries']['top'][:3]]}")
        if entry['related_queries'].get('rising'):
            print(f"      Rising: {[q['query'] for q in entry['related_queries']['rising'][:3]]}")

print("\n" + "=" * 60)
print("mZ3RIc SCRAPING TAMAMLANDI")
print("=" * 60)

from datetime import datetime
import csv, os

def save_to_csv(all_trends_data, filename):
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "query", "volume", "related_top", "related_rising"])
        for entry in all_trends_data:
            if entry.get("success"):
                writer.writerow([
                    entry["timestamp"],
                    entry["query"],
                    entry.get("volume", ""),
                    ", ".join([q["query"] for q in entry["related_queries"]["top"]]),
                    ", ".join([q["query"] for q in entry["related_queries"]["rising"]])
                ])

# In your main code:
today_file = f"trends_{datetime.now().strftime('%Y-%m-%d')}.csv"
save_to_csv(all_trends_data, "trends.csv")      # master log (all runs)
save_to_csv(all_trends_data, today_file)        # daily archive
import sys
import subprocess

def push_to_github():
    try:
        subprocess.run(["git", "add", "trends.csv"], check=True)

        today_file = f"trends_{datetime.now().strftime('%Y-%m-%d')}.csv"
        if os.path.exists(today_file):
            subprocess.run(["git", "add", today_file], check=True)

        subprocess.run(["git", "commit", "-m", f"Auto update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✓ Data pushed to GitHub")

    except Exception as e:
        print(f"✗ Git push failed: {e}")
push_to_github()

# Add at the end of your script:
if __name__ == "__main__":
    try:
        # ... your existing main code ...
        sys.exit(0)  # Success
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)  # Failure
