"""알약 찾기 도우미 MCP 서버(stdio). 앱과 같은 자료·코드로 후보 찾기·이름 검색·공식 원문·근거 찾기(RAG)를 도구로 제공한다.
모두 읽기 전용이고 CLOVA·Claude 같은 외부 유료 호출은 하지 않는다(근거 찾기는 수업 내부 BGE-M3·Chroma만 씀).
등록: claude mcp add pill-finder -- /opt/rag-lab-b/.venv/bin/python /opt/pill-finder/pill_mcp.py"""
import logging
import re
import sys
from typing import Annotated, Literal

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

import ai
import app  # .env 읽기와 자료 파일 불러오기를 앱과 같이 씀

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)  # stdio에서는 표준 출력에 아무것도 쓰면 안 됨
server = FastMCP('pill-finder')
NOTE = '결과는 후보이며 진단·복용 지시가 아닙니다. 복용 전 약사에게 확인하세요.'


def _plain(d, matches=None):
    out = {'item_seq': d['seq'], 'name': d['name'], 'company': d['co'], 'type': '일반의약품' if d['type'] == 'otc' else '전문의약품',
           'front': d['f'], 'back': d['b'], 'color': ', '.join(c for c in [d['color'], d['color2']] if c), 'shape': d['shape'],
           'has_official_info': d.get('doc', False)}
    if matches is not None:
        out['matches'] = [m[0] for m in matches]
    return out


def _call(fn, *args):
    # 앱 함수의 HTTP 오류를 MCP 도구 오류로 바꿈 (문구는 앱 화면과 같음)
    try:
        return fn(*args)
    except HTTPException as e:
        raise ToolError(e.detail) from None


@server.tool()
def search_pills(
    front: Annotated[str, Field(max_length=40, description='앞면 각인 (모르면 빈 칸)')] = '',
    back: Annotated[str, Field(max_length=40, description='뒷면 각인 (모르면 빈 칸)')] = '',
    colors: Annotated[list[str], Field(max_length=5, description='색 (예: 하양, 노랑, 분홍)')] = [],
    shape: Annotated[Literal['', '원형', '타원형', '장방형', '기타'], Field(description='모양')] = '',
    capsule: Annotated[Literal['', 'y', 'n'], Field(description='캡슐형이면 y, 아니면 n')] = '',
    imprint: Annotated[Literal['text', 'none', 'mark'], Field(description='text=글자 각인, none=각인 없음, mark=로고')] = 'text',
) -> dict:
    """알약의 각인·색·모양으로 식약처 낱알식별 자료(약 2만 5천 건)에서 후보를 최대 5개 찾습니다.
    대소문자·공백·하이픈은 무시하고 0/O, 1/I/l, 5/S, 8/B는 같은 글자로 보며, 앞뒤가 바뀌어도 찾습니다."""
    if imprint == 'text' and not (front.strip() or back.strip()):
        raise ToolError('각인을 입력하거나 imprint를 none 또는 mark로 정해 주세요.')
    total, cands = _call(app.search, _call(app.rows), imprint, front, back, colors, shape, capsule)
    return {'total_matches': total, 'candidates': [_plain(_call(app.with_doc, c['d']), c['matches']) for c in cands],
            'source': {'provider': '식품의약품안전처 · 의약품 낱알식별 정보', **app.source('pills')}, 'note': NOTE}


@server.tool()
def find_drug_by_name(name: Annotated[str, Field(min_length=1, max_length=40, description='약 이름 일부')]) -> dict:
    """약 이름으로 찾습니다(최대 20개). 물약처럼 낱알 자료에 없는 일반의약품도 e약은요에서 찾습니다."""
    return {'drugs': [_plain(d) for d in _call(app.api_names, name)['hits']], 'note': NOTE}


@server.tool()
def get_official_info(item_seq: Annotated[str, Field(pattern=r'^\d{6,12}$', description='품목일련번호 (search_pills·find_drug_by_name 결과의 item_seq)')]) -> dict:
    """일반의약품의 식약처 공식 설명(e약은요) 원문을 항목별로 돌려줍니다: 효능, 사용법, 경고, 주의사항, 상호작용, 부작용, 보관."""
    x, sections = _call(app.official, item_seq)
    return {'name': x['itemName'], 'sections': [{'title': t, 'text': b} for t, b in sections], 'updated': x.get('updateDe'),
            'source': {'provider': '식품의약품안전처 · 의약품개요정보(e약은요)', **app.source('edrug')}, 'note': NOTE}


@server.tool()
def find_evidence(
    item_seq: Annotated[str, Field(pattern=r'^\d{6,12}$', description='품목일련번호')],
    question: Annotated[str, Field(min_length=2, max_length=300, description='궁금한 점. 이름·나이·병명 같은 개인정보는 넣지 마세요')],
) -> dict:
    """질문과 가장 가까운 공식 원문 문단을 최대 5개 찾습니다(RAG: BGE-M3 임베딩 + Chroma pill-docs).
    답을 만들어 주지 않고 근거 문단만 돌려줍니다. 응급 상황(약을 많이 삼킴 등)이면 바로 119에 연락하세요."""
    x, sections = _call(app.official, item_seq)
    try:
        evidence = ai.retrieve(item_seq, x.get('updateDe'), sections, question.strip())
    except ai.Unavailable:
        raise ToolError('검색 서버에 연결할 수 없습니다. get_official_info로 공식 원문 전체를 확인해 주세요.') from None
    emergency = bool(re.search(r'삼켰|과다|과량|많이 먹|여러 알|한꺼번에|다 먹었|다 먹어 ?버|잘못 먹|통째', question))
    return {'name': x['itemName'], 'evidence': [{'n': i, **e} for i, e in enumerate(evidence, 1)],
            **({'emergency': '응급 상황이면 즉시 119에 연락하세요.'} if emergency else {}), 'note': NOTE}


if __name__ == '__main__':
    server.run(transport='stdio')
