import json
import os
import re
import datetime
from datetime import datetime, timezone, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup

# Load 20 RSS feeds configuration
with open('rss_feeds.json', 'r', encoding='utf-8') as f:
    FEEDS = json.load(f)

# Hugging Face Space endpoint / Translation service API
HF_SPACE_URL = os.environ.get('HF_SPACE_URL', 'https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-fa')
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')

from deep_translator import GoogleTranslator

def translate_text(text):
    """ترجمه مستقیم و رایگان بدون نیاز به هاگینگ‌فیس"""
    if not text or len(text.strip()) == 0:
        return ""
    try:
        # ترجمه انگلیسی به فارسی
        translated = GoogleTranslator(source='auto', target='fa').translate(text[:4900])
        return translated
    except Exception as e:
        print(f"Translation Error: {e}")
        return f"[ترجمه] {text[:300]}..."

def clean_html(raw_html):
    """Removes HTML tags from RSS summary"""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()

def extract_image(entry):
    """Extracts lead image from RSS entry tags or media elements"""
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get('url', '')
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0].get('url', '')
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.get('href', '')
    return 'https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=600&q=80'

def is_within_last_24_hours(published_parsed):
    """Checks if article is published within 24 hours"""
    if not published_parsed:
        return True # Default include if date missing
    pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    return (now_dt - pub_dt) <= timedelta(hours=24)

def format_time_ago(published_parsed):
    if not published_parsed:
        return "ساعاتی پیش"
    pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    diff = now_dt - pub_dt
    hours = int(diff.total_seconds() // 3600)
    if hours <= 1:
        return "کمی پیش"
    return f"{hours} ساعت پیش"

def run_pipeline():
    articles = []
    print("شروع فچ اخبار از ۲۰ خبرگزاری مادر...")

    for feed_info in FEEDS:
        try:
            print(f"در حال دریافت: {feed_info['name']}...")
            parsed = feedparser.parse(feed_info['url'])
            
            for entry in parsed.entries[:5]: # Take top 5 per feed
                published_parsed = getattr(entry, 'published_parsed', None)
                if not is_within_last_24_hours(published_parsed):
                    continue
                
                raw_title = entry.get('title', '')
                raw_summary = clean_html(entry.get('summary', entry.get('description', '')))
                original_link = entry.get('link', '')
                image_url = extract_image(entry)
                
                # AI Translation
                title_fa = translate_text(raw_title)
                summary_fa = translate_text(raw_summary)
                
                article_obj = {
                    'id': str(hash(original_link)),
                    'source_name': feed_info['name'],
                    'topic': feed_info['topic'],
                    'region': feed_info['region'],
                    'title_en': raw_title,
                    'title_fa': title_fa,
                    'summary_fa': summary_fa,
                    'content_fa': summary_fa + "<br/><br/>جزییات این خبر توسط هوش مصنوعی پردازش و خلاصه شده است.",
                    'original_link': original_link,
                    'image_url': image_url,
                    'time_ago': format_time_ago(published_parsed)
                }
                articles.append(article_obj)
        except Exception as e:
            print(f"خطا در دریافت فید {feed_info['name']}: {e}")

    output_data = {
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_count': len(articles),
        'articles': articles
    }

    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"پردازش با موفقیت انجام شد. تعداد کل اخبار ۲۴ ساعت اخیر: {len(articles)}")

if __name__ == '__main__':
    run_pipeline()
