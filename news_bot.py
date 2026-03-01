import os
import asyncio
import feedparser
import requests
from telegram import Bot
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import re

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@latest_news_2026"

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://indianexpress.com/section/india/feed/"
]

FILE_NAME = "posted_links.txt"

def load_posted_links():
    if not os.path.exists(FILE_NAME):
        return set()
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_posted_link(link):
    with open(FILE_NAME, "a", encoding="utf-8") as f:
        f.write(link + "\n")

posted_links = load_posted_links()
translator = GoogleTranslator(source='auto', target='hi')


def translate(text):
    try:
        return translator.translate(text)
    except:
        return ""


def clean_html(raw_html):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', raw_html)


def get_article_summary(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = soup.find_all("p")
        text = ""

        for p in paragraphs[:5]:
            text += p.get_text() + " "

        return text.strip()

    except:
        return ""


async def send_news():
    print("🔍 Checking for new articles...")
    bot = Bot(token=TOKEN)

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:2]:

            link = entry.link

            if link in posted_links:
                continue

            posted_links.add(link)
            save_posted_link(link)

            title = entry.title

            summary = get_article_summary(link)

            if not summary:
                summary = clean_html(entry.get("summary", ""))

            # 🔥 Control length for single message (Telegram limit safe)
            summary = summary[:400]
            hindi_summary = translate(summary[:250]) if summary else ""

            image_url = None

            if "media_content" in entry:
                image_url = entry.media_content[0].get("url")
            elif "media_thumbnail" in entry:
                image_url = entry.media_thumbnail[0].get("url")

            source_name = feed.feed.get("title", "News Source")

            caption = f"""
📰 *{title}*

📝 {summary}

🇮🇳 {hindi_summary}

🔗 Read More: {link}

✅ Verified Source: {source_name}
"""

            try:
                if image_url:
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=image_url,
                        caption=caption[:1000],  # Telegram 1024 limit safe
                        parse_mode="Markdown"
                    )
                else:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=caption,
                        parse_mode="Markdown"
                    )

                print("✅ News sent:", title)

            except Exception as e:
                print("❌ Telegram send error:", e)


async def main():
    print("🚀 News Bot Started Successfully...")

    while True:
        try:
            await send_news()
        except Exception as e:
            print("Main loop error:", e)

        await asyncio.sleep(600)  # 10 minutes


if __name__ == "__main__":
    asyncio.run(main())