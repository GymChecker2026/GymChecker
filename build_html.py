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
  --accent-tint: #fbe8dd;

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
    --accent-tint: #3a2a20;

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
  --accent-tint: #3a2a20;

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
  padding: 0 0 5rem;
  min-height: 100vh;
}}

.masthead {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  padding: 1.1rem 1.25rem 0.9rem;
  border-bottom: 1px solid var(--line);
}}

.masthead h1 {{
  margin: 0;
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  text-wrap: balance;
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
  font-size: 1.15rem;
  line-height: 1;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}}

.star-btn.active {{
  border-color: var(--accent);
  background: var(--accent-tint);
  color: var(--accent);
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
  border: none;
  background: none;
  padding: 0.7rem 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  font-family: inherit;
  color: var(--ink-dim);
  cursor: pointer;
}}

.tab-btn.active {{
  color: var(--accent);
}}

@media (max-width: 360px) {{
  .info-grid {{ grid-template-columns: 1fr; }}
  .event-row {{ grid-template-columns: auto auto 1fr; }}
  .event-arrow {{ display: none; }}
}}
</style>

<div class="page">
  <header class="masthead"><h1>ジムチェッカー</h1></header>

  <main id="tab-mylist" class="tab-panel"></main>

  <main id="tab-search" class="tab-panel" hidden>
    <div class="search-bar">
      <input id="search-input" type="search" placeholder="ジムを検索" autocomplete="off">
    </div>
    <div id="chain-filter" class="chain-filter"></div>
    <div id="search-cards" class="cards"></div>
  </main>
</div>

<nav class="tabbar">
  <button type="button" class="tab-btn active" data-tab="mylist">マイリスト</button>
  <button type="button" class="tab-btn" data-tab="search">検索</button>
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
  var FAVORITES_KEY = "gymchecker.favorites";

  function fetchGyms() {{
    return DISPLAY_DATA;
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

  function fieldHtml(value) {{
    if (value === null || value === undefined || value === "") {{
      return '<span class="no-data">No Data</span>';
    }}
    return escapeHtml(value);
  }}

  // =========================================================
  // 描画層（カード単位のHTML組み立て）
  // React Native移植時はここをコンポーネントに置き換える。
  // =========================================================
  function eventRowHtml(ev) {{
    var typeClass = TYPE_CLASS[ev.type] || "type-event";
    var href = ev.source_url ? escapeHtml(ev.source_url) : "#";
    return '<a class="event-row" href="' + href + '" target="_blank" rel="noopener">' +
      '<span class="event-date">' + fmtDate(ev.date) + '</span>' +
      '<span class="event-type ' + typeClass + '">' + escapeHtml(ev.type || "") + '</span>' +
      '<span class="event-note">' + escapeHtml(ev.note || "") + '</span>' +
      '<span class="event-arrow" aria-hidden="true">&#8594;</span>' +
      '</a>';
  }}

  function eventsSectionHtml(gym) {{
    if (!gym.enabled || gym.fetch_status !== "success") {{
      return '<p class="no-events">予定情報を取得できていません</p>';
    }}
    var events = gym.events || [];
    if (events.length === 0) {{
      return '<p class="no-events">直近14日間の予定はありません</p>';
    }}
    return events.map(eventRowHtml).join("");
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

    return '<article class="card" data-gym-id="' + escapeHtml(gym.gym_id) + '">' +
      '<header class="card-head">' +
        '<h2>' + escapeHtml(displayName) + '</h2>' +
        '<button type="button" class="star-btn' + (fav ? " active" : "") + '" data-fav-toggle="' + escapeHtml(gym.gym_id) + '" aria-pressed="' + fav + '" aria-label="マイリストに追加・削除">' + (fav ? "&#9733;" : "&#9734;") + '</button>' +
      '</header>' +
      '<dl class="info-grid">' +
        '<div class="info-item"><dt>営業時間</dt><dd>' + fieldHtml(gym.hours) + '</dd></div>' +
        '<div class="info-item"><dt>定休日</dt><dd>' + fieldHtml(gym.closed_days) + '</dd></div>' +
        '<div class="info-item"><dt>最寄り駅</dt><dd>' + fieldHtml(gym.station) + '</dd></div>' +
        '<div class="info-item"><dt>路線</dt><dd>' + fieldHtml(gym.line) + '</dd></div>' +
      '</dl>' +
      '<div class="events">' + eventsSectionHtml(gym) + '</div>' +
      noteHtml +
      linkRowHtml(gym) +
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

    var bodyHtml;
    if (list.length === 0) {{
      bodyHtml = '<p class="empty-state">検索タブからジムを追加してください</p>';
    }} else {{
      bodyHtml = '<div class="cards">' + list.map(gymCardHtml).join("") + '</div>';
    }}

    container.innerHTML = bodyHtml +
      '<footer class="note">' +
        '<p class="generated">display.json を元に生成 &middot; ' + escapeHtml(GENERATED_AT) + ' 時点</p>' +
        '<p class="disclaimer">掲載情報は各ジムの公式サイトから自動収集したものです。正確性・網羅性を保証しません。ご利用前に必ず公式サイトでご確認ください。</p>' +
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
      return name.indexOf(q) !== -1;
    }});
    container.innerHTML = filtered.map(gymCardHtml).join("");
  }}

  function renderSearchTab() {{
    renderChainFilter();
    renderSearchCards();
  }}

  // =========================================================
  // 状態管理・イベント配線（コントローラ）
  // =========================================================
  function switchTab(tab) {{
    document.getElementById("tab-mylist").hidden = tab !== "mylist";
    document.getElementById("tab-search").hidden = tab !== "search";
    document.querySelectorAll(".tab-btn").forEach(function (btn) {{
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tab);
    }});
    if (tab === "mylist") renderMyListTab();
  }}

  document.addEventListener("click", function (e) {{
    var tabBtn = e.target.closest(".tab-btn");
    if (tabBtn) {{
      switchTab(tabBtn.getAttribute("data-tab"));
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
  }});

  document.addEventListener("input", function (e) {{
    if (e.target && e.target.id === "search-input") {{
      searchState.query = e.target.value;
      renderSearchCards();
    }}
  }});

  // =========================================================
  // 初期描画
  // =========================================================
  renderMyListTab();
  renderSearchTab();
}})();
</script>
'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_doc)

print(f"index.html を生成しました（{len(gyms)}店舗）。")
