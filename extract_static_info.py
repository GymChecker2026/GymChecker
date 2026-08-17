import json
import re
import time

import anthropic
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "gym-checker/0.1"}
INTERVAL_SEC = 2
MODEL = "claude-haiku-4-5-20251001"

PROMPT_TEMPLATE = """以下はクライミングジムの公式ページのテキストです。

このページから、次の4項目を抽出し、JSONのみを出力してください。
前置きや説明、コードブロックの記号は不要です。

- hours: 営業時間（平日/土日祝で異なる場合はその違いが分かるように記載する）
- closed_days: 定休日（「定休日なし」「年中無休」等の記載があればそれもそのまま採用する）
- station: 最寄り駅（複数ある場合はすべて記載する）
- line: 最寄り駅の路線名（複数ある場合はすべて記載する）

ルール:
- ページ内に明記されていない項目は null にする
- 推測や一般常識による補完はしない。テキストに書かれている内容だけを使う

形式:
{{"hours": "...", "closed_days": "...", "station": "...", "line": "..."}}

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


def info_url_for(gym):
    if gym["chain"] == "NOBOROCK":
        return gym["url"]
    if gym["chain"] == "D-BOULDERING":
        slug = gym["id"].split("-", 1)[1]
        return f"https://www.d-b-c.jp/top/{slug}/"
    if gym["chain"] == "pump":
        return gym["url"].split("wp-json")[0]
    raise ValueError(f"unknown chain: {gym['chain']}")


def extract_static_info(client, text):
    prompt = PROMPT_TEMPLATE.format(text=text)
    res = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    out = res.content[0].text.strip()
    out = re.sub(r"^```(?:json)?|```$", "", out, flags=re.M).strip()
    return json.loads(out)


def main():
    with open("gyms.json", encoding="utf-8") as f:
        gyms = json.load(f)

    client = anthropic.Anthropic()

    for gym in gyms:
        label = f"{gym['chain']} {gym['name']}"
        info_url = info_url_for(gym)
        info = {"hours": None, "closed_days": None, "station": None, "line": None}
        try:
            r = http_get(info_url)
            r.raise_for_status()
            text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
            info = extract_static_info(client, text)
        except Exception as e:
            print(f"[{label}] {info_url} 失敗: {e}")

        gym["hours"] = info.get("hours")
        gym["closed_days"] = info.get("closed_days")
        gym["station"] = info.get("station")
        gym["line"] = info.get("line")
        print(f"[{label}] hours={gym['hours']!r} closed_days={gym['closed_days']!r} "
              f"station={gym['station']!r} line={gym['line']!r}")

    with open("gyms.json", "w", encoding="utf-8") as f:
        json.dump(gyms, f, ensure_ascii=False, indent=2)

    print("\ngyms.json を更新しました。")


if __name__ == "__main__":
    main()
