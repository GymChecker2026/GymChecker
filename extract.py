import json, re
import requests
from bs4 import BeautifulSoup
import anthropic

URL = "https://noborock-climbing.com/program/新宿店/"
TODAY = "2026-08-15"

r = requests.get(URL, headers={"User-Agent": "gym-checker/0.1"}, timeout=20)
text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
print("取得文字数:", len(text))

prompt = f"""以下はクライミングジムの店舗ページのテキストです。
今日は{TODAY}です。

お知らせに書かれている予定を抽出し、JSONのみを出力してください。
前置きや説明、コードブロックの記号は不要です。

ルール:
- 年の記載がない日付は、曜日が一致する年を採用する
- 過去の日付も含める
- 該当がなければ events を空配列にする
- 「セット完了」「リニューアル」などの完了報告も、日付付きなら含める

形式:
{{"events": [{{"date": "YYYY-MM-DD", "type": "種別", "note": "補足"}}]}}

種別は内容に応じて自由に判断してください。

---
{text}
"""

client = anthropic.Anthropic()
res = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}],
)

out = res.content[0].text.strip()
out = re.sub(r"^```(?:json)?|```$", "", out, flags=re.M).strip()

print("----- 生出力 -----")
print(out)
print("----- パース -----")
print(json.dumps(json.loads(out), ensure_ascii=False, indent=2))