# 必要なライブラリをインストールしてください
# pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import html
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://mamekichimameko.blog.jp"
ARCHIVE_URL = BASE_URL + "/archives/{year}-{month:02d}.html"


def format_rfc822_from_str(date_str):
    # date_str: "YYYY/MM/DD"
    try:
        dt = datetime.strptime(date_str, "%Y/%m/%d")
        dt = dt.replace(
            hour=12, minute=0, second=0, tzinfo=timezone(timedelta(hours=9))
        )
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return ""


def fetch_article(entry):
    # タイトルとリンク
    a_tag = entry.select_one('a[itemprop="url"]')
    if not a_tag:
        return None
    title = html.escape(a_tag.get_text(strip=True))
    link = a_tag["href"]
    if not link.startswith("http"):
        link = BASE_URL + link
    # 日付
    time_tag = entry.select_one('time[itemprop="datePublished"]')
    if not time_tag:
        return None
    date_str = time_tag.get_text(strip=True)
    pubDate = format_rfc822_from_str(date_str)
    return {
        "title": title,
        "link": link,
        "pubDate": pubDate,
    }


def fetch_monthly_articles(year, month):
    articles = []
    page = 1
    while True:
        if page == 1:
            url = f"{BASE_URL}/archives/{year}-{month:02d}.html"
        else:
            url = f"{BASE_URL}/archives/{year}-{month:02d}.html?p={page}"
        print(f"Fetching: {url}")
        res = requests.get(url)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, "html.parser")
        entry_list = soup.select("article.article")
        if not entry_list:
            break
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(filter(None, executor.map(fetch_article, entry_list)))
            articles.extend(results)
        page += 1
        time.sleep(0.05)
    return articles


articles = []
# 2015年分だけ取得
year = 2015
for month in range(1, 13):
    articles.extend(fetch_monthly_articles(year, month))

# pubDateで降順ソート
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
  <title>まめきちまめこ Blog RSS</title>
  <link>{BASE_URL}</link>
  <description>まめきちまめこ記事一覧</description>
{''.join(rss_items)}
</channel>
</rss>
"""

with open("mamekichi_rss.xml", "w", encoding="utf-8") as f:
    f.write(rss_xml)

print(f"{len(articles)}件の記事をmamekichi_rss.xmlに保存しました。")
