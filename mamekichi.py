# 必要なライブラリをインストールしてください
# pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor
import html
from datetime import datetime, timezone, timedelta

BASE_URL = "https://mamekichimameko.blog.jp/"
PAGE_URL = BASE_URL + "/archive?page={}"


def extract_pubdate(article_soup):
    # .article-date クラスから日付テキストを取得
    date_tag = article_soup.select_one(".article-date")
    if date_tag:
        date_str = date_tag.get_text(strip=True)
        try:
            # 例: 2024年6月10日 → "2024/06/10"
            dt = datetime.strptime(date_str, "%Y年%m月%d日")
            dt = dt.replace(
                hour=12, minute=0, second=0, tzinfo=timezone(timedelta(hours=9))
            )
            return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            return ""
    return ""


def fetch_article(a):
    title = html.escape(a.get_text(strip=True))
    link = a["href"]
    if not link.startswith("http"):
        link = BASE_URL + link

    # 記事詳細ページからpubDate取得
    res = requests.get(link)
    soup = BeautifulSoup(res.text, "html.parser")
    pubDate = extract_pubdate(soup)

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
