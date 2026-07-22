import os
import json
import re
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# لیست منابع خبری مادر
RSS_FEEDS = [
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://rss.app/feeds/v1.1/_techcrunch.xml", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://aljazeera.com/xml/rss/all.xml", "category": "سیاست", "region": "خاورمیانه"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", "category": "اقتصاد و بازار", "region": "بین‌المللی"},
    {"url": "https://sciencedaily.com/rss/all.xml", "category": "علم و سلامت", "region": "بین‌المللی"}
]

# مختصات تقریبی نقاط مهم جهان جهت تعویین موقعیت GIS هوشمند
LOCATION_GEO_MAP = {
    "iran": {"lat": 35.6892, "lng": 51.3890, "name": "ایران (تهران)"},
    "tehran": {"lat": 35.6892, "lng": 51.3890, "name": "تهران"},
    "middle east": {"lat": 29.2985, "lng": 42.5510, "name": "خاورمیانه"},
    "gaza": {"lat": 31.5017, "lng": 34.4668, "name": "غزه"},
    "israel": {"lat": 31.0461, "lng": 34.8516, "name": "فلسطین اشغالی"},
    "usa": {"lat": 38.9072, "lng": -77.0369, "name": "واشنگتن D.C"},
    "washington": {"lat": 38.9072, "lng": -77.0369, "name": "واشنگتن"},
    "china": {"lat": 39.9042, "lng": 116.4074, "name": "پکن"},
    "beijing": {"lat": 39.9042, "lng": 116.4074, "name": "پکن"},
    "russia": {"lat": 55.7558, "lng": 37.6173, "name": "مسکو"},
    "moscow": {"lat": 55.7558, "lng": 37.6173, "name": "مسکو"},
    "ukraine": {"lat": 50.4501, "lng": 30.5234, "name": "کی‌یف"},
    "europe": {"lat": 50.8503, "lng": 4.3517, "name": "اروپا"},
    "london": {"lat": 51.5074, "lng": -0.1278, "name": "لندن"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "name": "توکیو"}
}

DEFAULT_GEO = {"lat": 20.0, "lng": 0.0, "name": "بین‌المللی"}

def translate_text(text):
    if not text or len(text.strip()) == 0:
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='fa').translate(text[:4500])
        return translated
    except Exception as e:
        print(f"Translation Exception: {e}")
        return text

def extract_image(entry):
    """استخراج تصویر اصلی؛ در صورت عدم وجود تصویر، None برمی‌گرداند (بدون تصویر تزئینی)"""
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
    print("شروع دریافت و الگوریتم‌پردازی اخبار...")
    articles = []
    article_id = 1

    for feed_info in RSS_FEEDS:
        print(f"در حال پردازش: {feed_info['url']}...")
        parsed_feed = feedparser.parse(feed_info['url'])
        
        for entry in parsed_feed.entries[:10]:  # پردازش ۱۰ خبر برتر هر منبع
            title_en = entry.get('title', '')
            summary_en = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '#')
            pub_date = entry.get('published', datetime.datetime.now().isoformat())
            
            # پاکسازی تگ‌های HTML از خلاصه
            soup = BeautifulSoup(summary_en, 'html.parser')
            clean_summary_en = soup.get_text()

            # ترجمه هوشمند
            title_fa = translate_text(title_en)
            summary_fa = translate_text(clean_summary_en)

            # استخراج واقعی تصویر (بدون عکس تزئینی)
            image_url = extract_image(entry)

            # تحلیل مکانی جهت GIS
            geo_info = detect_geo_location(title_en + " " + clean_summary_en)

            article = {
                "id": article_id,
                "title": title_fa,
                "title_en": title_en,
                "summary": summary_fa,
                "link": link,
                "published_at": pub_date,
                "category": feed_info['category'],
                "region": feed_info['region'],
                "image": image_url,  # در صورت عدم وجود تصویر None خواهد بود
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

    # ۱. ذخیره اطلاعات نسخه جدید جریانی
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # ۲. ثبت و به‌روزرسانی بانک داده NoSQL تاریخ‌گذشته (Archive DB)
    archive_data = []
    if os.path.exists('news_archive.json'):
        try:
            with open('news_archive.json', 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        except Exception:
            archive_data = []

    # ترکیب داده‌ها بدون تکرار
    existing_links = {a.get('link') for a in archive_data}
    new_records = 0
    for art in articles:
        if art['link'] not in existing_links:
            archive_data.append(art)
            new_records += 1

    with open('news_archive.json', 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)

    print(f"پردازش پایان یافت. {len(articles)} خبر فعال به‌روزرسانی شد. {new_records} رکورد جدید به news_archive.json پیوست گردید.")

if __name__ == '__main__':
    process_all_feeds()
