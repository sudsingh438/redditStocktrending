import json
import json
from datetime import datetime, timezone
from config import DOCS_DIR, REPORTS_DIR
from db import get_latest_run, get_predictions_for_run, get_accuracy_stats, get_all_predictions

CSS = """<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 16px; max-width: 600px; margin: 0 auto; }
h1 { font-size: 1.4rem; color: #58a6ff; margin-bottom: 4px; }
.header { text-align: center; padding: 16px 0; border-bottom: 1px solid #21262d; margin-bottom: 16px; }
.subtitle { font-size: 0.8rem; color: #8b949e; }
.card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
.card h2 { font-size: 1rem; color: #58a6ff; margin-bottom: 10px; border-bottom: 1px solid #21262d; padding-bottom: 6px; }
.stock-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #21262d20; }
.stock-row:last-child { border-bottom: none; }
.stock-rank { font-size: 0.9rem; font-weight: bold; color: #8b949e; min-width: 24px; }
.stock-info { flex: 1; }
.stock-ticker { font-weight: bold; font-size: 1.05rem; }
.stock-reason { font-size: 0.8rem; color: #8b949e; margin-top: 2px; }
.stock-meta { font-size: 0.75rem; color: #484f58; margin-top: 2px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold; }
.badge-buy { background: #1a3a2a; color: #3fb950; }
.badge-sell { background: #3a1a1a; color: #f85149; }
.badge-hold { background: #3a351a; color: #d29922; }
.confidence { font-size: 0.75rem; color: #484f58; margin-left: 4px; }
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.stat-box { background: #0d1117; border-radius: 6px; padding: 10px; text-align: center; }
.stat-value { font-size: 1.3rem; font-weight: bold; color: #58a6ff; }
.stat-label { font-size: 0.7rem; color: #8b949e; margin-top: 2px; }
.history-row { padding: 8px 0; border-bottom: 1px solid #21262d20; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; }
.status-correct { color: #3fb950; }
.status-wrong { color: #f85149; }
.status-pending { color: #8b949e; }
.nav { display: flex; gap: 8px; justify-content: center; padding: 12px 0; }
.nav a { color: #58a6ff; text-decoration: none; font-size: 0.85rem; padding: 6px 12px; border-radius: 6px; }
.nav a:hover { background: #21262d; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
th { text-align: left; padding: 8px 6px; border-bottom: 1px solid #21262d; color: #8b949e; font-weight: normal; }
td { padding: 6px; border-bottom: 1px solid #21262d15; }
.empty { text-align: center; color: #8b949e; padding: 30px; }
.footer { text-align: center; font-size: 0.7rem; color: #484f58; padding: 20px 0; }
.refresh-time { color: #484f58; font-size: 0.7rem; }
</style>"""


def emoji_for_sentiment(s):
    return {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(s, "🟡")


def badge_class(s):
    return {"BUY": "badge-buy", "SELL": "badge-sell", "HOLD": "badge-hold"}.get(s, "badge-hold")


def generate_index():
    run = get_latest_run()
    stats = get_accuracy_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if run:
        predictions = get_predictions_for_run(run["id"])
        subreddits = json.loads(run["subreddits_scanned"])
    else:
        predictions = []
        subreddits = []

    report_files = sorted(REPORTS_DIR.glob("*.md"), reverse=True) if REPORTS_DIR.exists() else []

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Reddit Stock Trends</title>
{CSS}
</head>
<body>
<div class="header">
<h1>Reddit Stock Trends</h1>
<p class="subtitle">Last run: {run['timestamp'][:16] if run else 'No data yet'} | {', '.join(f'r/{s}' for s in subreddits[:2]) if subreddits else ''}</p>
</div>

<div class="nav">
<a href="index.html">Dashboard</a>
<a href="history.html">Full History</a>
</div>
"""

    if predictions:
        html += """<div class="card">
<h2>Today's Picks</h2>
"""
        for i, p in enumerate(predictions, 1):
            s = p["sentiment"]
            mentions = p.get("mentions", 0)
            reason = (p.get("reason") or "")[:120]
            html += f"""<div class="stock-row">
<div class="stock-rank">#{i}</div>
<div class="stock-info">
<div class="stock-ticker">${p['ticker']}</div>
<div class="stock-reason">{reason}</div>
<div class="stock-meta">{mentions} mentions"""
            top_posts_str = p.get("top_posts", "")
            if top_posts_str and top_posts_str != "[]":
                try:
                    top_posts = json.loads(top_posts_str)
                    for tp in top_posts[:2]:
                        title = tp.get("title", "")[:60]
                        url = tp.get("url", "")
                        if url:
                            html += f'<br>📎 <a href="{url}" target="_blank" style="color:#484f58;font-size:0.72rem;">{title}</a>'
                except Exception:
                    pass
            html += """</div>
</div>
<span class="badge {badge_class(s)}">{s}</span>
<span class="confidence">{p['confidence']:.0f}%</span>
</div>"""
        html += "</div>"
    else:
        html += '<div class="card"><div class="empty">No predictions yet. Run the scanner first.</div></div>'

    html += f"""<div class="card">
<h2>Accuracy Stats</h2>
<div class="stats-grid">
<div class="stat-box"><div class="stat-value">{stats['accuracy']}%</div><div class="stat-label">All-time hit rate</div></div>
<div class="stat-box"><div class="stat-value">{stats['seven_day_accuracy']}%</div><div class="stat-label">7-day hit rate</div></div>
<div class="stat-box"><div class="stat-value">{stats['correct']}/{stats['total']}</div><div class="stat-label">Correct / Total</div></div>
<div class="stat-box"><div class="stat-value" style="color:{'#3fb950' if stats['avg_buy_return'] > 0 else '#f85149'}">{stats['avg_buy_return']:+.1f}%</div><div class="stat-label">Avg BUY return</div></div>
</div>
</div>"""

    recent_predictions = get_all_predictions(limit=30)
    if recent_predictions:
        html += """<div class="card">
<h2>Recent Predictions</h2>
"""
        for p in recent_predictions[:15]:
            s = p["sentiment"]
            date = p["created_at"][:10] if p["created_at"] else ""
            html += f"""<div class="history-row">
<span>${p['ticker']} <span class="badge {badge_class(s)}">{s}</span></span>
<span style="font-size:0.75rem;">{date}</span>
</div>"""
        html += "</div>"

    if report_files:
        html += """<div class="card">
<h2>Daily Reports</h2>
"""
        for rp in report_files[:10]:
            date = rp.stem
            html += f'<div class="history-row"><a href="../reports/{rp.name}" target="_blank">📄 {date}</a></div>'
        html += "</div>"

    html += f"""<div class="footer">
<p class="refresh-time">Updated: {now}</p>
<p>Repo: <a href="https://github.com/sudsingh438/redditStocktrending" style="color:#484f58">redditStocktrending</a></p>
</div>
</body>
</html>"""

    doc_path = DOCS_DIR / "index.html"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(html)
    return doc_path


def generate_history():
    all_preds = get_all_predictions(limit=500)
    stats = get_accuracy_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>History — Reddit Stock Trends</title>
{CSS}
</head>
<body>
<div class="header">
<h1>Prediction History</h1>
<p class="subtitle">{stats['correct']}/{stats['total']} correct ({stats['accuracy']}% hit rate)</p>
</div>

<div class="nav">
<a href="index.html">Dashboard</a>
<a href="history.html">Full History</a>
</div>

<div class="card">
<table>
<tr><th>Ticker</th><th>Signal</th><th>Conf</th><th>Date</th><th>Mentions</th></tr>
"""

    for p in all_preds:
        s = p["sentiment"]
        date = p["created_at"][:10] if p["created_at"] else ""
        emoji = emoji_for_sentiment(s)
        html += f"""<tr>
<td><b>${p['ticker']}</b></td>
<td>{emoji} {s}</td>
<td>{p['confidence']:.0f}%</td>
<td>{date}</td>
<td>{p['mentions']}</td>
</tr>"""

    if not all_preds:
        html += '<tr><td colspan="5" class="empty">No predictions yet</td></tr>'

    html += f"""</table>
</div>
<div class="footer"><p class="refresh-time">Updated: {now}</p></div>
</body>
</html>"""

    doc_path = DOCS_DIR / "history.html"
    doc_path.write_text(html)
    return doc_path


def generate():
    i = generate_index()
    h = generate_history()
    return i, h
