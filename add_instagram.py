import json

HANDLES = {
    "noborock-shinjuku": "noborock_shinjuku",
    "noborock-shibuya": "noborock_shibuya",
    "noborock-takadanobaba": "noborock_takadanobaba",
    "noborock-asakusa": "noborock_asakusa",
    "noborock-ikebukuro": "noborock_ikebukuro",
    "noborock-machida": "noborock_machida",
    "noborock-mizonokuchi": "noborock_mizonokuchi",
    "noborock-omiya": "noborock_omiya",
    "dbc-tachikawa": "dbouldering_tachikawa",
    "dbc-tamachi": "dbouldering_tamachi",
    "dbc-tsunashima": "dbouldering_tsunashima",
    "dbc-honatsugi": "dbouldering_honatsugi",
    "dbc-yokohama": "dbouldering_yokohama",
    "dbc-kawasaki": "dbouldering_kawasaki",
    "bpump-akihabara": "bpumptokyo",
    "bpump-ogikubo": "bpump_ogikubo",
    "bpump-yokohama": "bpumpyokohama",
    "bpump-kawaguchi": "pump1_kawaguchi",
    "bpump-kawasaki": "pump2climbing",
}

with open("gyms.json", encoding="utf-8") as f:
    gyms = json.load(f)

for gym in gyms:
    handle = HANDLES.get(gym["id"])
    gym["instagram_url"] = f"https://www.instagram.com/{handle}/" if handle else None

with open("gyms.json", "w", encoding="utf-8") as f:
    json.dump(gyms, f, ensure_ascii=False, indent=2)

for gym in gyms:
    print(f"{gym['id']}: instagram_url={gym['instagram_url']!r}")
