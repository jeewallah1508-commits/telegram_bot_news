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


# ------------------ Duplicate Control ------------------

def load_posted_links():
    if not os.path.exists(FILE_NAME):
        return set()
    with open(FILE_NAME, "r") as f:
        return set(f.read().splitlines())


def save_posted_link(link):
    with open(FILE_NAME, "a") as f:
        f.write(link + "\n")


# ------------------ Article Scraper ------------------

def extract_full_article(link):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        paragraphs = soup.find_all("p")

        content = ""
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 40:
                content += text + " "

        content = re.sub(r'\s+', ' ', content)

        return content[:1500]

    except Exception as e:
        print("Article fetch error:", e)
        return None


# ------------------ Image Extractor ------------------

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


# ------------------ Message Formatter ------------------

def format_message_parts(title, summary, link, source):

    try:
        hindi_summary = GoogleTranslator(source='auto', target='hi').translate(summary)
    except:
        hindi_summary = "हिंदी अनुवाद उपलब्ध नहीं।"

    full_message = (
        f"📰 {title}\n\n"
        f"✍️ {summary}\n\n"
        f"🇮🇳 हिंदी सारांश:\n{hindi_summary}\n\n"
        f"🔗 Read More: {link}\n"
        f"✅ Verified Source: {source}"
    )

    if len(full_message) > 1000:
        part1 = "🔹 PART 1/2\n\n" + full_message[:1000]
        part2 = "🔹 PART 2/2 (Continuation)\n\n" + full_message[1000:]
        return part1, part2
    else:
        return full_message, None


# ------------------ Main Bot ------------------

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
                    summary = full_content[:1200]
                else:
                    summary = entry.summary if 'summary' in entry else "No summary available."

                image_url = get_image(entry)

                part1, part2 = format_message_parts(title, summary, link, source)

                try:
                    if image_url:
                        await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=image_url,
                            caption=part1
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=part1
                        )

                    if part2:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=part2
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