# scripts/daily_attendance.py
import os, json, requests
from datetime import datetime, timedelta, timezone
from scripts.utils import get_env, post_discord, KST

NOTION_API_KEY            = get_env("NOTION_API_KEY")
NOTION_SUBMISSIONS_DB_ID  = get_env("NOTION_SUBMISSIONS_DB_ID")
DISCORD_WEBHOOK_URL       = get_env("DISCORD_WEBHOOK_URL_REMINDER")  # 요약은 리마인드 채널로
# ATTENDANCE_DB_ID          = os.environ.get("NOTION_ATTENDANCE_DB_ID")  # 선택
MEMBERS_MAP_PATH          = os.path.join(os.path.dirname(__file__), "..", "config", "members.json")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def load_members():
    # members.json 의 key를 멤버명으로 사용 (["재성","성미",...])
    try:
        raw = json.load(open(MEMBERS_MAP_PATH,"r",encoding="utf-8"))
        return list(raw.keys())
    except:
        # fallback: ENV MEMBERS_CSV="A,B,C"
        csv = os.environ.get("MEMBERS_CSV","")
        return [s.strip() for s in csv.split(",") if s.strip()]

def notion_query(dbid, payload):
    url = f"https://api.notion.com/v1/databases/{dbid}/query"
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    if r.status_code >= 400:
        print("[NOTION][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def notion_create(dbid, props):
    url = "https://api.notion.com/v1/pages"
    r = requests.post(url, headers=HEADERS, json={"parent":{"database_id":dbid},"properties":props}, timeout=30)
    if r.status_code >= 400:
        print("[NOTION][CREATE][ERROR]", r.status_code, r.text)
    r.raise_for_status()

def props_attendance(name, date_str, status, first_time=None):
    props = {
        "Name": {"title":[{"text":{"content": f"{date_str}_{name}"}}]},
        "Date": {"date":{"start": date_str}},
        "Member": {"rich_text":[{"text":{"content": name}}]},
        "Status": {"select":{"name": status}},
    }
    if first_time:
        props["First Submit Time"] = {"date":{"start": first_time}}
    return props

def main():
    today = datetime.now(KST)
    date_str = today.strftime("%Y-%m-%d")

    # 오늘자 제출자 목록
    q = {"filter":{"property":"Week","date":{"equals":date_str}}, "page_size":200}
    res = notion_query(NOTION_SUBMISSIONS_DB_ID, q)
    submitted = set()
    first_time_map = {}
    for r in res.get("results",[]):
        props = r["properties"]
        name = (props["Submitter"]["rich_text"] or [{}])[0].get("plain_text","")
        when = (props["Commit Time"]["date"] or {}).get("start")
        if not name: 
            continue
        submitted.add(name)
        if when and name not in first_time_map:
            first_time_map[name] = when

    members = load_members()
    lines = [f"🗓️ {date_str} 출석 요약"]
    for m in members:
        if m in submitted:
            t = first_time_map.get(m)
            if t:
                t_kst = datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(KST)
                lines.append(f"✅ {m} — 퀴즈풀이 완료 ({t_kst.strftime('%H:%M')})")
            else:
                lines.append(f"✅ {m} — 퀴즈풀이 완료")
            status = "Present"
        else:
            lines.append(f"❌ {m} — 미참여(결석)")
            status = "Absent"

        # 기록 DB가 있으면 적재
        if ATTENDANCE_DB_ID:
            first_iso = first_time_map.get(m)
            notion_create(ATTENDANCE_DB_ID, props_attendance(m, date_str, status, first_iso))

    post_discord(os.environ.get("DISCORD_WEBHOOK_URL_REMINDER", DISCORD_WEBHOOK_URL), "\n".join(lines))

if __name__ == "__main__":
    main()
