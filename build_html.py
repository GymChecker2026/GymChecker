import json
from datetime import date, datetime, timedelta
from html import escape

with open("display.json", encoding="utf-8") as f:
    gyms = json.load(f)

today = date.today()
window_end = today + timedelta(days=14)

TYPE_CLASS = {
    "休業": "type-closed",
    "時間変更": "type-hours",
    "エリア制限": "type-area",
    "セット完了": "type-set",
    "イベント": "type-event",
}


def field(value):
    if value is None or value == "":
        return '<span class="no-data">No Data</span>'
    return escape(value)


def fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{int(m)}/{int(d)}"


def event_row(ev):
    type_class = TYPE_CLASS.get(ev.get("type"), "type-event")
    note = escape(ev.get("note") or "")
    type_label = escape(ev.get("type") or "")
    url = ev.get("source_url")
    d = fmt_date(ev["date"])
    href = escape(url) if url else "#"
    return f'''<a class="event-row" href="{href}" target="_blank" rel="noopener">
        <span class="event-date">{d}</span>
        <span class="event-type {type_class}">{type_label}</span>
        <span class="event-note">{note}</span>
        <span class="event-arrow" aria-hidden="true">&#8594;</span>
      </a>'''


def events_section(g):
    if not g.get("enabled", True) or g.get("fetch_status") != "success":
        return '<p class="no-events">予定情報を取得できていません</p>'

    events_html = "".join(event_row(e) for e in g["events"])
    if not events_html:
        return '<p class="no-events">直近14日間の予定はありません</p>'
    return events_html


def fmt_fetched_at(iso):
    if not iso:
        return None
    dt = datetime.fromisoformat(iso)
    return f"{dt.month}/{dt.day} {dt.hour:02d}:{dt.minute:02d} 取得"


def link_row(g):
    links = []
    if g.get("official_url"):
        links.append(f'<a class="site-link" href="{escape(g["official_url"])}" target="_blank" rel="noopener">公式サイト</a>')
    if g.get("instagram_url"):
        links.append(f'<a class="site-link" href="{escape(g["instagram_url"])}" target="_blank" rel="noopener">Instagram</a>')
    if not links:
        return ""
    return f'<div class="link-row">{"".join(links)}</div>'


def gym_card(g):
    events_html = events_section(g)
    display_name = g.get("display_name") or g["name"]
    data_note = g.get("data_note")
    note_html = f'<p class="data-note">{escape(data_note)}</p>' if data_note else ""
    fetched_label = fmt_fetched_at(g.get("fetched_at"))
    fetched_html = f'<p class="fetched-at">{escape(fetched_label)}</p>' if fetched_label else ""

    return f'''<article class="card">
      <header class="card-head">
        <h2>{escape(display_name)}</h2>
      </header>
      <dl class="info-grid">
        <div class="info-item"><dt>営業時間</dt><dd>{field(g.get("hours"))}</dd></div>
        <div class="info-item"><dt>定休日</dt><dd>{field(g.get("closed_days"))}</dd></div>
        <div class="info-item"><dt>最寄り駅</dt><dd>{field(g.get("station"))}</dd></div>
        <div class="info-item"><dt>路線</dt><dd>{field(g.get("line"))}</dd></div>
      </dl>
      <div class="events">{events_html}</div>
      {note_html}
      {link_row(g)}
      {fetched_html}
    </article>'''


cards_html = "\n".join(gym_card(g) for g in gyms)
total_events = sum(len(g["events"]) for g in gyms)
date_range = f"{today.month}/{today.day} - {window_end.month}/{window_end.day}"

html_doc = f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ジムチェッカー</title>
<style>
:root {{
  --bg: #f3efe8;
  --surface: #ffffff;
  --surface-2: #faf7f2;
  --ink: #24211d;
  --ink-dim: #6b6459;
  --line: #e4ddd1;
  --accent: #d45e2a;
  --accent-ink: #ffffff;

  --type-closed: #b34a3e;
  --type-hours: #a5791f;
  --type-area: #3a6ea5;
  --type-set: #3e7d52;
  --type-event: #6b4e9e;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #1c1a17;
    --surface: #262320;
    --surface-2: #2d2a26;
    --ink: #f0ece4;
    --ink-dim: #a89f8f;
    --line: #3a3630;
    --accent: #ef814a;
    --accent-ink: #1c1a17;

    --type-closed: #e07b6f;
    --type-hours: #d4a94a;
    --type-area: #6fa0d8;
    --type-set: #6bb883;
    --type-event: #a084d1;
  }}
}}

:root[data-theme="dark"] {{
  --bg: #1c1a17;
  --surface: #262320;
  --surface-2: #2d2a26;
  --ink: #f0ece4;
  --ink-dim: #a89f8f;
  --line: #3a3630;
  --accent: #ef814a;
  --accent-ink: #1c1a17;

  --type-closed: #e07b6f;
  --type-hours: #d4a94a;
  --type-area: #6fa0d8;
  --type-set: #6bb883;
  --type-event: #a084d1;
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic UI", "Segoe UI", sans-serif;
  font-variant-numeric: tabular-nums;
  -webkit-text-size-adjust: 100%;
}}

.page {{
  max-width: 560px;
  margin: 0 auto;
  padding: 0 0 3rem;
}}

.masthead {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid var(--line);
}}

.masthead h1 {{
  margin: 0 0 0.35rem;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  text-wrap: balance;
}}

.masthead .summary {{
  margin: 0;
  color: var(--ink-dim);
  font-size: 0.875rem;
}}

.masthead .summary strong {{
  color: var(--ink);
  font-weight: 700;
}}

.cards {{
  padding: 1rem 1.25rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}}

.card {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1rem 1.1rem 1.1rem;
  overflow: hidden;
}}

.card-head {{
  margin-bottom: 0.75rem;
}}

.card-head h2 {{
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}}

.info-grid {{
  margin: 0 0 0.9rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem 0.75rem;
  background: var(--surface-2);
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
}}

.info-item dt {{
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--ink-dim);
  margin-bottom: 0.15rem;
}}

.info-item dd {{
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.4;
}}

.no-data {{
  color: var(--ink-dim);
  font-style: italic;
  font-size: 0.8rem;
}}

.events {{
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}}

.fetched-at {{
  margin: 0.6rem 0 0;
  font-size: 0.68rem;
  color: var(--ink-dim);
  text-align: right;
}}

.no-events {{
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: var(--ink-dim);
}}

.data-note {{
  margin: 0.6rem 0 0;
  padding: 0.55rem 0.7rem;
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--ink-dim);
  font-size: 0.76rem;
  line-height: 1.4;
}}

.link-row {{
  display: flex;
  gap: 0.5rem;
  margin-top: 0.8rem;
}}

.site-link {{
  flex: 1;
  text-align: center;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  border: 1px solid var(--line);
  color: var(--ink);
  text-decoration: none;
  font-size: 0.78rem;
  font-weight: 700;
  transition: border-color 0.15s ease, color 0.15s ease;
}}

.site-link:hover,
.site-link:focus-visible {{
  border-color: var(--accent);
  color: var(--accent);
  outline: none;
}}

.event-row {{
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.6rem;
  border-radius: 9px;
  text-decoration: none;
  color: inherit;
  border: 1px solid var(--line);
  transition: border-color 0.15s ease, background 0.15s ease;
}}

.event-row:hover,
.event-row:focus-visible {{
  border-color: var(--accent);
  background: var(--surface-2);
  outline: none;
}}

.event-date {{
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--ink-dim);
  min-width: 2.6em;
}}

.event-type {{
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  color: #fff;
  white-space: nowrap;
}}
.type-closed {{ background: var(--type-closed); }}
.type-hours  {{ background: var(--type-hours); }}
.type-area   {{ background: var(--type-area); }}
.type-set    {{ background: var(--type-set); }}
.type-event  {{ background: var(--type-event); }}

.event-note {{
  font-size: 0.82rem;
  line-height: 1.35;
  min-width: 0;
  overflow-wrap: break-word;
}}

.event-arrow {{
  color: var(--accent);
  font-size: 0.85rem;
}}

footer.note {{
  padding: 1.5rem 1.25rem 0;
  font-size: 0.72rem;
  color: var(--ink-dim);
  text-align: center;
}}

@media (max-width: 360px) {{
  .info-grid {{ grid-template-columns: 1fr; }}
  .event-row {{ grid-template-columns: auto auto 1fr; }}
  .event-arrow {{ display: none; }}
}}
</style>

<div class="page">
  <div class="masthead">
    <h1>ジムチェッカー</h1>
    <p class="summary"><strong>{len(gyms)}</strong> 店舗 &middot; <strong>{total_events}</strong> 件の予定 &middot; {date_range}</p>
  </div>
  <div class="cards">
{cards_html}
  </div>
  <footer class="note">display.json を元に生成 &middot; {today.isoformat()} 時点</footer>
</div>
'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_doc)

print(f"index.html を生成しました（{len(gyms)}店舗、イベント{total_events}件）。")
