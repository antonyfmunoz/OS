import os
import re
import sys
import json
import time
import requests
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# --- Edit these ---
HASHTAGS = []  # populated at runtime by get_todays_hashtags()
COMPETITOR_ACCOUNTS = []  # add Instagram usernames here e.g. ["username1", "username2"]
# ------------------

OUTPUT_DIR = "01_Inbox/raw_signals"

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


# ---------------------------------------------------------------------------
# Hashtag config helpers
# ---------------------------------------------------------------------------

def load_hashtag_config():
    path = os.path.join(os.path.dirname(__file__), "hashtag_config.json")
    with open(path) as f:
        return json.load(f)


def save_hashtag_config(config):
    path = os.path.join(os.path.dirname(__file__), "hashtag_config.json")
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def get_todays_hashtags():
    config = load_hashtag_config()
    group = config["current_group"]
    hashtags = config["groups"][group]
    config["current_group"] = "B" if group == "A" else "A"
    save_hashtag_config(config)
    print(f"Today's group: {group} — {hashtags}")
    return hashtags


def update_hashtag_performance(counters):
    config = load_hashtag_config()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    for source, stats in counters.get("sources", {}).items():
        if source not in config["performance"]:
            config["performance"][source] = {
                "runs": 0,
                "total_scanned": 0,
                "total_qualified": 0,
                "total_priority": 0,
                "avg_qualified_rate": 0.0,
                "last_run": today,
            }
        p = config["performance"][source]
        p["runs"] += 1
        p["total_scanned"] += stats.get("scanned", 0)
        p["total_qualified"] += stats.get("qualified", 0)
        p["total_priority"] += stats.get("priority", 0)
        if p["total_scanned"] > 0:
            p["avg_qualified_rate"] = round(
                p["total_qualified"] / p["total_scanned"], 4)
        p["last_run"] = today
    save_hashtag_config(config)


# ---------------------------------------------------------------------------
# Scraped posts tracker
# ---------------------------------------------------------------------------

def load_scraped_posts():
    path = os.path.join(os.path.dirname(__file__), "scraped_posts.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_scraped_posts(data):
    path = os.path.join(os.path.dirname(__file__), "scraped_posts.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_post_url(post):
    short_code = post.get("shortCode")
    return post.get("url") or (
        f"https://www.instagram.com/p/{short_code}/" if short_code else None
    )


# ---------------------------------------------------------------------------
# Apify API helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Comment filtering
# ---------------------------------------------------------------------------

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

    for substr in BOT_USERNAME_SUBSTRINGS:
        if substr in u:
            return False, "bot account pattern"

    if re.search(r'\d{3,}$', u):
        return False, "bot account pattern"

    if re.search(r'_{3,}|\.{3,}', u):
        return False, "bot account pattern"

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


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_hashtag(hashtag, seen_usernames, seen_comment_texts, counters):
    """Scrape posts for a hashtag with smart first-run vs incremental logic."""
    print(f"\nScraping hashtag: #{hashtag}")
    scraped_posts = load_scraped_posts()
    key = f"#{hashtag}"
    known_urls = set(scraped_posts.get(key, {}).get("scraped_urls", []))
    is_first_run = len(known_urls) == 0
    results_limit = 50 if is_first_run else 10

    try:
        run_id = run_actor("reGe1ST3OBgYZSsZJ", {
            "hashtags": [hashtag],
            "resultsLimit": results_limit,
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

    new_posts = [p for p in posts if get_post_url(p) and get_post_url(p) not in known_urls]

    if not new_posts:
        print(f"  [SKIP] #{hashtag} — no new posts")
        return

    if is_first_run:
        new_posts.sort(
            key=lambda p: p.get("commentsCount") or p.get("comments") or 0,
            reverse=True,
        )
        new_posts = new_posts[:5]
        print(f"  [FIRST RUN] #{hashtag} — top 5 posts by engagement")
    else:
        print(f"  [UPDATE] #{hashtag} — {len(new_posts)} new posts")

    new_urls = []
    source = f"#{hashtag}"
    for post in new_posts:
        url = get_post_url(post)
        if not url:
            continue
        comments = scrape_comments_for_post(url, source, limit=100)
        print(f"  Found {len(comments)} comments on {url}")
        for comment in comments:
            _process_comment(comment, source, url, seen_usernames, seen_comment_texts, counters)
        new_urls.append(url)

    if key not in scraped_posts:
        scraped_posts[key] = {"scraped_urls": []}
    scraped_posts[key]["scraped_urls"].extend(new_urls)
    scraped_posts[key]["scraped_urls"] = scraped_posts[key]["scraped_urls"][-100:]
    scraped_posts[key]["last_scraped"] = datetime.datetime.now().strftime("%Y-%m-%d")
    save_scraped_posts(scraped_posts)


def scrape_competitor(account, seen_usernames, seen_comment_texts, counters):
    """Scrape high-engagement ICP-relevant posts from a competitor account."""
    print(f"\nScraping competitor: @{account}")
    scraped_posts = load_scraped_posts()
    known_urls = set(scraped_posts.get(account, {}).get("scraped_urls", []))
    is_first_run = len(known_urls) == 0
    results_limit = 50 if is_first_run else 10

    try:
        run_id = run_actor("shu8hvrXbJbY3Eb9W", {
            "usernames": [account],
            "resultsLimit": results_limit,
            "resultsType": "posts",
        })
        status = poll_run(run_id)
        if status != "SUCCEEDED":
            print(f"  Actor run failed for @{account} (status: {status})")
            return 0
        time.sleep(API_DELAY)
        posts = get_run_results(run_id)
    except Exception as e:
        print(f"  Error scraping @{account}: {e}")
        return 0

    matched_posts = []
    for post in posts:
        caption = (post.get("caption") or post.get("text") or "").lower()
        url = get_post_url(post)
        if not url or url in known_urls:
            counters["skipped_competitor_posts"] += 1
            continue
        for kw in CONTENT_KEYWORDS:
            if kw in caption:
                matched_posts.append(post)
                break

    if not matched_posts:
        print(f"  [SKIP] @{account} — no new keyword-matched posts")
        return 0

    if is_first_run:
        matched_posts.sort(
            key=lambda p: p.get("commentsCount") or p.get("comments") or 0,
            reverse=True,
        )
        matched_posts = matched_posts[:3]
        print(f"  [FIRST RUN] @{account} — top 3 posts:")
        for p in matched_posts:
            count = p.get("commentsCount") or 0
            preview = (p.get("caption") or "")[:60]
            print(f"    {count} comments — {preview}...")
    else:
        print(f"  [UPDATE] @{account} — {len(matched_posts)} new posts")

    counters["new_competitor_posts"] += len(matched_posts)
    new_urls = []
    source = f"@{account}"
    for post in matched_posts:
        url = get_post_url(post)
        if not url:
            continue
        comments = scrape_comments_for_post(url, source, limit=200)
        print(f"  Found {len(comments)} comments on {url}")
        for comment in comments:
            _process_comment(comment, source, url, seen_usernames, seen_comment_texts, counters)
        new_urls.append(url)

    if account not in scraped_posts:
        scraped_posts[account] = {"scraped_urls": []}
    scraped_posts[account]["scraped_urls"].extend(new_urls)
    scraped_posts[account]["scraped_urls"] = scraped_posts[account]["scraped_urls"][-100:]
    scraped_posts[account]["last_scraped"] = datetime.datetime.now().strftime("%Y-%m-%d")
    save_scraped_posts(scraped_posts)
    return len(new_urls)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global HASHTAGS
    HASHTAGS = get_todays_hashtags()

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
        "new_competitor_posts": 0,
        "skipped_competitor_posts": 0,
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
New competitor posts:       {counters["new_competitor_posts"]}
Skipped (already scraped): {counters["skipped_competitor_posts"]}
Total saved:               {total_saved}
""")
    print("--- Per Source Breakdown ---")
    for src, data in counters["sources"].items():
        print(f"  {src:<20} scanned: {data['scanned']} | qualified: {data['qualified']} | priority: {data['priority']}")
    print("---------------------")

    update_hashtag_performance(counters)

    import cost_tracker as ct
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    summary_path = os.path.join(OUTPUT_DIR, f"scrape_summary_{today}.json")
    haiku_calls = counters["priority_saved"] + counters["regular_saved"]
    counters["scraper_cost"] = ct.log_scraper_costs(
        apify_results=counters["scanned"],
        haiku_calls=haiku_calls,
        haiku_input_tokens=haiku_calls * 500,
        haiku_output_tokens=haiku_calls * 150,
    )
    print(f"Scraper cost logged: ${counters['scraper_cost']:.4f}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(counters, f, indent=2)
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
