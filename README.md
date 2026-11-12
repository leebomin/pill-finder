# 알약 찾기 도우미

낱알의 각인·색·모양으로 일반의약품 후보를 찾고, 식약처 e약은요 공식 원문을 근거로 쉬운 말 요약과 질문 답변을 보여 주는 웹앱입니다. 앱 기능은 MCP 도구 4개로도 쓸 수 있습니다.

| 폴더 | 내용 |
|---|---|
| `app/` | 실제 앱 (FastAPI + 정적 화면, MCP 서버 `pill_mcp.py`). 실행·설정은 [`app/README.md`](app/README.md) |
| `demo/` | 서버 없이 도는 데모 사이트 (실제 화면 + 녹화한 응답). GitHub Pages로 `…/demo/`에서 열림, [`demo/README.md`](demo/README.md) |
| `prototype/` | 디자인 시안을 옮긴 정적 페이지 (예시 데이터) |
| `deck/` | 발표 자료 PPTX와 만드는 스크립트 (`python-pptx` 필요) |
| `measure/` | 완료 기준 측정 스크립트와 결과 (갱신 전후, 연습 질문 3묶음) |
| `deploy/` | systemd 서비스, 주 1회 자동 갱신 cron |
| `docs/` | 기획서 `PROJECT.md`, 완료 기준 점검표 `completion-checklist.md`, 작업 정리 `pill-finder-handout.md`, 발표 요청서 |

## 빠른 시작

```bash
cd app
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # 키와 수업 서버 주소를 채움 (스위치는 off = 무료 모드)
.venv/bin/python refresh.py   # 공공데이터 받기 (data/는 저장소에 넣지 않음)
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

- 무료 모드에도 Local LLM(Qwen3 4B, BGE-M3)과 Chroma 서버가 필요합니다.
- 문서에 나오는 `/opt/pill-finder/`는 이 저장소의 `app/`, `/root/day06/plugin-lab/`은 저장소 루트입니다.
- 받은 공공데이터(`app/data/`)는 저장 허용·공공누리 유형을 확인하기 전이라 올리지 않았습니다.
