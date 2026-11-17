"""후보 비교 자가 검사. 실행: python test_search.py"""
from app import norm, prepare, search

rows = [prepare(i, x) for i, x in enumerate([
    {'ITEM_NAME': '타이레놀정500밀리그람', 'PRINT_FRONT': 'TYLENOL', 'PRINT_BACK': '500', 'COLOR_CLASS1': '하양', 'DRUG_SHAPE': '장방형', 'ETC_OTC_NAME': '일반의약품', 'FORM_CODE_NAME': '필름코팅정'},
    {'ITEM_NAME': '타이레놀8시간이알서방정', 'PRINT_FRONT': 'TYLENOL', 'PRINT_BACK': 'ER', 'COLOR_CLASS1': '하양', 'DRUG_SHAPE': '장방형', 'ETC_OTC_NAME': '일반의약품'},
    {'ITEM_NAME': '분할선약', 'PRINT_FRONT': 'V분할선T', 'COLOR_CLASS1': '노랑, 투명', 'DRUG_SHAPE': '팔각형', 'ETC_OTC_NAME': '전문의약품', 'FORM_CODE_NAME': '경질캡슐제, 산제'},
    {'ITEM_NAME': '로고약', 'PRINT_FRONT': '마크', 'COLOR_CLASS1': '분홍', 'DRUG_SHAPE': '원형'},
    {'ITEM_NAME': '민무늬약', 'COLOR_CLASS1': '하양', 'DRUG_SHAPE': '원형'},
])]
names = lambda res: [c['d']['name'] for c in res[1]]

# 완료 기준 19: 소문자·공백·0/O를 바꿔 넣어도 같은 후보
assert norm('tylenol') == norm('TYLEN0L') and norm('5 O-O') == norm('500') and norm('l') == norm('I')
assert names(search(rows, 'text', 'tylenol', '5OO', ['하양'], '장방형'))[0] == '타이레놀정500밀리그람'
assert names(search(rows, 'text', '500', 'TYLENOL'))[0] == '타이레놀정500밀리그람', '앞뒤가 바뀌어도 같은 후보'
assert names(search(rows, 'text', 'TYLENOL')) == ['타이레놀정500밀리그람', '타이레놀8시간이알서방정'], '빈 칸은 비교에서 뺌'
# 자료의 '분할선' 표기·여러 색·기타 모양·캡슐
r = search(rows, 'text', 'VT', '', ['투명'], '기타', 'y')
assert names(r) == ['분할선약'] and [m[0] for m in r[1][0]['matches']] == ['각인 완전 일치', '색 일치', '모양 일치', '캡슐 여부 일치']
assert names(search(rows, 'mark')) == ['로고약']
assert names(search(rows, 'none')) == ['민무늬약']
assert search(rows, 'text', 'ZZZ')[0] == 0, '각인이 안 맞으면 후보 없음'
one = [prepare(0, {'ITEM_NAME': '한글자', 'PRINT_FRONT': 'Q'}), prepare(1, {'ITEM_NAME': '두글자', 'PRINT_FRONT': 'ZQ'})]
assert names(search(one, 'text', 'ZZZQ')) == ['두글자'], '한 글자 각인은 입력 안에 들어 있어도 부분 일치로 보지 않음'
assert names(search(one, 'text', 'Q')) == ['한글자', '두글자'], '입력이 각인의 일부면 부분 일치'
# 하루 한도: 파일에 세고, 한도를 넘으면 429, 날짜가 바뀌면 0부터
import json, tempfile
from pathlib import Path
from fastapi import HTTPException
import app
app.LIMITS = Path(tempfile.mkdtemp()) / 'limits.json'
app.count_today('t', 2, 'x'); app.count_today('t', 2, 'x')
try:
    app.count_today('t', 2, 'x'); assert False, '한도를 넘으면 막아야 함'
except HTTPException as e:
    assert e.status_code == 429
assert json.loads(app.LIMITS.read_text())['t'] == 2
app.LIMITS.write_text(json.dumps({'day': '2000-01-01', 't': 9}))
app.count_today('t', 2, 'x')
assert json.loads(app.LIMITS.read_text())['t'] == 1, '날짜가 바뀌면 0부터'
# 질문: 근거 찾기·응급 판단은 가리기 전 질문, CLOVA·Claude에는 가린 질문만
from fastapi.testclient import TestClient
seen = {}
app.official = lambda seq: ({'itemName': '약', 'updateDe': '1'}, [('주의', '고혈압 환자는 상의')])
app.switches = lambda: {'clovaText': True, 'claudeReview': True}
app.count_today = lambda *a: None
app.write_with_fallback = lambda make: (make(None), 'm')
app.ai.is_emergency = lambda q: seen.setdefault('emergency', q) and False
app.ai.retrieve = lambda seq, u, sec, q: seen.setdefault('retrieve', q) and [{'title': '주의', 'body': '고혈압 환자는 상의'}]
app.ai.answer = lambda name, q, ev, w: seen.setdefault('answer', q) and '상의하라고 적혀 있습니다 [1].'
app.ai.review = lambda name, q, ev, t: seen.setdefault('review', q) and {}
c = TestClient(app.app)
assert c.post('/api/ask', json={'seq': '1', 'question': '고혈압인데 먹어도 되나요'}).status_code == 400, '켬이면 가리지 않은 질문 거부'
c.post('/api/ask', json={'seq': '1', 'question': '[가림]인데 먹어도 되나요', 'original': '고혈압인데 먹어도 되나요', 'masked': True})
assert seen == {'emergency': '고혈압인데 먹어도 되나요', 'retrieve': '고혈압인데 먹어도 되나요',
                'answer': '[가림]인데 먹어도 되나요', 'review': '[가림]인데 먹어도 되나요'}, seen
print('ok')
