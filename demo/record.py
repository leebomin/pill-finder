# 실제 서버(8000) 응답을 녹화해 demo-data.js로 저장. 실행: python record.py  (CLOVA·Claude 비용이 조금 듦)
import json, pathlib, urllib.parse, urllib.request

B = 'http://127.0.0.1:8000'
SAMPLE = {'mode': 'text', 'front': 'tylenol', 'back': '5OO', 'colors': '하양', 'shape': '장방형', 'capsule': ''}  # app.js fillSample
NAMES = ['타이레놀', '게보린', '베아제']
ASK_SEQS = ['202106092', '197900277', '198700405']  # 타이레놀정500 · 게보린정 · 베아제정
QUESTIONS = ['하루에 몇 알까지 먹을 수 있나요?', '저는 27살이고 고혈압이 있는데, 술 마신 날 먹어도 되나요?', '아이가 약을 여러 알 삼켰어요']  # app.js SUGGESTIONS


def call(path, params=None, post=None):
    url = B + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, json.dumps(post).encode() if post else None, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read().decode()


demo = {'search': {}, 'names': [], 'doc': {}, 'summary': {}, 'mask': {}, 'ask': {}}
key = lambda p: json.dumps(p, sort_keys=True, ensure_ascii=False)
r = json.loads(call('/api/search', SAMPLE))
demo['search'][key(SAMPLE)] = r
drugs = {c['d']['seq']: c['d'] for c in r['cands']}
for q in NAMES:
    hits = json.loads(call('/api/names', {'q': q}))['hits']
    demo['names'] += [h for h in hits if h['id'] not in {x['id'] for x in demo['names']}]
    drugs.update({h['seq']: h for h in hits if h['seq'] in ASK_SEQS})
for seq, d in drugs.items():
    if d['type'] == 'otc' and d['doc']:
        demo['doc'][seq] = json.loads(call(f'/api/doc/{seq}'))
        demo['summary'][seq] = json.loads(call(f'/api/summary/{seq}'))
        print('doc+summary', d['name'], flush=True)
for q in QUESTIONS:  # 같은 질문은 한 번만 가려서 약 3종에 같은 문장으로 질문
    demo['mask'][q] = json.loads(call('/api/mask', post={'question': q}))['masked']
for seq in ASK_SEQS:
    for q in QUESTIONS:
        masked = demo['mask'][q]
        text = call('/api/ask', post={'seq': seq, 'question': masked, 'masked': True})
        demo['ask'][seq + '|' + masked] = [[b.split('\n')[0][7:], json.loads(b.split('\n')[1][6:])] for b in text.strip().split('\n\n')]
        print('ask', seq, q, flush=True)
out = pathlib.Path(__file__).with_name('demo-data.js')
out.write_text('// record.py가 실제 서버 응답을 녹화한 데모 자료\nwindow.DEMO = ' + json.dumps(demo, ensure_ascii=False) + ';\n')
print(out, out.stat().st_size, 'bytes')
