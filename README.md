# Reddit Stock Trending

Daily stock sentiment scanner using Reddit discussions + Deepseek AI.

## Dashboard

**[View Live Dashboard](https://sudsingh438.github.io/redditStocktrending)**

## Quick Links

- [Trigger Scanner](https://github.com/sudsingh438/redditStocktrending/actions/workflows/scanner.yml)
- [Today's Report](reports/)
- [Full Prediction History](https://sudsingh438.github.io/redditStocktrending/history)

## How It Works

1. Scans r/wallstreetbets, r/stocks, r/investing, r/stockmarket for posts from the last 3 days
2. Extracts stock tickers using regex against 400+ known symbols
3. Sends top 15 most-mentioned tickers to Deepseek for BUY/SELL/HOLD sentiment analysis
4. Generates a mobile-optimized dashboard + markdown report
5. Tracks prediction accuracy via Yahoo Finance price backtesting (5-day returns)

## Auto-Schedule

Runs daily at **14:00 UTC** (8 AM Central) via GitHub Actions.
Manually trigger anytime from the Actions tab.
