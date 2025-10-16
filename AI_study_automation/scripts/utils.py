import os, time, requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

KST = timezone(timedelta(hours=9))

def get_env(key: str) -> str:
    v = os.environ.get(key)
    if not v:
        raise RuntimeError(f"Missing environment variable: {key}")
    return v

def post_discord(webhook_url: str, content=None, embeds=None, allow_roles=False):
    content = (content or "")
    if len(content) > 1800:
        content = content[:1800] + "\n…(truncated)"
    payload = {
        "content": content,
        "embeds": embeds or [],
        "allowed_mentions": {"parse": ["roles"] if allow_roles else []}
    }
    r = requests.post(webhook_url, json=payload, timeout=20)
    if r.status_code == 429:
        wait = int(r.headers.get("Retry-After", "1"))
        time.sleep(wait)
        r = requests.post(webhook_url, json=payload, timeout=20)
    # ↓ 디버그: 실패 시 서버 응답 보여주기
    if r.status_code >= 400:
        print("Discord error:", r.status_code, r.text)
    r.raise_for_status()

def chunk_embeds(embeds, size=10):
    for i in range(0, len(embeds), size):
        yield embeds[i:i+size]
