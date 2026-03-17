import os
import re
import json
import time
import requests
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# --- Edit these ---
# TEST MODE - restore full list after confirming
HASHTAGS = ["discipline"]
COMPETITOR_ACCOUNTS = []  # add Instagram usernames here e.g. ["username1", "username2"]
# ------------------

OUTPUT_DIR = "01_Inbox/raw_signals"
POSTS_PER_HASHTAG = 5  # TEST MODE - restore full list after confirming

CONTENT_KEYWORDS = [
    "discipline",
    "wasting",
    "potential",
    "execution",
    "structure",
    "consistency",
    "lazy",
    "focus",
    "drift",
    "stuck",
    "capable",
    "mindset",
    "grind",
    "accountability",
    "level up",
    "young men",
    "20s",
    "stop wasting",
]
API_DELAY = 2  # seconds between API calls
POLL_INTERVAL = 5  # seconds between status polls
MAX_RETRIES = 5
BASE_BACKOFF = 2


class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()


# Apify free tier: ~100 requests/minute but we stay conservative
apify_limiter = RateLimiter(calls_per_minute=10)


def run_actor(actor_id, input_data, retries=MAX_RETRIES):
    """Start an Apify actor run and return the run ID."""
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_API_TOKEN}"
    last_exc = None
    for attempt in range(retries):
        apify_limiter.wait()
        try:
            response = requests.post(url, json=input_data, timeout=30)
            if response.status_code == 429 or response.status_code >= 500:
                wait = BASE_BACKOFF ** attempt
                print(f"  [RETRY] Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()["data"]["id"]
        except requests.RequestException as e:
            last_exc = e
            if attempt == retries - 1:
                raise
            wait = BASE_BACKOFF ** attempt
            print(f"  [RETRY] Rate limited — waiting {wait}s before retry...")
            time.sleep(wait)
    raise RuntimeError(f"run_actor failed after {retries} retries") from last_exc


def poll_run(run_id):
    """Poll until run is SUCCEEDED or FAILED. Returns final status."""
    url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    while True:
        apify_limiter.wait()
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        status = response.json()["data"]["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            return status
        time.sleep(POLL_INTERVAL)


def get_run_results(run_id, retries=MAX_RETRIES):
    """Fetch dataset items from a completed run."""
    url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}"
    last_exc = None
    for attempt in range(retries):
        apify_limiter.wait()
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 429 or response.status_code >= 500:
                wait = BASE_BACKOFF ** attempt
                print(f"  [RETRY] Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            last_exc = e
            if attempt == retries - 1:
                raise
            wait = BASE_BACKOFF ** attempt
            print(f"  [RETRY] Rate limited — waiting {wait}s before retry...")
            time.sleep(wait)
    raise RuntimeError(f"get_run_results failed after {retries} retries") from last_exc


BOT_USERNAME_SUBSTRINGS = [
    "._.", "community", "official", "coach", "motivat", "fitness",
    "health", "store", "shop", "business", "marketing", "growth", "agency",
]

SPAM_PHRASES = [
    "follow", "check my", "link in bio", "dm me", "click",
    "visit my", "gain followers", "promo", "discount", "shop now",
    "buy now", "@everyone",
]

PRIORITY_SIGNALS = [
    "wast", "stuck", "struggle", "can't", "cant", "need", "help",
    "feel like", "keep", "never", "always", "trying", "failed", "failing",
    "potential", "discipline", "consistent", "consistency", "motivation",
    "lazy", "procrastinat", "anxious", "anxiety", "lost", "behind",
    "ashamed", "embarrassed",
]


def is_human_comment(username, text, seen_comment_texts):
    """Return (is_human: bool, reason: str). Also checks seen_comment_texts set."""
    u = username.lower()
    t = text.strip()
    t_lower = t.lower()

    # --- Account signals ---
    for substr in BOT_USERNAME_SUBSTRINGS:
        if substr in u:
            return False, "bot account pattern"

    if re.search(r'\d{3,}$', u):
        return False, "bot account pattern"

    if re.search(r'_{3,}|\.{3,}', u):
        return False, "bot account pattern"

    # --- Comment signals ---
    if len(t) < 20:
        return False, "spam comment"

    if t == t.upper() and any(c.isalpha() for c in t):
        return False, "spam comment"

    for phrase in SPAM_PHRASES:
        if phrase in t_lower:
            return False, "spam comment"

    if re.search(r'https?://|www\.', t_lower):
        return False, "spam comment"

    emoji_count = len(re.findall(
        r'[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F02F]', t
    ))
    if emoji_count > 3:
        return False, "spam comment"

    if t_lower in seen_comment_texts:
        return False, "spam comment"

    words = t_lower.split()
    if len(set(words)) == 1:
        return False, "spam comment"

    return True, "ok"


def is_priority_comment(text):
    """Return True if the comment contains buyer-signal language."""
    t = text.lower()
    return any(signal in t for signal in PRIORITY_SIGNALS)


def save_signal(username, comment_text, source, post_url, timestamp, priority=False):
    """Save a comment as a raw signal markdown file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_username = username.replace("/", "_").replace("\\", "_")
    prefix = "PRIORITY_" if priority else ""
    filename = f"{OUTPUT_DIR}/signal_{prefix}{timestamp}_{safe_username}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"---\n")
        f.write(f"username: {username}\n")
        f.write(f"source: {source}\n")
        f.write(f"post_url: {post_url}\n")
        f.write(f"timestamp: {timestamp}\n")
        f.write(f"priority: {'true' if priority else 'false'}\n")
        f.write(f"---\n\n")
        f.write(f"# Raw Signal{'  [PRIORITY]' if priority else ''}\n\n")
        f.write(f"**Username:** @{username}\n\n")
        f.write(f"**Source:** {source}\n\n")
        f.write(f"**Post URL:** {post_url}\n\n")
        f.write(f"**Timestamp:** {timestamp}\n\n")
        f.write(f"**Comment:**\n\n{comment_text}\n")
    return filename


def scrape_comments_for_post(post_url, source, limit=100):
    """Run the comment scraper for a single post. Returns list of comment dicts."""
    try:
        run_id = run_actor("SbK00X0JYCPblD2wp", {
            "directUrls": [post_url],
            "resultsLimit": limit,
        })
        status = poll_run(run_id)
        if status != "SUCCEEDED":
            return []
        time.sleep(API_DELAY)
        return get_run_results(run_id)
    except Exception as e:
        print(f"  Error scraping comments for {post_url}: {e}")
        return []


def _process_comment(comment, source, post_url, seen_usernames, seen_comment_texts, counters):
    """Filter, deduplicate, and save a single comment. Updates counters in place."""
    username = comment.get("ownerUsername") or comment.get("username") or "unknown"
    text = comment.get("text") or comment.get("commentText") or ""
    if not text:
        return

    counters["scanned"] += 1
    if source not in counters["sources"]:
        counters["sources"][source] = {"scanned": 0, "qualified": 0, "priority": 0}
    counters["sources"][source]["scanned"] += 1

    human, reason = is_human_comment(username, text, seen_comment_texts)
    if not human:
        if reason == "bot account pattern":
            print(f"  [BOT FILTERED] @{username} — bot account pattern")
            counters["bot_filtered"] += 1
        else:
            print(f"  [SPAM FILTERED] @{username} — spam comment")
            counters["spam_filtered"] += 1
        return

    if username in seen_usernames:
        print(f"  [DUPLICATE] @{username} — already seen this run")
        counters["duplicate_filtered"] += 1
        return

    seen_usernames.add(username)
    seen_comment_texts.add(text.strip().lower())

    priority = is_priority_comment(text)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_signal(username, text, source, post_url, timestamp, priority=priority)
    preview = text[:80]
    counters["sources"][source]["qualified"] += 1
    if priority:
        print(f"  [PRIORITY] @{username} — {preview}...")
        counters["priority_saved"] += 1
        counters["sources"][source]["priority"] += 1
    else:
        print(f"  [SAVED] @{username} — {preview}...")
        counters["regular_saved"] += 1
    time.sleep(API_DELAY)


def scrape_hashtag(hashtag, seen_usernames, seen_comment_texts, counters):
    """Scrape posts for a hashtag, then scrape comments for each post."""
    print(f"\nScraping hashtag: #{hashtag}")

    try:
        run_id = run_actor("reGe1ST3OBgYZSsZJ", {
            "hashtags": [hashtag],
            "resultsLimit": POSTS_PER_HASHTAG,
        })
        status = poll_run(run_id)
        if status != "SUCCEEDED":
            print(f"  Actor run failed for #{hashtag} (status: {status})")
            return
        time.sleep(API_DELAY)
        posts = get_run_results(run_id)
    except Exception as e:
        print(f"  Error scraping #{hashtag}: {e}")
        return

    for post in posts:
        short_code = post.get("shortCode")
        post_url = post.get("url") or (f"https://www.instagram.com/p/{short_code}/" if short_code else None)
        if not post_url:
            continue

        source = f"#{hashtag}"
        comments = scrape_comments_for_post(post_url, source, limit=100)
        print(f"  Found {len(comments)} comments on {post_url}")

        for comment in comments:
            _process_comment(comment, source, post_url, seen_usernames, seen_comment_texts, counters)


def scrape_competitor(account, seen_usernames, seen_comment_texts, counters):
    """Scrape high-engagement ICP-relevant posts from a competitor account, then scrape comments."""
    print(f"\nScraping competitor: @{account}")

    try:
        run_id = run_actor("shu8hvrXbJbY3Eb9W", {
            "usernames": [account],
            "resultsLimit": 10,
            "resultsType": "posts",
            "scrapePostsUntilDate": "",
        })
        status = poll_run(run_id)
        if status != "SUCCEEDED":
            print(f"  Actor run failed for @{account} (status: {status})")
            return
        time.sleep(API_DELAY)
        posts = get_run_results(run_id)
    except Exception as e:
        print(f"  Error scraping @{account}: {e}")
        return

    source = f"@{account}"
    for post in posts:
        short_code = post.get("shortCode")
        post_url = post.get("url") or (f"https://www.instagram.com/p/{short_code}/" if short_code else None)
        if not post_url:
            continue

        caption = (post.get("caption") or post.get("text") or "").lower()
        matched_keyword = next((kw for kw in CONTENT_KEYWORDS if kw in caption), None)

        if not matched_keyword:
            print(f"  [POST SKIP] @{account} — no ICP keywords in caption — skipping")
            continue

        print(f"  [POST MATCH] @{account} — caption contains: '{matched_keyword}' — scraping comments")
        comments = scrape_comments_for_post(post_url, source, limit=200)
        print(f"  Found {len(comments)} comments on {post_url}")

        for comment in comments:
            _process_comment(comment, source, post_url, seen_usernames, seen_comment_texts, counters)


def main():
    seen_usernames = set()
    seen_comment_texts = set()
    counters = {
        "scanned": 0,
        "bot_filtered": 0,
        "spam_filtered": 0,
        "duplicate_filtered": 0,
        "priority_saved": 0,
        "regular_saved": 0,
        "sources": {},
    }

    for hashtag in HASHTAGS:
        scrape_hashtag(hashtag, seen_usernames, seen_comment_texts, counters)

    for account in COMPETITOR_ACCOUNTS:
        scrape_competitor(account, seen_usernames, seen_comment_texts, counters)

    total_saved = counters["priority_saved"] + counters["regular_saved"]
    print(f"""
--- Scrape Summary ---
Total comments scanned:    {counters["scanned"]}
Bot accounts filtered:     {counters["bot_filtered"]}
Spam comments filtered:    {counters["spam_filtered"]}
Duplicate users filtered:  {counters["duplicate_filtered"]}
Priority signals saved:    {counters["priority_saved"]}
Regular signals saved:     {counters["regular_saved"]}
Total saved:               {total_saved}
""")
    print("--- Per Source Breakdown ---")
    for src, data in counters["sources"].items():
        print(f"  {src:<20} scanned: {data['scanned']} | qualified: {data['qualified']} | priority: {data['priority']}")
    print("---------------------")

    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import cost_tracker

    total_results = counters["scanned"]
    haiku_calls = counters["priority_saved"] + counters["regular_saved"]
    haiku_input = haiku_calls * 500
    haiku_output = haiku_calls * 150

    scraper_cost = cost_tracker.log_scraper_costs(
        apify_results=total_results,
        haiku_calls=haiku_calls,
        haiku_input_tokens=haiku_input,
        haiku_output_tokens=haiku_output,
    )
    print(f"Scraper cost logged: ${scraper_cost:.4f}")
    counters["scraper_cost"] = scraper_cost

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    summary_path = os.path.join(OUTPUT_DIR, f"scrape_summary_{today}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(counters, f)
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
