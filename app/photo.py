"""사진 읽기(PHOTO_READ): 위치 정보(EXIF)를 지우고 줄인 사진을 CLOVA HCX-005로 보내 각인·색·모양 값만 받는다. 사진은 저장하지 않는다."""
import base64
import io
import re

from PIL import Image, ImageOps

import clova
from ai import Unavailable

MAX_SIDE = 1024  # 보내기 전에 줄임: CLOVA 한도(긴 변 2240px)보다 작게, 토큰·비용 절약
COLORS = ['하양', '노랑', '주황', '분홍', '빨강', '초록', '파랑', '갈색', '연두', '회색', '보라', '청록', '자주', '검정', '남색', '투명']
SHAPES = ['원형', '타원형', '장방형']
PROMPT = (
    '사진 속 알약(앞면·뒷면이 나란히 있을 수 있음)을 보고 정확히 다음 다섯 줄로만 답한다. 약 이름이나 회사를 추측하지 않는다.\n'
    '앞: (앞면에 새겨진 글자·숫자, 없으면 없음)\n뒤: (뒷면에 새겨진 글자·숫자, 없거나 안 보이면 없음)\n'
    f'색: ({"·".join(COLORS)} 중에서, 여러 색이면 +로 이음)\n모양: (원형·타원형·장방형·기타 중 하나)\n캡슐: (예·아니요 중 하나)')


def prepare(images):
    """사진들(bytes)을 열어 방향만 바로잡고 픽셀만 새 사진으로 옮김(EXIF·위치 정보 제거) → 나란히 붙인 JPEG bytes.
    CLOVA는 한 턴에 사진 1장만 받아서 앞·뒤를 한 장으로 붙여 한 번만 호출한다."""
    pics = []
    for b in images:
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(b))).convert('RGB')
        except Exception:
            raise Unavailable('사진 파일을 읽을 수 없습니다.') from None
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        pics.append(im)
    h = max(p.height for p in pics)
    sheet = Image.new('RGB', (sum(p.width for p in pics) + 16 * (len(pics) - 1), h), 'white')
    x = 0
    for p in pics:
        sheet.paste(p, (x, (h - p.height) // 2))
        x += p.width + 16
    sheet.thumbnail((2240, 2240))
    out = io.BytesIO()
    sheet.save(out, 'JPEG', quality=85)  # exif를 넘기지 않으므로 메타데이터 없음
    return out.getvalue()


def parse(text):
    """다섯 줄 답 → 입력칸 값. 읽지 못한 칸은 비워 둠."""
    line = lambda k: (re.search(rf'^\s*{k}\s*[:：]\s*(.+)$', text, re.M) or [None, ''])[1].strip()
    clean = lambda v: '' if re.fullmatch(r'(없음|모름|안 보임|-)?\.?', v) else re.sub(r'[^0-9A-Za-z\- ]', '', v).strip()
    colors = [c for c in COLORS if c in line('색')]
    shape = line('모양')
    cap = line('캡슐')
    return {'front': clean(line('앞')), 'back': clean(line('뒤')), 'colors': colors,
            'shape': next((s for s in SHAPES if s == shape.rstrip('.')), '기타' if shape else ''),
            'capsule': 'y' if cap.startswith('예') else 'n' if cap.startswith('아니') else ''}


def read(images):
    jpeg = prepare(images)
    data = 'data:image/jpeg;base64,' + base64.b64encode(jpeg).decode()  # 접두어가 없으면 CLOVA가 40001 오류
    text = clova.chat([{'role': 'user', 'content': [{'type': 'image_url', 'dataUri': {'data': data}},
                                                     {'type': 'text', 'text': PROMPT}]}], 200, model='HCX-005')
    got = parse(text)
    if not (got['front'] or got['back'] or got['colors'] or got['shape']):
        raise Unavailable('각인을 읽지 못했습니다.')
    return got


if __name__ == '__main__':
    # 자가 검사: 답 읽기, EXIF(위치 정보) 제거
    assert parse('앞: TYLENOL\n뒤: 500\n색: 하양\n모양: 장방형\n캡슐: 아니요') == {
        'front': 'TYLENOL', 'back': '500', 'colors': ['하양'], 'shape': '장방형', 'capsule': 'n'}
    assert parse('앞: 없음\n뒤: 없음\n색: 노랑+투명\n모양: 팔각형\n캡슐: 예')['colors'] == ['노랑', '투명']
    assert parse('앞: 없음\n뒤: 없음\n색: 노랑\n모양: 팔각형\n캡슐: 예')['shape'] == '기타'
    im = Image.new('RGB', (40, 20), 'white'); exif = Image.Exif(); exif[0x8825] = {2: (37.0, 30.0, 0.0)}  # GPSInfo
    raw = io.BytesIO(); im.save(raw, 'JPEG', exif=exif); assert Image.open(io.BytesIO(raw.getvalue())).getexif().get(0x8825)
    out = Image.open(io.BytesIO(prepare([raw.getvalue(), raw.getvalue()])))
    assert not out.getexif() and out.size == (96, 20), out.size
    print('ok')
