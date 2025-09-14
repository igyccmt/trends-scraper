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

def scrape_trends_from_mz3ric():
    """Scrape trends specifically from mZ3RIc class elements"""
    print("mZ3RIc classından trendler alınıyor...")
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
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
    
    trends = []
    
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Google Trends sayfası yükleniyor...")
        driver.get('https://trends.google.com/trends/trendingsearches/daily?geo=TR&hl=tr')
        
        # Wait specifically for mZ3RIc elements to load
        print("mZ3RIc elementleri bekleniyor...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.mZ3RIc"))
        )
        
        # Additional wait for content to fully render
        time.sleep(3)
        
        # Take screenshot for debugging
        driver.save_screenshot('trends_page_debug.png')
        print("Sayfa ekran görüntüsü alındı: trends_page_debug.png")
        
        # STRATEGY 1: Direct mZ3RIc class scraping
        print("mZ3RIc elementleri aranıyor...")
        mz3ric_elements = driver.find_elements(By.CSS_SELECTOR, "div.mZ3RIc")
        print(f"Bulunan mZ3RIc element sayısı: {len(mz3ric_elements)}")
        
        for i, element in enumerate(mz3ric_elements):
            try:
                text = element.text.strip()
                if text and len(text) > 3:
                    print(f"  mZ3RIc [{i}]: {text}")
                    trends.append(text)
            except Exception as e:
                print(f"  mZ3RIc [{i}] okuma hatası: {e}")
                continue
        
        # STRATEGY 2: Look for child elements within mZ3RIc
        if not trends:
            print("mZ3RIc içindeki alt elementler aranıyor...")
            try:
                # Look for specific child elements that might contain trend text
                child_selectors = [
                    "div.mZ3RIc > div",
                    "div.mZ3RIc > a",
                    "div.mZ3RIc > span",
                    "div.mZ3RIc div[class*='title']",
                    "div.mZ3RIc div[class*='text']",
                    "div.mZ3RIc div[class*='content']"
                ]
                
                for selector in child_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 3:
                                trends.append(text)
                    except:
                        continue
            except Exception as e:
                print(f"Alt element arama hatası: {e}")
        
        # STRATEGY 3: JavaScript extraction from mZ3RIc elements
        if not trends:
            print("JavaScript ile mZ3RIc içeriği çıkarılıyor...")
            try:
                js_script = """
                var trends = [];
                var elements = document.querySelectorAll('div.mZ3RIc');
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    // Try different text extraction methods
                    var text = element.textContent || element.innerText;
                    if (text && text.trim().length > 3) {
                        trends.push(text.trim());
                    }
                    
                    // Also try child elements
                    var children = element.querySelectorAll('div, span, a, p');
                    for (var j = 0; j < children.length; j++) {
                        var childText = children[j].textContent || children[j].innerText;
                        if (childText && childText.trim().length > 3) {
                            trends.push(childText.trim());
                        }
                    }
                }
                return Array.from(new Set(trends)); // Remove duplicates
                """
                
                js_trends = driver.execute_script(js_script)
                if js_trends:
                    trends.extend(js_trends)
                    print(f"JavaScript ile {len(js_trends)} trend bulundu")
                
            except Exception as js_error:
                print(f"JavaScript extraction hatası: {js_error}")
        
        driver.quit()
        
    except Exception as e:
        print(f"Selenium hatası: {e}")
        if 'driver' in locals():
            driver.quit()
    
    return trends

def clean_trends_data(trends_list):
    """Clean and filter the scraped trends"""
    cleaned = []
    seen = set()
    
    for trend in trends_list:
        if not trend:
            continue
            
        # Clean the text
        clean_trend = trend.strip()
        clean_trend = re.sub(r'\s+', ' ', clean_trend)  # Remove extra spaces
        clean_trend = re.sub(r'^\d+\.\s*', '', clean_trend)  # Remove numbering
        
        # Filter criteria
        if (len(clean_trend) > 3 and 
            len(clean_trend) < 100 and
            not any(word in clean_trend.lower() for word in [
                'google', 'trends', 'keşfet', 'oturum', 'ara', 'search', 
                'maps', '●', 'saat önce', 'dakika önce'
            ]) and
            clean_trend not in seen):
            
            cleaned.append(clean_trend)
            seen.add(clean_trend)
    
    return cleaned

def generate_related_queries(trend):
    """Generate related queries for a given trend"""
    # Turkish keyword expansions
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
    
    related_data = {'top': [], 'rising': []}
    
    # Generate top queries
    top_queries = set()
    words = trend.lower().split()
    
    for word in words:
        if word in expansions:
            for expansion in expansions[word][:3]:
                top_queries.add(f"{trend} {expansion}")
                top_queries.add(f"{expansion} {trend}")
    
    # Add time-based variations
    time_vars = ['son dakika', 'güncel', 'canlı', 'bugün', '2024']
    for time_var in time_vars[:2]:
        top_queries.add(f"{trend} {time_var}")
    
    # Convert to required format
    related_data['top'] = [{'query': q, 'value': random.randint(50, 100)} for q in list(top_queries)[:5]]
    
    # Generate rising queries (more specific)
    rising_queries = set()
    for word in words:
        if word in expansions:
            for expansion in expansions[word][3:6]:
                rising_queries.add(f"{trend} {expansion} son dakika")
                rising_queries.add(f"{expansion} {trend} haberleri")
    
    related_data['rising'] = [{'query': q, 'value': random.randint(100, 200)} for q in list(rising_queries)[:5]]
    
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
        
        related_queries = generate_related_queries(trend)
        
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

import csv

def save_to_csv(data, filename="trends.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Query", "Top", "Rising", "Success", "Error"])
        for entry in data:
            writer.writerow([
                entry.get("timestamp"),
                entry.get("query"),
                "; ".join(q["query"] for q in entry["related_queries"].get("top", [])),
                "; ".join(q["query"] for q in entry["related_queries"].get("rising", [])),
                entry.get("success"),
                entry.get("error", "")
            ])

# After saving JSON:
save_to_csv(all_trends_data, "trends.csv")
print("✓ CSV kaydedildi: trends.csv")
