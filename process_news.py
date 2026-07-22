import os
import json
import re
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

RSS_FEEDS = [
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://rss.app/feeds/v1.1/_techcrunch.xml", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://aljazeera.com/xml/rss/all.xml", "category": "سیاست", "region": "خاورمیانه"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", "category": "اقتصاد و بازار", "region": "بین‌المللی"},
    {"url": "https://sciencedaily.com/rss/all.xml", "category": "علم و سلامت", "region": "بین‌المللی"}
]

LOCATION_GEO_MAP = {
    "iran": {"lat": 35.6892, "lng": 51.3890, "name": "ایران"},
    "tehran": {"lat": 35.6892, "lng": 51.3890, "name": "تهران"},
    "middle east": {"lat": 29.2985, "lng": 42.5510, "name": "خاورمیانه"},
    "gaza": {"lat": 31.5017, "lng": 34.4668, "name": "غزه"},
    "israel": {"lat": 31.0461, "lng": 34.8516, "name": "فلسطین"},
    "usa": {"lat": 38.9072, "lng": -77.0369, "name": "آمریکا"},
    "china": {"lat": 39.9042, "lng": 116.4074, "name": "چین"},
    "russia": {"lat": 55.7558, "lng": 37.6173, "name": "مسکو"},
    "ukraine": {"lat": 50.4501, "lng": 30.5234, "name": "اوکراین"},
    "europe": {"lat": 50.8503, "lng": 4.3517, "name": "اروپا"},
    "france": {"lat": 48.8566, "lng": 2.3522, "name": "فرانسه"}
}

DEFAULT_GEO = {"lat": 20.0, "lng": 0.0, "name": "بین‌المللی"}

def translate_text(text):
    if not text or len(text.strip()) == 0:
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='fa').translate(text[:4000])
        return translated if translated else text
    except Exception as e:
        print(f"Translation Error: {e}")
        return text

def extract_image(entry):
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get('url')
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0].get('url')
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.get('href')
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    # تصویر پیش‌فرض استوک باکیفیت در صورت عدم وجود تصویر
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=600&q=80"

def detect_geo(text):
    text_lower = text.lower()
    for key, geo in LOCATION_GEO_MAP.items():
        if key in text_lower:
            return geo
    return DEFAULT_GEO

def main():
    print("در حال استخراج و پردازش اخبار...")
    articles = []
    art_id = 1

    for feed in RSS_FEEDS:
        parsed = feedparser.parse(feed['url'])
        for entry in parsed.entries[:8]:
            title_en = entry.get('title', '')
            summary_raw = entry.get('summary', entry.get('description', ''))
            
            soup = BeautifulSoup(summary_raw, 'html.parser')
            summary_en = soup.get_text()

            title_fa = translate_text(title_en)
            summary_fa = translate_text(summary_en)
            image_url = extract_image(entry)
            geo_info = detect_geo(title_en + " " + summary_en)

            articles.append({
                "id": art_id,
                "title": title_fa,
                "title_fa": title_fa,
                "title_en": title_en,
                "summary": summary_fa,
                "summary_fa": summary_fa,
                "summary_en": summary_en,
                "link": entry.get('link', '#'),
                "published_at": entry.get('published', datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
                "category": feed['category'],
                "region": feed['region'],
                "image": image_url,
                "geo": geo_info
            })
            art_id += 1

    data_payload = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(articles),
        "articles": articles
    }

    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    print(f"تعداد {len(articles)} خبر با موفقیت پردازش شد.")

if __name__ == '__main__':
    main()
