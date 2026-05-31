import json
import sys
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, TOP_TICKERS_FOR_SENTIMENT

if not DEEPSEEK_API_KEY:
    print("ERROR: DEEPSEEK_API_KEY not set. Create a .env file with your key.")
    sys.exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SYSTEM_PROMPT = """You are a financial sentiment analyst specializing in Reddit stock discussions.
Analyze the given Reddit posts and comments about a stock ticker.
Classify the overall sentiment as BUY, SELL, or HOLD.
Factor in: bullish/bearish language, rocket emojis, sarcasm, confidence, consensus.
Respond with ONLY a JSON object and nothing else:

{"ticker": "SYMBOL", "sentiment": "BUY", "confidence": 85, "reason": "Brief one-line summary of the sentiment"}

Confidence is 0-100 integer."""


def analyze_sentiment(ticker_data):
    ticker = ticker_data["ticker"]
    posts = ticker_data.get("posts", [])
    comments = ticker_data.get("sample_comments", [])

    snippets = []
    for p in posts[:10]:
        title = p["title"][:200]
        body = p.get("selftext", "")[:300]
        if title.strip():
            snippets.append(f"[r/{p['subreddit']} | {p['score']}↑] {title}")
        if body.strip():
            snippets.append(body)

    for c in comments[:15]:
        if c.strip():
            snippets.append(f"[Comment] {c[:250]}")

    text = f"Ticker: ${ticker}\n\nReddit Discussion:\n" + "\n---\n".join(snippets[:30])
    if not snippets:
        return {"ticker": ticker, "sentiment": "HOLD", "confidence": 0, "reason": "No discussion data available"}

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text[:8000]},
            ],
            temperature=0.3,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result.setdefault("reason", "")
        result.setdefault("confidence", 50)
        result["ticker"] = ticker
        return result
    except json.JSONDecodeError:
        return {"ticker": ticker, "sentiment": "HOLD", "confidence": 0, "reason": f"Parse error: {raw[:100]}"}
    except Exception as e:
        return {"ticker": ticker, "sentiment": "HOLD", "confidence": 0, "reason": f"Error: {str(e)[:100]}"}


def analyze_top_tickers(ranked_tickers, top_n=None):
    if top_n is None:
        top_n = TOP_TICKERS_FOR_SENTIMENT
    to_analyze = ranked_tickers[:top_n]
    results = []
    for i, t in enumerate(to_analyze):
        print(f"  [{i+1}/{len(to_analyze)}] Analyzing ${t['ticker']} ({t['mentions']} mentions)...")
        sentiment = analyze_sentiment(t)
        sentiment["mentions"] = t["mentions"]
        sentiment["engagement_score"] = t["engagement_score"]
        sentiment["company_name"] = t.get("company_name", "")
        sentiment["posts"] = t.get("posts", [])
        top_posts = []
        for p in t.get("posts", [])[:3]:
            top_posts.append({"title": p["title"][:100], "url": p.get("url", ""), "subreddit": p.get("subreddit", "")})
        sentiment["top_posts"] = top_posts
        results.append(sentiment)
    results.sort(key=lambda x: x.get("mentions", 0), reverse=True)
    return results
