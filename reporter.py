from datetime import datetime, timezone
from pathlib import Path
from config import REPORTS_DIR


def emoji_for_sentiment(s):
    if s == "BUY":
        return "🟢"
    elif s == "SELL":
        return "🔴"
    return "🟡"


def generate_markdown(ranked_tickers, sentiment_results, posts, subreddits_scanned):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{today}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Reddit Stock Trending Report — {today}",
        "",
        f"**Subreddits scanned:** {', '.join(f'r/{s}' for s in subreddits_scanned)}",
        f"**Posts analyzed:** {len(posts)}",
        f"**Tickers detected:** {len(ranked_tickers)}",
        "",
        "---",
        "",
        "## Top Trending Stocks",
        "",
    ]

    for i, s in enumerate(sentiment_results, 1):
        ticker = s["ticker"]
        sentiment = s.get("sentiment", "HOLD")
        confidence = s.get("confidence", 0)
        mentions = s.get("mentions", 0)
        reason = s.get("reason", "")
        emoji = emoji_for_sentiment(sentiment)

        lines.append(f"### {i}. ${ticker} — {emoji} {sentiment} ({confidence}% confidence)")
        lines.append(f"**Mentions:** {mentions} | **Sentiment:** {sentiment.lower()}")
        if reason:
            lines.append(f"> {reason}")
        lines.append("")

        post_list = s.get("posts", [])
        if post_list:
            lines.append("**Top posts mentioning this stock:**")
            for p in post_list[:3]:
                lines.append(f"- [{p['title'][:100]}]({p['url']}) — r/{p['subreddit']} ({p['score']}↑)")
            lines.append("")

    if len(ranked_tickers) > len(sentiment_results):
        lines.append("## Other Mentioned Tickers (no sentiment analysis)")
        lines.append("")
        lines.append("| Ticker | Mentions |")
        lines.append("|--------|----------|")
        for t in ranked_tickers[len(sentiment_results):len(sentiment_results) + 15]:
            lines.append(f"| ${t['ticker']} | {t['mentions']} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

    report_path.write_text("\n".join(lines))
    return report_path


def print_terminal_summary(sentiment_results):
    print("\n" + "=" * 60)
    print("  REDDIT STOCK TRENDING — TODAY'S SIGNALS")
    print("=" * 60)
    for i, s in enumerate(sentiment_results, 1):
        emoji = emoji_for_sentiment(s.get("sentiment", "HOLD"))
        print(f"  {i:2}. ${s['ticker']:<6} {emoji} {s.get('sentiment', 'HOLD'):<5} ({s.get('confidence', 0):.0f}%) | {s.get('mentions', 0)} mentions")
        reason = s.get("reason", "")
        if reason:
            print(f"      \"{reason[:100]}\"")
    print("=" * 60)
