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
pages_by_gym = processed.get("pages", {})

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
        events_by_gym[ev["gym_id"]].append({
            "date": ev["date"],
            "type": ev.get("type"),
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
        "last_changed_at": pages_by_gym.get(gym["id"], {}).get("last_changed_at"),
        "events": events_by_gym.get(gym["id"], []),
    })

with open("display.json", "w", encoding="utf-8") as f:
    json.dump(display, f, ensure_ascii=False, indent=2)

total = sum(len(g["events"]) for g in display)
manual_total = sum(1 for g in display for e in g["events"] if e["source"] == "manual")
print(f"{len(display)}店舗、イベント{total}件（うち手動{manual_total}件）（{window_start}〜{window_end}）を display.json に保存しました。")
for g in display:
    print(f"  {g['chain']} {g['name']}: {len(g['events'])}件")
