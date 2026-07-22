import os
import json
import re
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# لیست جامع بیش از ۳۰ منبع خبری بزرگ و بین‌المللی در تمامی موضوعات
RSS_FEEDS = [
    # اخبار عمومی، بین‌الملل و سیاست
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "category": "سیاست", "region": "خاورمیانه"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "NY Times", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://www.theguardian.com/world/rss", "source": "The Guardian", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://feeds.washingtonpost.com/rss/world", "source": "Washington Post", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://www.euronews.com/rss?format=xml", "source": "EuroNews", "category": "سیاست", "region": "اروپا"},
    {"url": "http://rss.cnn.com/rss/edition_world.rss", "source": "CNN World", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best", "source": "Reuters", "category": "سیاست", "region": "بین‌المللی"},
    
    # فناوری، هوش مصنوعی، سایبر و دانش
    {"url": "https://rss.app/feeds/v1.1/_techcrunch.xml", "source": "TechCrunch", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://wired.com/feed/rss", "source": "Wired", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://arstechnica.com/feed/", "source": "Ars Technica", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://zdnet.com/news/rss.xml", "source": "ZDNet", "category": "فناوری و AI", "region": "بین‌المللی"},
    {"url": "https://sciencedaily.com/rss/all.xml", "source": "Science Daily", "category": "علم و سلامت", "region": "بین‌المللی"},
    {"url": "https://nature.com/nature.rss", "source": "Nature", "category": "علم و سلامت", "region": "بین‌المللی"},

    # اقتصاد، بورس، بازار و انرژی
    {"url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", "source": "Reuters Business", "category": "اقتصاد و بازار", "region": "بین‌المللی"},
    {"url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "source": "Wall Street Journal", "category": "اقتصاد و بازار", "region": "بین‌المللی"},
    {"url": "https://ft.com/rss/home/uk", "source": "Financial Times", "category": "اقتصاد و بازار", "region": "اروپا"},
    {"url": "https://cnbc.com/id/100003114/device/rss/rss.html", "source": "CNBC", "category": "اقتصاد و بازار", "region": "بین‌المللی"},
    {"url": "https://marketwatch.com/rss/topstories", "source": "MarketWatch", "category": "اقتصاد و بازار", "region": "بین‌المللی"},

    # امنیتی، دفاعی و منطقه‌ای
    {"url": "https://defense.gov/DesktopModules/ArticleCS/RSS.aspx?ContentType=400&Site=945", "source": "Defense News", "category": "سیاست", "region": "بین‌المللی"},
    {"url": "https://www.militarytimes.com/arc/outboundfeeds/rss/", "source": "Military Times", "category": "سیاست", "region": "بین‌المللی"}
]

# جدول نگاشت جغرافیایی جامع برای GIS
LOCATION_GEO_MAP = {
    "iran": {"lat": 35.6892, "lng": 51.3890, "name": "ایران"},
    "tehran": {"lat": 35.6892, "lng": 51.3890, "name": "تهران"},
    "middle east": {"lat": 29.2985, "lng": 42.5510, "name": "خاورمیانه"},
    "gaza": {"lat": 31.5017, "lng": 34.4668, "name": "غزه"},
    "israel": {"lat": 31.0461, "lng": 34.8516, "name": "فلسطین"},
    "usa": {"lat": 38.9072, "lng": -77.0369, "name": "آمریکا"},
    "washington": {"lat": 38.9072, "lng": -77.0369, "name": "واشنگتن"},
    "china": {"lat": 39.9042, "lng": 116.4074, "name": "چین"},
    "beijing": {"lat": 39.9042, "lng": 116.4074, "name": "پکن"},
    "russia": {"lat": 55.7558, "lng": 37.6173, "name": "روسیه"},
    "moscow": {"lat": 55.7558, "lng": 37.6173, "name": "مسکو"},
    "ukraine": {"lat": 50.4501, "lng": 30.5234, "name": "اوکراین"},
    "kyiv": {"lat": 50.4501, "lng": 30.5234, "name": "کی‌یف"},
    "europe": {"lat": 50.8503, "lng": 4.3517, "name": "اروپا"},
    "france": {"lat": 48.8566, "lng": 2.3522, "name": "فرانسه"},
    "paris": {"lat": 48.8566, "lng": 2.3522, "name": "پاریس"},
    "london": {"lat": 51.5074, "lng": -0.1278, "name": "لندن"},
    "uk": {"lat": 51.5074, "lng": -0.1278, "name": "بریتانیا"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "name": "توکیو"},
    "japan": {"lat": 35.6762, "lng": 139.6503, "name": "ژاپن"}
}

DEFAULT_GEO = {"lat": 20.0, "lng": 0.0, "name": "بین‌المللی"}

def generate_id(url):
    """تولید شناسه منحصربه‌فرد بر اساس هش URL"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def translate_text(text):
    """مترجم خودکار با کنترل خطا و مدیریت طول متن"""
    if not text or len(text.strip()) == 0:
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='fa').translate(text[:2500])
        return translated if translated else text
    except Exception as e:
        return text

def extract_image(entry):
    """استخراج پیشرفته تصویر از تمام فیلدهای ممکن RSS"""
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
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=600&q=80"

def detect_geo(text):
    """تشخیص مختصات جغرافیایی بر اساس متن خبر"""
    text_lower = text.lower()
    for key, geo in LOCATION_GEO_MAP.items():
        if key in text_lower:
            return geo
    return DEFAULT_GEO

def process_single_feed(feed_info):
    """استخراج و ترجمه اخبار یک Feed به‌صورت مجزا"""
    extracted = []
    try:
        parsed = feedparser.parse(feed_info['url'])
        for entry in parsed.entries[:25]:  # دریافت تا ۲۵ خبر از هر منبع
            link = entry.get('link', '')
            if not link:
                continue

            title_en = entry.get('title', '')
            summary_raw = entry.get('summary', entry.get('description', ''))
            soup = BeautifulSoup(summary_raw, 'html.parser')
            summary_en = soup.get_text()

            art_id = generate_id(link)
            title_fa = translate_text(title_en)
            summary_fa = translate_text(summary_en)
            image_url = extract_image(entry)
            geo_info = detect_geo(title_en + " " + summary_en)

            pub_date = entry.get('published', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

            extracted.append({
                "id": art_id,
                "title": title_fa,
                "title_fa": title_fa,
                "title_en": title_en,
                "summary": summary_fa,
                "summary_fa": summary_fa,
                "summary_en": summary_en,
                "link": link,
                "source": feed_info['source'],
                "published_at": pub_date,
                "date_iso": datetime.datetime.now().strftime("%Y-%m-%d"),
                "category": feed_info['category'],
                "region": feed_info['region'],
                "image": image_url,
                "geo": geo_info
            })
    except Exception as e:
        print(f"Error parsing feed {feed_info['source']}: {e}")
    return extracted

def main():
    print("شروع استخراج همزمان اخبار از کلیه منابع بزرگ جهانی...")
    
    existing_articles = {}
    
    # ۱. بارگذاری اخبار قبلی جهت ایجاد آرشیو انباشتی (عدم حذف اخبار قدیمی)
    if os.path.exists('news_data.json'):
        try:
            with open('news_data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                for art in old_data.get('articles', []):
                    existing_articles[art['id']] = art
            print(f"تعداد اخبار موجود در آرشیو قبلی: {len(existing_articles)}")
        except Exception as e:
            print(f"اشکال در خوندن آرشیو قبلی: {e}")

    # ۲. استخراج موازی اخبار جدید با Multithreading
    new_articles_flat = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = executor.map(process_single_feed, RSS_FEEDS)
        for res in results:
            new_articles_flat.extend(res)

    print(f"تعداد اخبار جدید دریافت شده: {len(new_articles_flat)}")

    # ۳. ادغام اخبار جدید با آرشیو (تکراری‌ها بر اساس ID به‌روزرسانی می‌شوند)
    for art in new_articles_flat:
        existing_articles[art['id']] = art

    final_articles = list(existing_articles.values())
    
    # ۴. مرتب‌سازی بر اساس تاریخ (جدیدترین در ابتدا)
    final_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    data_payload = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(final_articles),
        "articles": final_articles
    }

    # ۵. ذخیره‌سازی دیتابیس جامع
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    print(f"عملیات با موفقیت انجام شد. مجموع کل اخبار موجود در آرشیو: {len(final_articles)}")

if __name__ == '__main__':
    main()
