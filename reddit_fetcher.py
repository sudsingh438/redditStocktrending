import time
from datetime import datetime, timezone, timedelta
import requests
from config import (
    REDDIT_CLIENT_ID, REDDIT_USER_AGENT, REDDIT_OAUTH_URL, REDDIT_API_BASE,
    SUBREDDITS, POSTS_PER_SUB, COMMENTS_PER_POST
)


def _get_token():
    resp = requests.post(
        REDDIT_OAUTH_URL,
        auth=(REDDIT_CLIENT_ID, ""),
        data={
            "grant_type": "https://oauth.reddit.com/grants/installed_client",
            "device_id": "DO_NOT_TRACK_THIS_DEVICE",
        },
        headers={"User-Agent": REDDIT_USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _api_get(url, token, params=None):
    headers = {"Authorization": f"Bearer {token}", "User-Agent": REDDIT_USER_AGENT}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    if resp.status_code == 429:
        time.sleep(5)
        resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    resp.raise_for_status()
    remaining = float(resp.headers.get("x-ratelimit-remaining", 10))
    if remaining < 5:
        reset = int(resp.headers.get("x-ratelimit-reset", 30))
        time.sleep(reset + 1)
    return resp.json()


def fetch_posts_and_comments():
    token = _get_token()
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    all_posts = []
    total_posts = 0

    for sub in SUBREDDITS:
        after = None
        sub_posts = 0
        for page in range(3):
            params = {"limit": 100, "raw_json": 1}
            if after:
                params["after"] = after
            try:
                data = _api_get(f"{REDDIT_API_BASE}/r/{sub}/new", token, params)
            except Exception as e:
                print(f"  [WARN] Skipping r/{sub} page {page}: {e}")
                break

            posts = data["data"]["children"]
            after = data["data"].get("after")
            if not posts:
                break

            for p in posts:
                d = p["data"]
                created = datetime.fromtimestamp(d["created_utc"], tz=timezone.utc)
                if created < cutoff:
                    after = None
                    break
                post_data = {
                    "subreddit": sub,
                    "id": d["id"],
                    "title": d["title"],
                    "selftext": d.get("selftext", ""),
                    "url": f"https://www.reddit.com{d['permalink']}",
                    "score": d.get("score", 0),
                    "upvote_ratio": d.get("upvote_ratio", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": created.isoformat(),
                    "comments": [],
                }
                if sub_posts < POSTS_PER_SUB:
                    all_posts.append(post_data)
                    total_posts += 1
                    sub_posts += 1

            if after is None:
                break
            time.sleep(2)

        print(f"  r/{sub}: {sub_posts} posts")

    print(f"\nFetching comments for {total_posts} posts...")
    token = _get_token()
    for i, post in enumerate(all_posts):
        if i % 20 == 0 and i > 0:
            print(f"  Comments: {i}/{total_posts}...")
            token = _get_token()
            time.sleep(2)
        try:
            url = f"{REDDIT_API_BASE}/r/{post['subreddit']}/comments/{post['id']}/.json"
            data = _api_get(url, token, {"limit": COMMENTS_PER_POST, "depth": 1})
            if len(data) > 1:
                for c in data[1]["data"]["children"]:
                    if c["kind"] == "t1":
                        cd = c["data"]
                        post["comments"].append({
                            "body": cd.get("body", ""),
                            "score": cd.get("score", 0),
                        })
        except Exception:
            pass
        time.sleep(0.5)

    print(f"  Done: {sum(len(p['comments']) for p in all_posts)} comments fetched")
    return all_posts, list(set(p["subreddit"] for p in all_posts))
