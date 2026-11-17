# 갱신 전후 비교용: 자료 건수와 대표 검색의 후보 풀 크기
import json, sys, urllib.parse, urllib.request
D = '/opt/pill-finder/data/'
pills, edrug = json.load(open(D + 'pills.json')), json.load(open(D + 'edrug.json'))
seqs = {x['itemSeq'] for x in edrug}
otc = [p for p in pills if p['ETC_OTC_NAME'] == '일반의약품']
out = {'meta': json.load(open(D + 'meta.json')), '낱알': len(pills), '일반': len(otc),
       '일반 중 e약은요 있음': sum(p['ITEM_SEQ'] in seqs for p in otc), 'e약은요': len(edrug)}
for name, q in [('TYLENOL/500 하양 장방형', dict(front='TYLENOL', back='500', colors='하양', shape='장방형')),
                ('각인 없음 하양 원형', dict(mode='none', colors='하양', shape='원형')),
                ('마크 하양 원형', dict(mode='mark', colors='하양', shape='원형'))]:
    r = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/search?' + urllib.parse.urlencode(q)))
    out[name] = {'후보 풀': r['total'], '1위': r['cands'][0]['d']['name'] if r['cands'] else None}
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
