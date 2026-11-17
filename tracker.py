import json
import time
import random
import requests
from bs4 import BeautifulSoup

TOKEN = "8996279782:AAEJ-n3vP4K9bts15GC0_htKMceRC4yHj8E"
CHAT = "5124680786"
SCRAPER_KEY = "f6d0238203d38918204508f29a0acbbb"

BASE = "https://www.amazon.eg"
TARGET = BASE + "/s?i=electronics&rh=n%3A18018102031%2Cn%3A27972173031%2Cn%3A21832883031&s=date-desc-rank"
CHECK_EVERY = 60           # بالثواني (دقيقة)
SEEN_FILE = "seen_asins.json"

SCRAPER_ENDPOINTS = ["https://api.scraperapi.com/", "http://api.scraperapi.com/"]

DIRECT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
}


def tg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT, "text": text},
            timeout=20,
        )
    except Exception as e:
        print("❌ فشل إرسال تيليجرام:", e)


def fetch_direct():
    r = requests.get(TARGET, headers=DIRECT_HEADERS, timeout=30)
    r.raise_for_status()
    if "captcha" in r.text.lower() or "s-search-result" not in r.text:
        raise Exception("أمازون رجّعت كابتشا/صفحة غريبة")
    return r.text


def fetch_html():
    try:
        print("   محاولة مباشرة (ببلاش)...")
        return fetch_direct()
    except Exception as e:
        print("   المباشر فشل:", e, "← هجرب ScraperAPI")

    last = None
    for attempt in range(1, 4):
        for endpoint in SCRAPER_ENDPOINTS:
            try:
                print(f"   ScraperAPI محاولة {attempt}...")
                r = requests.get(
                    endpoint,
                    params={"api_key": SCRAPER_KEY, "url": TARGET, "country_code": "eg"},
                    timeout=(15, 120),
                )
                r.raise_for_status()
                return r.text
            except Exception as e:
                last = e
                print("   فشلت:", e)
        time.sleep(10)
    raise last


def fetch():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    items = {}
    for div in soup.select('div[data-component-type="s-search-result"]'):
        asin = div.get("data-asin")
        if not asin:
            continue

        # تجاهل الإعلانات
        classes = " ".join(div.get("class", []))
        text = div.get_text(" ", strip=True)
        if "AdHolder" in classes or "Sponsored" in text or "ممول" in text or "مُموَّل" in text:
            continue

        title = div.select_one("h2")
        price = div.select_one(".a-price .a-offscreen")
        items[asin] = {
            "title": title.get_text(strip=True) if title else "؟",
            "price": price.get_text(strip=True) if price else "غير متاح",
            "link": f"{BASE}/dp/{asin}",
        }

    for asin, p in items.items():
        print("   •", p["title"][:60])
    return items


def load():
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return None


def save(s):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(s), f)


def main():
    print("▶ الاسكريبت اشتغل")
    tg("✅ البوت اشتغل وبيراقب القسم")

    seen = load()
    first = seen is None
    seen = seen or set()

    while True:
        try:
            print("⏳ بجيب الصفحة...")
            items = fetch()
            print(f"📦 لقيت {len(items)} منتج")

            if not items:
                print("⚠ مفيش نتايج (الصفحة اتغيرت أو اتحجبت)")
            else:
                if first:
                    print("أول تشغيل: حفظت المنتجات الحالية من غير إشعارات")
                else:
                    new = [a for a in items if a not in seen]
                    print(f"🆕 منتجات جديدة: {len(new)}")
                    for asin in new:
                        p = items[asin]
                        tg(f"🆕 منتج جديد\n{p['title']}\n💰 {p['price']}\n{p['link']}")
                first = False
                seen.update(items)
                save(seen)
        except Exception as e:
            print("❌ Error:", e)

        wait = CHECK_EVERY + random.randint(0, 20)
        print(f"😴 هستنى {wait} ثانية\n")
        time.sleep(wait)


if __name__ == "__main__":
    main()
