from playwright.sync_api import sync_playwright
import datetime
import os

OUTPUT_DIR = "03_CRM/Lead_Signals"

ICP_KEYWORDS = [
    "discipline",
    "focus",
    "wasting",
    "potential",
    "stuck",
    "procrastinating",
    "can't stay consistent",
    "wasting time",
    "can't focus"
]

def save_lead(username, comment):

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{OUTPUT_DIR}/lead_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Instagram Lead Signal\n\n")
        f.write(f"User: {username}\n\n")
        f.write("Comment:\n")
        f.write(comment)

def matches_icp(text):

    text_lower = text.lower()

    for keyword in ICP_KEYWORDS:
        if keyword in text_lower:
            return True

    return False


def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        with open("01_Inbox/discovery_targets/targets.md") as f:
            targets = f.readlines()

        page.goto(account_url)

        print("Waiting for Instagram login...")
        page.wait_for_selector('svg[aria-label="Search"]', timeout=120000)

        page.wait_for_timeout(5000)

        posts = page.query_selector_all("article a")

        post_urls = []

        for p in posts[:5]:

            try:
                post_urls.append("https://instagram.com" + p.get_attribute("href"))
            except:
                pass

        print("Found posts:", len(post_urls))

        for post in post_urls:

            print("Scanning post:", post)

            page.goto(post)

            page.wait_for_timeout(4000)

            comments = page.query_selector_all("ul li")

            for c in comments[:30]:

                try:
                    username = c.query_selector("h3").inner_text()
                    text = c.query_selector("span").inner_text()

                    if matches_icp(text):

                        print("ICP lead detected:", username)

                        save_lead(username, text)

                except:
                    pass

        browser.close()


run()