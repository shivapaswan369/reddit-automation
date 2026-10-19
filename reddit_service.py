import os
import praw
from dotenv import load_dotenv
from prawcore.exceptions import RequestException, ResponseException

load_dotenv()

def get_reddit_client():
    required = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REFRESH_TOKEN"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        return None, "Missing .env values: " + ", ".join(missing)
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "windows:reddit_automation:v1.0")
        )
        return reddit, None
    except Exception as exc:
        return None, str(exc)

def verify_connection():
    reddit, err = get_reddit_client()
    if err:
        return False, err
    try:
        user = reddit.user.me()
        return (True, f"Connected as u/{user.name}") if user else (False, "Reddit did not return an account identity.")
    except Exception as exc:
        return False, str(exc)

def find_recent_matching_post(reddit, subreddit_name, title, body):
    """Best-effort check after uncertain network results; not a mathematical guarantee."""
    try:
        user = reddit.user.me()
        if not user:
            return None
        for submission in user.submissions.new(limit=25):
            if (submission.subreddit.display_name.lower() == subreddit_name.lower()
                and submission.title.strip() == title.strip()
                and (submission.selftext or "").strip() == body.strip()):
                return submission.id
    except Exception:
        return None
    return None

def submit_post(subreddit_name, title, body):
    reddit, err = get_reddit_client()
    if err:
        return False, err, False
    try:
        # Pre-check for recent identical content before submission.
        existing = find_recent_matching_post(reddit, subreddit_name, title, body)
        if existing:
            return True, existing, False
        submission = reddit.subreddit(subreddit_name).submit(title=title, selftext=body)
        return True, submission.id, False
    except (RequestException, ResponseException) as exc:
        existing = find_recent_matching_post(reddit, subreddit_name, title, body)
        if existing:
            return True, existing, False
        return False, f"Submission outcome is uncertain: {exc}", True
    except Exception as exc:
        return False, str(exc), False

def fetch_post_metrics(reddit_post_id):
    reddit, err = get_reddit_client()
    if err:
        return None, err
    try:
        submission = reddit.submission(id=reddit_post_id)
        return {
            "score": submission.score,
            "num_comments": submission.num_comments,
            "upvote_ratio": submission.upvote_ratio
        }, None
    except Exception as exc:
        return None, str(exc)
