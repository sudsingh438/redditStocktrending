import sqlite3
import json
from datetime import datetime, timezone
from config import DB_PATH


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            posts_analyzed INTEGER,
            tickers_found INTEGER,
            subreddits_scanned TEXT,
            top_tickers TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            company_name TEXT,
            mentions INTEGER,
            engagement_score REAL,
            sentiment TEXT,
            confidence REAL,
            reason TEXT,
            top_posts TEXT,
            price_at_time REAL,
            price_date TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL UNIQUE,
            price_5d REAL,
            price_1d REAL,
            price_change_5d_pct REAL,
            price_change_1d_pct REAL,
            was_correct INTEGER,
            checked_at TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES predictions(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtests_prediction ON backtests(prediction_id)")
    conn.commit()
    conn.close()


def save_run(posts_analyzed, tickers_found, subreddits_scanned, top_tickers):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO runs (timestamp, posts_analyzed, tickers_found, subreddits_scanned, top_tickers) VALUES (?, ?, ?, ?, ?)",
        (now, posts_analyzed, tickers_found, json.dumps(subreddits_scanned), json.dumps(top_tickers))
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id


def save_predictions(run_id, predictions):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    for p in predictions:
        top_posts_json = json.dumps(p.get("top_posts", [])[:3])
        conn.execute(
            "INSERT INTO predictions (run_id, ticker, company_name, mentions, engagement_score, sentiment, confidence, reason, top_posts, price_at_time, price_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, p.get("ticker"), p.get("company_name"), p.get("mentions"),
             p.get("engagement_score"), p.get("sentiment"), p.get("confidence"),
             p.get("reason"), top_posts_json, p.get("price_at_time"), p.get("price_date"), now)
        )
    conn.commit()
    conn.close()


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def get_latest_run():
    conn = get_db()
    row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_dict(row)


def get_predictions_for_run(run_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM predictions WHERE run_id = ? ORDER BY mentions DESC",
        (run_id,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_all_predictions(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_pending_backtests(min_days_old=5):
    conn = get_db()
    cutoff = datetime.now(timezone.utc).isoformat()
    rows = conn.execute("""
        SELECT p.* FROM predictions p
        LEFT JOIN backtests b ON p.id = b.prediction_id
        WHERE b.id IS NULL AND p.price_date IS NOT NULL
        ORDER BY p.created_at ASC
    """).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def save_backtest(prediction_id, price_5d, price_1d, change_5d, change_1d, was_correct):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO backtests (prediction_id, price_5d, price_1d, price_change_5d_pct, price_change_1d_pct, was_correct, checked_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (prediction_id, price_5d, price_1d, change_5d, change_1d, was_correct, now)
    )
    conn.commit()
    conn.close()


def get_accuracy_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM backtests").fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM backtests WHERE was_correct = 1").fetchone()[0]
    avg_buy_return = conn.execute(
        "SELECT AVG(price_change_5d_pct) FROM backtests b JOIN predictions p ON b.prediction_id = p.id WHERE p.sentiment = 'BUY' AND b.was_correct IS NOT NULL"
    ).fetchone()[0]
    avg_sell_return = conn.execute(
        "SELECT AVG(price_change_5d_pct) FROM backtests b JOIN predictions p ON b.prediction_id = p.id WHERE p.sentiment = 'SELL' AND b.was_correct IS NOT NULL"
    ).fetchone()[0]
    seven_day_correct = conn.execute(
        "SELECT COUNT(*) FROM backtests WHERE was_correct = 1 AND checked_at >= date('now', '-7 days')"
    ).fetchone()[0]
    seven_day_total = conn.execute(
        "SELECT COUNT(*) FROM backtests WHERE checked_at >= date('now', '-7 days')"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "avg_buy_return": round(avg_buy_return, 2) if avg_buy_return else 0,
        "avg_sell_return": round(avg_sell_return, 2) if avg_sell_return else 0,
        "seven_day_correct": seven_day_correct,
        "seven_day_total": seven_day_total,
        "seven_day_accuracy": round(seven_day_correct / seven_day_total * 100, 1) if seven_day_total > 0 else 0,
    }
