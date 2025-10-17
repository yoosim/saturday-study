# -*- coding: utf-8 -*-
"""
매주 수요일(KST 09:00) 문제 제출 리마인드
- 이번 주 'Week' 기간에 해당하는 카드의 Submitter/Next Submitters를 읽어
  Discord 채널에 멘션과 함께 리마인드 메시지 전송

필요 ENV (.env 또는 GitHub Secrets → GitHub Actions env로 전달)
- NOTION_API_KEY
- NOTION_DATABASE_ID
- DISCORD_WEBHOOK_URL_REMINDER   # YAML에서 secrets.DISCORD_WEBHOOK_NOTION_URL을 여기에 매핑
- NOTION_DB_URL                  # (선택) 노션 보드 링크
- ROLE_ID_PROBLEM_SETTER         # (선택) 역할 멘션 ID

실행 예)
python -m AI_study_automation.scripts.weekly_reminder
"""

import os, json, requests
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

# utils 모듈: get_env(key, default=None), post_discord(url, content=..., **kwargs), KST(tzinfo)
try:
    from AI_study_automation.scripts.utils import get_env, post_discord, KST
except Exception:
    from scripts.utils import get_env, post_discord, KST


# ──────────────────────────────────────────────────────────────────────────────
# ENV & CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
NOTION_API_KEY       = get_env("NOTION_API_KEY")
NOTION_DATABASE_ID   = get_env("NOTION_DATABASE_ID")

# YAML에서 secrets.DISCORD_WEBHOOK_NOTION_URL → DISCORD_WEBHOOK_URL_REMINDER로 매핑해 전달
DISCORD_WEBHOOK_URL  = get_env("DISCORD_WEBHOOK_NOTION_URL")

NOTION_DB_URL        = get_env("NOTION_DB_URL", "")
ROLE_ID              = get_env("ROLE_ID_PROBLEM_SETTER")  # 선택

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# members.json: {"홍길동":"123456789012345678", "Alice":"2345..."}
MEMBERS_MAP_PATH = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "members.json")
)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def rich_text_to_str(rt) -> str:
    if not rt:
        return ""
    return "".join([b.get("plain_text","") for b in rt])

def uniq_preserve(seq: List[str]) -> List[str]:
    seen, out = set(), []
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
        k = (n or "").strip().lower()
        if k and (k in name2id):
            ids.append(name2id[k])
    return uniq_preserve(ids)

def send_discord(content: str, allowed_mentions: dict | None = None):
    """
    post_discord 유틸이 allowed_mentions를 지원하지 않을 수 있어 직접 호출을 래핑.
    utils.post_discord가 allowed_mentions를 지원한다면 그걸 써도 무방.
    """
    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL_REMINDER")
    payload = {"content": content}
    if allowed_mentions is not None:
        payload["allowed_mentions"] = allowed_mentions
    r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
    if r.status_code >= 400:
        print("[DISCORD][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    print("[DISCORD] reminder sent:", r.status_code)


# ──────────────────────────────────────────────────────────────────────────────
# NOTION
# ──────────────────────────────────────────────────────────────────────────────
def query_this_week_submitters_and_next() -> Tuple[List[str], List[str]]:
    """
    이번 주(월 00:00 ~ 다음 주 월 00:00, KST 기준)의 카드에서
    Submitter, Next Submitters(둘 다 rich_text, 쉼표 구분)를 수집
    """
    now = datetime.now(KST)
    # 이번 주: 월요일 00:00
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
        print("[NOTION][ERROR]", r.status_code, r.text[:300])
    r.raise_for_status()
    results = r.json().get("results", [])

    submitters: List[str] = []
    next_submitters: List[str] = []

    for p in results:
        props = p.get("properties", {})
        # Submitter(Text rich_text)
        sub = rich_text_to_str(props.get("Submitter", {}).get("rich_text", []))
        submitters.extend(split_csv(sub))

        # (옵션) Next Submitters(Text rich_text)
        ns  = rich_text_to_str(props.get("Next Submitters", {}).get("rich_text", []))
        next_submitters.extend(split_csv(ns))

    return uniq_preserve(submitters), uniq_preserve(next_submitters)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # 필수 ENV 검증
    missing = []
    if not NOTION_API_KEY:     missing.append("NOTION_API_KEY")
    if not NOTION_DATABASE_ID: missing.append("NOTION_DATABASE_ID")
    if not DISCORD_WEBHOOK_URL:missing.append("DISCORD_WEBHOOK_URL_REMINDER")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    submitters, next_submitters = query_this_week_submitters_and_next()

    if not submitters:
        # 이번 주 카드가 없으면 간단 알림
        post_discord(DISCORD_WEBHOOK_URL, content="🔔 이번 주 문제 카드가 없습니다. 확인 부탁드려요!")
        return

    # 멘션 구성
    name2id = load_member_map()
    user_ids = names_to_user_ids(submitters, name2id)
    user_mentions = " ".join([f"<@{uid}>" for uid in user_ids])

    role_mention = f"<@&{ROLE_ID}>" if ROLE_ID else "@문제제출자"

    # 본문
    lines = [
        "🔔 수요일 리마인드",
        "이번 주 문제 제출자 :",
    ]
    lines += [f"• {n}" for n in submitters]

    if NOTION_DB_URL:
        lines += ["", f"   ↳ {NOTION_DB_URL}"]

    if next_submitters:
        lines += ["", f"다음 주 예정 : {', '.join(next_submitters)}"]

    if user_mentions:
        lines += ["", f"담당 {user_mentions} 님, 등록/업데이트 부탁드려요!"]
    else:
        lines += ["", f"담당 {role_mention} 님, 등록/업데이트 부탁드려요!"]

    content = "\n".join(lines)

    # allowed_mentions: 기본 파싱 차단 + 필요한 user/role만 허용
    allowed = {"parse": []}
    if user_ids:
        allowed["users"] = user_ids
    if ROLE_ID:
        allowed["roles"] = [ROLE_ID]

    send_discord(content, allowed_mentions=allowed)


if __name__ == "__main__":
    main()
