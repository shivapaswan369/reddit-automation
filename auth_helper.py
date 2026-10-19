import os
from urllib.parse import urlparse, parse_qs
import praw
from dotenv import load_dotenv

load_dotenv()

def main():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "windows:reddit_automation:v1.0")
    if not client_id or not client_secret:
        print("First set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file.")
        return

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8080",
        user_agent=user_agent
    )
    url = reddit.auth.url(
        scopes=["identity", "submit", "read", "history"],
        state="reddit_automation_setup",
        duration="permanent"
    )
    print("\nOpen this URL and approve access:\n")
    print(url)
    raw = input("\nPaste the redirected URL (or the code value): ").strip()
    if "://" in raw:
        parsed = urlparse(raw)
        params = parse_qs(parsed.query)
        if params.get("state", [""])[0] != "reddit_automation_setup":
            print("State mismatch. Stop and run the helper again.")
            return
        code = params.get("code", [""])[0]
    else:
        code = raw.split("code=", 1)[-1].split("&", 1)[0]
    if not code:
        print("No authorization code found.")
        return
    try:
        token = reddit.auth.authorize(code)
        print("\nRefresh token obtained. Add this line to .env:\n")
        print("REDDIT_REFRESH_TOKEN=" + token)
        print("\nTreat this token as a password. Do not share it.")
    except Exception as exc:
        print("Token exchange failed:", exc)

if __name__ == "__main__":
    main()
