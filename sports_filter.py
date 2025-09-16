import re

class SportsFilter:
    def __init__(self):
        # English sports keywords
        self.english_sports_keywords = [
            # Sports categories
            'sport', 'sports', 'athletic', 'game', 'games',
            
            # Specific sports
            'football', 'soccer', 'basketball', 'baseball', 'tennis', 
            'golf', 'cricket', 'rugby', 'hockey', 'volleyball',
            'boxing', 'mma', 'ufc', 'wrestling', 'cycling',
            'swimming', 'racing', 'formula', 'nascar', 'motogp',
            'olympics', 'olympic', 'world cup', 'champions league',
            'nfl', 'nba', 'mlb', 'nhl', 'premier league', 'la liga',
            'serie a', 'bundesliga', 'mls', 'epl',
            
            # Teams and leagues
            'lakers', 'warriors', 'yankees', 'red sox', 'manchester',
            'real madrid', 'barcelona', 'bayern', 'chelsea', 'arsenal',
            
            # Athletes
            'ronaldo', 'messi', 'lebron', 'curry', 'brady', 'hamilton',
            
            # Sports events
            'super bowl', 'world series', 'all-star', 'playoff', 'playoffs',
            'finals', 'championship', 'tournament', 'cup', 'match',
            'goal', 'touchdown', 'home run', 'point', 'score'
        ]
        
        # Turkish sports keywords
        self.turkish_sports_keywords = [
            # Sports categories
            'spor', 'sporlar', 'atletik', 'oyun', 'oyunlar', 'müsabaka', 'müsabakalar',
            
            # Specific sports
            'futbol', 'basketbol', 'voleybol', 'hentbol', 'tenis', 
            'golf', 'kriket', 'ragbi', 'buz hokeyi', 'yüzme',
            'boks', 'mma', 'ufc', 'güreş', 'bisiklet',
            'atletizm', 'formula 1', 'motogp', 'yarış', 'yarışlar',
            'olimpiyat', 'olimpiyatlar', 'dünya kupası', 'şampiyonlar ligi',
            
            # Turkish leagues and teams
            'süper lig', 'super lig', 'tff 1. lig', 'basketbol süper ligi',
            'fenerbahçe', 'galatasaray', 'beşiktaş', 'trabzonspor',
            'fb', 'gs', 'bjk', 'ts',
            
            # Sports events and terms
            'maç', 'maçlar', 'gol', 'asist', 'frikik', 'penaltı',
            'kupa', 'kupası', 'lig', 'ligi', 'şampiyon', 'şampiyonluğu',
            'playoff', 'play off', 'final', 'finaller',
            'puan', 'skor', 'sıralama', 'derece',
            
            # Turkish athlete names
            'arda güler', 'hakan şükür', 'burak yılmaz', 'volkan demirel',
            'alex de souza', 'ridvan yılmaz', 'merih demiral'
        ]
        
        # Combined keywords for both languages
        self.all_keywords = self.english_sports_keywords + self.turkish_sports_keywords
        
        # Create regex patterns for better matching
        self.patterns = [re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE) 
                        for keyword in self.all_keywords]
    
    def is_sports_related(self, text):
        """Check if text contains sports-related keywords in any language"""
        if not text or not isinstance(text, str):
            return False
            
        text_lower = text.lower()
        
        # Check for exact word matches
        for pattern in self.patterns:
            if pattern.search(text_lower):
                return True
        
        # Additional checks for Turkish-specific patterns
        turkish_checks = [
            # Team patterns like "Fenerbahçe - Galatasaray"
            r'\b(fb|gs|bjk|ts)\b',
            r'\b(fenerbahçe|galatasaray|beşiktaş|trabzonspor)\s*[-vs]\s*\w+',
            # League patterns
            r'süper\s+lig',
            r'super\s+lig',
            r'tff\s*\d\.\s*lig',
        ]
        
        for pattern in turkish_checks:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
                
        return False
    
    def filter_sports_topics(self, trends_list):
        """Filter out sports-related trends from a list (both English and Turkish)"""
        if not trends_list:
            return []
            
        non_sports_trends = []
        removed_count = 0
        
        for trend in trends_list:
            # Handle different trend formats
            if isinstance(trend, dict):
                trend_text = trend.get('name') or trend.get('title') or trend.get('query', '') or trend.get('trend', '')
            else:
                trend_text = str(trend)
                
            if not self.is_sports_related(trend_text):
                non_sports_trends.append(trend)
            else:
                removed_count += 1
                
        print(f"Filtered out {removed_count} sports-related trends")
        return non_sports_trends
    
    def get_filter_stats(self, trends_list):
        """Get statistics about filtered content"""
        sports_count = 0
        non_sports_count = 0
        
        for trend in trends_list:
            if isinstance(trend, dict):
                trend_text = trend.get('name') or trend.get('title') or trend.get('query', '') or trend.get('trend', '')
            else:
                trend_text = str(trend)
                
            if self.is_sports_related(trend_text):
                sports_count += 1
            else:
                non_sports_count += 1
                
        return {
            'total': len(trends_list),
            'sports_related': sports_count,
            'non_sports': non_sports_count,
            'filtered_percentage': (sports_count / len(trends_list) * 100) if trends_list else 0
        }

# Global instance
sports_filter = SportsFilter()

# Test function
def test_sports_filter():
    """Test the sports filter with sample data"""
    test_trends = [
        {"name": "Fenerbahçe Galatasaray maçı", "tweetCount": "100K"},
        {"name": "İklim Değişikliği Zirvesi", "tweetCount": "50K"},
        {"name": "NBA Finalleri", "tweetCount": "75K"},
        {"name": "Yapay Zeka Gelişmeleri", "tweetCount": "30K"},
        {"name": "Süper Lig puan durumu", "tweetCount": "60K"},
        {"name": "Ekonomi Haberleri", "tweetCount": "40K"},
        {"name": "FB - GS derbisi", "tweetCount": "90K"},
        {"name": "Teknoloji Fuarı", "tweetCount": "25K"},
    ]
    
    print("Original trends:")
    for trend in test_trends:
        print(f"  - {trend['name']}")
    
    print("\nFiltering sports topics...")
    filtered = sports_filter.filter_sports_topics(test_trends)
    
    print("\nNon-sports trends:")
    for trend in filtered:
        print(f"  - {trend['name']}")
    
    stats = sports_filter.get_filter_stats(test_trends)
    print(f"\nFilter stats: {stats}")

if __name__ == "__main__":
    test_sports_filter()
