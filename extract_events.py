import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import anthropic
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "gym-checker/0.1"}
INTERVAL_SEC = 2
# (connect, read)。ConnectTimeoutは待っても結果が変わらないため接続は10秒で見切り、
# 応答が返り始めてからのReadTimeoutだけ従来通り60秒許容する。
CONNECT_TIMEOUT_SEC = 10
READ_TIMEOUT_SEC = 60
REQUEST_TIMEOUT = (CONNECT_TIMEOUT_SEC, READ_TIMEOUT_SEC)
RETRY_COUNT = 3
RETRY_WAIT_SEC = 5
RECENT_DAYS = 45
# 同一ホストへの ConnectTimeout が連続でこの回数に達したら、そのホストの残り店舗は
# リトライせず即座に失敗扱いにする（Actions側からブロックされているホスト向け）。
HOST_TIMEOUT_BLOCK_THRESHOLD = 2
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

# shared_calendar: true の店舗（1ページに複数店舗ぶんの予定が1つのカレンダーとして
# まとめて掲載されているタイプ）にのみ追加する解釈ルール。LIST_PAGE_EXTRA_RULESと同じ
# パターンで、extract_events_from_text 内で "---\n{text}\n" の直前に差し込む。
# 店舗への振り分けはこの段階では行わず、gym_name フィールドに原文表記のまま出力させるだけ
# （振り分けは別段階でコード側が行う）。
SHARED_CALENDAR_EXTRA_RULES = """
このページには複数店舗の予定が1つのカレンダーとしてまとめて掲載されています。
特定の店舗の分だけに絞り込まず、カレンダーに書かれている全ての項目を抽出してください。

出力フォーマットについては、以下のルールを本文中の「形式」の指定より優先してください。
各項目について、どの店舗の予定かを示す gym_name フィールドを追加すること。
店舗名は原文の表記のまま出力すること（例：「大宮店」と書かれていれば「大宮店」、
「大宮」とだけ書かれていれば「大宮」とする。表記を変換・正規化しないこと）。
どの店舗の項目か読み取れない場合は、gym_name を空文字（""）にすること。

{{"events": [{{"date": "YYYY-MM-DD", "type": "種別", "note": "補足", "gym_name": "店舗名"}}]}}
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
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
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


def extract_events_from_text(client, text, ref_date, list_page=False, shared_calendar=False):
    extra_blocks = []
    if list_page:
        extra_blocks.append(LIST_PAGE_EXTRA_RULES.format(ref_date=ref_date.isoformat()))
    if shared_calendar:
        extra_blocks.append(SHARED_CALENDAR_EXTRA_RULES)
    if extra_blocks:
        marker = "\n---\n{text}\n"
        template = PROMPT_TEMPLATE.replace(marker, "".join(extra_blocks) + marker)
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


def route_shared_calendar_event(gym_name, chain, gyms):
    """shared_calendar: true のページから抽出したイベント（gym_name付き）を、
    本来の店舗の gym_id に振り分ける。同じ chain の全店舗の name のうち、
    gym_name に部分文字列として含まれるものを候補とし、複数一致した場合は
    最も長い name を採用する（NOBOROCK8店舗のnameは互いに部分文字列関係にないため
    通常は複数一致しないが、将来chainが増えた場合の安全策）。
    一致するnameが無い場合、あるいはgym_nameが空文字／Noneの場合は
    None を返す（呼び出し側でイベントを破棄する）。
    """
    if not gym_name:
        return None
    matches = [g for g in gyms if g["chain"] == chain and g["name"] in gym_name]
    if not matches:
        return None
    best = max(matches, key=lambda g: len(g["name"]))
    return best["id"]


def resolve_shared_calendar_duplicates(events):
    """route_shared_calendar_event() で振り分け済みのイベントについて、同一の
    (gym_id, date, type) が複数のページ（店舗）由来で重複することがあるため、
    抽出元ページの gym_id（origin_gym_id）と振り分け先の gym_id が一致するもの
    （＝自店舗ページ由来）を優先して1件だけ残す。

    この優先順位は、溝ノ口 2026-09-13 の1例のみを根拠にした推測である
    （新宿ページのカレンダーには「18:45 close」、溝ノ口自身のページには
    「17:00 close」と書かれており、自店舗ページの方が正しかった。サイト側の
    記載ミスと考えられるが、他の店舗・日付でも同様の傾向があるとは限らない）。

    自店舗ページ由来が1件も無いキー（例：高田馬場 09-28 のように自店舗ページ側で
    抽出漏れが起きているケース）では、他ページ由来のうち最初に出現したものを採用する。
    """
    best = {}
    for ev in events:
        key = (ev["gym_id"], ev["date"], ev["type"])
        is_self = ev["origin_gym_id"] == ev["gym_id"]
        existing = best.get(key)
        if existing is None:
            best[key] = (ev, is_self)
            continue
        _, existing_is_self = existing
        if is_self and not existing_is_self:
            print(
                f"[重複排除] {key[0]} {key[1]} {key[2]}: "
                f"自店舗ページ由来（{ev['origin_gym_id']}）を優先し、"
                f"他ページ由来（{existing[0]['origin_gym_id']}）を破棄します"
            )
            best[key] = (ev, is_self)
        elif existing_is_self and not is_self:
            print(
                f"[重複排除] {key[0]} {key[1]} {key[2]}: "
                f"既に自店舗ページ由来（{existing[0]['origin_gym_id']}）を採用済みのため、"
                f"他ページ由来（{ev['origin_gym_id']}）を破棄します"
            )
        else:
            print(
                f"[重複排除] {key[0]} {key[1]} {key[2]}: "
                f"{existing[0]['origin_gym_id']} 由来を採用済みのため、"
                f"{ev['origin_gym_id']} 由来を破棄します"
            )
    return [ev for ev, _ in best.values()]


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
    # shared_calendar: true のページから振り分けたイベントの一時置き場。gym_events/all_events
    # には直接積まず、全ターゲットの処理が終わってから resolve_shared_calendar_duplicates() で
    # 自店舗ページ由来を優先する重複排除を行った上でまとめて all_events に加える
    # （店舗をまたいだ重複判定になるため、店舗ごとのループの中では確定できない）。
    shared_calendar_events = []
    status_records = []
    llm_calls = 0
    targets = [g for g in gyms if g.get("enabled", True)]
    if requested_ids:
        targets = [g for g in targets if g["id"] in requested_ids]

    # ホスト単位でConnectTimeoutが連続した回数。閾値に達したホストは blocked_hosts に入れ、
    # 残りの店舗はリトライせず即座に失敗扱いにする（Actionsからブロックされたホスト対策）。
    host_timeout_streak = {}
    blocked_hosts = set()

    for gym in targets:
        label = f"{gym['chain']} {gym['name']}"
        fetched_at = now_jst().isoformat(timespec="seconds")
        host = urlparse((gym.get("urls") or [gym.get("url")])[0]).netloc

        if host in blocked_hosts:
            print(f"[{label}] スキップ: {host} への接続が連続{HOST_TIMEOUT_BLOCK_THRESHOLD}回タイムアウトしたためリトライしません")
            status_records.append({
                "gym_id": gym["id"],
                "status": "failure",
                "fetched_at": fetched_at,
                "error": f"{host} への接続が連続{HOST_TIMEOUT_BLOCK_THRESHOLD}回タイムアウトしたためスキップ",
                "reason": "host_blocked",
            })
            continue

        try:
            collector = COLLECTORS[gym["method"]]
            articles = collector(gym, cutoff)
        except requests.exceptions.ConnectTimeout as e:
            host_timeout_streak[host] = host_timeout_streak.get(host, 0) + 1
            print(f"[{label}] 取得失敗: {e}")
            status_records.append({
                "gym_id": gym["id"],
                "status": "failure",
                "fetched_at": fetched_at,
                "error": str(e),
            })
            if host_timeout_streak[host] >= HOST_TIMEOUT_BLOCK_THRESHOLD:
                blocked_hosts.add(host)
                print(f"  [{host}] 連続{HOST_TIMEOUT_BLOCK_THRESHOLD}回 ConnectTimeout のため、以降このホストの店舗はスキップします")
            continue
        except Exception as e:
            host_timeout_streak[host] = 0
            print(f"[{label}] 取得失敗: {e}")
            status_records.append({
                "gym_id": gym["id"],
                "status": "failure",
                "fetched_at": fetched_at,
                "error": str(e),
            })
            continue

        host_timeout_streak[host] = 0

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
                            client, llm_text, pub, list_page=list_page,
                            shared_calendar=gym.get("shared_calendar", False),
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
                if gym.get("shared_calendar", False):
                    gym_name = ev.get("gym_name")
                    target_gym_id = route_shared_calendar_event(gym_name, gym["chain"], gyms)
                    if target_gym_id is None:
                        print(
                            f"[振り分け失敗] {gym['id']} {ev.get('date')} {ev.get('type')}: "
                            f"gym_name='{gym_name}' が{gym['chain']}のどの店舗名にも一致しないため破棄します"
                        )
                        continue
                    shared_calendar_events.append({
                        "gym_id": target_gym_id,
                        "origin_gym_id": gym["id"],
                        "date": ev.get("date"),
                        "type": ev.get("type"),
                        "note": ev.get("note"),
                        "gym_name": gym_name,
                        "source_url": url,
                        "published": pub_iso,
                    })
                else:
                    gym_events.append({
                        "gym_id": gym["id"],
                        "date": ev.get("date"),
                        "type": ev.get("type"),
                        "note": ev.get("note"),
                        "gym_name": ev.get("gym_name"),
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

    # shared_calendar 由来で振り分けたイベントは、店舗をまたいだ重複排除
    # （自店舗ページ由来を優先）を行ってから all_events に加える。
    resolved_shared_events = resolve_shared_calendar_duplicates(shared_calendar_events)
    for ev in resolved_shared_events:
        del ev["origin_gym_id"]
    all_events.extend(resolved_shared_events)

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
