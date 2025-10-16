# scripts/weekly_reminder.py
import os, json, requests
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from scripts.utils import get_env, post_discord, KST

# ──────────────────────────────────────────────────────────────────────────────
# ENV & CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
NOTION_API_KEY       = get_env("NOTION_API_KEY")
NOTION_DATABASE_ID   = get_env("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL  = get_env("DISCORD_WEBHOOK_URL_REMINDER")
NOTION_DB_URL        = os.environ.get("NOTION_DB_URL", "")
ROLE_ID              = os.environ.get("ROLE_ID_PROBLEM_SETTER")  # 선택

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

MEMBERS_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "members.json")

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def iso_utc(dt): 
    return dt.astimezone(timezone.utc).isoformat()

def rich_text_to_str(rt):
    if not rt: 
        return ""
    return "".join([b.get("plain_text","") for b in rt])

def uniq_preserve(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

def split_csv(text: str) -> List[str]:
    return [t.strip() for t in (text or "").split(",") if t.strip()]

def load_member_map() -> dict:
    try:
        with open(MEMBERS_MAP_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # 키를 소문자/trim으로 통일해 유연 매칭
        return { (k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if (k and v) }
    except FileNotFoundError:
        return {}

def names_to_user_ids(names: List[str], name2id: dict) -> List[str]:
    ids = []
    for n in names:
        k = n.strip().lower()
        if k and (k in name2id):
            ids.append(name2id[k])
    return uniq_preserve(ids)

# ──────────────────────────────────────────────────────────────────────────────
# NOTION
# ──────────────────────────────────────────────────────────────────────────────
def query_this_week_submitters_and_next() -> Tuple[List[str], List[str]]:
    now = datetime.now(KST)
    # 이번 주: 월 00:00 ~ 다음 주 월 00:00
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=7)

    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "Week", "date": {"on_or_after": iso_utc(start)}},
                {"property": "Week", "date": {"before":     iso_utc(end)}},
            ]
        },
        "page_size": 100,
    }
    r = requests.post(url, headers=HEADERS, json=payload, timeout=20)
    if r.status_code >= 400:
        print("[NOTION][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    results = r.json().get("results", [])

    submitters: List[str] = []
    next_submitters: List[str] = []

    for p in results:
        props = p.get("properties", {})
        # Submitter(Text)
        sub = rich_text_to_str(props.get("Submitter", {}).get("rich_text", []))
        submitters.extend(split_csv(sub))

        # (옵션) Next Submitters(Text)
        ns  = rich_text_to_str(props.get("Next Submitters", {}).get("rich_text", []))
        next_submitters.extend(split_csv(ns))

    submitters      = uniq_preserve(submitters)
    next_submitters = uniq_preserve(next_submitters)
    return submitters, next_submitters

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    submitters, next_submitters = query_this_week_submitters_and_next()

    if not submitters:
        post_discord(DISCORD_WEBHOOK_URL, content="🔔 이번 주 문제 카드가 없습니다. 확인 부탁드려요!")
        return

    # 디스코드 멘션(개인)
    name2id = load_member_map()
    user_ids = names_to_user_ids(submitters, name2id)
    user_mentions = " ".join([f"<@{uid}>" for uid in user_ids])

    # 역할 멘션(보조/폴백)
    role_mention = f"<@&{ROLE_ID}>" if ROLE_ID else "@문제제출자"

    # 본문 구성
    lines = [
        "🔔 수요일 리마인드",
        "이번 주 문제 제출자 :",
    ]
    # 표시용 이름(불릿)
    lines += [f"• {n}" for n in submitters]

    if NOTION_DB_URL:
        lines += ["", f"   ↳ {NOTION_DB_URL}"]

    if next_submitters:
        lines += ["", f"다음 주 예정 : {', '.join(next_submitters)}"]

    # 마지막 줄: 개인 멘션이 있으면 개인 멘션 + 역할, 없으면 역할만
    if user_mentions:
        lines += ["", f"담당 {user_mentions} 님, 등록/업데이트 부탁드려요!"]
        # {role_mention}
    else:
        lines += ["", f"담당 {role_mention} 님, 등록/업데이트 부탁드려요!"]

    content = "\n".join(lines)

    # 멘션 허용 제어 (users/roles만)
    allowed = {"parse": []}
    if user_ids:
        allowed["users"] = user_ids
    if ROLE_ID:
        allowed["roles"] = [ROLE_ID]

    # 전송
    r = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"content": content, "allowed_mentions": allowed},
        timeout=20,
    )
    if r.status_code >= 400:
        print("[DISCORD][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    print("[DISCORD] reminder sent:", r.status_code)

if __name__ == "__main__":
    main()
