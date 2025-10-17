# 🤖 study-automation

> Notion(DB) ↔ Discord(Webhook), GitHub(푸시/PR) ↔ Discord 자동화 시스템  

---

## 🚀 Quick Start

1️⃣ **리포 복제/업로드**
```bash
git clone https://github.com/your-id/study-automation.git
cd study-automation
git checkout -b 개인브런치명
```

2️⃣2️ **업로드 규칙**

# 🧭 Pull Request Guide (study-automation)

> 이 문서는 **이 저장소에서 과제 제출을 PR로 올리는 표준 절차**를 설명합니다.  
> 워크플로(자동화)와 폴더 규칙을 꼭 지켜주세요.

---

## 📂 폴더 규칙 (꼭 지켜야 PR이 집계돼요)

- **제출 파일 경로**: `study/<이름>/<YYYY-MM-DD>/<파일명>`
  - 예) `study/성미/2025-10-18/프로그래머스_코딩기초트레이닝.py`
- PR/Push 자동화는 `study/**` 아래 변경만 반응합니다.

---

## 🌱 브랜치 전략

- 기본: `main`은 보호. 각자 **개인 브랜치**에서 작업 후 PR 생성
