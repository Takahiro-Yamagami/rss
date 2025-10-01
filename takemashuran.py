# 必要なライブラリをインストールしてください
# pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

BASE_URL = "https://www.takemachelin.com"
LIST_URLS = [
    "https://www.takemachelin.com/2022/01/ichiran.html",
    "https://www.takemachelin.com/2000/01/blog-post_01.html",
    "https://www.takemachelin.com/2000/01/blog-post.html",
]


def format_rfc822_from_datetime(dt):
    # dt: datetimeオブジェクト
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def fetch_article(a_tag):
    title = html.escape(a_tag.get_text(strip=True))
    link = a_tag.get("href")
    if not link or not link.startswith("http"):
        link = BASE_URL + link

    try:
        res = requests.get(link, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        meta_tag = soup.find("meta", {"property": "article:published_time"})
        if meta_tag and meta_tag.get("content"):
            dt = datetime.fromisoformat(meta_tag["content"].replace("Z", "+09:00"))
        else:
            time_tag = soup.find("time", {"datetime": True})
            if time_tag:
                dt = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+09:00"))
            else:
                return None
        pubDate = format_rfc822_from_datetime(dt)
    except Exception:
        return None

    return {
        "title": title,
        "link": link,
        "pubDate": pubDate,
    }


articles = []
for url in LIST_URLS:
    print(f"Fetching list: {url}")
    try:
        res = requests.get(url, timeout=10)
    except Exception as e:
        print(f"一覧ページ取得失敗: {url} ({e})")
        continue
    soup = BeautifulSoup(res.text, "html.parser")
    a_tags = [
        a
        for a in soup.find_all("a", href=True)
        if a["href"].startswith("https://www.takemachelin.com/20")
    ]

    print(f"  {len(a_tags)}件の記事リンクを検出")
    # 並列で記事詳細を取得
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {
            executor.submit(fetch_article, a_tag): idx
            for idx, a_tag in enumerate(a_tags, 1)
        }
        for future in as_completed(futures):
            idx = futures[future]
            article = future.result()
            if article:
                articles.append(article)
                print(f"    [{idx}/{len(a_tags)}] 記事取得: {article['title']}")
            else:
                print(f"    [{idx}/{len(a_tags)}] 記事取得失敗")
    time.sleep(0.1)  # サーバー負荷軽減

articles.sort(key=lambda x: x["pubDate"], reverse=True)

rss_items = []
for article in articles:
    rss_items.append(
        f"""  <item>
    <title>{article['title']}</title>
    <link>{article['link']}</link>
    <guid isPermaLink="true">{article['link']}</guid>
    <pubDate>{article['pubDate']}</pubDate>
  </item>
"""
    )

rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>タケマシュラン Blog RSS</title>
  <link>{BASE_URL}</link>
  <description>タケマシュラン記事一覧</description>
{''.join(rss_items)}
</channel>
</rss>
"""

with open("takemashuran_rss.xml", "w", encoding="utf-8") as f:
    f.write(rss_xml)

print(f"{len(articles)}件の記事をtakemashuran_rss.xmlに保存しました。")
