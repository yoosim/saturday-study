# -*- coding: utf-8 -*-
"""
Notion '문제 제출' DB 변경을 모니터링해 Discord로 알림 전송

환경변수 (.env 또는 GitHub Secrets)
- NOTION_API_KEY
- NOTION_DATABASE_ID
- DISCORD_WEBHOOK_URL          # GitHub Actions에서 secrets.DISCORD_WEBHOOK_NOTION_URL을 여기에 매핑

실행 예)
python -m AI_study_automation.scripts.notion_watch
"""

import re
import time
import requests
from datetime import datetime, timedelta, timezone

# 패키지/경로에 따라 둘 다 지원 (패키지로도, 스크립트로도 동작)
try:
    from AI_study_automation.scripts.utils import get_env, post_discord, KST
except Exception:
    from scripts.utils import get_env, post_discord, KST


# ─────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────
NOTION_API_KEY     = get_env("NOTION_API_KEY")
NOTION_DATABASE_ID = get_env("NOTION_DATABASE_ID")

# ✅ YAML에서 secrets.DISCORD_WEBHOOK_NOTION_URL → (env) DISCORD_WEBHOOK_URL 로 매핑해 전달
DISCORD_WEBHOOK_URL = get_env("DISCORD_WEBHOOK_URL")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

URL_RE = re.compile(r"(https?://\S+)", re.IGNORECASE)


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def iso_utc(dt: datetime) -> str:
    """datetime → ISO 8601 (UTC) 문자열"""
    return dt.astimezone(timezone.utc).isoformat()


def rich_text_to_str(rt) -> str:
    """Notion rich_text[] → plain text"""
    if not rt:
        return ""
    return "".join([b.get("plain_text", "") for b in rt])


def extract_links(text: str):
    """텍스트에서 URL만 추출(중복 제거하며 입력 순서 유지)"""
    links, seen = [], set()
    for u in URL_RE.findall(text or ""):
        if u not in seen:
            seen.add(u)
            links.append(u)
    return links


def page_to_message(page) -> str:
    """
    Notion 페이지 → 디스코드용 메시지 포맷
    필요한 Notion 속성(정확한 이름/타입으로 구성되어 있어야 함):
      - Name (title)
      - Week (date)
      - Submitter (rich_text)
      - Link (url)
      - More Links (rich_text)  # 내부에 여러 URL이 섞여 있는 자유 텍스트
    """
    props = page.get("properties", {})

    title     = rich_text_to_str(props.get("Name", {}).get("title", [])) or "(No title)"
    week      = (props.get("Week", {}) or {}).get("date", {}).get("start") or "-"
    submitter = rich_text_to_str(props.get("Submitter", {}).get("rich_text", [])) or "-"
    main_link = (props.get("Link", {}) or {}).get("url") or ""

    more_links_txt = rich_text_to_str(props.get("More Links", {}).get("rich_text", []))
    more_links     = extract_links(more_links_txt)

    lines = [
        "📣 Notion 문제 업데이트 📣",
        "",
        f"문제 풀이 일시 : {week}",
        f"문제 제공자 : {submitter}",
    ]

    idx = 1
    if main_link:
        lines.append(f"문제 {idx} : {main_link}")
        idx += 1
    if len(more_links) >= 1:
        lines.append(f"문제 {idx} : {more_links[0]}")
        idx += 1
    if len(more_links) >= 2:
        lines.append(f"문제 {idx} : {more_links[1]}")
        idx += 1

    remain = max(0, len(more_links) - 2)
    if remain > 0:
        lines.append(f"(More Links에 링크 {remain}건 추가로 있음)")

    # 제목 꼬리표(원치 않으면 아래 한 줄 제거)
    lines += ["", f"— {title}"]

    msg = "\n".join(lines)
    # Discord 2000자 제한 대비
    if len(msg) > 1900:
        msg = msg[:1900] + "\n…(truncated)"
    return msg


# ─────────────────────────────────────────────────────
# Query & Main
# ─────────────────────────────────────────────────────
def query_recent_pages(hours: int = 12):
    """
    최근 편집 페이지 조회 (기본: 지난 12시간)
    - last_edited_time >= since
    - 오름차순 정렬
    """
    since = datetime.now(KST) - timedelta(hours=hours)
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "timestamp": "last_edited_time",
            "last_edited_time": {"on_or_after": iso_utc(since)},
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "ascending"}],
        "page_size": 50,
    }
    r = requests.post(url, headers=HEADERS, json=payload, timeout=25)
    if r.status_code >= 400:
        print("[NOTION][ERROR]", r.status_code, r.text[:300])
    r.raise_for_status()
    return r.json().get("results", [])


def main():
    # 필수 ENV 확인
    missing = []
    if not NOTION_API_KEY:
        missing.append("NOTION_API_KEY")
    if not NOTION_DATABASE_ID:
        missing.append("NOTION_DATABASE_ID")
    if not DISCORD_WEBHOOK_URL:
        missing.append("DISCORD_WEBHOOK_URL")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    pages = query_recent_pages(hours=12)
    if not pages:
        print("[INFO] No recent updates.")
        return

    for idx, page in enumerate(pages, 1):
        content = page_to_message(page)
        try:
            post_discord(DISCORD_WEBHOOK_URL, content=content)
            print(f"[DISCORD] sent {idx}/{len(pages)}")
        except Exception as e:
            print("[DISCORD][EXCEPTION]", repr(e))
        time.sleep(1)


if __name__ == "__main__":
    main()
