"""CLOVA Studio 호출과 월 비용 상한. 상한을 넘으면 그 달은 CLOVA 단계를 무료 모드로 바꾼다."""
import json
import os
import threading
import time
import uuid
from datetime import date
from pathlib import Path

import httpx

from ai import Unavailable

USAGE = Path(__file__).parent / 'data' / 'clova-usage.json'
# 1,000토큰당 원(VAT 별도). 기존 앱 clova-pricing.json(2026-11-04) 기준. 단가를 모르는 모델은 상한을 지킬 수 없어 부르지 않음
PRICES = {'HCX-005': (1.25, 5.0)}
MIN_INTERVAL = float(os.environ.get('CLOVA_MIN_INTERVAL_SECONDS', '8'))  # 기존 앱과 같은 호출 간격
_lock = threading.Lock()
_last = 0.0


def cap():
    return float(os.environ.get('CLOVA_MONTHLY_CAP_KRW', '5000'))


def _usage():
    u = json.loads(USAGE.read_text()) if USAGE.exists() else {}
    month = date.today().strftime('%Y-%m')
    return u if u.get('month') == month else {'month': month, 'krw': 0.0, 'days': {}}


def spent():
    return _usage()['krw']


def over_cap():
    return spent() >= cap()


def available():
    return bool(os.environ.get('CLOVA_API_KEY', '').strip()) and not over_cap()


def _record(model, usage):
    i, o = PRICES[model]
    krw = ((usage.get('promptTokens') or 0) * i + (usage.get('completionTokens') or 0) * o) / 1000
    u = _usage()
    u['krw'] += krw
    day = date.today().isoformat()
    u['days'][day] = u['days'].get(day, 0) + krw
    USAGE.parent.mkdir(exist_ok=True)
    USAGE.write_text(json.dumps(u))
    return krw


def chat(messages, max_tokens, model=None):
    """messages: [{'role','content'(문자열 또는 이미지가 든 목록)}] → 답 문자열. 키·요청 주소는 오류에 남기지 않는다."""
    global _last
    model = model or os.environ.get('CLOVA_TEXT_MODEL', 'HCX-005')
    if model not in PRICES:
        raise Unavailable('단가를 모르는 CLOVA 모델입니다.')
    key = os.environ.get('CLOVA_API_KEY', '').strip()
    if not key:
        raise Unavailable('CLOVA_API_KEY가 설정되지 않았습니다.')
    with _lock:
        if over_cap():
            raise Unavailable('이번 달 CLOVA 사용 한도에 도달했습니다.')
        time.sleep(max(0.0, MIN_INTERVAL - (time.monotonic() - _last)))
        _last = time.monotonic()
        body = {'messages': messages, 'topP': 0.8, 'topK': 0, 'temperature': 0, 'maxTokens': max_tokens,
                'repetitionPenalty': 1.1, 'stop': [], 'seed': 7, 'includeAiFilters': False}
        try:
            r = httpx.post(os.environ.get('CLOVA_BASE_URL', 'https://clovastudio.stream.ntruss.com').rstrip('/') + '/v3/chat-completions/' + model,
                           json=body, timeout=120,
                           headers={'Authorization': 'Bearer ' + key, 'X-NCP-CLOVASTUDIO-REQUEST-ID': str(uuid.uuid4())})
            data = r.json()
        except (httpx.HTTPError, ValueError):
            raise Unavailable('CLOVA에 연결할 수 없습니다.') from None
        if (data.get('status') or {}).get('code') != '20000':
            raise Unavailable(f"CLOVA 오류({(data.get('status') or {}).get('code') or r.status_code})")
        result = data['result']
        _record(model, result.get('usage') or {})
        return result['message']['content']


if __name__ == '__main__':
    # 자가 검사: 금액 계산(입력 1,000토큰 1.25원 + 출력 1,000토큰 5원)
    import tempfile
    USAGE = Path(tempfile.mkdtemp()) / 'u.json'
    assert _record('HCX-005', {'promptTokens': 1000, 'completionTokens': 1000}) == 6.25 and spent() == 6.25
    os.environ['CLOVA_MONTHLY_CAP_KRW'] = '6'
    assert over_cap() and not available()
    print('ok')
