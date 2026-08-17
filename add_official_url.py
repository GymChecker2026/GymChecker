import json

DATA_NOTES = {
    "dbc-tachikawa": "月次カレンダーが画像のため予定を取得できません",
    "dbc-yokohama": "月次カレンダーが画像のため予定を取得できません",
}


def official_url_for(gym):
    if gym["chain"] == "NOBOROCK":
        return gym["url"]
    if gym["chain"] == "D-BOULDERING":
        slug = gym["id"].split("-", 1)[1]
        return f"https://www.d-b-c.jp/top/{slug}/"
    if gym["chain"] == "pump":
        return gym["url"].split("wp-json")[0]
    raise ValueError(f"unknown chain: {gym['chain']}")


with open("gyms.json", encoding="utf-8") as f:
    gyms = json.load(f)

for gym in gyms:
    if "official_url" not in gym or not gym["official_url"]:
        gym["official_url"] = official_url_for(gym)
    gym["data_note"] = DATA_NOTES.get(gym["id"])

with open("gyms.json", "w", encoding="utf-8") as f:
    json.dump(gyms, f, ensure_ascii=False, indent=2)

for gym in gyms:
    print(f"{gym['id']}: official_url={gym['official_url']!r} data_note={gym['data_note']!r}")
