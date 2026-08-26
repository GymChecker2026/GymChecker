# -*- coding: utf-8 -*-
"""
ROCKY系列 営業カレンダーの取得と反映

  https://www.rockyclimbing.com/set/ から全店舗のカレンダー画像URLを拾い、
  SHA-256で前回と比較して、変化した画像だけを rocky_calendar.py に通す。
  結果を manual_events.json に反映する。

使い方:
    py rocky_fetch.py            # 変化した画像だけ処理
    py rocky_fetch.py --all      # 変化の有無にかかわらず全部処理
    py rocky_fetch.py --dry-run  # ファイルを書き換えずに結果だけ表示

事前準備:
    py -m pip install requests beautifulsoup4 jpholiday anthropic

失敗の扱い:
    - 読み取りや検証に失敗した画像は、その場で1回だけ読み直す
    - それでも駄目なら pending_review.json に月単位のレコードとして記録する
      （コンソールを見なくても、保留リストだけ見れば全ての失敗が分かる）
    - 1つの月が失敗しても、他の月が成功していればその店舗は success のまま

生成/更新されるファイル:
    rocky_images/        ... 取得した画像
    rocky_state.json     ... 画像のハッシュ（差分検知用）
    rocky_status.json    ... 店舗ごとの取得成否（build_display.py が読む）
    pending_review.json  ... 自動判定できなかった日・月
    manual_events.json   ... 既存ファイルに反映
"""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from rocky_calendar import read_calendar_votes, validate, convert

JST = ZoneInfo("Asia/Tokyo")

SET_URL = "https://www.rockyclimbing.com/set/"
UA = "Mozilla/5.0 (compatible; GymChecker/1.0; +npplun995@gmail.com)"

IMAGE_DIR = Path("rocky_images")
STATE_PATH = Path("rocky_state.json")
STATUS_PATH = Path("rocky_status.json")
MANUAL_PATH = Path("manual_events.json")
PENDING_PATH = Path("pending_review.json")

# 失敗した画像を読み直す回数（成功した画像は1回で終わる）
RETRY = 1

# ページ上の店舗名 -> gym_id
GYM_IDS = {
    "品川店": "rocky-shinagawa",
    "新宿曙橋店": "rocky-akebonobashi",
    "両国店": "rocky-ryogoku",
    "印西店": "rocky-inzai",
    "つくば阿見店": "rocky-tsukuba",
    "船橋店": "rocky-funabashi",
}

# 予定を取得する店舗
TARGET_GYMS = {
    "rocky-shinagawa",
    "rocky-akebonobashi",
    "rocky-ryogoku",
    "rocky-inzai",
    "rocky-tsukuba",
    "rocky-funabashi",
}


# ---------------------------------------------------------------- ページ解析

def fetch_calendar_urls():
    """
    /set/ を取得し、[(gym_id, 店舗名, スロット番号, 画像URL), ...] を返す。
    スロット0が今月、1が来月。
    """
    res = requests.get(SET_URL, headers={"User-Agent": UA}, timeout=30)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    # <label for="tab11">品川店</label> から タブ番号 -> 店舗名 を作る
    tab_names = {}
    for label in soup.find_all("label"):
        m = re.fullmatch(r"tab(\d+)", label.get("for", "") or "")
        name = label.get_text(strip=True)
        if m and name in GYM_IDS:
            tab_names[m.group(1)] = name

    out = []
    for div in soup.find_all("div", id=re.compile(r"^content\d+_class$")):
        num = re.search(r"content(\d+)_class", div["id"]).group(1)
        name = tab_names.get(num)
        if not name:
            continue
        for slot, img in enumerate(div.find_all("img")):
            src = img.get("src")
            if src:
                out.append((GYM_IDS[name], name, slot, urljoin(SET_URL, src)))

    # PC版とスマホ版で同じ画像が重複するので (gym_id, slot) で最初だけ残す
    seen, uniq = set(), []
    for row in out:
        key = (row[0], row[2])
        if key not in seen:
            seen.add(key)
            uniq.append(row)
    return uniq


def download(url, dest):
    res = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    res.raise_for_status()
    dest.write_bytes(res.content)
    return hashlib.sha256(res.content).hexdigest()


# ---------------------------------------------------------------- 読み取り

def read_with_retry(path, label):
    """
    読み取りと検証を行う。失敗したら RETRY 回だけ読み直す。
    成功なら (data, None)、最後まで駄目なら (None, 理由) を返す。
    """
    reason = None
    for attempt in range(RETRY + 1):
        if attempt:
            print(f"  {label} 読み直します（{attempt}回目の再試行）")
        try:
            data = read_calendar_votes(path)
        except Exception as e:
            reason = f"読み取りに失敗: {e}"
            print(f"  {reason}")
            continue

        errors = validate(data)
        if not errors:
            return data, None

        reason = "検証に失敗: " + " / ".join(errors)
        print(f"  {reason}")
    return None, reason


# ---------------------------------------------------------------- 反映

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def merge_events(manual, new_events, touched_months):
    """
    処理した gym_id・年月の既存レコードを差し替える。
    ただし "locked": true が付いたレコードは手入力なので残す。
    """
    kept = []
    for e in manual.get("events", []):
        key = (e.get("gym_id"), str(e.get("date", ""))[:7])
        if key in touched_months and not e.get("locked"):
            continue
        kept.append(e)

    # 手入力で押さえた日は自動生成より優先する
    locked_dates = {(e.get("gym_id"), e.get("date"))
                    for e in kept if e.get("locked")}
    fresh = [e for e in new_events
             if (e["gym_id"], e["date"]) not in locked_dates]

    merged = kept + fresh
    merged.sort(key=lambda e: (str(e.get("date", "")), str(e.get("gym_id", ""))))
    manual["events"] = merged


# ---------------------------------------------------------------- 実行

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="変化の有無にかかわらず全画像を処理する")
    ap.add_argument("--dry-run", action="store_true",
                    help="ファイルを書き換えない")
    args = ap.parse_args()

    IMAGE_DIR.mkdir(exist_ok=True)
    state = load_json(STATE_PATH, {})
    status = load_json(STATUS_PATH, {})

    print(f"{SET_URL} を取得中...")
    rows = [r for r in fetch_calendar_urls() if r[0] in TARGET_GYMS]
    print(f"対象 {len(rows)} 枚\n")

    all_events, all_pending = [], []
    touched_months = set()
    seen_gyms, failed_gyms = set(), set()
    processed = 0

    for gym_id, name, slot, url in rows:
        key = f"{gym_id}:{slot}"
        dest = IMAGE_DIR / f"{gym_id}_{slot}.png"
        label = f"[{name} {slot}]"
        seen_gyms.add(gym_id)

        try:
            digest = download(url, dest)
        except Exception as e:
            print(f"{label} 画像の取得に失敗: {e}")
            all_pending.append({"gym_id": gym_id, "date": f"slot{slot}",
                                "reason": f"画像の取得に失敗: {e}"})
            failed_gyms.add(gym_id)
            continue
        time.sleep(2)  # 相手のサーバに負荷をかけない

        if not args.all and state.get(key, {}).get("sha256") == digest:
            print(f"{label} 変化なし。スキップ")
            continue

        print(f"{label} {url}")
        data, reason = read_with_retry(str(dest), label)

        if data is None:
            # 月単位の失敗も保留に記録する。コンソールを見なくても気づけるように
            all_pending.append({"gym_id": gym_id, "date": f"slot{slot}",
                                "reason": reason or "原因不明の失敗"})
            failed_gyms.add(gym_id)
            print()
            continue

        events, pending = convert(data, gym_id)
        print(f"  {data.get('year')}年{data.get('month')}月 "
              f"採用 {len(events)}件 / 保留 {len(pending)}件\n")

        all_events += events
        all_pending += [{k: v for k, v in p.items() if k != "raw"} for p in pending]
        touched_months.add((gym_id, f"{data['year']:04d}-{data['month']:02d}"))
        state[key] = {"url": url, "sha256": digest}
        processed += 1

    # 1つの月が失敗しても、その店舗のデータが全く無いわけではない。
    # 画像の取得自体に失敗した店舗だけを failure にする
    now = datetime.now(JST).isoformat(timespec="seconds")
    for gym_id in seen_gyms:
        prev = status.get(gym_id, {}).get("status")
        ok = gym_id not in failed_gyms or prev == "success"
        status[gym_id] = {"status": "success" if ok else "failure",
                          "fetched_at": now}

    print(f"=== 採用 {len(all_events)}件 / 保留 {len(all_pending)}件 "
          f"/ 処理した画像 {processed}枚 ===")

    if args.dry_run:
        print(json.dumps(all_events, ensure_ascii=False, indent=2))
        print("\n--dry-run のためファイルは書き換えていません")
        return

    if processed:
        manual = load_json(MANUAL_PATH, {"_readme": "", "events": []})
        merge_events(manual, all_events, touched_months)
        MANUAL_PATH.write_text(
            json.dumps(manual, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{MANUAL_PATH} を更新しました（該当月を差し替え）")
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    PENDING_PATH.write_text(
        json.dumps(all_pending, ensure_ascii=False, indent=2), encoding="utf-8")
    STATUS_PATH.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    if all_pending:
        print(f"\n保留 {len(all_pending)}件。{PENDING_PATH} を確認してください")
        for p in all_pending:
            print(f"  {p['date']}  {p['gym_id']}  {p['reason']}")

    print("\nこの後: py build_display.py -> py build_html.py -> commit & push")


if __name__ == "__main__":
    main()
