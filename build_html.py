import json
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

with open("display.json", encoding="utf-8") as f:
    gyms = json.load(f)

today = datetime.now(JST).date()

# <script> タグの中に安全に埋め込むためのエスケープ。
# データ取得部分は将来 fetch("display.json") 等に差し替える想定で、
# 埋め込みJSONはその暫定的な代替に過ぎない。
gyms_json = json.dumps(gyms, ensure_ascii=False).replace("</", "<\\/")

# Heroicons v2 (24px, outline/solid) を直接埋め込む。外部読み込みは行わない。
ICONS = {
    "star_outline": '<svg class="icon-outline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" /></svg>',
    "star_solid": '<svg class="icon-solid" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006Z" clip-rule="evenodd" /></svg>',
    "search_outline": '<svg class="icon-outline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>',
    "search_solid": '<svg class="icon-solid" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z" clip-rule="evenodd" /></svg>',
    "cog_outline": '<svg class="icon-outline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a7.775 7.775 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>',
    "cog_solid": '<svg class="icon-solid" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z" clip-rule="evenodd" /></svg>',
    "external_link_outline": '<svg class="icon-outline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>',
}

html_doc = f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ジムチェッカー</title>
<style>
:root {{
  --bg: #ffffff;
  --surface: #ffffff;
  --surface-2: #eef1f7;
  --ink: #1b2036;
  --ink-dim: #5b6a8c;
  --line: #dbe1ee;
  --accent: #1c3177;
  --accent-ink: #ffffff;
  --accent-tint: #d3ddf4;

  --type-closed: #c0392b;
  --type-hours: #a85f18;
  --type-area: #7d5ba6;
  --type-set: #217d47;
  --type-event: #187a89;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #10131f;
    --surface: #1a2036;
    --surface-2: #212843;
    --ink: #eef1f8;
    --ink-dim: #96a1c4;
    --line: #2c3452;
    --accent: #6c86d6;
    --accent-ink: #10131f;
    --accent-tint: #232a4a;

    --type-closed: #e0685c;
    --type-hours: #dba05a;
    --type-area: #a687d1;
    --type-set: #5cc98a;
    --type-event: #4dbdd1;
  }}
}}

:root[data-theme="dark"] {{
  --bg: #10131f;
  --surface: #1a2036;
  --surface-2: #212843;
  --ink: #eef1f8;
  --ink-dim: #96a1c4;
  --line: #2c3452;
  --accent: #6c86d6;
  --accent-ink: #10131f;
  --accent-tint: #232a4a;

  --type-closed: #e0685c;
  --type-hours: #dba05a;
  --type-area: #a687d1;
  --type-set: #5cc98a;
  --type-event: #4dbdd1;
}}

* {{ box-sizing: border-box; }}

html {{
  overflow-y: scroll;
  scrollbar-gutter: stable;
}}

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
  padding: 0 0 6.5rem;
  min-height: 100vh;
}}

.masthead {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  padding: 1.1rem 1.25rem 0.9rem;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}}

.masthead h1 {{
  margin: 0;
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  text-wrap: balance;
}}

.menu-wrap {{
  position: relative;
  flex: none;
}}

.menu-wrap[hidden] {{ display: none; }}

.menu-btn {{
  width: 2.1rem;
  height: 2.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink-dim);
  font-size: 1.2rem;
  line-height: 1;
  font-family: inherit;
  cursor: pointer;
}}

.menu-btn:hover,
.menu-btn:focus-visible {{
  border-color: var(--accent);
  color: var(--accent);
  outline: none;
}}

.menu-popover {{
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  z-index: 30;
  min-width: 11rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  padding: 0.4rem;
}}

.menu-popover[hidden] {{ display: none; }}

.menu-label {{
  margin: 0.35rem 0.6rem 0.2rem;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--ink-dim);
}}

.menu-item {{
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.6rem;
  border: none;
  background: none;
  border-radius: 8px;
  font-size: 0.85rem;
  font-family: inherit;
  color: var(--ink);
  cursor: pointer;
}}

.menu-item:hover,
.menu-item:focus-visible {{
  background: var(--surface-2);
  outline: none;
}}

.menu-item.active {{
  color: var(--accent);
  font-weight: 700;
}}

.menu-item.active::after {{
  content: " \\2713";
}}

.menu-divider {{
  height: 1px;
  background: var(--line);
  margin: 0.4rem 0.2rem;
}}

.menu-item-danger {{
  color: var(--type-closed);
}}

.settings-note {{
  margin: 3.5rem 1.25rem;
  text-align: center;
  color: var(--ink-dim);
  font-size: 0.9rem;
  line-height: 1.6;
}}

.tab-panel[hidden] {{ display: none; }}

.search-bar {{
  padding: 1rem 1.25rem 0;
}}

.search-bar input {{
  width: 100%;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  font-size: 0.9rem;
  font-family: inherit;
}}

.search-bar input:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}}

.chain-filter {{
  display: flex;
  gap: 0.4rem;
  padding: 0.75rem 1.25rem 0;
  overflow-x: auto;
}}

.chain-btn {{
  flex: none;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink-dim);
  font-size: 0.78rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
}}

.chain-btn.active {{
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-ink);
}}

.empty-state {{
  margin: 3.5rem 1.25rem;
  text-align: center;
  color: var(--ink-dim);
  font-size: 0.9rem;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.9rem;
}}

.empty-state p {{
  margin: 0;
}}

.empty-state-btn {{
  padding: 0.6rem 1.4rem;
  border-radius: 999px;
  border: none;
  background: var(--accent);
  color: var(--accent-ink);
  font-size: 0.85rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
}}

.empty-state-btn:hover,
.empty-state-btn:focus-visible {{
  opacity: 0.9;
  outline: none;
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}}

.card-head h2 {{
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}}

.star-btn {{
  flex: none;
  width: 2.1rem;
  height: 2.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--ink-dim);
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}}

.star-btn.active {{
  border-color: var(--accent);
  background: var(--accent-tint);
  color: var(--accent);
}}

.star-icon {{
  width: 20px;
  height: 20px;
  display: block;
}}

.star-icon svg {{
  width: 20px;
  height: 20px;
  display: block;
}}

.star-icon .icon-solid {{ display: none; }}
.star-btn.active .star-icon .icon-outline {{ display: none; }}
.star-btn.active .star-icon .icon-solid {{ display: block; }}

.hours-block {{
  margin: 0 0 0.7rem;
  background: var(--surface-2);
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
}}

.hours-heading {{
  margin: 0 0 0.45rem;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--ink-dim);
}}

.hours-list {{
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 0.9rem;
  row-gap: 0.35rem;
}}

.hours-list dt {{
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
}}

.hours-list dd {{
  margin: 0;
  font-size: 0.82rem;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}}

.hours-note {{
  margin: 0.5rem 0 0;
  font-size: 0.7rem;
  line-height: 1.5;
  color: var(--ink-dim);
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

.last-changed {{
  margin: 0.2rem 0 0;
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

a.event-row:hover,
a.event-row:focus-visible {{
  border-color: var(--accent);
  background: var(--surface-2);
  outline: none;
}}

.event-row.is-past {{
  opacity: 0.55;
  border-style: dashed;
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
  width: 16px;
  height: 16px;
  display: block;
}}

.event-arrow svg {{
  width: 16px;
  height: 16px;
  display: block;
}}

footer.note {{
  padding: 1.5rem 1.25rem 0;
  text-align: center;
}}

footer.note .generated {{
  margin: 0;
  font-size: 0.72rem;
  color: var(--ink-dim);
}}

footer.note .disclaimer {{
  margin: 0.4rem 0 0;
  font-size: 0.66rem;
  line-height: 1.5;
  color: var(--ink-dim);
  opacity: 0.8;
}}

footer.note .contact {{
  margin: 0.6rem 0 0;
  font-size: 0.66rem;
  line-height: 1.6;
  color: var(--ink-dim);
  opacity: 0.8;
  overflow-wrap: break-word;
}}

footer.note .contact a {{
  color: var(--accent);
}}

.tabbar {{
  position: fixed;
  left: 50%;
  bottom: 0;
  width: 100%;
  max-width: 560px;
  transform: translateX(-50%);
  z-index: 20;
  display: flex;
  background: var(--surface);
  border-top: 1px solid var(--line);
  padding-bottom: env(safe-area-inset-bottom, 0);
}}

.tab-btn {{
  flex: 1;
  min-height: 72px;
  border: none;
  background: none;
  padding: 0.55rem 0.3rem 0.3rem;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  font-family: inherit;
  cursor: pointer;
}}

.tab-pill {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 700;
  color: var(--ink-dim);
  transition: background-color 0.15s ease, color 0.15s ease;
}}

.tab-btn.active .tab-pill {{
  background: var(--accent-tint);
  color: var(--accent);
}}

.tab-icon {{
  width: 24px;
  height: 24px;
  display: block;
}}

.tab-icon svg {{
  width: 24px;
  height: 24px;
  display: block;
}}

.tab-icon .icon-solid {{ display: none; }}
.tab-btn.active .tab-icon .icon-outline {{ display: none; }}
.tab-btn.active .tab-icon .icon-solid {{ display: block; }}

/* 検索アイコンはoutline/solidの塗り面積差により、solid切替時に一回り小さく見えるため補正する。 */
.tab-btn[data-tab="search"] .tab-icon .icon-solid {{
  transform: scale(1.15);
  transform-origin: 50% 50%;
}}

.tab-label {{
  line-height: 1;
}}

@media (max-width: 360px) {{
  .info-grid {{ grid-template-columns: 1fr; }}
  .event-row {{ grid-template-columns: auto auto 1fr; }}
  .event-arrow {{ display: none; }}
}}
</style>

<div class="page">
  <header class="masthead">
    <h1 id="tab-title">マイリスト</h1>
    <div class="menu-wrap" id="mylist-menu-wrap">
      <button type="button" id="mylist-menu-btn" class="menu-btn" aria-haspopup="true" aria-expanded="false" aria-label="メニュー">&#8943;</button>
      <div class="menu-popover" id="mylist-menu" hidden></div>
    </div>
  </header>

  <main id="tab-mylist" class="tab-panel"></main>

  <main id="tab-search" class="tab-panel" hidden>
    <div class="search-bar">
      <input id="search-input" type="search" placeholder="ジムを検索" autocomplete="off">
    </div>
    <div id="chain-filter" class="chain-filter"></div>
    <div id="search-cards" class="cards"></div>
  </main>

  <main id="tab-settings" class="tab-panel" hidden>
    <p class="settings-note">通知設定は今後追加予定です。</p>
  </main>
</div>

<nav class="tabbar">
  <button type="button" class="tab-btn active" data-tab="mylist">
    <span class="tab-pill">
      <span class="tab-icon">{ICONS["star_outline"]}{ICONS["star_solid"]}</span>
      <span class="tab-label">マイリスト</span>
    </span>
  </button>
  <button type="button" class="tab-btn" data-tab="search">
    <span class="tab-pill">
      <span class="tab-icon">{ICONS["search_outline"]}{ICONS["search_solid"]}</span>
      <span class="tab-label">検索</span>
    </span>
  </button>
  <button type="button" class="tab-btn" data-tab="settings">
    <span class="tab-pill">
      <span class="tab-icon">{ICONS["cog_outline"]}{ICONS["cog_solid"]}</span>
      <span class="tab-label">設定</span>
    </span>
  </button>
</nav>

<script>
(function () {{
  "use strict";

  // =========================================================
  // データ取得層
  // 今は display.json の内容を埋め込んだものを返すだけだが、
  // React Native 移植時はここを実際の fetch/AsyncStorage 読み込みに
  // 差し替えれば、下の描画層はそのまま流用できる想定。
  // =========================================================
  var DISPLAY_DATA = {gyms_json};
  var GENERATED_AT = {json.dumps(today.isoformat())};
  var STAR_OUTLINE_SVG = {json.dumps(ICONS["star_outline"])};
  var STAR_SOLID_SVG = {json.dumps(ICONS["star_solid"])};
  var EXTERNAL_LINK_SVG = {json.dumps(ICONS["external_link_outline"])};
  var FAVORITES_KEY = "gymchecker.favorites";
  var SORT_ORDER_KEY = "gymchecker.sortOrder";

  function fetchGyms() {{
    return DISPLAY_DATA;
  }}

  function getSortOrder() {{
    var v = localStorage.getItem(SORT_ORDER_KEY);
    return v === "name" ? "name" : "added";
  }}

  function setSortOrder(order) {{
    localStorage.setItem(SORT_ORDER_KEY, order);
  }}

  function getFavoriteIds() {{
    try {{
      var raw = localStorage.getItem(FAVORITES_KEY);
      var ids = raw ? JSON.parse(raw) : [];
      return Array.isArray(ids) ? ids : [];
    }} catch (e) {{
      return [];
    }}
  }}

  function setFavoriteIds(ids) {{
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(ids));
  }}

  function isFavorite(gymId) {{
    return getFavoriteIds().indexOf(gymId) !== -1;
  }}

  function toggleFavorite(gymId) {{
    var ids = getFavoriteIds();
    var idx = ids.indexOf(gymId);
    if (idx === -1) {{
      ids.push(gymId);
    }} else {{
      ids.splice(idx, 1);
    }}
    setFavoriteIds(ids);
  }}

  // =========================================================
  // 共通ユーティリティ
  // =========================================================
  var ESCAPE_MAP = {{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }};
  function escapeHtml(value) {{
    return String(value).replace(/[&<>"']/g, function (c) {{ return ESCAPE_MAP[c]; }});
  }}

  var TYPE_CLASS = {{
    "休業": "type-closed",
    "時間変更": "type-hours",
    "エリア制限": "type-area",
    "セット完了": "type-set",
    "イベント": "type-event"
  }};

  function fmtDate(iso) {{
    var parts = iso.split("-");
    return parseInt(parts[1], 10) + "/" + parseInt(parts[2], 10);
  }}

  function fmtFetchedAt(iso) {{
    if (!iso) return null;
    var dt = new Date(iso);
    var hh = String(dt.getHours()).padStart(2, "0");
    var mm = String(dt.getMinutes()).padStart(2, "0");
    return (dt.getMonth() + 1) + "/" + dt.getDate() + " " + hh + ":" + mm + " 取得";
  }}

  function fmtLastChangedAt(iso) {{
    if (!iso) return null;
    var dt = new Date(iso);
    return "ページ最終更新: " + (dt.getMonth() + 1) + "月" + dt.getDate() + "日";
  }}

  function fieldHtml(value) {{
    if (value === null || value === undefined || value === "") {{
      return '<span class="no-data">No Data</span>';
    }}
    return escapeHtml(value);
  }}

  function hoursBlockHtml(gym) {{
    var hours = gym.hours || [];
    var rowsHtml;
    if (hours.length === 0) {{
      rowsHtml = '<dt>&nbsp;</dt><dd><span class="no-data">No Data</span></dd>';
    }} else {{
      rowsHtml = hours.map(function (h) {{
        return '<dt>' + escapeHtml(h.label) + '</dt><dd>' + escapeHtml(h.value) + '</dd>';
      }}).join("");
    }}
    var noteHtml = gym.hours_note ? '<p class="hours-note">※' + escapeHtml(gym.hours_note) + '</p>' : "";
    return '<div class="hours-block">' +
      '<p class="hours-heading">営業時間</p>' +
      '<dl class="hours-list">' + rowsHtml + '</dl>' +
      noteHtml +
      '</div>';
  }}

  // =========================================================
  // 描画層（カード単位のHTML組み立て）
  // React Native移植時はここをコンポーネントに置き換える。
  // =========================================================
  function eventRowHtml(ev) {{
    var typeClass = TYPE_CLASS[ev.type] || "type-event";
    var pastClass = ev.date < GENERATED_AT ? " is-past" : "";
    var inner = '<span class="event-date">' + fmtDate(ev.date) + '</span>' +
      '<span class="event-type ' + typeClass + '">' + escapeHtml(ev.type || "") + '</span>' +
      '<span class="event-note">' + escapeHtml(ev.note || "") + '</span>';
    if (ev.source_url) {{
      return '<a class="event-row' + pastClass + '" href="' + escapeHtml(ev.source_url) + '" target="_blank" rel="noopener">' +
        inner +
        '<span class="event-arrow">' + EXTERNAL_LINK_SVG + '</span>' +
        '</a>';
    }}
    return '<div class="event-row' + pastClass + '">' +
      inner +
      '<span class="event-arrow"></span>' +
      '</div>';
  }}

  // 過去1件（直近）＋今後2件（近い順）を選び、日付の古い順に並べる。
  // 過去が無ければ今後を3件、今後が無ければ過去1件のみ（埋め合わせしない）。
  function selectDisplayEvents(events) {{
    var past = events.filter(function (e) {{ return e.date < GENERATED_AT; }});
    var future = events.filter(function (e) {{ return e.date >= GENERATED_AT; }});
    past.sort(function (a, b) {{ return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0); }});
    future.sort(function (a, b) {{ return a.date < b.date ? -1 : (a.date > b.date ? 1 : 0); }});

    var selectedPast = past.slice(0, 1);
    var selectedFuture = future.slice(0, selectedPast.length === 0 ? 3 : 2);
    var combined = selectedPast.concat(selectedFuture);
    combined.sort(function (a, b) {{ return a.date < b.date ? -1 : (a.date > b.date ? 1 : 0); }});
    return combined;
  }}

  function eventsSectionHtml(gym) {{
    if (!gym.enabled || gym.fetch_status !== "success") {{
      return '<p class="no-events">予定情報を取得できていません</p>';
    }}
    var selected = selectDisplayEvents(gym.events || []);
    if (selected.length === 0) {{
      return '<p class="no-events">直近14日間の予定はありません</p>';
    }}
    return selected.map(eventRowHtml).join("");
  }}

  function linkRowHtml(gym) {{
    var links = [];
    if (gym.official_url) {{
      links.push('<a class="site-link" href="' + escapeHtml(gym.official_url) + '" target="_blank" rel="noopener">公式サイト</a>');
    }}
    if (gym.instagram_url) {{
      links.push('<a class="site-link" href="' + escapeHtml(gym.instagram_url) + '" target="_blank" rel="noopener">Instagram</a>');
    }}
    if (links.length === 0) return "";
    return '<div class="link-row">' + links.join("") + '</div>';
  }}

  function gymCardHtml(gym) {{
    var displayName = gym.display_name || gym.name;
    var fav = isFavorite(gym.gym_id);
    var noteHtml = gym.data_note ? '<p class="data-note">' + escapeHtml(gym.data_note) + '</p>' : "";
    var fetchedLabel = fmtFetchedAt(gym.fetched_at);
    var fetchedHtml = fetchedLabel ? '<p class="fetched-at">' + escapeHtml(fetchedLabel) + '</p>' : "";
    var lastChangedLabel = fmtLastChangedAt(gym.last_changed_at);
    var lastChangedHtml = lastChangedLabel ? '<p class="last-changed">' + escapeHtml(lastChangedLabel) + '</p>' : "";

    return '<article class="card" data-gym-id="' + escapeHtml(gym.gym_id) + '">' +
      '<header class="card-head">' +
        '<h2>' + escapeHtml(displayName) + '</h2>' +
        '<button type="button" class="star-btn' + (fav ? " active" : "") + '" data-fav-toggle="' + escapeHtml(gym.gym_id) + '" aria-pressed="' + fav + '" aria-label="マイリストに追加・削除"><span class="star-icon">' + STAR_OUTLINE_SVG + STAR_SOLID_SVG + '</span></button>' +
      '</header>' +
      hoursBlockHtml(gym) +
      '<dl class="info-grid">' +
        '<div class="info-item"><dt>最寄り駅</dt><dd>' + fieldHtml(gym.station) + '</dd></div>' +
        '<div class="info-item"><dt>路線</dt><dd>' + fieldHtml(gym.line) + '</dd></div>' +
      '</dl>' +
      '<div class="events">' + eventsSectionHtml(gym) + '</div>' +
      noteHtml +
      linkRowHtml(gym) +
      lastChangedHtml +
      fetchedHtml +
      '</article>';
  }}

  // =========================================================
  // 描画層（タブ単位）
  // =========================================================
  function renderMyListTab() {{
    var container = document.getElementById("tab-mylist");
    var gyms = fetchGyms();
    var byId = {{}};
    gyms.forEach(function (g) {{ byId[g.gym_id] = g; }});
    var ids = getFavoriteIds();
    var list = ids.map(function (id) {{ return byId[id]; }}).filter(Boolean);

    if (getSortOrder() === "name") {{
      list = list.slice().sort(function (a, b) {{
        var an = a.display_name || a.name;
        var bn = b.display_name || b.name;
        return an.localeCompare(bn, "ja");
      }});
    }}

    var bodyHtml;
    if (list.length === 0) {{
      bodyHtml = '<div class="empty-state">' +
        '<p>検索タブからジムを追加してください</p>' +
        '<button type="button" class="empty-state-btn" data-goto-tab="search">検索タブへ</button>' +
        '</div>';
    }} else {{
      bodyHtml = '<div class="cards">' + list.map(gymCardHtml).join("") + '</div>';
    }}

    container.innerHTML = bodyHtml +
      '<footer class="note">' +
        '<p class="generated">' + escapeHtml(GENERATED_AT) + ' 時点</p>' +
        '<p class="disclaimer">本アプリは非公式のツールであり、掲載各ジムとは無関係です。掲載情報は自動収集したものであり、正確性・網羅性を保証しません。ご利用前に必ず公式サイトでご確認ください。</p>' +
        '<p class="contact">' +
          '<a href="https://docs.google.com/forms/d/e/1FAIpQLSdtbwAd35cDHh-LynHptFWlsBzafz5Qf6hATgnquO-pVquGgw/viewform" target="_blank" rel="noopener">お問い合わせ・情報の誤りのご報告</a><br>' +
          '本サイト・アプリは非公式です。掲載内容についてのご連絡は <a href="mailto:npplun995@gmail.com">npplun995@gmail.com</a> までお願いいたします。' +
        '</p>' +
      '</footer>';
  }}

  var CHAIN_OPTIONS = [
    {{ key: "all", label: "すべて" }},
    {{ key: "NOBOROCK", label: "ノボロック" }},
    {{ key: "D-BOULDERING", label: "Dボルダリング" }},
    {{ key: "pump", label: "pump" }}
  ];

  var searchState = {{ query: "", chain: "all" }};

  function renderChainFilter() {{
    var container = document.getElementById("chain-filter");
    container.innerHTML = CHAIN_OPTIONS.map(function (c) {{
      var active = c.key === searchState.chain ? " active" : "";
      return '<button type="button" class="chain-btn' + active + '" data-chain="' + c.key + '">' + c.label + '</button>';
    }}).join("");
  }}

  function renderSearchCards() {{
    var container = document.getElementById("search-cards");
    var gyms = fetchGyms();
    var q = searchState.query.trim().toLowerCase();
    var filtered = gyms.filter(function (g) {{
      if (searchState.chain !== "all" && g.chain !== searchState.chain) return false;
      if (!q) return true;
      var name = (g.display_name || g.name || "").toLowerCase();
      var station = (g.station || "").toLowerCase();
      return name.indexOf(q) !== -1 || station.indexOf(q) !== -1;
    }});
    container.innerHTML = filtered.map(gymCardHtml).join("");
  }}

  function renderSearchTab() {{
    renderChainFilter();
    renderSearchCards();
  }}

  function renderMylistMenu() {{
    var menu = document.getElementById("mylist-menu");
    var sort = getSortOrder();
    menu.innerHTML =
      '<p class="menu-label">並び順</p>' +
      '<button type="button" class="menu-item' + (sort === "added" ? " active" : "") + '" data-sort="added">追加順</button>' +
      '<button type="button" class="menu-item' + (sort === "name" ? " active" : "") + '" data-sort="name">名前順</button>' +
      '<div class="menu-divider"></div>' +
      '<button type="button" class="menu-item menu-item-danger" id="mylist-clear-btn">マイリストを全削除</button>';
  }}

  function toggleMylistMenu(force) {{
    var menu = document.getElementById("mylist-menu");
    var btn = document.getElementById("mylist-menu-btn");
    var show = typeof force === "boolean" ? force : menu.hidden;
    if (show) renderMylistMenu();
    menu.hidden = !show;
    btn.setAttribute("aria-expanded", String(show));
  }}

  // =========================================================
  // 状態管理・イベント配線（コントローラ）
  // =========================================================
  var TAB_LABELS = {{ mylist: "マイリスト", search: "検索", settings: "設定" }};

  function switchTab(tab) {{
    document.getElementById("tab-mylist").hidden = tab !== "mylist";
    document.getElementById("tab-search").hidden = tab !== "search";
    document.getElementById("tab-settings").hidden = tab !== "settings";
    document.querySelectorAll(".tab-btn").forEach(function (btn) {{
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tab);
    }});
    document.getElementById("tab-title").textContent = TAB_LABELS[tab] || "";
    document.getElementById("mylist-menu-wrap").hidden = tab !== "mylist";
    if (tab !== "mylist") toggleMylistMenu(false);
    if (tab === "mylist") renderMyListTab();
  }}

  document.addEventListener("click", function (e) {{
    var tabBtn = e.target.closest(".tab-btn");
    if (tabBtn) {{
      switchTab(tabBtn.getAttribute("data-tab"));
      return;
    }}
    var gotoTabBtn = e.target.closest("[data-goto-tab]");
    if (gotoTabBtn) {{
      switchTab(gotoTabBtn.getAttribute("data-goto-tab"));
      return;
    }}
    var chainBtn = e.target.closest(".chain-btn");
    if (chainBtn) {{
      searchState.chain = chainBtn.getAttribute("data-chain");
      renderSearchTab();
      return;
    }}
    var favBtn = e.target.closest("[data-fav-toggle]");
    if (favBtn) {{
      toggleFavorite(favBtn.getAttribute("data-fav-toggle"));
      renderMyListTab();
      renderSearchCards();
      return;
    }}
    var menuBtn = e.target.closest("#mylist-menu-btn");
    if (menuBtn) {{
      toggleMylistMenu();
      return;
    }}
    var sortItem = e.target.closest(".menu-item[data-sort]");
    if (sortItem) {{
      setSortOrder(sortItem.getAttribute("data-sort"));
      toggleMylistMenu(false);
      renderMyListTab();
      return;
    }}
    var clearBtn = e.target.closest("#mylist-clear-btn");
    if (clearBtn) {{
      toggleMylistMenu(false);
      if (window.confirm("マイリストを全て削除しますか？")) {{
        setFavoriteIds([]);
        renderMyListTab();
        renderSearchCards();
      }}
      return;
    }}
    var insideMenu = e.target.closest("#mylist-menu-wrap");
    if (!insideMenu) {{
      var menu = document.getElementById("mylist-menu");
      if (!menu.hidden) toggleMylistMenu(false);
    }}
  }});

  document.addEventListener("input", function (e) {{
    if (e.target && e.target.id === "search-input") {{
      searchState.query = e.target.value;
      renderSearchCards();
    }}
  }});

  // =========================================================
  // 初期描画
  // マイリストが空なら検索タブ、1件以上あればマイリストタブを表示する。
  // =========================================================
  switchTab(getFavoriteIds().length > 0 ? "mylist" : "search");
  renderSearchTab();
}})();
</script>
'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_doc)

print(f"index.html を生成しました（{len(gyms)}店舗）。")
