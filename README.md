# Reddit Automation (Windows)

A local Streamlit dashboard with draft generation, scheduled publishing, and post analytics. This project is provided as a starter implementation; live Reddit actions depend on API access and valid OAuth credentials.

## Requirements
- Python 3.10 or newer
- A Reddit app and authorized API access
- Optional Gemini API key for AI draft generation

## Install
Open Command Prompt in this folder:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT` in `.env`. Leave `REDDIT_REFRESH_TOKEN` blank initially.

## Reddit OAuth
Configure your Reddit app's redirect URI as exactly `http://localhost:8080`. Run:

```bat
python auth_helper.py
```

Open the authorization URL, approve it, then paste the full redirected URL (or its code) into the terminal. Add the returned `REDDIT_REFRESH_TOKEN` to `.env`. Keep `.env` private and never share tokens. OAuth setup may fail if Reddit does not grant API access or the app type/redirect configuration is incompatible.

## Run
Use two Command Prompt windows, both opened in this folder and with the virtual environment activated.

Window 1 — scheduler:
```bat
python scheduler_worker.py
```

Window 2 — dashboard:
```bat
streamlit run app.py
```

The scheduler checks due posts every 20 seconds and refreshes metrics every 5 minutes. Keep Window 1 open; this is not a cloud-hosted service. The computer must remain awake and connected to the internet.

## Important limitations
- The code cannot guarantee exactly-once posting because Reddit submission and local database updates are separate operations. If a request times out, the item is flagged for manual review instead of blindly retrying.
- The matching-post check is best effort and only inspects recent account submissions.
- Confirm subreddit rules and API access before publishing. First test OAuth and use a suitable test subreddit only if you have permission to post there.
- Do not commit or share `.env`.
