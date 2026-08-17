import json

with open("gyms.json", encoding="utf-8") as f:
    gyms = json.load(f)

for gym in gyms:
    if gym["chain"] == "NOBOROCK":
        gym["display_name"] = f"ノボロック{gym['name']}店"
    elif gym["chain"] == "D-BOULDERING":
        gym["display_name"] = f"Dボルダリング{gym['name']}店"
    elif gym["chain"] == "B-PUMP":
        gym["chain"] = "pump"
        gym["display_name"] = None
    else:
        raise ValueError(f"unknown chain: {gym['chain']}")

with open("gyms.json", "w", encoding="utf-8") as f:
    json.dump(gyms, f, ensure_ascii=False, indent=2)

for gym in gyms:
    print(f"{gym['id']}: chain={gym['chain']!r} display_name={gym['display_name']!r}")
