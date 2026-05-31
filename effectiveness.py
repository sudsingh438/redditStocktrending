from datetime import datetime, timezone, timedelta, date
import yfinance as yf
from db import get_pending_backtests, save_backtest


def truncate_date(d):
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return datetime.fromisoformat(d).date()
    return d


def run_backtests():
    pending = get_pending_backtests()
    if not pending:
        print("  No pending backtests")
        return []

    results = []
    today = date.today()
    tickers = list(set(p["ticker"] for p in pending))

    print(f"  Checking {len(pending)} pending backtests for {len(tickers)} tickers...")

    for i, p in enumerate(pending):
        ticker = p["ticker"]
        created_at = p["created_at"]
        pred_date = truncate_date(created_at)

        days_since = (today - pred_date).days if isinstance(pred_date, date) else 0
        if days_since < 5:
            continue

        try:
            stock = yf.Ticker(ticker)
            hist_5d = stock.history(start=pred_date, end=pred_date + timedelta(days=15))
            hist_1d = stock.history(start=pred_date, end=pred_date + timedelta(days=5))

            if len(hist_5d) < 2:
                continue

            price_start = hist_5d["Close"].iloc[0]
            price_5d = hist_5d["Close"].iloc[-1]
            price_1d = hist_1d["Close"].iloc[-1] if len(hist_1d) > 0 else price_start

            change_5d = ((price_5d - price_start) / price_start) * 100
            change_1d = ((price_1d - price_start) / price_start) * 100

            sentiment = p["sentiment"]
            if sentiment == "BUY":
                was_correct = 1 if change_5d > 0 else 0
            elif sentiment == "SELL":
                was_correct = 1 if change_5d < 0 else 0
            else:
                was_correct = 1 if abs(change_5d) < 2 else 0

            save_backtest(p["id"], price_5d, price_1d, change_5d, change_1d, was_correct)
            results.append({
                "ticker": ticker,
                "sentiment": sentiment,
                "change_5d": round(change_5d, 2),
                "was_correct": was_correct,
            })

            status = "✅" if was_correct else "❌"
            print(f"    ${ticker} ({sentiment}): {change_5d:+.2f}% {status}")

        except Exception as e:
            print(f"    ${ticker}: Error — {e}")

    return results


def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 2), datetime.now(timezone.utc).isoformat()
    except Exception:
        pass
    return None, None
