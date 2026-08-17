import re, json, requests
from bs4 import BeautifulSoup
import anthropic

h = {"User-Agent": "gym-checker/0.1"}
API = "https://pump-climbing.com/gym/bpump/wp-json/wp/v2/posts?per_page=5"

posts = requests.get(API, headers=h, timeout=20).json()

for p in posts[:2]:
    pub = p["date"][:10]
    title = p["title"]["rendered"]
    body = BeautifulSoup(p["content"]["rendered"], "html.parser").get_text("\n", strip=True)

    print("=====", pub, title)
    print("本文長:", len(body))
    print(body[:800])

    prompt = f"""以下はクライミングジムのお知らせ記事です。
この記事の公開日は{pub}です。
タイトル: {title}

記事に書かれた予定を抽出し、JSONのみを出力してください。

ルール:
- 年の記載がない日付は、公開日から最も近い将来の日付として解釈する
- 休業・時間変更・セット・イベント・セット完了報告を対象とする
- 料金改定やキャンペーンなど、営業日程に関係しないものは除外する
- 該当がなければ events を空配列にする

形式:
{{"events": [{{"date": "YYYY-MM-DD", "type": "種別", "note": "補足"}}]}}

---
{body}
"""
    client = anthropic.Anthropic()
    res = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1500,
                                 messages=[{"role": "user", "content": prompt}])
    out = re.sub(r"^```(?:json)?|```$", "", res.content[0].text.strip(), flags=re.M).strip()
    print("--- 抽出 ---")
    print(json.dumps(json.loads(out), ensure_ascii=False, indent=2))