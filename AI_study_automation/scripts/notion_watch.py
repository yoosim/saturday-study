# scripts/notion_watch.py
import os, re, time, requests, json
from datetime import datetime, timedelta, timezone
from scripts.utils import get_env, post_discord, KST

# =======================
# 환경 변수 로드 & 점검 로그
# =======================
NOTION_API_KEY = get_env("NOTION_API_KEY")
NOTION_DATABASE_ID = get_env("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = get_env("DISCORD_WEBHOOK_URL")

def dbg_env():
    def mask(s, head=6, tail=4):
        if not s: return ""
        if len(s) <= head + tail: return s
        return s[:head] + "..." + s[-tail:]
    print("[ENV] NOTION_API_KEY:", mask(NOTION_API_KEY))
    print("[ENV] NOTION_DATABASE_ID:", NOTION_DATABASE_ID, "len:", len(NOTION_DATABASE_ID))
    print("[ENV] DISCORD_WEBHOOK_URL:", mask(DISCORD_WEBHOOK_URL, 30, 10))

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

URL_RE = re.compile(r"(https?://[^\s,，、]+)", re.IGNORECASE)

def iso_utc(dt): 
    return dt.astimezone(timezone.utc).isoformat()

def rich_text_to_str(rt):
    if not rt: 
        return ""
    return "".join([b.get("plain_text","") for b in rt])

def extract_links(text):
    links, seen = [], set()
    for u in URL_RE.findall(text or ""):
        if u not in seen:
            seen.add(u)
            links.append(u)
    return links

def page_to_embed_and_content(page):
    props = page.get("properties", {})
    title = rich_text_to_str(props.get("Name", {}).get("title", [])) or "(No title)"
    link  = (props.get("Link", {}) or {}).get("url") or ""
    more_links_txt = rich_text_to_str(props.get("More Links", {}).get("rich_text", []))
    more_links = extract_links(more_links_txt)

    difficulty = props.get("Difficulty", {}).get("select", {}).get("name", "-")
    status     = props.get("Status", {}).get("select", {}).get("name", "-")
    submitter  = rich_text_to_str(props.get("Submitter", {}).get("rich_text", [])) or "-"
    week       = props.get("Week", {}).get("date", {}).get("start")
    page_url   = page.get("url")

    embed = {
        "title": f"📌 새/업데이트 문제: {title}",
        "url": page_url,
        "fields": [
            {"name": "Difficulty", "value": difficulty or "-", "inline": True},
            {"name": "Status",     "value": status or "-",     "inline": True},
            {"name": "Submitter",  "value": submitter or "-",  "inline": True},
            {"name": "Week",       "value": week or "-",       "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    lines = ["📣 Notion 문제 업데이트", ""]

    if link:
        lines.append(f"문제 링크: {link}")

    if more_links:
        lines.extend(more_links)

    content = "\n".join(lines)
    # 디스코드 2000자 제한 가드
    if len(content) > 1800:
        content = content[:1800] + "\n…(truncated)"
    return embed, content

def query_recent_pages(hours=12):
    since = datetime.now(KST) - timedelta(hours=hours)
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "timestamp": "last_edited_time",
            "last_edited_time": {"on_or_after": iso_utc(since)}
        },
        "sorts": [
            {"timestamp": "last_edited_time", "direction": "ascending"}
        ],
        "page_size": 50
    }
    print("[NOTION] POST", url)
    print("[NOTION] payload:", json.dumps(payload, ensure_ascii=False))
    res = requests.post(url, headers=HEADERS, json=payload, timeout=20)

    if res.status_code >= 400:
        print("[NOTION][ERROR]", res.status_code, res.text)
    else:
        js = res.json()
        print("[NOTION] ok. count:", len(js.get("results", [])))

    res.raise_for_status()
    return res.json().get("results", [])

def main():
    dbg_env()
    results = query_recent_pages(hours=12)
    if not results:
        print("[INFO] No recent updates.")
        return

    for idx, page in enumerate(results, 1):
        embed, content = page_to_embed_and_content(page)
        print(f"[DISCORD] sending {idx}/{len(results)} | content_len={len(content)}")
        try:
            # post_discord 내부에서도 4xx 출력하도록 구현했다면 여기 로그만으로 충분
            r = requests.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "content": content or "📣 Notion 업데이트",
                    "embeds": [embed],
                    "allowed_mentions": {"parse": []}
                },
                timeout=20
            )
            if r.status_code >= 400:
                print("[DISCORD][ERROR]", r.status_code, r.text)
            else:
                print("[DISCORD] ok.", r.status_code)
            r.raise_for_status()
        except Exception as e:
            print("[DISCORD][EXCEPTION]", repr(e))
        time.sleep(1)

if __name__ == "__main__":
    main()
