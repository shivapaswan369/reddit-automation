import os
from datetime import datetime, timedelta
import pandas as pd
import pytz
import streamlit as st
from dotenv import load_dotenv
import database as db
import ai_generator
import reddit_service

load_dotenv()
db.init_db()
timezone_name = os.getenv("TIMEZONE", "Asia/Kolkata")
tz = pytz.timezone(timezone_name)

st.set_page_config(page_title="Reddit Automation", layout="wide")
st.title("Reddit Content Automation")
st.caption("Local dashboard. Automatic publishing requires scheduler_worker.py to run in a separate terminal.")

with st.sidebar:
    st.subheader("Reddit connection")
    if st.button("Test OAuth connection"):
        ok, message = reddit_service.verify_connection()
        st.success(message) if ok else st.error(message)
    st.write("Current time:", datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"), timezone_name)

create_tab, queue_tab, analytics_tab, logs_tab = st.tabs(
    ["Create & Schedule", "Post Queue", "Analytics", "Logs"]
)

with create_tab:
    topic = st.text_input("Topic", "Excel shortcuts that save time")
    subreddit = st.text_input("Subreddit name (without r/)", "excel")
    tone = st.selectbox("Writing style", ["Informative", "Friendly question", "Practical tip"])
    if st.button("Generate draft"):
        draft = ai_generator.generate_reddit_content(topic, subreddit.strip(), tone)
        st.session_state["draft_title"] = draft["title"]
        st.session_state["draft_body"] = draft["body"]

    title = st.text_input("Post title", st.session_state.get("draft_title", ""))
    body = st.text_area("Post body", st.session_state.get("draft_body", ""), height=220)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save draft"):
            if title.strip() and body.strip() and subreddit.strip():
                db.save_post(title, body, subreddit.strip(), status="draft")
                st.success("Draft saved.")
            else:
                st.error("Title, body, and subreddit are required.")
    with c2:
        schedule_date = st.date_input("Publish date (IST)", datetime.now(tz).date())
        schedule_time = st.time_input("Publish time (IST)", (datetime.now(tz) + timedelta(minutes=10)).time().replace(second=0, microsecond=0))
        if st.button("Schedule post"):
            if not title.strip() or not body.strip() or not subreddit.strip():
                st.error("Title, body, and subreddit are required.")
            else:
                scheduled = f"{schedule_date} {schedule_time.strftime('%H:%M:%S')}"
                if datetime.strptime(scheduled, "%Y-%m-%d %H:%M:%S") <= datetime.now(tz).replace(tzinfo=None):
                    st.error("Choose a future date and time.")
                else:
                    db.save_post(title, body, subreddit.strip(), scheduled_time=scheduled, status="scheduled")
                    st.success(f"Scheduled for {scheduled} IST. Keep the worker running.")

    st.warning("Review the subreddit rules and your draft before publishing. API access and permissions are required.")

with queue_tab:
    status = st.selectbox("Filter status", ["All", "draft", "scheduled", "publishing", "published", "failed", "needs_review"])
    posts = db.get_posts(status)
    if posts:
        df = pd.DataFrame([dict(row) for row in posts])
        cols = ["id", "title", "subreddit", "status", "scheduled_time", "reddit_post_id", "error_log"]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("No posts found.")

with analytics_tab:
    if st.button("Sync analytics now"):
        for post in db.get_posts("published"):
            if post["reddit_post_id"]:
                metrics, err = reddit_service.fetch_post_metrics(post["reddit_post_id"])
                if metrics:
                    db.update_metrics(post["reddit_post_id"], metrics["score"], metrics["num_comments"], metrics["upvote_ratio"])
                else:
                    db.log_event("WARNING", f"Analytics sync failed: {err}")
        st.rerun()
    posts = db.get_posts("published")
    if posts:
        df = pd.DataFrame([dict(row) for row in posts])
        columns = ["id", "title", "subreddit", "reddit_post_id", "score", "num_comments", "upvote_ratio", "last_synced_at"]
        st.dataframe(df[columns], use_container_width=True)
        st.download_button("Download CSV", df[columns].to_csv(index=False).encode("utf-8"), "reddit_analytics.csv", "text/csv")
    else:
        st.info("No published posts tracked yet.")

with logs_tab:
    logs = db.get_logs()
    if logs:
        st.dataframe(pd.DataFrame([dict(row) for row in logs]), use_container_width=True)
    else:
        st.info("No logs yet.")
