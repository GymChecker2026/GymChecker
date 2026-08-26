# -*- coding: utf-8 -*-
"""
ROCKY系列 営業カレンダー画像 -> manual_events.json 形式への変換
method: calendar_image

使い方:
    py rocky_calendar.py <画像パス> <gym_id>
    例) py rocky_calendar.py shinagawa_2026_07.png rocky-shinagawa

事前準備:
    py -m pip install jpholiday anthropic
    setx ANTHROPIC_API_KEY "sk-ant-..."   （初回のみ。以後は不要）

設計方針:
    - VLMは「見えているものを写す」だけ。分類はPython側のルールで行う
    - 凡例(色 -> 営業時間)を1回だけ読ませ、各日は色だけ答えさせて表を引く
    - 凡例に載っていない色は rocky_colors.json から引く
    - どちらにも無い色は営業状態が確定できないので公開せず pending に回す
"""

import base64
import calendar
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"

# 画像を何回読むか。検証が効いているので通常は1で足りる。
# 読み間違いが目立つようなら 3 に上げる（奇数にすること）
READS = 1

# 通常営業とみなす時間帯（注釈なし）。これと一致する日はレコードを作らない
NORMAL_HOURS = {"10:00-23:00", "10:00-21:00"}

HOLIDAY_HOURS = "10:00-21:00"
WEEKDAY_HOURS = "10:00-23:00"

WEEKDAY_FIX = {"FRY": "FRI", "THUR": "THU", "TUES": "TUE",
               "SUNDAY": "SUN", "SATURDAY": "SAT"}
WEEKDAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

COLOR_TABLE_PATH = Path("rocky_colors.json")


# ---------------------------------------------------------------- プロンプト

PROMPT = """このボルダリングジムの月間営業カレンダー画像を読み取ってください。

出力は次のJSONのみ。前置き・説明・コードフェンスは一切不要です。

{
  "store": "店舗名",
  "year": 2026,
  "month": 8,
  "legend": [
    {"color": "灰", "hours": "10:00-23:00"},
    {"color": "黄", "hours": "10:00-21:00"}
  ],
  "days": [
    {"d": 1, "w": "SAT", "c": "黄", "t": null}
  ]
}

【legend の作り方】
画像下部の「STORE HOURS」欄には、色見本と営業時間が対になって並んでいます。
1項目ずつ、その色見本の色を `color` に、隣に書かれた文字を `hours` に入れてください。
色と文字の対応を取り違えないよう、1つずつ順に確認してください。
欄に載っている項目を全て含めてください。載っていない色は含めないでください。

【days の作り方】
- その月の全日を含めてください。抜けや重複は許されません
- `d` は日付
- `w` は、そのセルが置かれている列の見出しをそのまま。綴りが FRY などでも見たまま書く。
  曜日を自分で計算しないでください
- `t` はセル内の文字をそのまま。改行は半角スペースに置き換える。文字が無ければ null。
  イラストやロゴに文字が含まれていれば、それも `t` に入れてください

【色の呼び方】
`c` と legend の `color` は、必ず次の12語のいずれかで書いてください。
他の言葉（黄緑、薄紫、オレンジなど）は使わず、最も近いものを選んでください。

  白 / 灰 / 黒 / 赤 / ピンク / 橙 / 黄 / 緑 / 水色 / 青 / 紫 / 茶

【読み取らないもの】
EVENT INFO 欄の説明文。ヘッダーのロゴマークの文字。
"""


# ---------------------------------------------------------------- 共通処理

def norm(s):
    """全角・波ダッシュ・空白の揺れを吸収する"""
    if not s:
        return ""
    s = str(s)
    s = s.replace("〜", "-").replace("~", "-").replace("～", "-").replace("–", "-")
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", s)


def plain_hours(s):
    """
    注釈の付いていない営業時間だけを "10:00-23:00" の形で返す。
    括弧の注釈が付いていれば通常営業ではないので、空文字を返す。
    """
    n = norm(s)
    return "" if "(" in n else n


def is_normal(hours):
    return plain_hours(hours) in NORMAL_HOURS


def is_holiday(y, m, d):
    """土日祝の判定。jpholiday が入っていれば祝日も見る"""
    if calendar.weekday(y, m, d) >= 5:
        return True
    try:
        import jpholiday
        return jpholiday.is_holiday(date(y, m, d))
    except ImportError:
        return False


def load_color_table():
    """
    rocky_colors.json から「凡例に載っていない色」の意味を読む。
    凡例が主、この表は補助。
    """
    if COLOR_TABLE_PATH.exists():
        data = json.loads(COLOR_TABLE_PATH.read_text(encoding="utf-8"))
        return data.get("colors", {})
    return {}


# ---------------------------------------------------------------- VLM呼び出し

def read_calendar(image_path):
    media = {
        ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".webp": "image/webp",
    }[Path(image_path).suffix.lower()]

    data = base64.b64encode(Path(image_path).read_bytes()).decode()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    res = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media, "data": data}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    raw = "".join(b.text for b in res.content if b.type == "text")
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  応答をJSONとして読めませんでした（{len(raw)}文字, {e}）")
        return None


def read_calendar_votes(image_path):
    """READS 回読む。2回以上なら日ごとに多数決を取る"""
    runs = []
    for i in range(READS):
        print(f"{i + 1}回目を読み取り中...")
        r = read_calendar(image_path)
        if r and r.get("days"):
            runs.append(r)

    if not runs:
        raise RuntimeError("読み取りが全て失敗しました")

    base = runs[0]

    for key in ("store", "year", "month"):
        vals = [r.get(key) for r in runs if r.get(key) is not None]
        if vals:
            base[key] = Counter(map(str, vals)).most_common(1)[0][0]
    base["year"], base["month"] = int(base["year"]), int(base["month"])

    legend = {}
    for r in runs:
        for item in r.get("legend", []):
            if isinstance(item, dict) and item.get("color"):
                legend.setdefault(item["color"], []).append(item.get("hours", ""))
    base["legend_map"] = {
        c: Counter(v).most_common(1)[0][0] for c, v in legend.items()
    }

    if len(runs) == 1:
        for d in base["days"]:
            d["unstable"] = False
        return base

    per_day = {}
    for r in runs:
        for d in r.get("days", []):
            per_day.setdefault(d.get("d"), []).append(d)

    need = len(runs) // 2 + 1
    days, unstable = [], 0
    for dn in sorted(k for k in per_day if isinstance(k, int)):
        cands = per_day[dn]
        merged, ok = {"d": dn}, True
        for field in ("w", "c"):
            counts = Counter(norm(x.get(field)) for x in cands)
            val, n = counts.most_common(1)[0]
            if n < need:
                ok = False
            for x in cands:
                if norm(x.get(field)) == val:
                    merged[field] = x.get(field)
                    break
        texts = [x.get("t") for x in cands if x.get("t")]
        merged["t"] = Counter(texts).most_common(1)[0][0] if texts else None
        merged["unstable"] = not ok
        if not ok:
            unstable += 1
        days.append(merged)

    base["days"] = days
    print(f"多数決が割れた日: {unstable} 件")
    return base


# ---------------------------------------------------------------- 検証

def validate(data):
    """1つでも落ちたら、その月は丸ごと採用しない"""
    errors = []
    y, m = data.get("year"), data.get("month")

    if not isinstance(y, int) or not isinstance(m, int):
        return ["year / month が読み取れていない"]

    today = date.today()
    span = (y - today.year) * 12 + (m - today.month)
    if not -1 <= span <= 3:
        errors.append(f"年月が想定範囲外: {y}年{m}月")

    days = data.get("days", [])
    last = calendar.monthrange(y, m)[1]
    got = sorted(d["d"] for d in days)
    if got != list(range(1, last + 1)):
        return [f"日付の抜けか重複（{len(got)}件 / 正 {last}件）"]

    for d in days:
        w = str(d.get("w", "")).upper()
        w = WEEKDAY_FIX.get(w, w)
        expected = WEEKDAY_ORDER[calendar.weekday(y, m, d["d"])]
        if w != expected:
            errors.append(f"{d['d']}日 曜日不一致（{d.get('w')} / 正 {expected}）")

    # 凡例の色対応が土日祝の運用と逆になっていないか
    lm = data.get("legend_map", {})
    weekend, weekday = Counter(), Counter()
    for d in days:
        h = plain_hours(lm.get(d.get("c"), ""))
        if h not in NORMAL_HOURS:
            continue
        (weekend if is_holiday(y, m, d["d"]) else weekday)[h] += 1
    if weekend and weekday:
        if (weekend.most_common(1)[0][0] == WEEKDAY_HOURS
                and weekday.most_common(1)[0][0] == HOLIDAY_HOURS):
            errors.append("凡例の色と営業時間の対応が逆の可能性")

    return errors


# ---------------------------------------------------------------- 種別判定

def classify(hours, text):
    """
    凡例の営業時間(hours)を主、セルのテキストを従として5種別に振り分ける。
    通常営業で特記なしなら None を返す。
    """
    h, t = norm(hours), norm(text)

    # 1) 休業が最優先
    if any(k in h for k in ("終日休業", "全日休業", "休館", "休業")):
        return "休業"
    if any(k in t for k in ("終日休業", "全日休業", "休館")):
        return "休業"

    # 2) 一部エリアが使えない（凡例の文言はOCRで揺れるので複数の手掛かりを見る）
    if any(k in h for k in ("外し", "外レ", "17時以降", "17時まで")):
        return "エリア制限"
    if "ホールド外し" in t:
        return "エリア制限"

    # 3) セット後にエリアが開放される
    if any(k in h for k in ("セットエリア", "セット替え", "19時から")):
        return "セット完了"

    # 4) 通常と違う営業時間
    if h and h != "UNKNOWN" and not is_normal(h):
        return "時間変更"

    # 5) 通常営業。セルに文字がある日だけ拾う
    if not t:
        return None
    if "セット" in t:
        return "セット完了"
    return "イベント"


def build_note(text, hours):
    parts = []
    if text:
        parts.append(re.sub(r"\s+", " ", str(text)).strip())
    if hours and norm(hours) != "UNKNOWN" and not is_normal(hours):
        parts.append(str(hours).strip())
    return " / ".join(parts) if parts else "詳細は公式サイトをご確認ください"


# ---------------------------------------------------------------- 変換

def convert(data, gym_id):
    """
    採用の基準は「営業状態が確定できたか」の一点。
    凡例 -> rocky_colors.json の順に色を引き、どちらにも無ければ保留。
    """
    events, pending = [], []
    lm = data.get("legend_map", {})
    table = load_color_table()
    y, m = data["year"], data["month"]
    today = date.today().isoformat()

    for d in data["days"]:
        day = d["d"]
        iso = f"{y:04d}-{m:02d}-{day:02d}"
        text, color = d.get("t"), d.get("c")

        # 凡例が主、対応表は補助
        hours = lm.get(color) or table.get(color, "")

        def hold(reason):
            pending.append({"gym_id": gym_id, "date": iso,
                            "reason": reason, "raw": d, "hours": hours})

        # 1) 複数回読んで色が割れた日は、営業状態が確定していない
        if d.get("unstable"):
            hold("読み取りが安定しなかった")
            continue

        # 2) 凡例にも対応表にも無い色は営業状態が分からない
        if not hours:
            hold(f"色 '{color}' が凡例にも rocky_colors.json にも無い")
            continue

        # 3) 土日祝なのに平日の営業時間なら読み間違いを疑い、補正する
        #    （逆方向は金曜短縮などの運用がありうるので補正しない）
        if plain_hours(hours) == WEEKDAY_HOURS and is_holiday(y, m, day):
            hours = HOLIDAY_HOURS

        t = classify(hours, text)
        if t is None:
            continue  # 通常営業で特記なし

        events.append({
            "gym_id": gym_id,
            "date": iso,
            "type": t,
            "note": build_note(text, hours),
            "source_url": None,
            "published": today,
        })

    return events, pending


# ---------------------------------------------------------------- 実行

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    image_path, gym_id = sys.argv[1], sys.argv[2]

    data = read_calendar_votes(image_path)

    print("\n--- 凡例（色 -> 営業時間） ---")
    for c, h in data.get("legend_map", {}).items():
        print(f"  {c} : {h}")

    errors = validate(data)
    if errors:
        print("\n=== 検証に失敗。この月は採用しません ===")
        for e in errors:
            print(" -", e)
        sys.exit(2)

    events, pending = convert(data, gym_id)

    print(f"\n=== {data['store']} {data['year']}年{data['month']}月 ===")
    print(f"採用 {len(events)}件 / 保留 {len(pending)}件\n")
    print("--- events（manual_events.json に貼る） ---")
    print(json.dumps(events, ensure_ascii=False, indent=2))

    if pending:
        print("\n--- pending（目視で確認する） ---")
        for p in pending:
            print(f"  {p['date']}  {p['reason']}")
            print(f"            t={p['raw'].get('t')!r} c={p['raw'].get('c')!r}")


if __name__ == "__main__":
    main()
