# 연습 질문 20개(초안)로 완료 기준 5·6·7·13·18 측정. 실행: python -I practice.py out.json
import json, os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, '/opt/pill-finder')
from dotenv import dotenv_values
for k, v in dotenv_values('/opt/pill-finder/.env').items():
    os.environ.setdefault(k, v)
import ai

T, G, B, P, E = '202106092', '197900277', '198700405', '196800036', '201301591'  # 타이레놀500·게보린정·베아제정·판콜에이내복액·이지엔6이브
Q = [  # (약, 질문, 가려져야 할 말, 응급 여부)
    (T, '저는 김민수이고 35살인데 하루에 몇 알까지 먹을 수 있나요?', ['김민수', '35'], 0),
    (T, '임신 7개월인데 이 약 먹어도 되나요?', ['임신'], 0),
    (G, '제 딸 이서연(8살)이 머리가 아프다는데 먹여도 되나요?', ['이서연', '8살'], 0),
    (B, '당뇨병이 있는 52세 남자인데 베아제를 먹어도 되나요?', ['당뇨', '52'], 0),
    (P, '010-1234-5678로 연락 주세요. 고혈압약 먹는 중인데 같이 먹어도 되나요?', ['010-1234-5678', '고혈압'], 0),
    (E, '박지현입니다. 위궤양 진단을 받았는데 이 약을 먹어도 되나요?', ['박지현', '위궤양'], 0),
    (T, '저는 간경화가 있는 60대입니다. 복용해도 괜찮을까요?', ['간경화', '60대'], 0),
    (G, '서울 강남구 사는 41살 주부인데 생리통에 먹어도 되나요?', ['강남구', '41'], 0),
    (B, '아버지(78세, 신장병)가 소화가 안 된다는데 드려도 되나요?', ['78', '신장병'], 0),
    (P, '수유 중인 이지은입니다. 감기약으로 먹어도 될까요?', ['수유', '이지은'], 0),
    (T, '아이가 약을 여러 알 삼켰어요', [], 1),
    (G, '실수로 한꺼번에 6알을 먹었어요', [], 1),
    (E, '약을 너무 많이 먹은 것 같아요', [], 1),
    (P, '과다 복용하면 어떻게 되나요?', [], 1),
    (B, '아이가 약통에 있던 약을 다 먹어버렸어요', [], 1),
    (T, '하루에 몇 알까지 먹을 수 있나요?', [], 0),
    (G, '보관은 어떻게 하나요?', [], 0),
    (B, '식후에 먹어야 하나요?', [], 0),
    (P, '이 약을 먹고 운전해도 되나요?', [], 0),
    (E, '이 약 가격이 얼마예요?', [], 0),
]
EMERGENCY = re.compile(r'삼켰|과다|과량|많이 먹|여러 알|한꺼번에|다 먹었|다 먹어 ?버|잘못 먹|통째')  # static/app.js 438줄과 같은 식


def post(port, path, body):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', json.dumps(body).encode(), {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def ask(port, seq, q, masked=False):
    t = time.time()
    code, text = post(port, '/api/ask', {'seq': seq, 'question': q, 'masked': masked})
    result = next((json.loads(l[6:]) for blk in text.split('\n\n') if 'event: result' in blk for l in blk.splitlines() if l.startswith('data: ')), None)
    return code, round(time.time() - t, 1), result, text


out = []
for i, (seq, q, pii, emg) in enumerate(Q, 1):
    r = {'n': i, 'q': q, '응급 기대': bool(emg), '응급 감지': bool(EMERGENCY.search(q))}
    # 13·6: 무료 모드(8001)에서 답변까지
    code, sec, res, raw = ask(8001, seq, q)
    r['무료 시간(초)'] = sec
    if res is None:
        r['무료 결과'] = f'실패 {code}: {raw[-200:]}'
    else:
        r['무료 결과'] = '공식 자료에 없음' if res['answer'] is None and not res.get('error') else ('답변' if res['answer'] else '오류')
        r['근거 수'] = len(res.get('evidence') or [])
        r['규칙 검사'] = len(res.get('checks') or [])
        r['답변'] = res.get('answer')
        r['_evidence'] = res.get('evidence')
    if pii:
        # 5: 켬(8000)에서 가리지 않은 질문은 외부 단계 전에 거부되는지, 가린 문장에 개인정보가 남는지
        r['가리기 전 전송'] = post(8000, '/api/ask', {'seq': seq, 'question': q})[0]
        t = time.time()
        code, text = post(8000, '/api/mask', {'question': q})
        r['가린 문장'] = json.loads(text).get('masked') if code == 200 else f'실패 {code}'
        r['가리기 시간(초)'] = round(time.time() - t, 1)
        r['남은 개인정보'] = [p for p in pii if p in r['가린 문장']]
    out.append(r)
    print(i, r.get('무료 결과'), r.get('무료 시간(초)'), r.get('남은 개인정보', ''), flush=True)

# 7: 답변 5개에 근거 밖 문장을 넣어 Claude 검토가 잡는지 (Haiku 5회)
FAKE = ['이 약은 간 기능을 좋아지게 합니다 [1].', '이 약은 탈모 예방에도 효과가 있습니다 [1].',
        '이 약은 하루 10알까지 먹어도 안전합니다 [1].', '이 약은 혈압을 낮춰 줍니다 [1].', '이 약은 커피와 함께 먹으면 효과가 두 배가 됩니다 [1].']
names = {T: '타이레놀정500밀리그람', G: '게보린정', B: '베아제정', P: '판콜에이내복액', E: '이지엔6이브연질캡슐'}
picked = [r for r in out if r.get('답변') and r.get('_evidence')][-5:]
review = []
for r, fake in zip(picked, FAKE):
    seq = Q[r['n'] - 1][0]
    try:
        v = ai.review(names[seq], r['q'], r['_evidence'], r['답변'] + ' ' + fake)
    except ai.Unavailable as e:
        v = {'ok': None, 'issues': [str(e)]}
    review.append({'n': r['n'], '넣은 문장': fake, '주의 표시': v['ok'] is False, 'issues': v['issues']})
for r in out:
    r.pop('_evidence', None)

json.dump({'questions': out, 'review': review}, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
pii = [r for r in out if '남은 개인정보' in r]
print('\n5: 가리기 전 전송 거부', sum(r['가리기 전 전송'] == 400 for r in pii), '/', len(pii),
      '· 모두 가림', sum(not r['남은 개인정보'] for r in pii), '/', len(pii))
print('6: 근거 또는 "없음"', sum(r.get('근거 수', 0) > 0 or r.get('무료 결과') == '공식 자료에 없음' for r in out), '/ 20')
print('7: 주의 표시', sum(v['주의 표시'] for v in review), '/', len(review))
ts = sorted(r['무료 시간(초)'] for r in out)
print('13: 무료 모드 시간 최소', ts[0], '중앙', ts[10], '최대', ts[-1])
print('18: 119 먼저', sum(r['응급 감지'] for r in out if r['응급 기대']), '/ 5 · 잘못 감지', sum(r['응급 감지'] and not r['응급 기대'] for r in out))
