import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import anthropic
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "gym-checker/0.1"}
INTERVAL_SEC = 2
REQUEST_TIMEOUT_SEC = 60
RETRY_COUNT = 3
RETRY_WAIT_SEC = 5
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

# 綱島店は記事URLに -news/ を含まない独自パターン(/tsunashima/YYYY/MM/ID/)のため専用の正規表現を使う。
TSUNASHIMA_ARTICLE_URL_RE = re.compile(r"/tsunashima/\d{4}/\d{1,2}/\d+/?$")
TSUNASHIMA_MAX_ARTICLES = 8

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

# list_page: true の店舗（一覧ページに複数記事が並ぶタイプ）にのみ追加する解釈ルール。
# PROMPT_TEMPLATE 自体は変更せず、extract_events_from_text 内でこのブロックを
# "---\n{text}\n" の直前に差し込む（既存店舗のプロンプトはバイト単位で不変のまま）。
# 掲載日による90日フィルタはコード側（split_list_page_blocks）で行うため、ここには書かない。
LIST_PAGE_EXTRA_RULES = """
このページは複数の記事が一覧になった店舗ページです。日付の解釈については、
以下のルールを他のどのルールよりも優先してください。
- 各記事の直前に表示されている掲載日を、その記事の公開日として扱うこと
- 予定の日付に年の記載がない場合は、基準日（{ref_date}）ではなく、その記事の掲載日の年を基準に解決すること

種別の判定については、以下のルールを追加で守ってください。
- 「セットスケジュール」「リニューアル」など、これから行う作業を告知する記述は「エリア制限」に分類すること
- 「セット完了」は、作業が完了して利用可能になったことを事後に知らせる記述にのみ使うこと
- 予定なのか完了なのか記述から判別できない場合は「エリア制限」に分類すること（利用できない可能性を示す方が安全なため）

期間で書かれた予定については、以下のルールを追加で守ってください。
- 「8/24(月)～25(火)」のように期間で書かれた予定は、期間に含まれる日付ごとに1件ずつ、
  同じ内容で出力すること（この例なら8/24分と8/25分をそれぞれ出力する）
"""

# 掲載日（「2026年08月01日」のように全店で統一された半角形式）だけを対象にした区切り。
# 記事本文中の予定日（表記ゆれがある）は対象外で、正規表現でのパースは行わない。
LIST_PAGE_DATE_RE = re.compile(r"^(\d{4}年\d{2}月\d{2}日)$", re.MULTILINE)
LIST_PAGE_MAX_AGE_DAYS = 90


def split_list_page_blocks(text, today):
    """一覧ページのテキストを掲載日（YYYY年MM月DD日）ごとの記事ブロックに分割し、
    today から LIST_PAGE_MAX_AGE_DAYS 日以内の掲載日を持つブロックだけを残して結合する。

    戻り値: (残したブロックを結合したテキスト, 残した掲載日のリスト, 除外した掲載日のリスト)
    掲載日の区切りが1つも見つからない場合は、絞り込まず元のテキストをそのまま返す（安全側）。
    """
    parts = LIST_PAGE_DATE_RE.split(text)
    if len(parts) < 3:
        return text, [], []

    cutoff = today - timedelta(days=LIST_PAGE_MAX_AGE_DAYS)
    kept_blocks = []
    kept_dates = []
    excluded_dates = []
    for i in range(1, len(parts), 2):
        date_str = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        try:
            pub_date = date(int(date_str[0:4]), int(date_str[5:7]), int(date_str[8:10]))
        except ValueError:
            # 万一パースできなければ、除外せず残す（安全側）
            kept_blocks.append(date_str + body)
            kept_dates.append(date_str)
            continue
        if pub_date >= cutoff:
            kept_blocks.append(date_str + body)
            kept_dates.append(date_str)
        else:
            excluded_dates.append(date_str)

    return "\n".join(kept_blocks), kept_dates, excluded_dates


_last_request_time = None


def http_get(url, **kwargs):
    global _last_request_time
    last_exc = None
    for attempt in range(1, RETRY_COUNT + 1):
        if _last_request_time is not None:
            wait = INTERVAL_SEC - (time.time() - _last_request_time)
            if wait > 0:
                time.sleep(wait)
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SEC, **kwargs)
            _last_request_time = time.time()
            return r
        except requests.exceptions.RequestException as e:
            _last_request_time = time.time()
            last_exc = e
            if attempt < RETRY_COUNT:
                print(f"  [retry {attempt}/{RETRY_COUNT - 1}] {url}: {e}")
                time.sleep(RETRY_WAIT_SEC)
    raise last_exc


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
    """戻り値: [(一覧ページURL, 取得日 date, ページ全文テキスト), ...]。cutoffは使わない（記事単位でないため）。

    gyms.json に "urls"（複数URLのリスト）があれば、各URLを個別のターゲットとして1件ずつ返す
    （計 len(urls) 件）。無ければ従来通り "url" 単体を1件返す。
    URLごとに個別に返すのは、その後の source_url（元記事リンク）が常に実際の掲載元URLと
    一致するようにするため（結合すると、片方のURL由来のイベントにもう片方のURLが付いてしまう）。
    """
    urls = gym.get("urls") or [gym["url"]]
    results = []
    for u in urls:
        r = http_get(u)
        r.raise_for_status()
        text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
        results.append((u, today_jst(), text))
    return results


def collect_tsunashima_articles(gym, cutoff):
    """戻り値: [(記事URL, 公開日 date, 本文テキスト), ...]
    綱島店トップページの新着情報リンク（上位8件、ページ掲載順）を対象に、
    本厚木と同じフォールバック（記事ページのdatetime属性から日付取得）で処理する。
    """
    r = http_get(gym["url"])
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(gym["url"], a["href"])
        if TSUNASHIMA_ARTICLE_URL_RE.search(full) and full not in seen:
            seen.add(full)
            links.append(full)
        if len(links) >= TSUNASHIMA_MAX_ARTICLES:
            break

    results = []
    for link in links:
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


COLLECTORS = {
    "news_list": collect_dbc_recent_articles,
    "wp_rest_api": collect_bpump_recent_articles,
    "page": collect_page_target,
    "tsunashima_news": collect_tsunashima_articles,
}


def extract_events_from_text(client, text, ref_date, list_page=False):
    if list_page:
        marker = "\n---\n{text}\n"
        extra = LIST_PAGE_EXTRA_RULES.format(ref_date=ref_date.isoformat())
        template = PROMPT_TEMPLATE.replace(marker, extra + marker)
        prompt = template.format(ref_date=ref_date.isoformat(), text=text)
    else:
        prompt = PROMPT_TEMPLATE.format(ref_date=ref_date.isoformat(), text=text)
    res = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    print(f"    [トークン] input={res.usage.input_tokens} output={res.usage.output_tokens}")
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


def migrate_page_cache(processed, gyms):
    """processed["pages"] のキーを gym_id 単位から "gym_id::url" 単位へ移行する。

    旧形式（キーがそのまま gym_id で "::" を含まない）のエントリだけを変換し、
    既に新形式（"::" を含む）のエントリはそのまま引き継ぐ。何度呼んでも結果は同じ（冪等）。
    旧キーは変換後に残さない（新旧どちらを読むべきか曖昧にならないようにするため）。

    変換先のURLは、そのgym_idの現在の gyms.json の urls[0]（無ければ url）を使う。
    gyms.json に該当gym_idが見つからない場合（店舗が削除された等）は、データを失わないよう
    元のキーのまま残す。
    """
    gym_url = {}
    for g in gyms:
        urls = g.get("urls") or [g.get("url")]
        if urls and urls[0]:
            gym_url[g["id"]] = urls[0]

    pages = processed.get("pages", {})
    migrated = {}
    for key, value in pages.items():
        if "::" in key:
            migrated[key] = value
            continue
        url = gym_url.get(key)
        if url is None:
            migrated[key] = value
            continue
        migrated[f"{key}::{url}"] = value

    processed["pages"] = migrated
    return processed


def main():
    with open("gyms.json", encoding="utf-8") as f:
        gyms = json.load(f)

    # 引数なし: 従来通り有効な全店舗を処理する（GitHub Actionsからの呼び出しはこちら）。
    # 引数あり: スペース区切りで渡した gym_id だけを対象にする（動作確認・個別再実行用）。
    # 存在しない gym_id が1つでも混ざっていたら、黙って無視せずエラーで停止する。
    # --force: 指定した gym_id のキャッシュを無視して強制的に再抽出する。絞り込み実行専用。
    raw_args = sys.argv[1:]
    force = "--force" in raw_args
    requested_ids = [a for a in raw_args if a != "--force"]
    if force and not requested_ids:
        sys.exit("--force は gym_id を指定した絞り込み実行でのみ使用できます。")
    if requested_ids:
        known_ids = {g["id"] for g in gyms}
        unknown = [gid for gid in requested_ids if gid not in known_ids]
        if unknown:
            sys.exit(f"gyms.json に存在しない gym_id: {', '.join(unknown)}")
        force_note = "（--force: キャッシュ無視）" if force else ""
        print(f"対象を {len(requested_ids)} 店舗に限定します{force_note}: {', '.join(requested_ids)}")

    today = today_jst()
    now_iso = now_jst().isoformat(timespec="seconds")
    cutoff = today - timedelta(days=RECENT_DAYS)
    client = anthropic.Anthropic()
    processed = load_processed()
    processed = migrate_page_cache(processed, gyms)

    all_events = []
    status_records = []
    llm_calls = 0
    targets = [g for g in gyms if g.get("enabled", True)]
    if requested_ids:
        targets = [g for g in targets if g["id"] in requested_ids]

    for gym in targets:
        label = f"{gym['chain']} {gym['name']}"
        collector = COLLECTORS[gym["method"]]
        fetched_at = now_jst().isoformat(timespec="seconds")

        try:
            articles = collector(gym, cutoff)
        except Exception as e:
            print(f"[{label}] 取得失敗: {e}")
            status_records.append({
                "gym_id": gym["id"],
                "status": "failure",
                "fetched_at": fetched_at,
                "error": str(e),
            })
            continue

        status_records.append({"gym_id": gym["id"], "status": "success", "fetched_at": fetched_at})
        print(f"[{label}] 対象 {len(articles)}件")

        gym_events = []

        for i, (url, pub, body) in enumerate(articles, 1):
            if gym["method"] == "page":
                h = text_hash(body)
                page_key = f"{gym['id']}::{url}"
                cached = processed["pages"].get(page_key)
                if cached and cached["text_hash"] == h and not force:
                    events = cached["events"]
                    pub_iso = cached["published"]
                    print(f"  ({i}/{len(articles)}) {url} 変更なし → キャッシュ再利用 (events: {len(events)})")
                else:
                    list_page = gym.get("list_page", False)
                    llm_text = body
                    if list_page:
                        llm_text, kept_dates, excluded_dates = split_list_page_blocks(body, pub)
                        print(
                            f"    [掲載日フィルタ] 対象{len(kept_dates)}件 / "
                            f"除外{len(excluded_dates)}件"
                        )
                        print(f"      対象の掲載日: {', '.join(kept_dates) if kept_dates else '(なし)'}")
                        if excluded_dates:
                            print(f"      除外した掲載日: {', '.join(excluded_dates)}")
                    try:
                        events = extract_events_from_text(
                            client, llm_text, pub, list_page=list_page
                        )
                        llm_calls += 1
                    except Exception as e:
                        print(f"  ({i}/{len(articles)}) {url} 失敗: {e}")
                        continue
                    pub_iso = pub.isoformat()
                    processed["pages"][page_key] = {
                        "text_hash": h,
                        "last_changed_at": now_iso,
                        "published": pub_iso,
                        "events": events,
                    }
                    print(f"  ({i}/{len(articles)}) {url} events: {len(events)}")
            else:
                cached = processed["articles"].get(url)
                if cached and cached["published"] == pub.isoformat() and not force:
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
                gym_events.append({
                    "gym_id": gym["id"],
                    "date": ev.get("date"),
                    "type": ev.get("type"),
                    "note": ev.get("note"),
                    "source_url": url,
                    "published": pub_iso,
                })

        # 複数URL（route/pickup等）の店舗のみ、同一店舗内で (date, type) が完全一致するイベントを
        # 重複排除する。urls に先に書いたURL由来を残す（先勝ち）。note の連結はしない。
        # キャッシュ（processed["pages"]）には生のイベントをそのまま保存しており、ここでは
        # events.json に積む直前の集約後の一時リストにのみ適用するため、片方の記事が後日
        # 無くなった場合でも、残った側のキャッシュから正しく復元できる。
        # 単一URL店舗（既存19店舗）は urls が1件のため、このブロックは何もしない。
        if len(gym.get("urls") or [gym.get("url")]) > 1:
            seen = set()
            deduped = []
            for ev in gym_events:
                key = (ev["date"], ev["type"])
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(ev)
            gym_events = deduped

        all_events.extend(gym_events)

    # 絞り込み実行（requested_ids指定あり）のときだけ、既存の events.json / collection_status.json を
    # 読み込み、対象外の店舗分を温存してから今回の結果をマージする。無指定時は従来通り全体を書き出す。
    if requested_ids:
        try:
            with open("events.json", encoding="utf-8") as f:
                existing_events = json.load(f)
        except FileNotFoundError:
            existing_events = []
        all_events = [e for e in existing_events if e["gym_id"] not in requested_ids] + all_events

        try:
            with open("collection_status.json", encoding="utf-8") as f:
                existing_status = json.load(f)
        except FileNotFoundError:
            existing_status = []
        status_records = [s for s in existing_status if s["gym_id"] not in requested_ids] + status_records

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
