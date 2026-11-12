"""낱알식별·e약은요 자료 전체를 받아 data/*.json으로 교체한다. 실행: python refresh.py"""
import fcntl
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
SOURCES = {  # 이름: (주소, 저장 파일)
    'pills': ('https://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService03/getMdcinGrnIdntfcInfoList03', 'pills.json'),
    'edrug': ('https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList', 'edrug.json'),
}
ROWS = 500          # API가 허용하는 한 번 최대 행 수
MAX_CALLS = 500     # 한 번 실행에 공공 API 최대 호출 수 (기획 8장)
TRIES = 3


class RefreshError(Exception):
    pass


def fetch_page(client, url, key, page):
    # 키가 요청 주소에 들어가므로 오류 메시지에 주소나 예외 원문을 남기지 않는다
    try:
        r = client.get(url, params={'serviceKey': key, 'pageNo': page, 'numOfRows': ROWS, 'type': 'json'})
        body = r.json()
    except httpx.HTTPError as e:
        raise RefreshError(f'{page}쪽 연결 실패({type(e).__name__})') from None
    except ValueError:
        raise RefreshError(f'{page}쪽 응답 형식 오류(HTTP {r.status_code})') from None
    head = body.get('header') or {}
    if head.get('resultCode') != '00':
        # 키 오류·한도 초과(22·23)는 data.go.kr 공통 오류 모양(OpenAPI_ServiceResponse)으로 옴
        gw = (body.get('OpenAPI_ServiceResponse') or {}).get('cmmMsgHeader') or {}
        code = head.get('resultCode') or gw.get('returnReasonCode')
        msg = head.get('resultMsg') or gw.get('returnAuthMsg') or gw.get('errMsg')
        raise RefreshError(f'{page}쪽 API 오류 {code}: {msg}')
    return body['body']


def download(client, url, key, budget):
    """budget: 남은 호출 수를 담은 [n]. 실행 전체에서 함께 줄어든다."""
    def get(page):
        for attempt in range(TRIES):
            if budget[0] <= 0:
                raise RefreshError(f'호출 한도 {MAX_CALLS}회 초과')
            budget[0] -= 1
            try:
                return fetch_page(client, url, key, page)
            except RefreshError:
                if attempt == TRIES - 1:
                    raise
                time.sleep(2 * (attempt + 1))
    first = get(1)
    total = first['totalCount']
    items = list(first['items'] or [])
    for page in range(2, math.ceil(total / ROWS) + 1):
        items += get(page)['items'] or []
    if len(items) != total:
        raise RefreshError(f'받은 행 수 {len(items)} ≠ 전체 {total}')
    return items


def write_json(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False))
    os.replace(tmp, path)  # 다 받은 뒤에만 교체: 실패하면 기존 파일 유지


def main():
    env = {**dotenv_values(ROOT / '.env'), **os.environ}
    if '--scheduled' in sys.argv and (env.get('AUTO_REFRESH') or 'on').lower() == 'off':
        print('AUTO_REFRESH=off: 예약 실행을 건너뜁니다'); return 0
    DATA.mkdir(exist_ok=True)
    lock = open(DATA / 'refresh.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('이미 갱신 중입니다'); return 1
    meta_path = DATA / 'meta.json'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    key = env.get('DATA_GO_KR_KEY')
    budget = [MAX_CALLS]
    with httpx.Client(timeout=60) as client:
        for name, (url, file) in SOURCES.items():
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            m = meta.setdefault(name, {})
            try:
                if not key:
                    raise RefreshError('DATA_GO_KR_KEY가 없습니다')
                items = download(client, url, key, budget)
                write_json(DATA / file, items)
                m.update(fetched_at=now, count=len(items), last_ok=True, last_attempt=now, error=None)
                print(f'{name} 완료: {len(items)}건')
            except RefreshError as e:
                m.update(last_ok=False, last_attempt=now, error=str(e))
                print(f'{name} 실패: {e} (기존 자료 유지)')
    print(f'호출 {MAX_CALLS - budget[0]}회')
    write_json(meta_path, meta)
    return 0 if all(meta[n]['last_ok'] for n in SOURCES) else 1


if __name__ == '__main__':
    sys.exit(main())
