from playwright.sync_api import sync_playwright
import datetime

OUTPUT_FILE = "01_Inbox/discovery_targets/targets.md"

HASHTAGS = [
    "selfimprovement",
    "discipline",
    "productivity",
    "focus",
    "mindset"
]

def save_target(username):

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:

        f.write(f"- https://instagram.com/{username}\n")

def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://instagram.com")

        print("Waiting for Instagram login...")
        page.wait_for_selector('svg[aria-label="Search"]', timeout=120000)

        for hashtag in HASHTAGS:

            url = f"https://www.instagram.com/explore/tags/{hashtag}/"

            print("Scanning hashtag:", hashtag)

            page.goto(url)

            page.wait_for_timeout(5000)

            posts = page.query_selector_all("article a")

            for post in posts[:10]:

                try:

                    link = "https://instagram.com" + post.get_attribute("href")

                    page.goto(link)

                    page.wait_for_timeout(3000)

                    username = page.query_selector("header a").inner_text()

                    print("Found creator:", username)

                    save_target(username)

                except:
                    pass

        browser.close()

run()