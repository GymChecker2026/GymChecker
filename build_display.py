import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

with open("gyms.json", encoding="utf-8") as f:
    gyms = json.load(f)
with open("events.json", encoding="utf-8") as f:
    events = json.load(f)
try:
    with open("collection_status.json", encoding="utf-8") as f:
        status_records = json.load(f)
except FileNotFoundError:
    print("collection_status.json が見つかりません（extract_events.py 未実行）。全店舗を未取得扱いにします。")
    status_records = []

status_by_gym = {s["gym_id"]: s for s in status_records}

try:
    with open("processed.json", encoding="utf-8") as f:
        processed = json.load(f)
except FileNotFoundError:
    processed = {"pages": {}}
pages_by_gym = processed.get("pages", {})

today = datetime.now(JST).date()
window_end = today + timedelta(days=14)

events_by_gym = defaultdict(list)
for ev in events:
    try:
        ev_date = date.fromisoformat(ev.get("date", ""))
    except ValueError:
        continue
    if ev_date <= window_end:
        events_by_gym[ev["gym_id"]].append({
            "date": ev["date"],
            "type": ev.get("type"),
            "note": ev.get("note"),
            "source_url": ev.get("source_url"),
            "published": ev.get("published"),
        })

for gym_events in events_by_gym.values():
    gym_events.sort(key=lambda e: e["date"])

display = []
for gym in gyms:
    status = status_by_gym.get(gym["id"])
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
        "enabled": gym.get("enabled", True),
        "data_note": gym.get("data_note"),
        "official_url": gym.get("official_url"),
        "instagram_url": gym.get("instagram_url"),
        "fetch_status": status["status"] if status else None,
        "fetched_at": status["fetched_at"] if status else None,
        "last_changed_at": pages_by_gym.get(gym["id"], {}).get("last_changed_at"),
        "events": events_by_gym.get(gym["id"], []),
    })

with open("display.json", "w", encoding="utf-8") as f:
    json.dump(display, f, ensure_ascii=False, indent=2)

total = sum(len(g["events"]) for g in display)
print(f"{len(display)}店舗、イベント{total}件（{today}〜{window_end}）を display.json に保存しました。")
for g in display:
    print(f"  {g['chain']} {g['name']}: {len(g['events'])}件")
