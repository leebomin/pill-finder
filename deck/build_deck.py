"""Claude Design 'Pill Finder Deck v2.dc.html'(1920×1080)을 PPTX로 옮김. 1px = 6350 EMU = 0.5pt.
실행: <python-pptx가 있는 python> build_deck.py  → pill-finder-deck.pptx
화면 캡처는 shots/screen1.png·screen2.png·screen3.png가 있으면 넣고, 없으면 자리 표시를 둔다."""
import copy
import re
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = Path(__file__).parent
FONT = '맑은 고딕'  # 받는 PC에 Pretendard가 없을 수 있어 Windows·Office 기본 한글 글꼴을 테마 글꼴로 씀
E = lambda v: Emu(int(round(v * 6350)))

prs = Presentation()
prs.slide_width, prs.slide_height = E(1920), E(1080)
TITLE_ONLY = prs.slide_layouts[5]

# 테마 글꼴(제목·본문, 영문·한글)을 한 번에 바꿈 → 글자마다 글꼴 이름을 쓰지 않음
theme_part = prs.slide_master.part.part_related_by('http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme')
theme = etree.fromstring(theme_part.blob)
for tag in ('majorFont', 'minorFont'):
    for sub in ('latin', 'ea'):
        theme.find(f'.//{qn("a:" + tag)}/{qn("a:" + sub)}').set('typeface', FONT)
theme_part._blob = etree.tostring(theme, xml_declaration=True, encoding='UTF-8', standalone=True)


def rgb(h):
    return RGBColor.from_string(h.lstrip('#'))


def box(slide, x, y, w, h, fill=None, r=0, line=None, lw=2, dash=None, shape=None, name=None):
    """사각형(r>0이면 둥근 모서리, px). fill/line은 '#rrggbb' 또는 None."""
    kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if r else MSO_SHAPE.RECTANGLE)
    s = slide.shapes.add_shape(kind, E(x), E(y), E(w), E(h))
    if r and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, r / min(w, h))
    if fill:
        s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line); s.line.width = Pt(lw * 0.5)
        if dash:
            s.line.dash_style = dash
    else:
        s.line.fill.background()
    st = s._element.find(qn('p:style'))
    if st is not None:
        s._element.remove(st)  # 기본 도형 스타일(그림자·테두리 효과)을 지움: 시안에는 그림자가 없음
    if name:
        s.name = name
    return s


def style_run(run, size, bold=False, color='#111111', spc=0):
    f = run.font
    f.size, f.bold, f.color.rgb = Pt(size * 0.5), bold, rgb(color)
    if spc:
        run._r.get_or_add_rPr().set('spc', str(int(spc * 50)))  # 글자 사이 px → 1/100pt


def fill_frame(tf, paras, anchor='top', margin=(0, 0, 0, 0)):
    """paras: [{'runs': [(글, {size,bold,color,spc})], 'align': 'l|c|r', 'lh': CSS line-height, 'before': px}]"""
    tf.word_wrap = True
    tf.auto_size = None
    l, t, r, b = margin
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = E(l), E(t), E(r), E(b)
    tf.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE, 'bottom': MSO_ANCHOR.BOTTOM}[anchor]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[p.get('align', 'l')]
        para.line_spacing = p.get('lh', 1.2) / 1.2  # CSS 줄 높이 → PowerPoint 배수(한 줄 ≈ 글자 1.2배)
        if p.get('before'):
            para.space_before = Pt(p['before'] * 0.5)
        for text, st in p['runs']:
            run = para.add_run()
            run.text = text
            style_run(run, **st)


def text(slide, x, y, w, h, paras, anchor='top', name=None, margin=(0, 0, 0, 0), fill=None):
    tb = slide.shapes.add_textbox(E(x), E(y), E(w), E(h))
    fill_frame(tb.text_frame, paras, anchor, margin)
    if fill:
        tb.fill.solid(); tb.fill.fore_color.rgb = rgb(fill)
    if name:
        tb.name = name
    return tb


def P(t, size, bold=False, color='#111111', spc=0, align='l', lh=1.2, before=0):
    return {'runs': [(t, dict(size=size, bold=bold, color=color, spc=spc))], 'align': align, 'lh': lh, 'before': before}


def new_slide(title, x, y, w, h, size, color='#111111', spc=-2, notes='', bg='#ffffff', anchor='top', lh=1.15):
    """제목은 진짜 제목 칸에 넣음(개요·화면 읽기 프로그램에 슬라이드 제목이 보이게)."""
    s = prs.slides.add_slide(TITLE_ONLY)
    s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(bg)
    t = s.shapes.title
    t.left, t.top, t.width, t.height = E(x), E(y), E(w), E(h)
    fill_frame(t.text_frame, [P(title, size, True, color, spc, lh=lh)], anchor)
    bp = t.text_frame._txBody.find(qn('a:bodyPr'))
    for child in list(bp):
        bp.remove(child)  # 레이아웃의 자동 맞춤 끄기
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def arrow(slide, pts, color='#111111', start=False, end=True, dash=False, w=3):
    """pts: [(x,y), …] px. 두 점이면 직선, 더 많으면 꺾은선."""
    if len(pts) == 2:
        (x1, y1), (x2, y2) = pts
        ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
        line = ln.line
    else:
        fb = slide.shapes.build_freeform(E(pts[0][0]), E(pts[0][1]), scale=1.0)
        fb.add_line_segments([(E(px), E(py)) for px, py in pts[1:]], close=False)
        ln = fb.convert_to_shape()
        ln.fill.background()
        line = ln.line
    line.color.rgb = rgb(color); line.width = Pt(w * 0.5)
    ln_xml = line._get_or_add_ln()
    if dash:
        from pptx.enum.dml import MSO_LINE
        line.dash_style = MSO_LINE.DASH
    for tag, on in (('a:headEnd', start), ('a:tailEnd', end)):
        if on:
            el = etree.SubElement(ln_xml, qn(tag)); el.set('type', 'triangle'); el.set('w', 'med'); el.set('len', 'med')
    ln.shadow.inherit = False
    return ln


def header(s, eyebrow, color='#3b82f6', y=90):
    text(s, 100, y, 1720, 40, [P(eyebrow, 28, False, color, spc=6)], name='Eyebrow')


GRAY, BODY, INK, BLUE = '#6b7280', '#374151', '#111111', '#3b82f6'

# ---------- 01 표지 ----------
s = new_slide('알약 찾기 도우미', 110, 392, 1700, 200, 176, spc=-6, notes='프로젝트 소개', lh=1.05)
box(s, 1200, -60, 1100, 1100, '#eef4ff', shape=MSO_SHAPE.OVAL, name='Background circle')
tile = box(s, 1670, 80, 150, 150, '#34c98a', r=38, name='Pill icon')
tile.fill.gradient(); tile.fill.gradient_angle = 315
tile.fill.gradient_stops[0].color.rgb = rgb('#a7f0c8'); tile.fill.gradient_stops[1].color.rgb = rgb('#34c98a')
pill = box(s, 1745 - 42, 155 - 20, 84, 40, None, r=20, line='#ffffff', lw=6, name='Pill icon outline')
pill.rotation = 320
t_el = s.shapes.title._element
s.shapes._spTree.remove(t_el); s.shapes._spTree.append(t_el)  # 제목을 배경 원 위로
text(s, 110, 340, 1700, 40, [P('과제 제출 · 표지', 30, False, BLUE, spc=6)])
text(s, 110, 628, 1200, 130, [P('알약 각인·색·모양이나 사진으로 무슨 약인지 후보를 찾고, 식약처 공식 자료로 답하는 웹 도구', 42, False, BODY, lh=1.5)])
for x, w, t in ((110, 380, '[이름] · [학번]'), (514, 250, '[제출일]')):
    b = box(s, x, 922, w, 68, '#ffffff', r=34, line='#9ca3af', lw=2, name='Placeholder ' + t)
    fill_frame(b.text_frame, [P(t, 30, False, BODY, align='c')], 'middle')

# ---------- 02 SOW ----------
s = new_slide('SOW (작업 범위)', 100, 132, 1720, 104, 84, notes='목적과 산출물 세 가지')
header(s, 'SCOPE OF WORK')
b = box(s, 100, 276, 1720, 180, '#f5f5f5', r=28, name='Purpose')
text(s, 144, 276, 90, 180, [P('목적', 30, True, BLUE)], anchor='middle')
text(s, 254, 276, 1522, 180, [P('집에 남은 알약이 무엇인지 각인·색·모양이나 사진으로 후보를 찾고, 식약처 공식 자료만 근거로 약 정보와 질문에 답한다.', 38, False, INK, lh=1.5)], anchor='middle')
cards = [('산출물 1', '화면 시안', 'claude.ai/design 시안을 정적 웹페이지로 옮김. 화면 1 약 찾기 · 2 후보 비교 · 3 약 정보와 질문', '완료', 170),
         ('산출물 2', '동작하는 기능', '식약처 자료로 후보 찾기·이름 검색, 공식 원문·쉬운 말 요약, 근거 기반 질문 답변, 사진으로 각인 읽기, 개인정보 가리기, 답변 검토', '완료 (서버에서 동작)', 370),
         ('산출물 3', '시연 영상', '[시연 영상 링크 또는 QR — 제출자가 넣음]', '[ ]', 90)]
cw = (1720 - 2 * 28) / 3
for i, (lab, title, body, badge, bw) in enumerate(cards):
    x = 100 + i * (cw + 28)
    if i < 2:
        box(s, x, 480, cw, 430, '#eef4ff', r=28, name=title)
    else:
        from pptx.enum.dml import MSO_LINE
        box(s, x, 480, cw, 430, None, r=28, line='#9ca3af', lw=2, dash=MSO_LINE.DASH, name=title)
    text(s, x + 36, 516, cw - 72, 300, [P(lab, 26, False, GRAY), P(title, 44, True, INK, before=20), P(body, 28, False, BODY, lh=1.55, before=20)])
    done = badge.startswith('완료')
    bd = box(s, x + 36, 826, bw, 48, '#d9f5e5' if done else '#f5f5f5', r=24, name='Status ' + title)
    fill_frame(bd.text_frame, [P(badge, 28, True, '#065f46' if done else GRAY, align='c')], 'middle')
text(s, 100, 936, 1720, 80, [P('하지 않는 것: 진단·복용 지시, 로그인, 결제, 처방전 사진, 병용 금기 확인 · 결과는 “후보”이며 복용 전 약사 확인을 안내함', 26, False, GRAY, lh=1.5)])

# ---------- 03 구성과 데이터 흐름 ----------
s = new_slide('구성과 데이터 흐름', 60, 40, 560, 80, 56, spc=-1.5, notes='서버, 모델, RAG, MCP 연결. 번호 순서가 질문 한 번의 흐름')
text(s, 630, 62, 900, 50, [P('6절 · 번호 순서가 질문 한 번의 흐름', 30, False, GRAY)])


def card(s, x, y, w, h, fill, lines, r=12, line=None, lw=2, pad=20, dark=False, name=None, dash=None):
    b = box(s, x, y, w, h, fill, r=r, line=line, lw=lw, dash=dash, name=name)
    fill_frame(b.text_frame, lines, 'middle', (pad, pad, pad, pad))
    return b


# 영역 상자 (화살표보다 먼저 = 아래)
box(s, 900, 230, 480, 570, '#eef4ff', r=28, name='수업 내부 서버')
from pptx.enum.dml import MSO_LINE
box(s, 1460, 230, 400, 570, None, r=28, line='#9ca3af', lw=3, dash=MSO_LINE.DASH, name='외부 서비스')
text(s, 924, 244, 400, 36, [P('수업 내부 서버', 26, True, '#1d4ed8')])
text(s, 1480, 244, 370, 36, [P('외부 서비스 (스위치)', 26, True, BODY)])
# 화살표 (도식의 SVG 경로 그대로)
for pts, st in [([(330, 450), (420, 450)], True), ([(330, 690), (420, 690)], False), ([(800, 380), (940, 380)], False),
                ([(800, 690), (940, 690)], False), ([(800, 530), (1480, 530)], False), ([(700, 230), (700, 190), (1660, 190), (1660, 300)], False)]:
    arrow(s, pts, INK, start=st)
arrow(s, [(330, 930), (420, 930)], BLUE)
arrow(s, [(800, 930), (1120, 930), (1120, 790)], BLUE)
arrow(s, [(610, 870), (610, 800)], BLUE, end=False, dash=True)
# 구성 요소
card(s, 60, 370, 270, 160, '#f5f5f5', [P('브라우저(폰)', 32, True), P('화면 1·2·3', 26, False, BODY, before=6)], name='브라우저')
card(s, 60, 600, 270, 200, '#f5f5f5', [P('공공데이터포털 (식약처)', 28, True, lh=1.25), P('낱알식별 25,501건 · e약은요 4,749건 · 매주 월 03:00 갱신', 22, False, BODY, lh=1.35, before=6)], pad=16, name='공공데이터포털')
card(s, 420, 230, 380, 570, '#111111', [P('서버', 26, True, '#93c5fd', spc=3), P('앱 서버', 34, True, '#ffffff', before=14, lh=1.25), P('FastAPI · 포트 8000', 30, True, '#ffffff', lh=1.25),
     P('후보 비교·이름 검색은 코드가 직접 함', 26, False, '#e5e7eb', lh=1.5, before=14), P('비용 스위치 · 하루 한도', 26, False, '#e5e7eb', lh=1.5),
     P('코드 규칙 검사 (단정 표현, 근거 번호 없는 문장)', 26, False, '#e5e7eb', lh=1.5)], r=28, pad=28, name='앱 서버')
s.shapes[-1].text_frame.vertical_anchor = MSO_ANCHOR.TOP
card(s, 940, 300, 400, 200, '#ffffff', [P('모델', 24, True, BLUE, spc=3), P('Local LLM · Qwen3 4B', 30, True, before=8), P('쉬운 말 요약 · 답변 작성(무료 모드) · 개인정보 가리기', 26, False, BODY, lh=1.4, before=8)], line='#bfd3fb', pad=24, name='Qwen3 4B')
card(s, 940, 600, 400, 180, '#ffffff', [P('RAG', 24, True, BLUE, spc=3), P('BGE-M3 + Chroma', 32, True, before=8), P('공식 문단에서 근거 최대 5개', 26, False, BODY, lh=1.4, before=8)], line='#bfd3fb', pad=24, name='RAG')
card(s, 1480, 300, 360, 200, '#f5f5f5', [P('모델', 24, True, GRAY, spc=3), P('CLOVA HCX-005', 32, True, before=8), P('사진으로 각인 읽기 · 요약·답변 작성 · 월 상한 5,000원', 24, False, BODY, lh=1.35, before=8)], name='CLOVA')
card(s, 1480, 560, 360, 200, '#f5f5f5', [P('모델', 24, True, GRAY, spc=3), P('Claude Haiku 5.5 (API)', 32, True, before=8), P('답변 검토 (근거 밖 내용·단정적 복용 지시)', 24, False, BODY, lh=1.35, before=8)], name='Claude')
card(s, 420, 870, 380, 170, '#ffffff', [P('MCP', 24, True, BLUE, spc=3), P('pill-finder MCP 서버', 30, True, before=4), P('stdio · 같은 자료 파일, 같은 RAG', 24, False, BODY, before=4)], line=BLUE, lw=3, pad=16, name='MCP 서버')
card(s, 60, 870, 270, 170, '#f5f5f5', [P('MCP 클라이언트', 24, False, GRAY), P('Claude Code', 30, True, before=4)], pad=16, name='MCP 클라이언트')
# 화살표 이름표 (흰 바탕)
for x, y, w, t, c, b in [(440, 818, 280, '같은 자료·같은 RAG', BLUE, True), (331, 892, 88, '도구 4개', BLUE, True),
                         (1100, 512, 260, '6 · 7 · 8 → Claude', INK, True), (1150, 172, 200, '3 · 6 → CLOVA', INK, True),
                         (340, 410, 70, '2', BODY, False), (340, 650, 70, '1', BODY, False), (810, 340, 120, '4', BODY, False),
                         (810, 650, 120, '5', BODY, False), (340, 470, 70, '9', GRAY, False)]:
    text(s, x, y, w, 34, [P(t, 21 if w < 100 and b else 24, b, c, align='c')], fill='#ffffff' if b else None, name='Label ' + t)
text(s, 1160, 860, 700, 190, [{'runs': [('MCP는 읽기 전용. ', dict(size=26, bold=True, color=BLUE)), ('외부 유료 서비스로 가는 화살표 없음.', dict(size=26, color=BODY))], 'lh': 1.45},
                              P('외부로 나가는 것은 가린 질문 · 자른 사진 · 공개 원문뿐이며 질문·사진은 저장하지 않음. 스위치 3개(PHOTO_READ, CLOVA_TEXT, CLAUDE_REVIEW)를 모두 끄면 무료 모드.', 26, False, BODY, lh=1.45, before=12)])

# ---------- 04 화면 흐름 ----------
s = new_slide('화면 흐름', 104, 108, 900, 104, 84, spc=-3, notes='화면 1, 2, 3')
text(s, 110, 70, 600, 40, [P('SCREENS', 28, True, BLUE, spc=6)])
text(s, 1210, 124, 600, 50, [P('찾기 → 후보 비교 → 약 정보 순서로 이어집니다.', 28, False, GRAY, lh=1.6)])
from PIL import Image
for i, (x, title, sub) in enumerate([(110, '1 · 약 찾기', '직접 입력 / 사진 / 이름 검색'), (690, '2 · 후보 비교', '최대 5개 · 일치 배지'), (1270, '3 · 약 정보', '요약 / 원문 / 질문하기')], 1):
    box(s, x, 250, 540, 650, '#f5f5f5', r=28, name=f'Screen {i} card')
    shot = HERE / 'shots' / f'screen{i}.png'
    ix, iy, iw = x + 100, 284, 340
    if shot.exists():
        W, H = Image.open(shot).size
        ih = iw * H / W
        pic = s.shapes.add_picture(str(shot), E(ix), E(iy), E(iw))
        if ih > 900 - 20 - iy:  # 카드 아래(여백 20px)에서 잘라냄 = 시안의 overflow:hidden
            pic.crop_bottom = 1 - (900 - 20 - iy) / ih
            pic.height = E(900 - 20 - iy)
        pic.name = f'화면 캡처 {i}'
        pic._element.nvPicPr.cNvPr.set('descr', f'앱 화면 {title}: {sub}')
    else:
        ph = box(s, ix, iy, iw, 596, '#ffffff', r=14, line='#d1d5db', lw=2, name=f'화면 캡처 {i} 자리')
        fill_frame(ph.text_frame, [P(f'[화면 캡처 {i}]', 28, True, GRAY, align='c'), P(title, 24, False, GRAY, align='c', before=8)], 'middle')
    text(s, x, 925, 540, 90, [P(title, 34, True), P(sub, 26, False, GRAY, before=4)])

# ---------- 05 각인 비교 규칙 ----------
s = new_slide('각인 비교 규칙', 100, 132, 1720, 104, 84, notes='점수 규칙', bg='#f5f5f5')
header(s, 'MATCHING')
lw_, rw_ = (1720 - 48) / 2.1, (1720 - 48) * 1.1 / 2.1
box(s, 100, 288, lw_, 712, '#ffffff', r=28, name='같은 글자로 보기')
text(s, 140, 328, lw_ - 80, 640, [P('같은 글자로 보기', 36, True), P('대소문자·공백·하이픈 무시', 30, False, BODY, lh=1.6, before=28),
                                  P('0/O · 1/I/l · 5/S · 8/B 같은 글자로 봄', 30, False, BODY, lh=1.6), P('앞뒤가 바뀌어도 찾음', 30, False, BODY, lh=1.6),
                                  P('실제 자료에서 찾은 점', 36, True, before=40), P('각인 칸에 “분할선”·“마크”가 섞여 있어 빼고 비교', 30, False, BODY, lh=1.6, before=28),
                                  P('한 글자 각인(“Q”)은 부분 일치에서 제외', 30, False, BODY, lh=1.6)])
rx = 100 + lw_ + 48
box(s, rx, 288, rw_, 712, '#ffffff', r=28, name='점수')
text(s, rx + 40, 328, rw_ - 80, 50, [P('점수 → 상위 5개', 36, True)])
for j, (lab, val) in enumerate([('각인 완전 일치', '40'), ('각인 부분 일치', '20'), ('색', '+15'), ('모양', '+15'), ('캡슐', '+10')]):
    y = 400 + j * 112
    text(s, rx + 40, y, 500, 96, [P(lab, 32)], anchor='middle')
    text(s, rx + rw_ - 340, y, 300, 96, [P(val, 56, True, BLUE if j == 0 else INK, align='r')], anchor='middle')
    if j < 4:
        box(s, rx + 40, y + 104, rw_ - 80, 2, '#e5e7eb', name='Row divider')

# ---------- 06 안전장치 ----------
s = new_slide('안전장치', 100, 132, 1720, 104, 84, notes='여섯 가지 안전장치')
header(s, 'SAFEGUARDS')
items = [('응급 표현', '119 안내를 답변보다 먼저'), ('개인정보 가리기', '외부로 보내기 전 가리고, 사용자 확인 후 전송'), ('근거 문단만 사용', '없으면 “공식 자료에 해당 내용이 없습니다”'),
         ('코드 규칙 검사', '단정 표현, 근거 번호 없는 문장'), ('Claude 검토', '근거 밖 내용·단정적 복용 지시 확인'), ('요약 숫자 경고', '원문에 없는 숫자가 있으면 경고')]
cw, ch = (1720 - 56) / 3, (704 - 28) / 2
for k, (t, d) in enumerate(items):
    x, y = 100 + (k % 3) * (cw + 28), 296 + (k // 3) * (ch + 28)
    box(s, x, y, cw, ch, '#f5f5f5', r=28, name=t)
    c = box(s, x + 32, y + 32, 60, 60, '#dbe7fd', shape=MSO_SHAPE.OVAL, name=f'Number {k + 1:02d}')
    fill_frame(c.text_frame, [P(f'{k + 1:02d}', 26, False, INK, align='c')], 'middle')
    text(s, x + 32, y + 108, cw - 64, ch - 140, [P(t, 36, True), P(d, 28, False, BODY, lh=1.5, before=16)])

# ---------- 07 비용 스위치 ----------
s = new_slide('비용 스위치와 무료 모드', 100, 132, 1720, 104, 84, notes='비용 스위치와 무료 모드', bg='#f5f5f5')
header(s, 'COST CONTROL')
box(s, 100, 284, 1720, 380, '#ffffff', r=28, name='Switch table')
cols = [(140, 320), (484, 650), (1158, 622)]
rows = [(('스위치', '켰을 때', '껐을 때'), 26, True, GRAY), (('PHOTO_READ', 'CLOVA가 사진에서 각인 읽기', '사진 탭 사용 불가'), 30, False, BODY),
        (('CLOVA_TEXT', 'CLOVA가 요약·답변 작성', 'Qwen이 작성 (무료)'), 30, False, BODY), (('CLAUDE_REVIEW', 'Claude가 답변 검토', '코드 규칙 검사만'), 30, False, BODY)]
y = 296
for n, (cells, size, head, color) in enumerate(rows):
    h = 72 if head else 90
    for (cx, cw_), cell, ci in zip(cols, cells, range(3)):
        text(s, cx, y, cw_, h, [P(cell, size, head or ci == 0, color if head else (INK if ci == 0 else BODY))], anchor='middle')
    y += h
    if n < 3:
        box(s, 140, y, 1640, 2, '#e5e7eb', name='Row divider')
stats = [('5,000원', 'CLOVA 월 상한, 넘으면 그 달은 무료 모드', BLUE), ('약 2.3원', '사진 읽기 한 장', INK), ('약 0.3원', 'Claude 검토 1회', INK), ('20.22원', '개발 중 시험에 쓴 CLOVA 비용', INK)]
sw = (1720 - 3 * 24) / 4
for k, (v, d, c) in enumerate(stats):
    text(s, 100 + k * (sw + 24), 712, sw, 180, [P(v, 52, True, c), P(d, 26, False, BODY, lh=1.4, before=6)])

# ---------- 08 검증 결과 ----------
s = new_slide('검증 결과', 100, 132, 1720, 104, 84, notes='연습 질문 20개(초안)로 잰 완료 기준과 자동 검사, 속도')
header(s, 'VERIFICATION')
sw = (1720 - 3 * 28) / 4
for k, (v, d) in enumerate([('10/10', '개인정보 가리기'), ('5/5', '응급 119 먼저'), ('20/20', '근거 제시'), ('5/5', '근거 밖 문장 잡기')]):
    x = 100 + k * (sw + 28)
    box(s, x, 296, sw, 230, '#f5f5f5', r=28, name=d)
    text(s, x + 32, 320, sw - 64, 190, [P(v, 96, True, spc=-3), P(d, 30, True, before=12)])
text(s, 100, 566, 1720, 44, [P('연습 질문 20개(초안) 기준 · 자동 검사 60개 모두 통과 (무료 모드 21 · 스위치 켬 18 · 자르기 12 · MCP 9)', 30, False, BODY)])
box(s, 100, 660, 1720, 2, '#e5e7eb', name='Divider')
tw = (1720 - 2 * 28) / 3
for k, (lab, v, sub) in enumerate([('요약', '18~22초', '저장 후 즉시'), ('질문 답변 · 무료 모드', '중앙 4.6초', '1.8~9.6초'), ('Claude 검토', '2~3초', '')]):
    text(s, 100 + k * (tw + 28), 702, tw, 170, [P(lab, 26, False, GRAY), P(v, 44, True, before=8)] + ([P(sub, 26, False, BODY, before=8)] if sub else []))

# ---------- 09 한계와 다음 할 일 ----------
s = new_slide('한계와 다음 할 일', 100, 132, 1720, 104, 84, color='#ffffff', notes='한계와 다음 단계', bg='#111111')
header(s, 'NEXT', '#93c5fd')
for k, t in enumerate(['실제 폰 화면 확인', '약 10종 사진으로 사진 읽기 정확도 측정', '직접 만든 연습 질문 20개로 다시 측정', '식약처 자료 이용 허용 문의']):
    y = 400 + k * 130
    text(s, 100, y, 80, 117, [P(f'{k + 1:02d}', 30, True, '#93c5fd')], anchor='middle')
    text(s, 200, y, 1620, 117, [P(t, 44, False, '#ffffff')], anchor='middle')
    if k < 3:
        box(s, 100, y + 128, 1720, 2, '#374151', name='Row divider')

prs.core_properties.title = '알약 찾기 도우미'
out = HERE / 'pill-finder-deck.pptx'
prs.save(out)
print(out)
