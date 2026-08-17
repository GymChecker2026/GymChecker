import hashlib
import json
import re
import time
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import anthropic
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "gym-checker/0.1"}
INTERVAL_SEC = 2
RECENT_DAYS = 45
MODEL = "claude-haiku-4-5-20251001"
JST = ZoneInfo("Asia/Tokyo")


def now_jst():
    return datetime.now(JST)


def today_jst():
    return now_jst().date()

DATE_RE = re.compile(r"(\d{4})[.\-]\s?(\d{1,2})[.\-]\s?(\d{1,2})")
ARTICLE_URL_RE = re.compile(r"-news/\d{4}/\d{1,2}/\d+/?$")
HENTRY_RE = re.compile(r"\bhentry\b")

PROMPT_TEMPLATE = """以下はクライミングジムのお知らせのテキストです。
このテキストの基準日は{ref_date}です（記事単位の場合は公開日、店舗ページ単位の場合は取得日）。

お知らせに書かれている予定を抽出し、JSONのみを出力してください。
前置きや説明、コードブロックの記号は不要です。

種別は次の5種類のいずれかに分類してください。それ以外には分類しないでください。
- 休業
- 時間変更（早じまい、遅い開店、祝日営業、営業再開を含む）
- エリア制限（ホールド外し、メンテナンス、セット作業、Route Setting Day、エリアクローズを含む）
- セット完了
- イベント

以下のような、上記5種類のいずれにも当てはまらない内容は抽出せず除外してください。
- 落とし物・忘れ物
- 商品販売
- 料金改定
- スクールやキャンプの募集・申込期限
- コンディショニングケア等の予約枠
- 入会キャンペーン

日付のルール:
- 日付の記載がない予定は、基準日（{ref_date}）をそのまま採用する
- 年の記載がない日付は、基準日に最も近い日付として解釈する（前後どちらでもよい）
- 過去の日付も含める
- 該当がなければ events を空配列にする

形式:
{{"events": [{{"date": "YYYY-MM-DD", "type": "種別", "note": "補足"}}]}}

---
{text}
"""

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


def dbc_article_body(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    start_marker = "NEWS & CAMPAIGN"
    end_marker = "最新の投稿"
    si = text.find(start_marker)
    if si != -1:
        ei = text.find(end_marker, si)
        if ei != -1:
            return text[si + len(start_marker):ei].strip()

    container = soup.find(class_=HENTRY_RE)
    if container is not None:
        return container.get_text("\n", strip=True)

    return text


def collect_dbc_recent_articles(gym, cutoff):
    """戻り値: [(記事URL, 公開日 date, 本文テキスト), ...]"""
    r = http_get(gym["url"])
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    primary = []
    for a in soup.find_all("a", href=True):
        if "-news/" not in a["href"]:
            continue
        m = DATE_RE.search(a.get_text(" ", strip=True))
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        primary.append((urljoin(gym["url"], a["href"]), d))

    results = []
    if primary:
        for url, d in primary:
            if d < cutoff:
                continue
            ar = http_get(url)
            ar.raise_for_status()
            results.append((url, d, dbc_article_body(ar.text)))
    else:
        links = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(gym["url"], a["href"])
            if ARTICLE_URL_RE.search(full):
                links.add(full)

        for link in sorted(links):
            try:
                ar = http_get(link)
                ar.raise_for_status()
            except Exception:
                continue
            asoup = BeautifulSoup(ar.text, "html.parser")
            tag = asoup.find(attrs={"datetime": True})
            if tag is None:
                continue
            try:
                d = date.fromisoformat(tag["datetime"][:10])
            except ValueError:
                continue
            if d < cutoff:
                continue
            results.append((link, d, dbc_article_body(ar.text)))

    return results


def collect_bpump_recent_articles(gym, cutoff):
    """戻り値: [(記事URL, 公開日 date, 本文テキスト), ...]"""
    r = http_get(gym["url"], params={"per_page": 100})
    r.raise_for_status()
    posts = r.json()

    results = []
    for p in posts:
        try:
            d = date.fromisoformat(p["date"][:10])
        except (KeyError, ValueError):
            continue
        if d < cutoff:
            continue
        body_html = p.get("content", {}).get("rendered", "")
        body_text = BeautifulSoup(body_html, "html.parser").get_text("\n", strip=True)
        results.append((p["link"], d, body_text))

    return results


def collect_page_target(gym, cutoff):
    """戻り値: [(店舗ページURL, 取得日 date, ページ全文テキスト)]。cutoffは使わない（記事単位でないため）。"""
    r = http_get(gym["url"])
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
    return [(gym["url"], today_jst(), text)]


COLLECTORS = {
    "news_list": collect_dbc_recent_articles,
    "wp_rest_api": collect_bpump_recent_articles,
    "page": collect_page_target,
}


def extract_events_from_text(client, text, ref_date):
    prompt = PROMPT_TEMPLATE.format(ref_date=ref_date.isoformat(), text=text)
    res = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    out = res.content[0].text.strip()
    out = re.sub(r"^```(?:json)?|```$", "", out, flags=re.M).strip()
    data = json.loads(out)
    return data.get("events", [])


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_processed():
    try:
        with open("processed.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"articles": {}, "pages": {}}


def main():
    with open("gyms.json", encoding="utf-8") as f:
        gyms = json.load(f)

    today = today_jst()
    now_iso = now_jst().isoformat(timespec="seconds")
    cutoff = today - timedelta(days=RECENT_DAYS)
    client = anthropic.Anthropic()
    processed = load_processed()

    all_events = []
    status_records = []
    llm_calls = 0
    targets = [g for g in gyms if g.get("enabled", True)]

    for gym in targets:
        label = f"{gym['chain']} {gym['name']}"
        collector = COLLECTORS[gym["method"]]
        fetched_at = now_jst().isoformat(timespec="seconds")

        try:
            articles = collector(gym, cutoff)
        except Exception as e:
            print(f"[{label}] 取得失敗: {e}")
            status_records.append({"gym_id": gym["id"], "status": "failure", "fetched_at": fetched_at})
            continue

        status_records.append({"gym_id": gym["id"], "status": "success", "fetched_at": fetched_at})
        print(f"[{label}] 対象 {len(articles)}件")

        for i, (url, pub, body) in enumerate(articles, 1):
            if gym["method"] == "page":
                h = text_hash(body)
                cached = processed["pages"].get(gym["id"])
                if cached and cached["text_hash"] == h:
                    events = cached["events"]
                    pub_iso = cached["published"]
                    print(f"  ({i}/{len(articles)}) {url} 変更なし → キャッシュ再利用 (events: {len(events)})")
                else:
                    try:
                        events = extract_events_from_text(client, body, pub)
                        llm_calls += 1
                    except Exception as e:
                        print(f"  ({i}/{len(articles)}) {url} 失敗: {e}")
                        continue
                    pub_iso = pub.isoformat()
                    processed["pages"][gym["id"]] = {
                        "text_hash": h,
                        "last_changed_at": now_iso,
                        "published": pub_iso,
                        "events": events,
                    }
                    print(f"  ({i}/{len(articles)}) {url} events: {len(events)}")
            else:
                cached = processed["articles"].get(url)
                if cached and cached["published"] == pub.isoformat():
                    events = cached["events"]
                    pub_iso = cached["published"]
                    print(f"  ({i}/{len(articles)}) {url} 処理済み → スキップ (events: {len(events)})")
                else:
                    try:
                        events = extract_events_from_text(client, body, pub)
                        llm_calls += 1
                    except Exception as e:
                        print(f"  ({i}/{len(articles)}) {url} 失敗: {e}")
                        continue
                    pub_iso = pub.isoformat()
                    processed["articles"][url] = {
                        "published": pub_iso,
                        "events": events,
                    }
                    print(f"  ({i}/{len(articles)}) {url} events: {len(events)}")

            for ev in events:
                all_events.append({
                    "gym_id": gym["id"],
                    "date": ev.get("date"),
                    "type": ev.get("type"),
                    "note": ev.get("note"),
                    "source_url": url,
                    "published": pub_iso,
                })

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    with open("collection_status.json", "w", encoding="utf-8") as f:
        json.dump(status_records, f, ensure_ascii=False, indent=2)

    with open("processed.json", "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    ok = sum(1 for s in status_records if s["status"] == "success")
    ng = sum(1 for s in status_records if s["status"] == "failure")
    print(f"\n合計 {len(all_events)} 件のイベントを events.json に保存しました。")
    print(f"取得ステータス（成功{ok}/失敗{ng}）を collection_status.json に保存しました。")
    print(f"LLM呼び出し回数: {llm_calls} 回")


if __name__ == "__main__":
    main()
