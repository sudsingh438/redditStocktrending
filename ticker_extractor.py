import re
from collections import Counter
from config import TICKERS_FILE


def load_tickers():
    tickers = {}
    blocked = set()
    with open(TICKERS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                symbol, meta = line.split("|", 1)
                symbol = symbol.strip().upper()
                meta = meta.strip()
                if meta == "BLOCK":
                    blocked.add(symbol)
                else:
                    if symbol not in tickers:
                        tickers[symbol] = meta
    for b in blocked:
        tickers.pop(b, None)
    return tickers


TICKER_REGEX = re.compile(r"\$?\b([A-Z]{1,5})\b")


def extract_tickers_from_text(text, known_tickers):
    found = set()
    for match in TICKER_REGEX.finditer(text):
        ticker = match.group(1)
        if ticker in known_tickers:
            found.add(ticker)
    matches = re.findall(r"\$([A-Z]{1,5})\b", text)
    for t in matches:
        if t in known_tickers:
            found.add(t)
    return found


def extract_and_rank(posts, known_tickers, min_mentions=1):
    ticker_posts = {}
    ticker_engagement = {}
    ticker_comments = {}

    for post in posts:
        all_text = post["title"] + " " + post["selftext"]
        for comment in post.get("comments", []):
            all_text += " " + comment["body"]

        engagement = post["score"] + post["num_comments"] * 2

        found = extract_tickers_from_text(all_text, known_tickers)
        for ticker in found:
            if ticker not in ticker_posts:
                ticker_posts[ticker] = []
                ticker_engagement[ticker] = 0
                ticker_comments[ticker] = []
            ticker_posts[ticker].append(post)
            ticker_engagement[ticker] += engagement
            for c in post.get("comments", []):
                if ticker in extract_tickers_from_text(c["body"], known_tickers):
                    ticker_comments[ticker].append(c["body"][:300])

    ranked = []
    for ticker, post_list in ticker_posts.items():
        mentions = len(post_list)
        if mentions < min_mentions:
            continue
        score = ticker_engagement[ticker]
        ranked.append({
            "ticker": ticker,
            "company_name": known_tickers.get(ticker, ""),
            "mentions": mentions,
            "engagement_score": score,
            "posts": post_list,
            "sample_comments": ticker_comments.get(ticker, [])[:20],
        })

    ranked.sort(key=lambda x: x["engagement_score"], reverse=True)
    return ranked
