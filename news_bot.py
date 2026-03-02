import os
import asyncio
import feedparser
import requests
from telegram import Bot
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@latest_news_2026"

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.bbci.co.uk/news/india/rss.xml",
    "https://indianexpress.com/section/india/feed/",
    "https://indianexpress.com/section/world/feed/",
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"
]

FILE_NAME = "posted_links.txt"


# ---------- Load Posted Links ----------
def load_posted_links():
    if not os.path.exists(FILE_NAME):
        return set()
    with open(FILE_NAME, "r") as f:
        return set(f.read().splitlines())


def save_posted_link(link):
    with open(FILE_NAME, "a") as f:
        f.write(link + "\n")


# ---------- Clean Summary ----------
def clean_summary(text):
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = text.split('. ')
    text = '. '.join(sentences[:5])  # 4-5 sentences max
    if len(text) > 900:
        text = text[:900] + "..."
    return text


# ---------- Extract Image ----------
def get_image(entry):
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    if 'media_thumbnail' in entry:
        return entry.media_thumbnail[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if link.type and "image" in link.type:
                return link.href
    return None


# ---------- Format Message ----------
def format_message(title, summary, link, source):
    try:
        hindi_summary = GoogleTranslator(source='auto', target='hi').translate(summary)
    except:
        hindi_summary = "हिंदी अनुवाद उपलब्ध नहीं।"

    message = (
        f"📰 {title}\n\n"
        f"✍️ {summary}\n\n"
        f"🇮🇳 हिंदी सारांश:\n{hindi_summary}\n\n"
        f"🔗 Read More: {link}\n"
        f"✅ Verified Source: {source}"
    )

    if len(message) > 1024:
        message = message[:1000] + "..."

    return message


# ---------- Main Bot Logic ----------
async def send_news():
    bot = Bot(token=TOKEN)
    posted_links = load_posted_links()

    while True:
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:3]:
                link = entry.link

                if link in posted_links:
                    continue

                title = entry.title
                summary = entry.summary if 'summary' in entry else "No summary available."
                source = feed.feed.title if 'title' in feed.feed else "News Source"

                summary = clean_summary(summary)
                image_url = get_image(entry)
                message = format_message(title, summary, link, source)

                try:
                    if image_url:
                        await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=image_url,
                            caption=message
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=message
                        )

                    save_posted_link(link)
                    posted_links.add(link)

                except Exception as e:
                    print("Telegram Error:", e)

        await asyncio.sleep(300)  # 5 minutes


# ---------- Start ----------
async def main():
    await send_news()


if __name__ == "__main__":
    asyncio.run(main())