import sys
import traceback
from datetime import datetime, timezone
from config import TOP_TICKERS_FOR_SENTIMENT, MIN_MENTIONS_FOR_SENTIMENT
from db import init_db, save_run, save_predictions
from reddit_fetcher import fetch_posts_and_comments
from ticker_extractor import load_tickers, extract_and_rank
from sentiment import analyze_top_tickers
from reporter import generate_markdown, print_terminal_summary
from dashboard import generate as generate_dashboard
from effectiveness import run_backtests, get_current_price


def main():
    print("=" * 60)
    print("  REDDIT STOCK TRENDING SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    init_db()

    print("\n[Step 1/7] Loading ticker database...")
    known_tickers = load_tickers()
    print(f"  Loaded {len(known_tickers)} tickers from tickers.txt")

    print("\n[Step 2/7] Fetching Reddit posts and comments...")
    try:
        posts, subreddits_scanned = fetch_posts_and_comments()
    except Exception as e:
        print(f"  ERROR fetching Reddit data: {e}")
        traceback.print_exc()
        sys.exit(1)
    print(f"  Total: {len(posts)} posts from {len(subreddits_scanned)} subreddits")

    print("\n[Step 3/7] Extracting stock tickers...")
    ranked = extract_and_rank(posts, known_tickers, min_mentions=MIN_MENTIONS_FOR_SENTIMENT)
    print(f"  Found {len(ranked)} tickers with ≥{MIN_MENTIONS_FOR_SENTIMENT} mentions")
    for t in ranked[:5]:
        print(f"    ${t['ticker']}: {t['mentions']} mentions, score={t['engagement_score']:.0f}")

    print(f"\n[Step 4/7] Analyzing sentiment for top {TOP_TICKERS_FOR_SENTIMENT} tickers via Deepseek...")
    sentiment_results = analyze_top_tickers(ranked, top_n=TOP_TICKERS_FOR_SENTIMENT)

    print(f"\n  Getting current prices...")
    for s in sentiment_results:
        price, price_date = get_current_price(s["ticker"])
        if price:
            s["price_at_time"] = price
            s["price_date"] = price_date

    print("\n[Step 5/7] Saving to database...")
    subreddits_list = list(subreddits_scanned)
    top_list = [{"ticker": r["ticker"], "mentions": r["mentions"]} for r in ranked[:TOP_TICKERS_FOR_SENTIMENT]]
    run_id = save_run(len(posts), len(ranked), subreddits_list, top_list)
    save_predictions(run_id, sentiment_results)
    print(f"  Run #{run_id} saved with {len(sentiment_results)} predictions")

    print("\n[Step 6/7] Generating reports...")
    report_path = generate_markdown(ranked, sentiment_results, posts, subreddits_list)
    print(f"  Report: {report_path}")
    print_terminal_summary(sentiment_results)

    doc_index, doc_history = generate_dashboard()
    print(f"  Dashboard: {doc_index}")
    print(f"  History:   {doc_history}")

    print("\n[Step 7/7] Running backtests on old predictions...")
    backtest_results = run_backtests()
    if backtest_results:
        correct = sum(1 for b in backtest_results if b["was_correct"])
        print(f"  Backtested {len(backtest_results)} predictions: {correct}/{len(backtest_results)} correct")

    print("\n" + "=" * 60)
    print("  SCAN COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
