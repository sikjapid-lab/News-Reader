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

def load_feeds():
    """بارگذاری لیست منابع فید از فایل خارجی feeds.json"""
    if os.path.exists('feeds.json'):
        try:
            with open('feeds.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"خطا در خواندن فایل feeds.json: {e}")
    return []

def generate_id(title, link):
    """تولید هش یکتا بر اساس ترکیب عنوان و لینک برای ممانعت از ثبت تکراری"""
    normalized = f"{title.strip().lower()}_{link.strip().lower()}"
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

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
    """استخراج پیشرفته تصویر از تمامی تک‌ها و سورس‌های ممکن RSS"""
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
    """استخراج و ترجمه اخبار یک Feed به‌صورت مجزا با درخواست مستقیم requests"""
    extracted = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(feed_info['url'], headers=headers, timeout=12)
        parsed = feedparser.parse(response.content)

        for entry in parsed.entries[:30]:
            link = entry.get('link', '')
            title_en = entry.get('title', '')
            if not link or not title_en:
                continue

            summary_raw = entry.get('summary', entry.get('description', ''))
            soup = BeautifulSoup(summary_raw, 'html.parser')
            summary_en = soup.get_text()

            art_id = generate_id(title_en, link)
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
        print(f"اشکال در دریافت فید {feed_info.get('source', 'نامشخص')}: {e}")
    return extracted

def main():
    rss_feeds = load_feeds()
    if not rss_feeds:
        print("هیچ منبعی در feeds.json یافت نشد!")
        return

    print(f"شروع استخراج همزمان اخبار از {len(rss_feeds)} منبع در لایه‌های مختلف...")
    
    existing_articles = {}
    
    # ۱. بارگذاری آرشیو قدیمی جهت ادغام اخبار و حفظ دیتابیس
    if os.path.exists('news_data.json'):
        try:
            with open('news_data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                for art in old_data.get('articles', []):
                    existing_articles[art['id']] = art
            print(f"تعداد اخبار موجود در آرشیو: {len(existing_articles)}")
        except Exception as e:
            print(f"خطا در خواندن آرشیو قبلی: {e}")

    # ۲. پردازش همزمان فیدها با ThreadPoolExecutor
    new_articles_flat = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = executor.map(process_single_feed, rss_feeds)
        for res in results:
            new_articles_flat.extend(res)

    print(f"تعداد کل کاندیدهای خبر دریافت شده: {len(new_articles_flat)}")

    # ۳. جلوگیری از ثبت اخبار تکراری با بررسی هش یکتا
    added_new_count = 0
    for art in new_articles_flat:
        if art['id'] not in existing_articles:
            existing_articles[art['id']] = art
            added_new_count += 1

    final_articles = list(existing_articles.values())
    
    # ۴. مرتب‌سازی اخبار بر اساس تاریخ
    final_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    data_payload = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(final_articles),
        "articles": final_articles
    }

    # ۵. ذخیره‌سازی فایل خروجی
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    print(f"عملیات موفقیت‌آمیز بود. اخبار جدید اضافه شده: {added_new_count} | مجموع اخبار دیتابیس: {len(final_articles)}")

if __name__ == '__main__':
    main()
