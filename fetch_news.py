import feedparser
import psycopg2
from datetime import datetime

# اتصال به دیتابیس Supabase (اطلاعات را از پنل خود جایگزین کنید)
DB_CONN = "postgresql://postgres:1359arsMeh%40@db.zmxsoglhttfzuccdwtgc.supabase.co:5432/postgres"

# کلیدواژه‌های فیلترینگ شما
KEYWORDS = ["military", "geopolitics", "drone", "naval", "security", "sanction"]

# لیست فیدهای RSS اندیشکده‌ها و خبرگزاری‌ها (نمونه)
RSS_FEEDS = [
    "https://www.rand.org/blogs/rand-blog.xml",
    "https://www.defenseone.com/rss/all/",
    "https://www.reutersagency.com/feed/"
]

def check_keywords(text):
    return any(keyword.lower() in text.lower() for keyword in KEYWORDS)

def save_to_db(title, link, summary):
    try:
        conn = psycopg2.connect(DB_CONN)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO news_monitor (title, link, summary) VALUES (%s, %s, %s) ON CONFLICT (link) DO NOTHING",
            (title, link, summary)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error Database: {e}")

# اجرای عملیات جمع‌آوری
for url in RSS_FEEDS:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        link = entry.get('link', '')
        
        # فیلتر کردن بر اساس کلیدواژه در عنوان یا متن
        if check_keywords(title) or check_keywords(summary):
            save_to_db(title, link, summary)
            print(f"Saved: {title}")
