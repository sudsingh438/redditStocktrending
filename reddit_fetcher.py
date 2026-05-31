import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import requests
from config import (
    REDDIT_CLIENT_ID, REDDIT_USER_AGENT, REDDIT_OAUTH_URL, REDDIT_API_BASE,
    SUBREDDITS, POSTS_PER_SUB, COMMENTS_PER_POST
)

NS = {"atom": "http://www.w3.org/2005/Atom"}


def _get_token():
    try:
        resp = requests.post(
            REDDIT_OAUTH_URL,
            auth=(REDDIT_CLIENT_ID, ""),
            data={
                "grant_type": "https://oauth.reddit.com/grants/installed_client",
                "device_id": "DO_NOT_TRACK_THIS_DEVICE",
            },
            headers={"User-Agent": REDDIT_USER_AGENT, "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        print(f"  [INFO] OAuth unavailable: {e}")
        return None


def _fetch_rss(sub):
    url = f"https://www.reddit.com/r/{sub}/new/.rss?limit=100"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RedditScanner/1.0)"}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"    [WARN] RSS {resp.status_code}")
        return []
    root = ET.fromstring(resp.text)
    entries = root.findall("atom:entry", NS)
    if not entries:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

    posts = []
    for entry in entries:
        title_el = entry.find("atom:title", NS) or entry.find("{http://www.w3.org/2005/Atom}title")
        link_el = entry.find("atom:link", NS) or entry.find("{http://www.w3.org/2005/Atom}link")
        updated_el = entry.find("atom:updated", NS) or entry.find("{http://www.w3.org/2005/Atom}updated")
        id_el = entry.find("atom:id", NS) or entry.find("{http://www.w3.org/2005/Atom}id")
        content_el = entry.find("atom:content", NS) or entry.find("{http://www.w3.org/2005/Atom}content")

        title = title_el.text if title_el is not None else ""
        link = link_el.get("href") if link_el is not None else ""
        updated = updated_el.text if updated_el is not None else ""
        raw_id = id_el.text.split("/")[-1] if id_el is not None and id_el.text else ""
        post_id = raw_id.replace("t3_", "").replace("t1_", "")
        selftext = content_el.text if content_el is not None else ""

        posts.append({
            "id": post_id,
            "title": title,
            "selftext": selftext[:1000],
            "url": link,
            "updated": updated,
        })
    return posts


def _fetch_json_post(sub, post_id, token):
    try:
        headers = {"Authorization": f"Bearer {token}", "User-Agent": REDDIT_USER_AGENT}
        url = f"{REDDIT_API_BASE}/r/{sub}/comments/{post_id}/.json"
        resp = requests.get(url, headers=headers, params={"limit": COMMENTS_PER_POST, "depth": 1}, timeout=15)
        if resp.status_code != 200:
            return [], None, None, 0
        data = resp.json()
        if len(data) < 1:
            return [], None, None, 0

        post_listing = data[0]["data"]["children"]
        if not post_listing:
            return [], None, None, 0
        post_data = post_listing[0]["data"]
        score = post_data.get("score", 0)
        upvote_ratio = post_data.get("upvote_ratio", 0)
        num_comments = post_data.get("num_comments", 0)

        comments = []
        if len(data) > 1:
            for c in data[1]["data"]["children"]:
                if c["kind"] == "t1":
                    comments.append({
                        "body": c["data"].get("body", ""),
                        "score": c["data"].get("score", 0),
                    })
        return comments, score, upvote_ratio, num_comments
    except Exception as e:
        return [], None, None, 0


def fetch_posts_and_comments():
    print("  Using RSS feeds for post discovery...")
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    all_posts = []

    # Phase 1: Get posts via RSS (no auth, works everywhere)
    for sub in SUBREDDITS:
        try:
            rss_posts = _fetch_rss(sub)
            sub_count = 0
            for rp in rss_posts:
                updated_dt = datetime.fromisoformat(rp["updated"].replace("Z", "+00:00"))
                if updated_dt < cutoff:
                    continue
                post_data = {
                    "subreddit": sub,
                    "id": rp["id"],
                    "title": rp["title"],
                    "selftext": rp.get("selftext", ""),
                    "url": rp["url"],
                    "score": 0,
                    "upvote_ratio": 0,
                    "num_comments": 0,
                    "created_utc": updated_dt.isoformat(),
                    "comments": [],
                }
                all_posts.append(post_data)
                sub_count += 1
                if sub_count >= POSTS_PER_SUB:
                    break
            print(f"  r/{sub}: {sub_count} posts")
        except Exception as e:
            print(f"  [WARN] r/{sub}: {e}")

    total = len(all_posts)
    print(f"\n  Total posts: {total}")

    if total == 0:
        print("  No recent posts found")
        return [], []

    # Phase 2: Try OAuth for enrichment (comments + scores)
    token = _get_token()
    if token:
        print(f"  Enriching {min(total, 60)} posts with scores & comments...")
        enriched = 0
        for i, post in enumerate(all_posts[:60]):
            if i % 20 == 0 and i > 0:
                print(f"    {i}/{min(total, 60)}...")
                time.sleep(2)
            comments, score, ratio, num_comments = _fetch_json_post(
                post["subreddit"], post["id"], token
            )
            if score is not None:
                post["score"] = score
                post["upvote_ratio"] = ratio
                post["num_comments"] = num_comments
                post["comments"] = comments
                enriched += 1
            time.sleep(0.3)

        print(f"    Enriched: {enriched} posts")
    else:
        print("  Skipping enrichment (no OAuth token)")

    comment_count = sum(len(p.get("comments", [])) for p in all_posts)
    print(f"  Comments fetched: {comment_count}")
    subreddits_found = list(set(p["subreddit"] for p in all_posts))
    return all_posts, subreddits_found
