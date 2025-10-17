# 🌟 토요 AI 스터디 (Saturday AI Study)

> 함께 배우고 성장하는 주말 AI 탐구 스터디  
> **매주 토요일 오전 10시 | GitHub + Notion + Discord 완전 자동화 연동**

---

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/yoosim/study-automation/git-to-notion.yml?label=Git→Notion)
![Weekly Reminder](https://img.shields.io/github/actions/workflow/status/yoosim/study-automation/weekly-reminder.yml?label=Weekly%20Reminder)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

---

## 📌 스터디 개요

- **목표:** AI / 데이터분석 / 모델링 기반 문제해결 능력 향상  
- **주제:** 매주 3개 문제 선정 → 개인 풀이 / 코드 리뷰 / 미니 프로젝트  
- **형태:** 팀별 문제 풀이 + 코드 발표 + 기술 토론  
- **자동화:** Notion(DB) ↔ Discord(Webhook) ↔ GitHub(PR) 완전 연동

---

## 🧭 연동 다이어그램

> Notion, Discord, GitHub Actions 간 자동화 데이터 흐름

```
┌─────────────────────────┐
│       GitHub Repo       │
│  study/<이름>/<날짜>/…  │
└─────────────┬───────────┘
              │ Push / PR (trigger)
              ▼
      ┌─────────────────────┐
      │  GitHub Actions     │
      │  ├ git-to-notion.yml│
      │  ├ weekly-reminder  │
      │  ├ notion-watch     │
      │  └ daily-attendance │
      └──────────┬──────────┘
                 │
                 ▼
┌──────────────────────────────────┐
│           Notion DB              │
│ ├ Problem Management (문제관리)  │
│ └ Submissions Log (제출기록)     │
└──────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────┐
│           Discord Channels        │
│ 🟣 #문제-공지 → 문제 업데이트/리마인드 │
│ 🟢 #스터디-출석 → 일일/주간 요약      │
│ 🔵 #깃-알림 → Push/PR 이벤트 카드    │
└──────────────────────────────────┘
```

---

## 🗓️ 진행 방식

| 구분 | 내용 |
|------|------|
| 🔹 월~금 | 개인별 AI/데이터 스터디 진행 |
| 🔹 수~금 | 개인 문제 풀이 및 코드 업로드 (GitHub) |
| 🔹 수요일 | 자동 리마인드 / 오프라인 공유회 |
| 🔹 토요일 | 발표 + 코드 리뷰 + 다음 주 주제 선정 |

---

## ⚙️ 리포지토리 구조

> **스터디 과제 + 자동화 시스템 + 워크플로우 관리용 통합 구조**

```bash
code_study/
├── 🧠 AI_study_automation/       # 자동화 스크립트 (Notion, Discord, GitHub Actions)
│   ├── scripts/
│   │   ├── notion_watch.py        # 노션 문제 업데이트 감시
│   │   ├── weekly_reminder.py     # 매주 수요일 문제 제출자 리마인드
│   │   ├── git_to_notion.py       # Git push/PR → Notion 제출 DB 연동
│   │   ├── daily_attendance.py    # 일일 출석 요약 자동 전송
│   │   ├── utils.py               # 공용 함수 (get_env, post_discord 등)
│   └── config/
│       ├── members.json           # 팀원 이름 ↔ Discord ID 매핑
│       └── schema.md              # Notion DB 스키마 정의
│
├── 🧩 study/                      # 개인별 과제 제출 폴더
│   ├── 김영신/2025-10-18/...
│   ├── 심재성/2025-10-18/...
│   ├── 유성미/2025-10-18/...
│   ├── 정종혁/2025-10-18/...
│   └── 최장호/2025-10-18/...
│
└── .github/workflows/             # GitHub Actions 자동화
    ├── notion-watch.yml
    ├── weekly-reminder.yml
    ├── git-to-notion.yml
    ├── git-to-discord.yml
    └── daily-attendance.yml
```

---

## 💻 사용 기술 & 연동 구조

| 구분 | 역할 |
|------|------|
| 🧩 **GitHub Actions** | 과제 제출, 리마인드, 출석 자동화 실행 |
| 📘 **Notion API** | 문제 관리 DB / 과제 제출 DB 데이터 기록 |
| 💬 **Discord Webhook** | 알림 / 리마인드 / 출석 요약 실시간 전달 |
| 🐍 **Python Scripts** | Actions 내부 실행 로직 (requests, json 등) |
| 🗃️ **members.json** | Discord Mentions용 멤버 ID 매핑 |

---

## 🔄 자동화 워크플로우 요약

| 이름 | 트리거 | 주요 기능 | 출력 |
|------|---------|------------|--------|
| **notion-watch.yml** | 10분마다 (cron) | 노션 문제 DB 변경 감지 | Discord 문제 업데이트 알림 |
| **weekly-reminder.yml** | 매주 수요일 09:00 KST | 이번 주 문제 제출자 리마인드 | Discord 멘션 메시지 |
| **git-to-notion.yml** | push / PR merged | 제출 파일 자동 등록 → Notion DB 업서트 | Discord 제출 현황 메시지 |
| **daily-attendance.py** | 매일 밤 (cron) | 제출 여부 기반 출석 요약 | Discord 출석 요약 |
| **git-to-discord.yml** | push / PR merged | Git 이벤트 카드 전송 | Discord 깃 채널 메시지 |

---

## 👥 스터디 구성원

| 이름 | 역할 | GitHub |
|------|------|---------|
| 김영신 | 프론트엔드, AI 개발 | [@youngsshi](https://github.com/youngsshi) |
| 심재성 | 컴퓨터비전, 백엔드 | — |
| 유성미 | 데이터분석, AI 개발 | [@yoosim](https://github.com/yoosim) |
| 정종혁 | AI 기획 및 시스템 설계 | — |
| 최장호 | 웹 개발 및 MLOps | — |

---

## 🧠 스터디 목표

- AI 문제 접근 방식 체계화 및 실무형 프로젝트 경험 축적  
- GitHub Actions, Notion API, Discord Webhook을 이용한 자동화 실습  
- 협업 중심 코드 리뷰 및 PR 기반 개발 워크플로우 숙련  
- “자동화 + 학습 + 협업” 세 가지를 모두 익히는 스터디 모델 구축

---

## 💬 권장 Discord 채널 구조

| 채널명 | 역할 | 메시지 종류 |
|--------|------|--------------|
| 🟣 #문제-공지 | Notion 문제 업데이트 / 리마인드 | “📣 Notion 문제 업데이트” |
| 🔵 #깃-알림 | Push / Merge 카드 | “📦 push on main by …” |

---

## 📘 Notion 스키마

👉 [config/schema.md](./AI_study_automation/config/schema.md) 참고

---

## 🧾 라이선스
© 2025 Saturday AI Study Automation Team
