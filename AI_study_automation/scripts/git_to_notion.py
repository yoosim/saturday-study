# scripts/git_to_notion.py
import os, re, argparse, json, requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
from scripts.utils import get_env, post_discord, KST

# ─────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────
NOTION_API_KEY            = get_env("NOTION_API_KEY")
NOTION_DATABASE_ID_PROB   = get_env("NOTION_DATABASE_ID")                 # 문제 DB (기존)
NOTION_SUBMISSIONS_DB_ID  = get_env("NOTION_SUBMISSIONS_DB_ID")           # 제출 로그 DB (신규)
DISCORD_WEBHOOK_URL       = get_env("DISCORD_WEBHOOK_URL")                # 제출 알림 채널
NOTION_DB_URL             = os.environ.get("NOTION_DB_URL", "")
DEADLINE_HOUR_KST         = int(os.environ.get("DEADLINE_HOUR_KST", "23"))  # 마감시각(기본 23:00)
MEMBERS_MAP_PATH          = os.path.join(os.path.dirname(__file__), "..", "config", "members.json")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
PATH_RE = re.compile(r"^study/([^/]+)/(\d{4}-\d{2}-\d{2})/(.+)$")

def parse_changed_paths(paths: List[str]) -> List[Tuple[str,str,str,str]]:
    """return list of (name, date, problem, path) from study/<name>/<YYYY-MM-DD>/<file>"""
    found = []
    for p in paths:
        m = PATH_RE.match(p.strip())
        if not m: 
            continue
        name, date_str, tail = m.groups()
        # 문제명: 파일명에서 확장자 제거
        problem = tail.rsplit("/", 1)[-1]
        problem = problem.rsplit(".", 1)[0]
        found.append((name, date_str, problem, p))
    return found

def kst_now_iso():
    return datetime.now(KST).astimezone(timezone.utc).isoformat()

def to_kst(dt: datetime) -> datetime:
    return dt.astimezone(KST)

def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def load_member_map() -> Dict[str,str]:
    try:
        with open(MEMBERS_MAP_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return { (k or "").strip().lower(): (v or "").strip() for k,v in raw.items() if k and v }
    except FileNotFoundError:
        return {}

def notion_query(dbid: str, payload: dict) -> dict:
    url = f"https://api.notion.com/v1/databases/{dbid}/query"
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    if r.status_code >= 400:
        print("[NOTION][QUERY][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def notion_create(dbid: str, props: dict) -> str:
    url = "https://api.notion.com/v1/pages"
    payload = {"parent": {"database_id": dbid}, "properties": props}
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    if r.status_code >= 400:
        print("[NOTION][CREATE][ERROR]", r.status_code, r.text)
    r.raise_for_status()
    return r.json().get("id")

def notion_update(page_id: str, props: dict):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    r = requests.patch(url, headers=HEADERS, json={"properties": props}, timeout=30)
    if r.status_code >= 400:
        print("[NOTION][UPDATE][ERROR]", r.status_code, r.text)
    r.raise_for_status()

def props_submission(name, date_str, problem, commit_dt_kst, file_path, repo=None, branch=None, sha=None, pr_url=None, ontime=None, late_min=None):
    props = {
        "Name": {"title": [{"text": {"content": f"{date_str}_{name}"}}]},
        "Week": {"date": {"start": date_str}},
        "Submitter": {"rich_text": [{"text": {"content": name}}]},
        "Problem": {"rich_text": [{"text": {"content": problem}}]},
        "File Path": {"rich_text": [{"text": {"content": file_path}}]},
        "Commit Time": {"date": {"start": iso(commit_dt_kst)}},
        "Status": {"select": {"name": "Submitted"}},
    }
    if repo or branch:
        props["Repo/Branch"] = {"rich_text": [{"text": {"content": f"{repo or ''} / {branch or ''}"}}]}
    if sha:
        props["SHA"] = {"rich_text": [{"text": {"content": sha}}]}
    if pr_url:
        props["PR URL"] = {"url": pr_url}
    if ontime is not None:
        props["On-time"] = {"checkbox": bool(ontime)}
    if late_min is not None:
        props["Late (min)"] = {"number": int(late_min)}
    return props

def upsert_submission(name, date_str, problem, commit_dt_kst, file_path, repo=None, branch=None, sha=None, pr_url=None):
    # 업서트 키: Date + Submitter + File Path
    q = {
        "filter": {
            "and": [
                {"property": "Week", "date": {"equals": date_str}},
                {"property": "Submitter", "rich_text": {"equals": name}},
                {"property": "File Path", "rich_text": {"equals": file_path}},
            ]
        },
        "page_size": 1
    }
    res = notion_query(NOTION_SUBMISSIONS_DB_ID, q)
    # 마감/지각 계산
    deadline_kst = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST).replace(hour=DEADLINE_HOUR_KST, minute=0, second=0, microsecond=0)
    ontime = commit_dt_kst <= deadline_kst
    late_min = 0 if ontime else int((commit_dt_kst - deadline_kst).total_seconds() // 60)

    props = props_submission(name, date_str, problem, commit_dt_kst, file_path, repo, branch, sha, pr_url, ontime, late_min)

    if res.get("results"):
        page_id = res["results"][0]["id"]
        notion_update(page_id, props)
        return page_id, "update"
    else:
        page_id = notion_create(NOTION_SUBMISSIONS_DB_ID, props)
        return page_id, "create"

def mark_problem_done_if_match(name, date_str):
    # 문제 DB에서 Submitter contains name & Week equals date
    q = {
        "filter": {
            "and": [
                {"property": "Submitter", "rich_text": {"contains": name}},
                {"property": "Week", "date": {"equals": date_str}}
            ]
        },
        "page_size": 5
    }
    res = notion_query(NOTION_DATABASE_ID_PROB, q)
    for p in res.get("results", []):
        pid = p["id"]
        # 이미 Done이면 패스
        st = (p.get("properties", {}).get("Status", {}).get("select") or {}).get("name")
        if st == "Done":
            continue
        notion_update(pid, {"Status": {"select": {"name": "Done"}}})

def query_today_submissions_kst(today_kst: datetime):
    date_str = today_kst.strftime("%Y-%m-%d")
    q = {
        "filter": {"property": "Week", "date": {"equals": date_str}},
        "sorts": [{"timestamp": "last_edited_time", "direction": "ascending"}],
        "page_size": 100
    }
    res = notion_query(NOTION_SUBMISSIONS_DB_ID, q)
    entries = []
    for r in res.get("results", []):
        props = r.get("properties", {})
        name = ((props.get("Submitter", {}) or {}).get("rich_text") or [{}])[0].get("plain_text","")
        prob = ((props.get("Problem", {}) or {}).get("rich_text") or [{}])[0].get("plain_text","미지정")
        when = (props.get("Commit Time", {}) or {}).get("date", {}).get("start")
        entries.append((prob, name, when))
    return entries

def build_daily_message(entries: List[Tuple[str,str,str]], today_kst: datetime) -> str:
    # Group by problem
    groups: Dict[str, List[Tuple[str,str]]] = {}
    for prob, name, when in entries:
        groups.setdefault(prob, []).append((name, when))
    # 정렬: 문제명 알파 → 시간
    msg_lines = []
    date_str = today_kst.strftime("%Y-%m-%d")
    for prob in sorted(groups.keys()):
        msg_lines.append(f"{prob}")
        for name, when in sorted(groups[prob], key=lambda x: x[1]):
            # 시간 표시 KST HH:MM
            t = datetime.fromisoformat(when.replace("Z","+00:00")).astimezone(KST)
            msg_lines.append(f"{name}님 과제 제출 완료 ( {date_str} {t.strftime('%H:%M')} )")
        msg_lines.append("")  # 빈 줄
    if NOTION_DB_URL:
        msg_lines.append(f"↳ 오늘자 제출 로그: {NOTION_DB_URL}")
    return "\n".join(msg_lines).strip()

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default="")              # 콤마/개행 구분 가능
    ap.add_argument("--event", default="")              # push / pull_request
    ap.add_argument("--action", default="")             # opened / synchronize / closed
    ap.add_argument("--is_merged", default="false")     # PR merged 여부
    ap.add_argument("--pr_title", default="")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY",""))
    ap.add_argument("--ref", default=os.environ.get("GITHUB_REF",""))
    ap.add_argument("--sha", default=os.environ.get("GITHUB_SHA",""))
    ap.add_argument("--pr_url", default=os.environ.get("GITHUB_SERVER_URL","") + "/" + os.environ.get("GITHUB_REPOSITORY",""))
    args = ap.parse_args()

    # 1) 변경 경로 파싱
    raw = args.paths.replace("\r"," ").replace("\n"," ").replace(",", " ")
    paths = [p for p in raw.split(" ") if p]
    changes = parse_changed_paths(paths)
    if not changes:
        print("[INFO] No study/ submissions detected.")
        return

    # 2) 커밋 시각(KST)
    # GITHUB_ACTIONS에서는 커밋시각을 git로부터 가져오기 어려울 수 있어 now(KST) 사용
    commit_dt_kst = datetime.now(KST)

    # 3) 업서트 + 문제 Done
    for (name, date_str, problem, file_path) in changes:
        pid, op = upsert_submission(
            name=name,
            date_str=date_str,
            problem=problem,
            commit_dt_kst=commit_dt_kst,
            file_path=file_path,
            repo=args.repo,
            branch=args.ref,
            sha=args.sha,
            pr_url=args.pr_url if "pull" in args.pr_url else None
        )
        print(f"[NOTION][SUBMISSION] {op}: {name} {date_str} {problem} {file_path} -> {pid}")
        # PR merged 또는 main push일 때만 문제 Done 처리
        merged = (str(args.is_merged).lower() == "true") or (args.event == "push")
        if merged:
            try:
                mark_problem_done_if_match(name, date_str)
            except Exception as e:
                print("[WARN] mark_problem_done_if_match:", repr(e))

    # 4) 오늘자 누적 현황 → Discord
    today_kst = datetime.now(KST)
    entries = query_today_submissions_kst(today_kst)
    if not entries:
        print("[INFO] No entries for today.")
        return
    content = build_daily_message(entries, today_kst)
    post_discord(DISCORD_WEBHOOK_URL, content=content)

if __name__ == "__main__":
    main()
