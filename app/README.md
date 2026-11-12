# 알약 찾기 도우미

```bash
cd /opt/pill-finder
/opt/rag-lab-b/.venv/bin/python refresh.py      # 낱알식별·e약은요 자료 전체 받기 (약 40초, 호출 62회)
/opt/rag-lab-b/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
# 자가 검사
for f in test_search ai clova photo; do /opt/rag-lab-b/.venv/bin/python $f.py; done
```

## 설정 (`.env`, 실행할 때 준 환경변수가 우선)
- 키: `DATA_GO_KR_KEY`(Decoding 키), `CLOVA_API_KEY`, `ANTHROPIC_API_KEY`. 화면·로그에 키를 남기지 않는다.
- 수업 서버: `OLLAMA_CHAT_URL`(Qwen3 4B), `OLLAMA_EMBED_URL`(BGE-M3), `CHROMA_HOST`·`CHROMA_PORT`(컬렉션 `pill-docs`)
- 스위치(`on`/`off`, 없으면 꺼짐 = 무료 모드): `PHOTO_READ`(사진 → CLOVA HCX-005), `CLOVA_TEXT`(요약·답변 → CLOVA), `CLAUDE_REVIEW`(답변 검토 → Claude Haiku 5.5)
- `CLOVA_MONTHLY_CAP_KRW`(기본 5000): 넘으면 그 달은 CLOVA 단계가 무료 모드로 바뀜. 사용 금액은 `data/clova-usage.json`
- `AUTO_REFRESH=off`: 매주 월 03:00 cron 예약 실행만 건너뜀(직접 실행한 `refresh.py`는 항상 받음). cron 확인: `crontab -l`

## 동작
- 갱신이 실패하면 기존 `data/*.json`을 그대로 두고 `data/meta.json`에 실패를 기록한다. 서버는 다시 켜지 않아도 새 파일을 읽는다.
- 요약은 `data/summaries/<품목일련번호>.json`에 저장되고, e약은요 수정일이 바뀌면 새로 만든다.
- 질문은 외부 전송 단계(CLOVA_TEXT·CLAUDE_REVIEW)가 켜져 있으면 Qwen이 먼저 가리고 사용자가 확인한 문장만 받는다. 질문·사진은 저장하지 않는다.
- 질문 답변(`POST /api/ask`)은 SSE(`text/event-stream`)로 단계(`step`: search·write·check·review, start/done/skip/fail)와 마지막 `result`(또는 `error`)를 보낸다. 질문이 주소·기록에 남지 않게 EventSource(GET) 대신 POST 응답 본문을 화면에서 읽는다.
- 하루 한도(앱 전체, 메모리): 질문 50회, 사진 읽기 50회. 서버를 다시 켜면 0부터 센다.

## MCP
- `pill_mcp.py`: 후보 찾기·이름 검색·공식 원문·근거 찾기 도구 4개(stdio, 읽기 전용, 외부 유료 호출 없음)
- 등록: `claude mcp add pill-finder -s local -- /opt/rag-lab-b/.venv/bin/python /opt/pill-finder/pill_mcp.py`
