# study-automation

노션(DB) ↔ 디스코드(Webhook), 깃허브(푸시/PR) ↔ 디스코드 자동화.

## Quick Start
1) 리포 복제/생성 → 파일 업로드
2) Settings → Secrets and variables → Actions → 다음 등록:
   - `NOTION_API_KEY`, `NOTION_DATABASE_ID`
   - `DISCORD_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL_REMINDER`
   - `ROLE_ID_PROBLEM_SETTER`(선택)
3) Actions 탭에서 **Run workflow**로 수동 테스트

## Notion 스키마
`config/schema.md` 참조.

## 채널 권장
- #문제-공지 (읽기:모두 / 쓰기:운영자/봇)
- #깃-알림 (봇 전용)
