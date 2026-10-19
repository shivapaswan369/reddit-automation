import os
from dotenv import load_dotenv
load_dotenv()

def generate_reddit_content(topic, subreddit, tone="Informative"):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {
            "title": f"How do you handle {topic}?",
            "body": f"I'm learning about {topic} and want to compare practical approaches in r/{subreddit}.\n\n"
                    "What methods have worked well for you, and what mistakes should beginners avoid?"
        }
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""Create an authentic, useful Reddit discussion draft for r/{subreddit}.
Topic: {topic}
Tone: {tone}
Avoid promotional claims and respect that subreddit may have its own rules.
Return exactly:
[TITLE]
one title
[BODY]
post body in Markdown"""
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        output = (response.text or "").strip()
        if "[TITLE]" in output and "[BODY]" in output:
            before, body = output.split("[BODY]", 1)
            title = before.replace("[TITLE]", "").strip()
            body = body.strip()
        else:
            lines = output.splitlines()
            title = lines[0].lstrip("# ").strip() if lines else f"Discussion: {topic}"
            body = "\n".join(lines[1:]).strip()
        if not title or not body:
            raise ValueError("Gemini returned an empty title or body.")
        return {"title": title, "body": body}
    except Exception as exc:
        return {"title": f"Draft: {topic}", "body": f"AI generation failed: {exc}\n\nPlease edit this draft manually."}
