# 必要なライブラリをインストールしてください
# pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
import time
import re
from concurrent.futures import ThreadPoolExecutor
import html
from email.utils import format_datetime
from datetime import datetime, timezone, timedelta

BASE_URL = "https://chikirin.hatenablog.com"
PAGE_URL = BASE_URL + "/archive?page={}"


def fetch_article(a):
    title = html.escape(a.get_text(strip=True))
    link = a["href"]
    if not link.startswith("http"):
        link = BASE_URL + link

    detail_res = requests.get(link)
    detail_soup = BeautifulSoup(detail_res.text, "html.parser")
    desc_tag = detail_soup.select_one(".entry-content")
    description = html.escape(desc_tag.get_text(strip=True)[:100]) if desc_tag else ""

    m = re.search(r"/entry/(\d{4})/(\d{2})/(\d{2})/(\d{6})", link)
    if m:
        year, month, day, time_str = m.groups()
        dt = datetime(
            int(year),
            int(month),
            int(day),
            int(time_str[:2]),
            int(time_str[2:4]),
            int(time_str[4:6]),
            tzinfo=timezone(timedelta(hours=9)),
        )
        pubDate = format_datetime(dt)
    else:
        pubDate = ""

    return {
        "title": title,
        "link": link,
        "description": description,
        "pubDate": pubDate,
    }


articles = []
page = 1
while True:
    url = PAGE_URL.format(page)
    print(f"Fetching: {url}")
    res = requests.get(url)
    if res.status_code != 200:
        break
    soup = BeautifulSoup(res.text, "html.parser")
    entry_list = soup.select(".entry-title-link")
    if not entry_list:
        break

    # 並列で記事詳細を取得
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(fetch_article, entry_list))
        articles.extend(results)

    page += 1
    time.sleep(0.05)  # サーバー負荷軽減

# pubDateで降順ソート
articles.sort(key=lambda x: x["pubDate"], reverse=True)

rss_items = []
for article in articles:
    rss_items.append(
        f"""  <item>
    <title>{article['title']}</title>
    <link>{article['link']}</link>
    <description>{article['description']}</description>
    <pubDate>{article['pubDate']}</pubDate>
  </item>
"""
    )

rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Chikirin Blog RSS</title>
  <link>https://chikirin.hatenablog.com/</link>
  <description>Chikirinの日記 記事一覧</description>
{''.join(rss_items)}
</channel>
</rss>
"""

with open("chikirin_rss.xml", "w", encoding="utf-8") as f:
    f.write(rss_xml)

print(f"{len(articles)}件の記事をchikirin_rss.xmlに保存しました。")
