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


# -------- Load Posted Links --------
def load_posted_links():
    if not os.path.exists(FILE_NAME):
        return set()
    with open(FILE_NAME, "r") as f:
        return set(f.read().splitlines())


def save_posted_link(link):
    with open(FILE_NAME, "a") as f:
        f.write(link + "\n")


# -------- Extract Full Article --------
def extract_full_article(link):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        paragraphs = soup.find_all("p")

        content = ""
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 40:
                content += text + " "

        content = re.sub(r'\s+', ' ', content)

        # Keep first 1200 chars
        content = content[:1200]

        return content

    except Exception as e:
        print("Article fetch error:", e)
        return None


# -------- Extract Image --------
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


# -------- Format Message --------
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


# -------- Main Bot --------
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
                source = feed.feed.title if 'title' in feed.feed else "News Source"

                full_content = extract_full_article(link)

                if full_content:
                    summary = full_content[:900]
                else:
                    summary = entry.summary if 'summary' in entry else "No summary available."

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

        await asyncio.sleep(300)


async def main():
    await send_news()


if __name__ == "__main__":
    asyncio.run(main())