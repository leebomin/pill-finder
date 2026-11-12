"""알약 찾기 도우미. 실행: uvicorn app:app --host 0.0.0.0 --port 8000"""
import fcntl
import json
import os
import re
from datetime import date
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai
import clova
import photo

ROOT = Path(__file__).parent
for k, v in dotenv_values(ROOT / '.env').items():  # 스위치를 .env에 적어도 되게 함 (실행 환경변수가 우선)
    if v is not None:
        os.environ.setdefault(k, v)
DATA = ROOT / 'data'
SUMMARIES = DATA / 'summaries'
MAIN_SHAPES = ('원형', '타원형', '장방형')
CONFUSABLE = str.maketrans('OILSB', '01158')
# e약은요 항목 → 원문 탭 제목
DOC_FIELDS = [('efcyQesitm', '효능'), ('useMethodQesitm', '사용법'), ('atpnWarnQesitm', '경고'), ('atpnQesitm', '복용 전 주의사항'),
              ('intrcQesitm', '함께 복용하면 안 되는 약'), ('seQesitm', '부작용'), ('depositMethodQesitm', '보관')]
ASK_PER_DAY = 50  # 질문 하루 50회 (앱 전체, IP 저장 안 함)
PHOTO_PER_DAY = 50  # 사진 읽기 하루 50회
MAX_PHOTO = 5 * 1024 * 1024  # 장당 5MB, 한 번에 2장


def norm(v):
    """각인 비교 규칙: 대소문자·공백·하이픈 무시, 0/O·1/I/l·5/S·8/B 같은 문자로 봄. 자료의 '마크'·'분할선' 표기는 뺌."""
    v = re.sub(r'마크|분할선|[\s-]', '', (v or '').upper())
    return v.translate(CONFUSABLE)


def colors_of(x):
    return {c for k in ('COLOR_CLASS1', 'COLOR_CLASS2') for c in (x.get(k) or '').split(', ') if c}


def prepare(i, x):
    pf, pb = x.get('PRINT_FRONT') or '', x.get('PRINT_BACK') or ''
    return {
        'nf': norm(pf), 'nb': norm(pb), 'colors': colors_of(x),
        'group': x.get('DRUG_SHAPE') if x.get('DRUG_SHAPE') in MAIN_SHAPES else '기타',
        'capsule': '캡슐' in (x.get('FORM_CODE_NAME') or ''),
        'mark': bool(x.get('MARK_CODE_FRONT') or x.get('MARK_CODE_BACK')) or '마크' in pf + pb,
        'name_key': (x.get('ITEM_NAME') or '').casefold(),
        # 화면에 보내는 값 (식별 번호는 자료 순번: 품목일련번호가 겹치는 약이 있음)
        'd': {
            'id': str(i), 'seq': x.get('ITEM_SEQ'), 'name': x.get('ITEM_NAME') or '', 'co': x.get('ENTP_NAME') or '',
            'type': 'otc' if (x.get('ETC_OTC_NAME') or '').startswith('일반') else 'rx',
            'f': pf, 'b': pb, 'color': x.get('COLOR_CLASS1') or '', 'color2': x.get('COLOR_CLASS2') or '',
            'shape': x.get('DRUG_SHAPE') or '', 'form': x.get('FORM_CODE_NAME') or '',
        },
    }


_cache = {}


def load(file, build):
    # 갱신 명령이 파일을 바꾸면 서버를 다시 켜지 않아도 새 자료를 씀
    path = DATA / file
    if not path.exists():
        raise HTTPException(503, '약 자료를 아직 받지 않았습니다. 갱신 명령을 먼저 실행해 주세요.')
    m = path.stat().st_mtime
    if file not in _cache or _cache[file][0] != m:
        _cache[file] = (m, build(json.loads(path.read_text())))
    return _cache[file][1]


def rows():
    return load('pills.json', lambda xs: [prepare(i, x) for i, x in enumerate(xs)])


def edrug():
    return load('edrug.json', lambda xs: {x['itemSeq']: x for x in xs})


def with_doc(d):
    return {**d, 'doc': d['seq'] in edrug()}


def side(q, v):
    if not q or not v:
        return 0
    # 입력이 각인의 일부면 부분 일치. 반대(각인이 입력 안에 있음)는 'Q'·'Z' 같은 한 글자 각인이 아무 입력에나 걸려서 두 글자 이상만 인정
    return 40 if q == v else 20 if (q in v or (len(v) >= 2 and v in q)) else 0


def search(data, mode, front='', back='', colors=(), shape='', capsule=''):
    qf, qb = (norm(front), norm(back)) if mode == 'text' else ('', '')
    full = (40 if qf else 0) + (40 if qb else 0)
    picked = {c.strip() for c in colors if c.strip()}
    found = []
    for r in data:
        if mode == 'text':
            imp = max(side(qf, r['nf']) + side(qb, r['nb']), side(qf, r['nb']) + side(qb, r['nf']))  # 앞뒤가 바뀐 경우도 비교
            if not imp:
                continue  # 각인을 적었으면 각인이 맞는 약만 후보
        elif mode == 'none' and (r['nf'] or r['nb'] or r['mark']):
            continue
        elif mode == 'mark' and not r['mark']:
            continue
        else:
            imp = 0
        c_ok, s_ok = bool(picked & r['colors']), bool(shape) and r['group'] == shape
        k_ok = bool(capsule) and r['capsule'] == (capsule == 'y')
        matches = []
        if mode == 'text':
            matches.append(['각인 완전 일치', 'mint'] if imp == full else ['각인 부분 일치', 'yellow'])
        if picked:
            matches.append(['색 일치', 'mint'] if c_ok else ['색 불일치', 'gray'])
        if shape:
            matches.append(['모양 일치', 'mint'] if s_ok else ['모양 불일치', 'gray'])
        if capsule:
            matches.append(['캡슐 여부 일치', 'mint'] if k_ok else ['캡슐 여부 불일치', 'gray'])
        found.append((imp + 15 * c_ok + 15 * s_ok + 10 * k_ok, r, matches))
    found.sort(key=lambda t: -t[0])
    return len(found), [{'d': r['d'], 'matches': m} for _, r, m in found[:5]]


def source(name):
    meta = json.loads((DATA / 'meta.json').read_text()) if (DATA / 'meta.json').exists() else {}
    return meta.get(name, {})


def official(seq):
    x = edrug().get(seq)
    if not x:
        raise HTTPException(404, '공식 정보(e약은요)에 없는 약입니다.')
    return x, [(t, x[k].strip()) for k, t in DOC_FIELDS if (x.get(k) or '').strip()]


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def on(k):
    return os.environ.get(k, 'off').lower() in ('1', 'on', 'true')


def switches():
    """켠 스위치 중 지금 실제로 쓸 수 있는 것. CLOVA 월 상한을 넘으면 그 달은 무료 모드로 바뀜."""
    return {'photoRead': on('PHOTO_READ') and clova.available(), 'clovaText': on('CLOVA_TEXT') and clova.available(),
            'claudeReview': on('CLAUDE_REVIEW') and bool(os.environ.get('ANTHROPIC_API_KEY')),
            'clovaCapped': (on('PHOTO_READ') or on('CLOVA_TEXT')) and clova.over_cap()}


def write_with_fallback(make):
    """CLOVA_TEXT면 CLOVA로 쓰고, CLOVA가 실패하면 Local LLM이 대신 씀(기획 7장). make(작성 함수) → (결과, 모델 이름)"""
    if switches()['clovaText']:
        try:
            return make(clova.chat), 'CLOVA ' + os.environ.get('CLOVA_TEXT_MODEL', 'HCX-005')
        except ai.Unavailable:
            pass
    return make(ai.chat), 'Qwen3 4B'


@app.get('/api/config')
def config():
    return switches()


@app.get('/api/search')
def api_search(mode: str = 'text', front: str = '', back: str = '', colors: str = '', shape: str = '', capsule: str = ''):
    if mode not in ('text', 'none', 'mark') or len(front) > 40 or len(back) > 40 or len(colors) > 200:
        raise HTTPException(400, '검색 조건이 올바르지 않습니다.')
    total, cands = search(rows(), mode, front, back, re.split(r'[+,]', colors), shape, capsule)
    return {'total': total, 'cands': [{**c, 'd': with_doc(c['d'])} for c in cands], 'source': source('pills')}


@app.get('/api/names')
def api_names(q: str = ''):
    q = q.strip().casefold()[:40]
    if not q:
        return {'hits': []}
    hits = [with_doc(r['d']) for r in rows() if q in r['name_key']][:20]
    # 물약처럼 낱알 자료에 없는 일반의약품도 이름으로 찾음
    pill_seqs = {r['d']['seq'] for r in rows()}
    hits += [{'id': 'e' + s, 'seq': s, 'name': x['itemName'], 'co': x.get('entpName') or '', 'type': 'otc', 'doc': True,
              'f': '', 'b': '', 'color': '', 'color2': '', 'shape': '', 'form': ''}
             for s, x in edrug().items() if s not in pill_seqs and q in (x.get('itemName') or '').casefold()][:20 - len(hits)]
    return {'hits': hits}


@app.get('/api/doc/{seq}')
def api_doc(seq: str):
    x, sections = official(seq)
    return {'sections': sections, 'updateDe': x.get('updateDe'), 'source': source('edrug')}


@app.get('/api/summary/{seq}')
def api_summary(seq: str):
    """약마다 한 번 만들어 저장하고, 공식 원문 수정일(updateDe)이 바뀌면 새로 만든다."""
    x, sections = official(seq)
    path = SUMMARIES / f'{seq}.json'
    saved = json.loads(path.read_text()) if path.exists() else {}
    if saved.get('updateDe') != x.get('updateDe') or 'parts' not in saved:
        try:
            parts, model = write_with_fallback(lambda w: ai.summarize(x['itemName'], sections, w))
        except ai.Unavailable:
            raise HTTPException(503, '요약을 만들지 못했습니다. 원문 탭에서 공식 내용을 확인해 주세요.')
        saved = {'parts': parts, 'model': model, 'updateDe': x.get('updateDe')}
        SUMMARIES.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(saved, ensure_ascii=False))
    source_text = ' '.join(b for _, b in sections)
    return {**saved, 'bad_numbers': ai.numbers_not_in(' '.join(b for _, b in saved['parts']), source_text)}


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=300)


class Ask(Question):
    seq: str = Field(max_length=20)
    masked: bool = False  # 사용자가 가린 문장을 확인하고 보냈는지


@app.post('/api/mask')
def api_mask(body: Question):
    """외부 전송 단계가 켜졌을 때만: 원문 질문은 수업 내부 서버(local-llm-chat)에서만 처리하고, 가린 문장을 사용자에게 돌려줌."""
    try:
        return {'masked': ai.mask(body.question.strip())}
    except ai.Unavailable:
        raise HTTPException(503, '개인정보 확인을 할 수 없어 질문을 보내지 않았습니다.')


LIMITS = DATA / 'limits.json'  # {"day": "2026-11-12", "ask": 3, "photo": 1}


def count_today(name, limit, message):
    """앱 전체 하루 횟수 제한(IP 저장 안 함). 파일에 세므로 서버를 다시 켜도 이어서 셈."""
    with open(LIMITS, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # 같은 자료 폴더를 쓰는 서버(8000·8001)와 스레드가 함께 셈
        f.seek(0)
        try:
            c = json.loads(f.read() or '{}')
        except ValueError:  # 깨진 파일이면 오늘 0부터
            c = {}
        if c.get('day') != date.today().isoformat():
            c = {'day': date.today().isoformat()}
        if c.get(name, 0) >= limit:
            raise HTTPException(429, message)
        c[name] = c.get(name, 0) + 1
        f.seek(0), f.truncate(), f.write(json.dumps(c))


@app.post('/api/photo')
def api_photo(files: list[UploadFile] = File(...)):
    """사용자가 '사진으로 각인 읽기'를 눌렀을 때만 불림. 받은 사진은 메모리에서만 처리하고 저장하지 않음."""
    if not switches()['photoRead']:
        raise HTTPException(403, '사진 읽기를 쓸 수 없습니다. 직접 입력으로 찾아 주세요.')
    if not 1 <= len(files) <= 2:
        raise HTTPException(400, '사진은 한 번에 2장까지 올릴 수 있습니다.')
    images = [f.file.read(MAX_PHOTO + 1) for f in files]
    if any(len(b) > MAX_PHOTO or not b for b in images):
        raise HTTPException(400, '사진은 한 장에 5MB까지 올릴 수 있습니다.')
    count_today('photo', PHOTO_PER_DAY, '오늘 사진 읽기 한도에 도달했습니다. 직접 입력으로 찾아 주세요.')
    try:
        return photo.read(images)
    except ai.Unavailable:
        raise HTTPException(422, '각인을 읽지 못했습니다. 직접 입력하거나 다시 찍어 주세요.')


def sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


@app.post('/api/ask')
def api_ask(body: Ask):
    """근거 찾기(BGE-M3·Chroma) → 답변(CLOVA 또는 Qwen) → 코드 규칙 검사 → Claude 검토(켰을 때).
    단계마다 SSE(step 이벤트)로 알리고 마지막에 result 이벤트를 보냄. 질문은 POST 본문으로만 받고 저장·기록하지 않음."""
    x, sections = official(body.seq)
    sw = switches()
    if (sw['clovaText'] or sw['claudeReview']) and not body.masked:
        # 외부로 나가는 단계가 켜져 있으면 가리기·확인을 거친 질문만 받음 (완료 기준 5)
        raise HTTPException(400, '개인정보를 가린 질문만 보낼 수 있습니다. 화면을 새로 고친 뒤 다시 질문해 주세요.')
    count_today('ask', ASK_PER_DAY, '오늘 이용 한도에 도달했습니다. 내일 다시 시도해 주세요.')
    q = body.question.strip()
    later = ['check'] + (['review'] if sw['claudeReview'] else [])

    def run():
        step = lambda name, status: sse('step', {'step': name, 'status': status})
        yield step('search', 'start')
        try:
            evidence = ai.retrieve(body.seq, x.get('updateDe'), sections, q)
        except ai.Unavailable:
            yield step('search', 'fail')
            yield sse('error', {'detail': '검색 서버에 연결할 수 없습니다. 원문 탭에서 공식 원문 전체를 확인해 주세요.'})
            return
        yield step('search', 'done') + step('write', 'start')
        try:
            text, model = write_with_fallback(lambda w: ai.answer(x['itemName'], q, evidence, w))
        except ai.Unavailable:
            # 답변을 못 만들면 근거 문단만 보여 줌 (기획 7장)
            yield step('write', 'fail') + ''.join(step(s, 'skip') for s in later)
            yield sse('result', {'answer': None, 'evidence': evidence, 'error': '답변을 만들지 못했습니다. 아래 근거 문단을 확인해 주세요.'})
            return
        yield step('write', 'done')
        if not text or ai.NO_ANSWER in text:
            yield ''.join(step(s, 'skip') for s in later) + sse('result', {'answer': None, 'evidence': [], 'error': None})
            return
        out = {'answer': text, 'evidence': evidence, 'checks': ai.rule_check(text, len(evidence)), 'model': model, 'reviewed': False}
        yield step('check', 'done')
        if sw['claudeReview']:
            yield step('review', 'start')
            try:
                out.update(reviewed=True, review=ai.review(x['itemName'], q, evidence, text))
                yield step('review', 'done')
            except ai.Unavailable:
                out['review_error'] = '검토를 마치지 못한 답변입니다'
                yield step('review', 'fail')
        yield sse('result', out)

    return StreamingResponse(run(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


app.mount('/', StaticFiles(directory=ROOT / 'static', html=True), name='static')
