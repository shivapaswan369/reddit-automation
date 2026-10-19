import time
import schedule
import database as db
import reddit_service as reddit

def publish_due():
    for post in db.claim_due_posts():
        db.log_event("INFO", f"Publishing queued item #{post['id']} to r/{post['subreddit']}")
        ok, result, uncertain = reddit.submit_post(post["subreddit"], post["title"], post["body"])
        if ok:
            db.mark_published(post["id"], result)
            db.log_event("SUCCESS", f"Item #{post['id']} published or matching post found: {result}")
        elif uncertain:
            db.mark_status(post["id"], "needs_review", result)
            db.log_event("WARNING", f"Item #{post['id']} needs manual review; no blind retry.")
        else:
            db.mark_status(post["id"], "failed", result)
            db.log_event("ERROR", f"Item #{post['id']} failed: {result}")

def sync_metrics():
    for post in db.get_posts("published"):
        post_id = post["reddit_post_id"]
        if not post_id:
            continue
        metrics, err = reddit.fetch_post_metrics(post_id)
        if metrics:
            db.update_metrics(post_id, metrics["score"], metrics["num_comments"], metrics["upvote_ratio"])
        else:
            db.log_event("WARNING", f"Metrics sync failed for {post_id}: {err}")

def main():
    db.init_db()
    db.recover_interrupted_posts()
    db.log_event("SYSTEM", "Worker started.")
    schedule.every(20).seconds.do(publish_due)
    schedule.every(5).minutes.do(sync_metrics)
    publish_due()
    sync_metrics()
    print("Worker running. Keep this terminal open. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(2)

if __name__ == "__main__":
    main()
