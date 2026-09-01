import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# イベントの表示対象期間（この日数だけ変更すれば調整できる）。
# EVENT_WINDOW_PAST_DAYS: 今日からこの日数より前のイベントは対象外にする（下限）。
#   selectDisplayEvents側で「直近の過去1件」を表示に使うため、0にはしないこと。
# EVENT_WINDOW_FUTURE_DAYS: 今日からこの日数より先のイベントは対象外にする（上限）。
EVENT_WINDOW_PAST_DAYS = 60
EVENT_WINDOW_FUTURE_DAYS = 14

VALID_TYPES = {"休業", "時間変更", "エリア制限", "セット完了", "イベント"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_manual_event(ev, gym_ids, index):
    gym_id = ev.get("gym_id")
    if gym_id not in gym_ids:
        raise ValueError(
            f"manual_events.json[{index}]: gym_id '{gym_id}' が gyms.json に存在しません"
        )
    date_str = ev.get("date")
    if not isinstance(date_str, str) or not DATE_RE.match(date_str):
        raise ValueError(
            f"manual_events.json[{index}] ({gym_id}): date '{date_str}' が YYYY-MM-DD 形式ではありません"
        )
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(
            f"manual_events.json[{index}] ({gym_id}): date '{date_str}' は実在しない日付です"
        )
    ev_type = ev.get("type")
    if ev_type not in VALID_TYPES:
        raise ValueError(
            f"manual_events.json[{index}] ({gym_id}): type '{ev_type}' が5分類"
            f"（{'/'.join(sorted(VALID_TYPES))}）のいずれでもありません"
        )


def normalize_auto_event_type(ev_type, gym_id, date_str):
    """events.json（LLM抽出）由来の type を検証する。VALID_TYPESに完全一致すればそのまま
    採用し、5種のいずれかで「始まる」場合はその正規の種別名に正規化する（LLMがプロンプト中の
    括弧書きの説明文ごと出力してしまう揺れに対応するため。前方一致の判定はVALID_TYPESの5種
    そのものをprefixとして使うので、括弧が全角・半角どちらでも、あるいは括弧以外の余分な
    文字が続く場合でも同じロジックで拾える）。
    どちらにも当てはまらない場合は None を返し、呼び出し側でそのイベントを破棄する。
    manual_events.json 側は validate_manual_event() で別途 ValueError を送出して厳格に検証して
    いるが、こちらはLLM出力の揺れで日次バッチ全体を止めないよう、例外は送出しない。
    """
    if ev_type in VALID_TYPES:
        return ev_type
    if isinstance(ev_type, str):
        for valid in VALID_TYPES:
            if ev_type.startswith(valid):
                print(f"[正規化] {gym_id} {date_str}: type '{ev_type}' → '{valid}'")
                return valid
    print(f"[破棄] {gym_id} {date_str}: type '{ev_type}' が5分類のいずれにも該当しないためイベントを破棄します")
    return None


def is_covered(gym_id, coverage, today):
    """継続的な手動運用の店舗（data_source: "manual"）について、coverageの日付が
    今日以降かどうかを返す。エントリが無い・日付形式が不正な場合は安全側で False。
    """
    raw = coverage.get(gym_id)
    if not raw:
        return False
    try:
        covered_until = date.fromisoformat(raw)
    except (TypeError, ValueError):
        return False
    return covered_until >= today


def parse_page_datetime(raw):
    """processed.json の last_changed_at 文字列を aware な datetime に変換する。
    タイムゾーンなしの文字列（旧形式）は JST とみなす。パースできない場合は
    None を返す（呼び出し側でそのレコードを無視して処理を続けるため）。
    """
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt


with open("gyms.json", encoding="utf-8") as f:
    gyms = json.load(f)
with open("events.json", encoding="utf-8") as f:
    events = json.load(f)
try:
    with open("manual_events.json", encoding="utf-8") as f:
        manual_data = json.load(f)
        manual_events = manual_data.get("events", [])
        coverage = manual_data.get("coverage", {})
except FileNotFoundError:
    print("manual_events.json が見つかりません。手動イベントなしで続行します。")
    manual_events = []
    coverage = {}
try:
    with open("collection_status.json", encoding="utf-8") as f:
        status_records = json.load(f)
except FileNotFoundError:
    print("collection_status.json が見つかりません（extract_events.py 未実行）。全店舗を未取得扱いにします。")
    status_records = []

status_by_gym = {s["gym_id"]: s for s in status_records}
try:
    with open("rocky_status.json", encoding="utf-8") as f:
        rocky_status = json.load(f)
except FileNotFoundError:
    rocky_status = {}

try:
    with open("processed.json", encoding="utf-8") as f:
        processed = json.load(f)
except FileNotFoundError:
    processed = {"pages": {}}

# processed["pages"] のキーは "{gym_id}::{url}" 形式（例: Base Camp は urls が
# [pickup, route] の2件あるため、1店舗につきレコードが2件存在する）。
# gym_id ごとに集約し、last_changed_at が最も新しいレコードを採用する
# （どちらか一方のページが更新されていれば、その店舗の情報は更新されているため）。
last_changed_by_gym = {}
for page_key, record in processed.get("pages", {}).items():
    gym_id = page_key.split("::", 1)[0]
    raw_last_changed = record.get("last_changed_at")
    dt = parse_page_datetime(raw_last_changed)
    if dt is None:
        continue
    best = last_changed_by_gym.get(gym_id)
    if best is None or dt > best[0]:
        last_changed_by_gym[gym_id] = (dt, raw_last_changed)

today = datetime.now(JST).date()
window_start = today - timedelta(days=EVENT_WINDOW_PAST_DAYS)
window_end = today + timedelta(days=EVENT_WINDOW_FUTURE_DAYS)
gym_ids = {g["id"] for g in gyms}

for i, ev in enumerate(manual_events):
    validate_manual_event(ev, gym_ids, i)

events_by_gym = defaultdict(list)
for ev in events:
    try:
        ev_date = date.fromisoformat(ev.get("date", ""))
    except ValueError:
        continue
    if window_start <= ev_date <= window_end:
        ev_type = normalize_auto_event_type(ev.get("type"), ev["gym_id"], ev["date"])
        if ev_type is None:
            continue
        events_by_gym[ev["gym_id"]].append({
            "date": ev["date"],
            "type": ev_type,
            "note": ev.get("note"),
            "source_url": ev.get("source_url"),
            "published": ev.get("published"),
            "source": "auto",
        })

for ev in manual_events:
    ev_date = date.fromisoformat(ev["date"])
    if window_start <= ev_date <= window_end:
        events_by_gym[ev["gym_id"]].append({
            "date": ev["date"],
            "type": ev["type"],
            "note": ev.get("note"),
            "source_url": ev.get("source_url"),
            "published": ev.get("published") or today.isoformat(),
            "source": "manual",
        })

for gym_events in events_by_gym.values():
    gym_events.sort(key=lambda e: e["date"])

display = []
for gym in gyms:
    if not gym.get("visible", True):
        continue
    status = status_by_gym.get(gym["id"])
    rocky = rocky_status.get(gym["id"])
    manual_only = gym.get("data_source") == "manual"
    covered = is_covered(gym["id"], coverage, today) if manual_only else False
    if manual_only and not covered:
        print(f"[警告] {gym['id']} は coverage の期限が切れています（fetch_status: stale）。")
    display.append({
        "gym_id": gym["id"],
        "name": gym["name"],
        "display_name": gym.get("display_name"),
        "sort_key": gym.get("sort_key"),
        "chain": gym["chain"],
        "hours": gym.get("hours"),
        "hours_note": gym.get("hours_note"),
        "station": gym.get("station"),
        "line": gym.get("line"),
        "enabled": True if (rocky or manual_only) else gym.get("enabled", True),
        "data_note": gym.get("data_note"),
        "official_url": gym.get("official_url"),
        "instagram_url": gym.get("instagram_url"),
        "fetch_status": (
            ("success" if covered else "stale") if manual_only
            else (rocky["status"] if rocky else (status["status"] if status else None))
        ),
        "fetched_at": rocky["fetched_at"] if rocky else (status["fetched_at"] if status else None),
        "last_changed_at": (
            last_changed_by_gym[gym["id"]][1] if gym["id"] in last_changed_by_gym else None
        ),
        "events": events_by_gym.get(gym["id"], []),
    })

with open("display.json", "w", encoding="utf-8") as f:
    json.dump(display, f, ensure_ascii=False, indent=2)

total = sum(len(g["events"]) for g in display)
manual_total = sum(1 for g in display for e in g["events"] if e["source"] == "manual")
print(f"{len(display)}店舗、イベント{total}件（うち手動{manual_total}件）（{window_start}〜{window_end}）を display.json に保存しました。")
for g in display:
    print(f"  {g['chain']} {g['name']}: {len(g['events'])}件")
