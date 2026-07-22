import os
import json
import re
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# لیست کامل RSS
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
    "washington": {"lat": 38.9072, "lng": -77.0369, "name": "واشنگتن"},
    "china": {"lat": 39.9042, "lng": 116.4074, "name": "چین"},
    "russia": {"lat": 55.7558, "lng": 37.6173, "name": "روسیه"},
    "ukraine": {"lat": 50.4501, "lng": 30.5234, "name": "اوکراین"},
    "europe": {"lat": 50.8503, "lng": 4.3517, "name": "اروپا"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "name": "توکیو"}
}

DEFAULT_GEO = {"lat": 20.0, "lng": 0.0, "name": "بین‌المللی"}

def translate_text(text):
    if not text or len(text.strip()) == 0:
        return ""
    try:
        return GoogleTranslator(source='auto', target='fa').translate(text[:4500])
    except Exception as e:
        print(f"Translation Error: {e}")
        return text

def extract_image(entry):
    """حذف کامل تصاویر تزئینی؛ اگر تصویر واقعی نبود None برمی‌گرداند"""
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0]['url']
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.get('href')
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    return None

def detect_geo_location(text):
    text_lower = text.lower()
    for key, geo in LOCATION_GEO_MAP.items():
        if key in text_lower:
            return geo
    return DEFAULT_GEO

def process_all_feeds():
    print("شروع پردازش اخبار...")
    articles = []
    article_id = 1

    for feed_info in RSS_FEEDS:
        parsed_feed = feedparser.parse(feed_info['url'])
        for entry in parsed_feed.entries[:10]:
            title_en = entry.get('title', '')
            summary_en = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '#')
            pub_date = entry.get('published', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

            soup = BeautifulSoup(summary_en, 'html.parser')
            clean_summary_en = soup.get_text()

            title_fa = translate_text(title_en)
            summary_fa = translate_text(clean_summary_en)
            image_url = extract_image(entry)
            geo_info = detect_geo_location(title_en + " " + clean_summary_en)

            article = {
                "id": article_id,
                "title": title_fa,
                "title_fa": title_fa,
                "title_en": title_en,
                "summary": summary_fa,
                "summary_fa": summary_fa,
                "summary_en": clean_summary_en,
                "link": link,
                "published_at": pub_date,
                "category": feed_info['category'],
                "region": feed_info['region'],
                "image": image_url,
                "geo": geo_info
            }
                articles.append(article)
            article_id += 1

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_data = {
        "last_update": now_str,
        "total_count": len(articles),
        "articles": articles
    }

    # ۱. بروزرسانی فایل اصلی اخبار
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # ۲. ذخیره پایدار NoSQL در فایل news_archive.json
    archive_data = []
    if os.path.exists('news_archive.json'):
        try:
            with open('news_archive.json', 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        except Exception:
            archive_data = []

    existing_links = {a.get('link') for a in archive_data if isinstance(a, dict)}
    for art in articles:
        if art['link'] not in existing_links:
            archive_data.append(art)

    with open('news_archive.json', 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)

    print("پردازش و آرشیو با موفقیت کامل انجام شد.")

if __name__ == '__main__':
    process_all_feeds()
