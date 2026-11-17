# 완료 기준 18: 응급 감지를 표현 목록만 vs 목록 + Qwen으로 비교. 서버·하루 한도를 쓰지 않음.
# 실행: python -I emergency.py questions-emergency-fresh.json [다른 질문 파일 …]
import json, os, sys, time
sys.path.insert(0, '/opt/pill-finder')
from dotenv import dotenv_values
for k, v in dotenv_values('/opt/pill-finder/.env').items():
    os.environ.setdefault(k, v)
import ai

for f in sys.argv[1:]:
    rows, ts = [], []
    for x in json.load(open(f)):
        t = time.time()
        both = ai.is_emergency(x['q'])
        ts.append(time.time() - t)
        rows.append((bool(x['emergency']), bool(ai.EMERGENCY.search(x['q'])), both, x['q']))
    pos = sum(r[0] for r in rows)
    for name, i in [('목록만', 1), ('목록+Qwen', 2)]:
        print(f'{f} {name}: 응급 {sum(r[0] and r[i] for r in rows)}/{pos} · 잘못 감지 {sum(r[i] and not r[0] for r in rows)}/{len(rows) - pos}')
    print('  판정 시간 중앙', round(sorted(ts)[len(ts) // 2], 2), '최대', round(max(ts), 2), '초')
    for exp, _, got, q in rows:
        if exp != got:
            print('  ', '놓침' if exp else '잘못', q)
