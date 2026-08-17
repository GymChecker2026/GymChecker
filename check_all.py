import json
import re
import time
from datetime import date, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "gym-checker/0.1"}
INTERVAL_SEC = 2
RECENT_DAYS = 45
DATE_RE = re.compile(r"(\d{4})[.\-]\s?(\d{1,2})[.\-]\s?(\d{1,2})")
ARTICLE_URL_RE = re.compile(r"-news/\d{4}/\d{1,2}/\d+/?$")

_last_request_time = None


def http_get(url, **kwargs):
    global _last_request_time
    if _last_request_time is not None:
        wait = INTERVAL_SEC - (time.time() - _last_request_time)
        if wait > 0:
            time.sleep(wait)
    r = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
    _last_request_time = time.time()
    return r


def fetch_page(url, cutoff):
    r = http_get(url)
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
    return len(text), None, None


def fetch_news_list(url, cutoff):
    r = http_get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    dates = []
    for a in soup.find_all("a", href=True):
        if "-news/" not in a["href"]:
            continue
        m = DATE_RE.search(a.get_text(" ", strip=True))
        if not m:
            continue
        try:
            dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue

    if not dates:
        dates = fetch_news_list_fallback(url, soup)

    recent = sum(1 for d in dates if d >= cutoff)
    return len(text), len(dates), recent


def fetch_news_list_fallback(list_url, soup):
    # 日付付きタイトルの一次ルールで0件のときだけ使う。
    # URLパターン(/YYYY/MM/連番/)で記事リンクを拾い、記事ページ本文の日付要素から日付を取得する。
    links = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(list_url, a["href"])
        if ARTICLE_URL_RE.search(full):
            links.add(full)

    dates = []
    for link in sorted(links):
        try:
            r = http_get(link)
            r.raise_for_status()
        except Exception:
            continue
        article_soup = BeautifulSoup(r.text, "html.parser")
        tag = article_soup.find(attrs={"datetime": True})
        if tag is None:
            continue
        try:
            dates.append(date.fromisoformat(tag["datetime"][:10]))
        except ValueError:
            continue
    return dates


def fetch_wp_rest_api(url, cutoff):
    r = http_get(url, params={"per_page": 100})
    r.raise_for_status()
    posts = r.json()

    total_len = 0
    recent = 0
    for p in posts:
        body_html = p.get("content", {}).get("rendered", "")
        total_len += len(BeautifulSoup(body_html, "html.parser").get_text("\n", strip=True))
        try:
            pub = date.fromisoformat(p["date"][:10])
        except (KeyError, ValueError):
            continue
        if pub >= cutoff:
            recent += 1
    return total_len, len(posts), recent


METHODS = {
    "page": fetch_page,
    "news_list": fetch_news_list,
    "wp_rest_api": fetch_wp_rest_api,
}


def main():
    with open("gyms.json", encoding="utf-8") as f:
        gyms = json.load(f)

    cutoff = date.today() - timedelta(days=RECENT_DAYS)
    targets = [g for g in gyms if g.get("enabled", True)]
    rows = []

    for gym in targets:
        fetch = METHODS[gym["method"]]
        try:
            char_count, article_count, recent_count = fetch(gym["url"], cutoff)
            ok = True
        except Exception:
            char_count, article_count, recent_count = None, None, None
            ok = False

        rows.append((f"{gym['chain']} {gym['name']}", ok, char_count, article_count, recent_count))

    name_w = max(len(r[0]) for r in rows)
    print(f"{'店舗名':<{name_w}}  取得  文字数    記事件数  {RECENT_DAYS}日以内")
    for name, ok, char_count, article_count, recent_count in rows:
        ok_s = "OK" if ok else "NG"
        char_s = str(char_count) if char_count is not None else "-"
        art_s = str(article_count) if article_count is not None else "-"
        recent_s = str(recent_count) if recent_count is not None else "-"
        print(f"{name:<{name_w}}  {ok_s:<4}  {char_s:<8}  {art_s:<8}  {recent_s}")


if __name__ == "__main__":
    main()
