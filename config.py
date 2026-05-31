import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
DOCS_DIR = BASE_DIR / "docs"
DB_PATH = BASE_DIR / "scanner.db"
TICKERS_FILE = BASE_DIR / "tickers.txt"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

REDDIT_CLIENT_ID = "ohXpoqrZYub1kg"
REDDIT_USER_AGENT = "RedditStockTrending/1.0"
REDDIT_OAUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "stockmarket"]
POSTS_PER_SUB = 100
COMMENTS_PER_POST = 10
TOP_TICKERS_FOR_SENTIMENT = 15
MIN_MENTIONS_FOR_SENTIMENT = 3
DAYS_BACK = 3

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
