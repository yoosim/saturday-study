# 📘 Notion DB 스키마 정의

스터디 자동화 연동을 위한 Notion Database 설정 가이드입니다.  
GitHub Actions + Notion API + Discord Webhook이 동일한 필드 이름으로 접근하므로,  
아래 **필드명/타입**을 정확히 맞춰주세요.

---

## 🧩 문제 관리용 DB (Problem Management)

### 필드(필수)
| 필드명 | 타입 | 설명 |
|:--|:--|:--|
| **Name** | title | 문제 제목 |
| **Week** | date | 해당 주차 기준 날짜 |
| **Difficulty** | select (Easy / Medium / Hard) | 문제 난이도 |
| **Status** | select (Proposed / Assigned / Done) | 문제 상태 <br>예: `Assigned` → `Done` 자동 업데이트 |
| **Submitter** | rich_text *(또는 people)* | 문제 제공자 |
| **Next Submitters** | rich_text | 다음 주 문제 담당자 |
| **Link** | url | 문제 메인 링크 |
| **More Links** | rich_text | 보조 링크 (쉼표 또는 줄바꿈으로 여러 개 입력 가능) |

> ⚙️ *코드에서는 `Assigned`/`Done` 값만 직접 사용합니다.  
> 나머지 값(`Proposed`)은 기획 단계 구분용입니다.*

---

### 예시 행
| Name | Week | Difficulty | Status | Submitter | Next Submitters | Link | More Links |
| ---- | ---- | ---------- | ------ | ---------- | ---------------- | ---- | ----------- |
| 프로그래머스 1931_각도계산 | 2025-10-15 | Medium | Assigned | 재성 | 성미 | https://boj.kr/1931 | https://school.programmers.co.kr/learn/courses/30/lessons/181944, https://school.programmers.co.kr/learn/courses/30/lessons/181899 |

---

## 📗 과제 제출 현황 DB (Submissions Log)

### 필드(필수)
| 필드명 | 타입 | 설명 |
|:--|:--|:--|
| **Name** | title | `YYYY-MM-DD_이름` 자동 생성 |
| **Week** | date | 주차 기준 날짜 |
| **Submitter** | rich_text | 제출자 이름 |
| **Problem** | rich_text | 과제명 (파일명 기반) |
| **Commit Time** | date | 제출 시각 (KST) |
| **File Path** | rich_text | 예: `study/성미/2025-10-18/test.py` |
| **Status** | select (Submitted) | 기본 제출 상태 |
| **On-time** | checkbox | 마감 시각 전 제출 여부 |
| **Late (min)** | number | 마감 후 지연 시간(분) |
| **Repo/Branch** | rich_text | 예: `yoosim/study-automation / main` |
| **SHA** | rich_text | 커밋 해시 |
| **PR URL** | url | Pull Request 링크 (선택) |

---

### 예시 행
| Name | Week | Submitter | Problem | Commit Time | File Path | Status | On-time | Late(min) |
| ---- | ---- | ---------- | -------- | ------------ | ---------- | -------- | ---------- | ---------- |
| 2025-10-18_성미 | 2025-10-18 | 성미 | 프로그래머스_코딩기초트레이닝 | 2025-10-18 21:42 | study/성미/2025-10-18/test.py | Submitted | ✅ | 0 |

---

### 🧾 참고
- `git_to_notion.py` 실행 시 위 스키마에 자동 기록됩니다.  
- Status가 자동으로 `Submitted`로 설정되고, 마감 전/후 여부에 따라 `On-time`, `Late(min)`이 계산됩니다.  
- 매일/매주 스케줄러(`daily_attendance.py`, `weekly_reminder.py`)에서 이 DB를 참조하여 Discord 메시지를 보냅니다.
