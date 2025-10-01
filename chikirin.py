# 必要なライブラリをインストールしてください
# pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
import time
import re
from concurrent.futures import ThreadPoolExecutor
import html
from datetime import datetime, timezone, timedelta

BASE_URL = "https://chikirin.hatenablog.com"
PAGE_URL = BASE_URL + "/archive?page={}"


def extract_pubdate(link):
    # パターン1: /entry/YYYY/MM/DD/...
    m = re.search(r"/entry/(\d{4})/(\d{2})/(\d{2})/", link)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    # パターン2: /entry/YYYYMMDD
    m = re.search(r"/entry/(\d{4})(\d{2})(\d{2})$", link)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    # 該当しない場合は空欄
    return ""


def fetch_article(a):
    title = html.escape(a.get_text(strip=True))
    link = a["href"]
    if not link.startswith("http"):
        link = BASE_URL + link

    pubDate = extract_pubdate(link)

    return {
        "title": title,
        "link": link,
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

    # 並列で記事詳細を取得（description取得しないので高速化）
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(fetch_article, entry_list))
        articles.extend(results)

    page += 1
    time.sleep(0.05)  # サーバー負荷軽減

# pubDateで降順ソート
articles.sort(key=lambda x: x["pubDate"], reverse=True)


def format_rfc822(dt):
    # dt: datetimeオブジェクト
    # タイムゾーンがなければ日本時間を付与
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def format_rfc822_from_str(date_str):
    # date_str: "YYYY/MM/DD" 形式
    try:
        dt = datetime.strptime(date_str, "%Y/%m/%d")
        dt = dt.replace(
            hour=12, minute=0, second=0, tzinfo=timezone(timedelta(hours=9))
        )
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return ""


rss_items = []
for article in articles:
    pub_date = format_rfc822_from_str(article["pubDate"])
    rss_items.append(
        f"""  <item>
    <title>{article['title']}</title>
    <link>{article['link']}</link>
    <pubDate>{pub_date}</pubDate>
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
