import requests
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RedditScanner/1.0)"}


def get_trending_tickers():
    try:
        r = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/trending/US",
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code != 200:
            return []
        quotes = (
            r.json()
            .get("finance", {})
            .get("result", [{}])[0]
            .get("quotes", [])
        )
        tickers = []
        for q in quotes:
            symbol = q.get("symbol", "")
            if not symbol:
                continue
            if "=F" in symbol or "^" in symbol or "=X" in symbol:
                continue
            skip = False
            for suffix in ("-USD", "-CAD", "-EUR", "-GBP", "-JPY", "-AUD", "-CNY", "-KRW", "-INR"):
                if symbol.endswith(suffix):
                    skip = True
                    break
            if skip:
                continue
            tickers.append(symbol)
        return tickers[:20]
    except Exception as e:
        print(f"  [WARN] Yahoo trending error: {e}")
        return []


def get_news_for_ticker(ticker):
    try:
        r = requests.get(
            f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}&newsCount=3",
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code != 200:
            return []
        news_items = r.json().get("news", [])
        headlines = []
        for n in news_items[:3]:
            headlines.append(
                {
                    "title": n.get("title", "")[:100],
                    "link": n.get("link", ""),
                    "publisher": n.get("publisher", ""),
                }
            )
        return headlines
    except Exception:
        return []


def get_market_movers():
    movers = {"gainers": [], "losers": [], "most_active": []}

    screener_ids = {
        "gainers": "day_gainers",
        "losers": "day_losers",
        "most_active": "most_actives",
    }

    for key, scr_id in screener_ids.items():
        try:
            r = requests.get(
                f"https://query2.finance.yahoo.com/v1/finance/screeners/predefined/saved?scrIds={scr_id}&count=5",
                headers=HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                continue
            quotes = (
                r.json()
                .get("finance", {})
                .get("result", [{}])[0]
                .get("quotes", [])
            )
            for q in quotes[:5]:
                symbol = q.get("symbol", "")
                name = q.get("shortName") or q.get("longName") or symbol
                change_pct = (
                    q.get("regularMarketChangePercent", {})
                    .get("raw", 0)
                )
                movers[key].append(
                    {
                        "symbol": symbol,
                        "name": name[:40],
                        "change_pct": round(change_pct, 2),
                    }
                )
        except Exception:
            pass
        time.sleep(0.5)

    return movers


def fetch_all():
    print("  Fetching Yahoo trending tickers...")
    trending = get_trending_tickers()
    print(f"    Trending: {len(trending)} tickers")

    print("  Fetching market movers...")
    movers = get_market_movers()
    for key, items in movers.items():
        print(f"    {key}: {len(items)}")

    return {
        "trending": trending,
        "gainers": movers.get("gainers", []),
        "losers": movers.get("losers", []),
        "most_active": movers.get("most_active", []),
    }
