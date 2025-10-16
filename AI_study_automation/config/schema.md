# Notion DB 스키마(문제 관리)

## 필드(필수)
- Name (type: title) — 문제 제목
- Week (type: date) — 주차 기준 날짜
- Difficulty (type: select: Easy/Medium/Hard)
- Status (type: select: Proposed/Assigned/Solved)
- Submitter (type: rich_text or people)
- Link (type: url)

## 예시 행
| Name | Week | Difficulty | Status | Submitter | Link |
| ---- | ---- | ---------- | ------ | --------- | ---- |
| 프로그래머스 1931_각도계산 | 2025-10-15 | Medium | Assigned | 재성 | https://boj.kr/1931 |
