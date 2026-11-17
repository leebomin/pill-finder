'use strict';
// shortcut: 예시 데이터·가짜 사진 읽기·가짜 답변으로 동작함, 백엔드 API가 생기면 DRUGS·DOCS·SUMMARY·QA와 sendPhoto·startAsk를 서버 호출로 바꿀 것

const DRUGS = [
  { id: 1, name: '타이레놀정500밀리그람', co: '한국존슨앤드존슨판매(유)', type: 'otc', f: 'TYLENOL', b: '500', color: '하양', shape: '장방형', doc: 'ir' },
  { id: 2, name: '타이레놀8시간이알서방정', co: '한국존슨앤드존슨판매(유)', type: 'otc', f: 'TYLENOL', b: 'ER', color: '하양', shape: '장방형', doc: 'er' },
  { id: 3, name: '타세놀8시간이알서방정', co: '부광약품(주)', type: 'otc', f: 'TSN', b: 'ER', color: '하양', shape: '장방형', doc: 'er' },
  { id: 4, name: '세토펜정500밀리그람', co: '삼아제약(주)', type: 'otc', f: 'SA', b: '500', color: '하양', shape: '원형', doc: 'ir' },
  { id: 5, name: '울트라셋정', co: '(주)한국얀센', type: 'rx', f: 'ULTRACET', b: '', color: '노랑', shape: '장방형' },
  { id: 6, name: '울트라셋이알서방정', co: '(주)한국얀센', type: 'rx', f: 'ULTRACET', b: 'ER', color: '하양', shape: '타원형' },
];
const COLORS = [['하양', '#ffffff'], ['노랑', '#fde68a'], ['주황', '#fdba74'], ['분홍', '#f9a8d4'], ['빨강', '#f87171'], ['초록', '#86efac'], ['파랑', '#93c5fd'], ['갈색', '#b08968']];
const SHAPES = [['원형', 18, 18, '50%'], ['타원형', 26, 16, '50%'], ['장방형', 28, 13, '9999px'], ['기타', 18, 18, '4px']];
const DOCS = {
  ir: [
    ['효능', '감기로 인한 발열 및 동통(통증), 두통, 신경통, 근육통, 월경통, 염좌통(삔 통증)에 사용합니다.'],
    ['사용법', '만 12세 이상 소아 및 성인은 1회 1~2정씩 1일 3~4회(4~6시간마다) 필요시 복용합니다. 1일 최대 4그램(8정)을 초과하지 않습니다.'],
    ['복용 전 주의사항', '매일 세 잔 이상 정기적으로 술을 마시는 사람은 복용 전 의사 또는 약사와 상의하십시오. 간 손상이 유발될 수 있습니다.'],
    ['함께 복용하면 안 되는 약', '아세트아미노펜을 포함하는 다른 제품과 함께 복용하지 마십시오.'],
    ['보관', '습기와 빛을 피해 실온에서 보관하고, 어린이의 손이 닿지 않는 곳에 두십시오.'],
  ],
  er: [
    ['효능', '해열 및 감기에 의한 동통(통증)과 두통, 치통, 근육통, 허리통증, 생리통, 관절통의 완화에 사용합니다.'],
    ['사용법', '만 12세 이상 소아 및 성인은 1회 2정씩 8시간마다 복용합니다. 24시간 동안 6정을 초과하지 않습니다. 서방정이므로 씹거나 부수지 말고 그대로 삼킵니다.'],
    ['복용 전 주의사항', '매일 세 잔 이상 정기적으로 술을 마시는 사람은 복용 전 의사 또는 약사와 상의하십시오. 간 손상이 유발될 수 있습니다.'],
    ['함께 복용하면 안 되는 약', '아세트아미노펜을 포함하는 다른 제품과 함께 복용하지 마십시오.'],
    ['보관', '습기와 빛을 피해 실온에서 보관하고, 어린이의 손이 닿지 않는 곳에 두십시오.'],
  ],
};
const SUMMARY = {
  ir: [['무슨 약인가요', '열을 내리고 통증을 줄이는 약이에요. 감기로 열이 나거나 머리·근육·생리통이 있을 때 쓴다고 적혀 있어요.'], ['어떻게 복용하나요', '원문 기준으로 만 12세 이상은 한 번에 1~2정, 4~6시간 간격, 하루 8정까지예요.'], ['주의할 점', '술을 매일 세 잔 이상 마시는 사람은 먼저 의사·약사와 상의하라고 되어 있어요. 같은 성분(아세트아미노펜)이 든 다른 약과는 함께 쓰지 않도록 안내하고 있어요.']],
  er: [['무슨 약인가요', '열을 내리고 통증을 줄이는 약이에요. 천천히 녹아 오래 가도록 만든 서방정이에요.'], ['어떻게 복용하나요', '원문 기준으로 만 12세 이상은 한 번에 2정, 8시간 간격, 하루 6정까지예요. 씹거나 부수지 않고 그대로 삼키라고 적혀 있어요.'], ['주의할 점', '술을 매일 세 잔 이상 마시는 사람은 먼저 의사·약사와 상의하라고 되어 있어요. 같은 성분(아세트아미노펜)이 든 다른 약과는 함께 쓰지 않도록 안내하고 있어요.']],
};
const QA = [
  [/술|음주|맥주|소주/, 3, '공식 자료에는 매일 세 잔 이상 정기적으로 술을 마시는 사람은 복용 전에 의사나 약사와 상의하도록 적혀 있습니다 [3]. 간 손상이 생길 수 있다는 내용도 함께 있습니다 [3].'],
  [/몇\s?알|몇\s?정|얼마나|하루|간격|용량/, 2, null],
  [/같이|함께|감기약|다른 약/, 4, '공식 자료에는 아세트아미노펜이 들어 있는 다른 제품과 함께 복용하지 않도록 적혀 있습니다 [4].'],
  [/보관|냉장/, 5, '공식 자료에는 습기와 빛을 피해 실온에서, 어린이의 손이 닿지 않는 곳에 보관하도록 적혀 있습니다 [5].'],
];
const SUGGESTIONS = ['하루에 몇 알까지 먹을 수 있나요?', '저는 27살이고 고혈압이 있는데, 술 마신 날 먹어도 되나요?', '아이가 약을 여러 알 삼켰어요'];
const MAX_PHOTO = 5 * 1024 * 1024;

// shortcut: 비용 스위치를 주소(?photo=0&clova=0&review=0)로 받음, 서버가 생기면 서버 환경변수 값을 내려받아 쓸 것
const qs = new URLSearchParams(location.search);
const F = { photoRead: qs.get('photo') !== '0', clovaText: qs.get('clova') !== '0', claudeReview: qs.get('review') !== '0' };
const EXTERNAL = F.clovaText || F.claudeReview;
const STEP_LABELS = ['공식 자료에서 근거 찾기', '답변 작성', '규칙 검사'].concat(F.claudeReview ? ['Claude 검토'] : []);
const WRITER = F.clovaText ? 'CLOVA HCX-007' : 'Qwen3 4B';

const esc = v => String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// 각인 비교 규칙: 대소문자·공백·하이픈 무시, 0/O·1/I/l·5/S·8/B 같은 문자로 봄
const norm = v => (v || '').toUpperCase().replace(/[\s-]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1').replace(/S/g, '5').replace(/B/g, '8');
const hexOf = c => (COLORS.find(v => v[0] === c) || COLORS[0])[1];
const typeLabel = d => d.type === 'otc' ? '일반' : '전문';

const s = {
  screen: 'find', tab: 'manual', imprintMode: 'text', front: '', back: '', colors: [], colorUnknown: false, customOn: false, customColor: '',
  shape: '', capsule: '', photos: { f: null, b: null }, photoError: '', reading: false, filledFromPhoto: false, nameQuery: '',
  drugId: null, from: 'find', dtab: 'summary', question: '', qa: 'idle', step: 0, masked: '', result: null, emergency: false,
};
let timers = [];
const later = (fn, ms) => timers.push(setTimeout(fn, ms));
const clearTimers = () => { timers.forEach(clearTimeout); timers = []; };
const set = patch => { Object.assign(s, patch); render(); };

function pickedColors(c) { return c.colorUnknown ? [] : c.colors.concat(c.customOn && c.customColor.trim() ? [c.customColor.trim()] : []); }
// 각인·색·모양을 모두 정해야 후보 찾기로 넘어감 (캡슐 여부는 선택)
const missing = () => [
  s.imprintMode === 'text' && !s.front.trim() && !s.back.trim() && '각인',
  !s.colorUnknown && !pickedColors(s).length && '색',
  !s.shape && '모양',
].filter(Boolean);
const hasCriteria = () => !missing().length;
const missingText = () => missing().length ? missing().join('·') + '을 알려 주세요' : '';

function scoreAll(c) {
  const color = pickedColors(c);
  const qf = c.imprintMode === 'text' ? norm(c.front) : '', qb = c.imprintMode === 'text' ? norm(c.back) : '';
  const side = (q, v) => !q ? 0 : (v && q === v ? 40 : (v && (v.includes(q) || q.includes(v)) ? 20 : 0));
  return DRUGS.map(d => {
    const f = norm(d.f), b = norm(d.b);
    const imp = Math.max(side(qf, f) + side(qb, b), side(qf, b) + side(qb, f)); // 앞뒤가 바뀐 경우도 비교
    const full = (qf ? 40 : 0) + (qb ? 40 : 0);
    const cOk = color.length > 0 && color.includes(d.color), sOk = c.shape && d.shape === c.shape;
    const kOk = c.capsule && (d.capsule ? 'y' : 'n') === c.capsule;
    const matches = [];
    if (qf || qb) matches.push(imp === full ? ['각인 완전 일치', 'mint'] : imp > 0 ? ['각인 부분 일치', 'yellow'] : ['각인 불일치', 'gray']);
    if (color.length) matches.push(cOk ? ['색 일치', 'mint'] : ['색 불일치', 'gray']);
    if (c.shape) matches.push(sOk ? ['모양 일치', 'mint'] : ['모양 불일치', 'gray']);
    if (c.capsule) matches.push(kOk ? ['캡슐 여부 일치', 'mint'] : ['캡슐 여부 불일치', 'gray']);
    return { d, score: imp + (cOk ? 15 : 0) + (sOk ? 15 : 0) + (kOk ? 10 : 0), matches };
  }).filter(x => x.score > 0).sort((x, y) => y.score - x.score).slice(0, 5);
}

function querySummary() {
  const q = [];
  if (s.imprintMode === 'text') { if (s.front) q.push('앞 ' + s.front); if (s.back) q.push('뒤 ' + s.back); } else q.push(s.imprintMode === 'none' ? '각인 없음' : '마크 있음');
  if (s.colorUnknown) q.push('색 모름'); else if (pickedColors(s).length) q.push(pickedColors(s).join('+'));
  if (s.shape) q.push(s.shape);
  if (s.capsule) q.push(s.capsule === 'y' ? '캡슐형' : '캡슐 아님');
  return q.join(' · ');
}

// ---------- 화면 조각 ----------
const ICON_BACK = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>';
const ICON_CAM = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>';
const ICON_BULB = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1.5v2.5"/><path d="M5.2 4.2l1.6 1.6"/><path d="M18.8 4.2l-1.6 1.6"/><path d="M12 7.5a5 5 0 0 0-3.3 8.7c.6.6.8 1.2.8 2.1h5c0-.9.2-1.5.8-2.1A5 5 0 0 0 12 7.5z"/><path d="M10 21h4"/></svg>';

const SUM_ICON = {
  '무슨 약인가요': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.5 20.5a5 5 0 0 1-7-7l10-10a5 5 0 0 1 7 7z"/><path d="M8.5 8.5l7 7"/></svg>',
  '어떻게 복용하나요': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  '주의할 점': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9.5 17h-19z"/><path d="M12 10v4"/><path d="M12 17.5v.01"/></svg>',
};
const opt = (act, v, on, inner, cls = '') => `<button type="button" class="opt ${cls}" data-act="${act}" data-v="${esc(v)}" aria-pressed="${!!on}">${inner}</button>`;
const pills = (items, val, act, label) => `<div class="pills" role="tablist" aria-label="${label}">${items.map(([v, l]) => `<button type="button" role="tab" aria-selected="${v === val}" data-act="${act}" data-v="${v}">${l}</button>`).join('')}</div>`;
// '머리·근육·생리통'처럼 ·로 이은 말은 줄 중간에서 끊지 않음
const keep = text => text.replace(/\S+·\S+/g, m => `<span class="nw">${m}</span>`);
const badge = (text, cls = '') => `<span class="badge ${cls}">${text}</span>`;
const pulse = text => `<div class="pulse" role="status">${text}</div>`;

function header() {
  const back = s.screen !== 'find';
  const title = { find: '알약 찾기 도우미', results: '후보 비교', detail: '약 정보' }[s.screen];
  const mode = F.photoRead ? '사진 촬영 가능' : '사진 촬영 꺼짐';
  return `<header class="bar">
    ${back ? `<button type="button" class="icon-btn" data-act="back" aria-label="뒤로">${ICON_BACK}</button>` : ''}
    <div class="bar-title${back ? '' : ' pad'}">${title}</div>
    <span class="mode${F.photoRead ? ' on' : ''}" role="img" aria-label="${mode}" title="${mode}"><span class="mode-pill"><span>A</span><span>I</span></span></span>
  </header>`;
}

function findScreen(tab) {
  const tabs = [['manual', '직접 입력']].concat(F.photoRead ? [['photo', '사진']] : [], [['name', '이름 검색']]);
  const body = tab === 'manual' ? manualTab() : tab === 'photo' ? photoTab() : nameTab();
  return `<section class="col" style="gap:12px">
    <div class="col" style="gap:2px"><h1 class="title">어떤 약인지 찾아볼까요</h1><p class="sub">알약에 새겨진 글자와 색, 모양을 알려주세요.</p></div>
    ${pills(tabs, tab, 'tab', '찾는 방법')}
    ${body}
  </section>`;
}

function manualTab() {
  return `<div class="col" style="gap:8px">
    ${s.filledFromPhoto ? '<div class="note">사진에서 읽은 값입니다. 알약과 비교해 틀린 곳을 고쳐 주세요.</div>' : ''}
    <div class="row-between"><h2 class="sec-h">각인</h2><button type="button" class="link-btn" data-act="fillSample">예시 값 채우기</button></div>
    <div class="box">
      <div class="row" style="gap:8px">${[['text', '글자 있음'], ['none', '각인 없음'], ['mark', '마크(로고)']].map(([v, l]) => opt('imprint', v, s.imprintMode === v, l, 'grow')).join('')}</div>
      ${s.imprintMode === 'text' ? `<div class="imprint-grid">
        <label class="lbl" for="f-front">앞</label><input id="f-front" class="input s14" data-field="front" placeholder="예: TYLENOL" value="${esc(s.front)}" autocomplete="off" spellcheck="false">
        <label class="lbl" for="f-back">뒤</label><input id="f-back" class="input s14" data-field="back" placeholder="예: 500" value="${esc(s.back)}" autocomplete="off" spellcheck="false">
        <div class="hint">한쪽에만 있으면 다른 칸은 비워 두세요. 대소문자·띄어쓰기는 무시합니다.</div>
      </div>` : ''}
    </div>
    <div class="divider"></div>
    <h2 class="sec-h">색</h2>
    <div class="box">
      <div class="grid4" style="gap:6px">
        ${COLORS.map(([l, hex]) => opt('color', l, s.colors.includes(l), `<span class="sw" style="background:${hex}"></span>${l}`, 'color')).join('')}
        ${opt('custom', '', s.customOn, '직접 색 입력하기', 'dark span2')}
        ${opt('unknown', '', s.colorUnknown, '알 수 없음', 'grey span2')}
      </div>
      ${s.customOn ? `<input class="input s13" aria-label="색 직접 입력" data-field="customColor" placeholder="예: 연두, 하양+파랑" value="${esc(s.customColor)}" autocomplete="off">` : ''}
    </div>
    <div class="divider"></div>
    <h2 class="sec-h">모양</h2>
    <div class="box">
      <div class="grid4" style="gap:8px">${SHAPES.map(([l, w, h, r]) => opt('shape', l, s.shape === l, `<span class="shape-ic" style="width:${w}px;height:${h}px;border-radius:${r}"></span>${l}`, 'shape')).join('')}</div>
      <div class="row" style="gap:8px"><span class="lbl grow">캡슐형인가요?</span>${[['y', '예'], ['n', '아니요']].map(([v, l]) => opt('capsule', v, s.capsule === v, l, 'cap')).join('')}</div>
    </div>
  </div>`;
}

function slot(k, label) {
  const url = s.photos[k];
  if (!url) return `<label class="slot"><input type="file" accept="image/*" class="sr-only" data-photo="${k}" aria-label="${label} 사진 올리기">${ICON_CAM}<span style="font-weight:600;color:var(--cal-ink)">${label} 사진</span><span style="font-size:12px">눌러서 올리기</span></label>`;
  return `<div class="slot added"><img src="${url}" alt="${label}면 사진 미리보기"><span class="crop" aria-hidden="true"></span><span class="slot-tag">자르기 영역</span><button type="button" class="slot-clear" data-act="clearPhoto" data-v="${k}" aria-label="${label} 사진 지우기">지우기</button></div>`;
}

function photoTab() {
  return `<div class="col" style="gap:16px">
    <div class="grid2">${slot('f', '앞')}${slot('b', '뒤')}</div>
    ${s.photoError ? `<div class="note" role="alert">${esc(s.photoError)}</div>` : ''}
    ${s.reading ? pulse('각인·색·모양을 읽는 중입니다') : ''}
    <button type="button" class="btn lg full" data-act="sendPhoto" ${s.reading || !(s.photos.f || s.photos.b) ? 'disabled' : ''}>사진으로 각인 읽기</button>
    <div class="muted12" style="text-align:center;margin-top:-8px">위치 정보를 지운 뒤 CLOVA로 보내 읽고, 사진은 저장하지 않습니다.</div>
    <div class="tip">${ICON_BULB}<strong style="font-size:14px">촬영 팁</strong><span class="tip-sep"></span><strong>알약만 보이게 찍어 주세요</strong><span style="font-size:11px;color:var(--cal-muted)">(손·얼굴·처방 봉투 X)</span></div>
  </div>`;
}

function hitsHtml() {
  const nq = s.nameQuery.trim();
  const hits = DRUGS.filter(d => !nq || d.name.includes(nq));
  if (!hits.length) return '<div class="empty">일치하는 약을 찾지 못했습니다.</div>';
  return hits.map(d => `<button type="button" class="hit" data-act="open" data-v="${d.id}" data-from="find">
    <span class="col grow" style="gap:2px"><span class="hit-n">${d.name}</span><span class="hit-c">${d.co}</span></span>${badge(typeLabel(d), d.type === 'otc' ? 'b-otc' : 'b-rx')}
  </button>`).join('');
}

function nameTab() {
  return `<div class="col" style="gap:12px">
    <input class="input" type="search" aria-label="약 이름" placeholder="약 이름을 입력하세요" data-field="nameQuery" value="${esc(s.nameQuery)}" autocomplete="off">
    <div class="col" id="hits" aria-live="polite">${hitsHtml()}</div>
  </div>`;
}

const SOURCE_PILL = `<div class="src">
  <div class="row-between" style="align-items:center"><span class="src-h">출처</span>${badge('마지막 갱신 성공', 'b-success dot')}</div>
  <div>식품의약품안전처 · 의약품 낱알식별 정보</div>
  <div>자료 기준 시점: 2026-11-09 03:00</div>
  <div class="soft">알약 그림은 값으로 그린 도식이며 실제 사진이 아닙니다.</div>
</div>`;

function candidate({ d, matches }) {
  const sh = SHAPES.find(v => v[0] === d.shape) || SHAPES[3];
  return `<button type="button" class="card cand" data-act="open" data-v="${d.id}" data-from="results">
    <span class="row" style="gap:14px">
      <span class="pill-pic" aria-hidden="true"><span style="width:${sh[1] * 1.9}px;height:${sh[2] * 1.9}px;border-radius:${sh[3]};background:${hexOf(d.color)}">${d.f}</span></span>
      <span class="col grow" style="gap:3px;min-width:0"><span class="cand-n">${d.name}</span><span class="hit-c">${d.co}</span><span class="cand-o">${d.f} / ${d.b || '없음'} · ${d.color} · ${d.shape}</span></span>
      ${badge(typeLabel(d), d.type === 'otc' ? 'b-otc' : '')}
    </span>
    <span class="row wrap" style="gap:6px">${matches.map(([l, c]) => badge(l, 'b-' + c)).join('')}</span>
  </button>`;
}

function resultsScreen() {
  const cands = scoreAll(s);
  return `<section class="col" style="gap:16px">
    <div class="col" style="gap:6px"><h1 class="title lg">${cands.length ? '후보 ' + cands.length + '개' : '후보 없음'}</h1><p class="sub" style="font-size:14px">검색한 약의 후보입니다.<br>확정된 결과가 아니니 복용 전 약사에게 확인해 주세요.</p></div>
    <div class="query">${esc(querySummary())}</div>
    ${cands.map(candidate).join('')}
    ${cands.length ? '' : `<div class="panel col" style="padding:24px;gap:14px;align-items:flex-start"><div class="strong15">일치하는 약을 찾지 못했습니다</div><button type="button" class="btn sec" data-act="toNameTab">이름으로 찾기</button></div>`}
    ${SOURCE_PILL}
  </section>`;
}

function summaryTab(d) {
  return `<div class="col" style="gap:12px">
    <div class="row">${badge('AI 작성 · ' + (F.clovaText ? 'CLOVA HCX-DASH-002' : 'Qwen3 4B'), 'b-pink')}</div>
    ${(SUMMARY[d.doc] || SUMMARY.ir).map(([t, b]) => `<div class="panel col" style="gap:6px"><div class="sum-t row" style="gap:6px">${SUM_ICON[t] || ''}${t}</div><div class="sum-b">${keep(b)}</div></div>`).join('')}
  </div>`;
}

function originalTab(doc) {
  return `<div class="col">
    ${doc.map(([t, b], i) => `<div class="sec-row"><span class="num">${i + 1}</span><div class="col" style="gap:4px"><div style="font-size:14px;font-weight:600">${t}</div><div class="body14" style="line-height:1.6">${keep(b)}</div></div></div>`).join('')}
    <div class="src" style="margin-top:14px;display:block"><span class="src-h">출처</span><br>식품의약품안전처 · 의약품개요정보(e약은요)<br>수정일 2026-10-21 · 받은 시각 2026-11-09 03:00</div>
  </div>`;
}

function askTab() {
  let h = '';
  if (s.qa === 'idle') {
    h += `<div class="col" style="gap:8px">${SUGGESTIONS.map(t => `<button type="button" class="suggest" data-act="suggest" data-v="${esc(t)}">${t}</button>`).join('')}</div>
      <div class="col" style="gap:6px">
        <textarea class="qbox" data-field="question" maxlength="300" aria-label="질문" placeholder="이 약에 대해 궁금한 점을 적어 주세요">${esc(s.question)}</textarea>
        <div class="muted12" style="text-align:right"><span><span id="q-count">${s.question.length}</span>/300</span></div>
      </div>
      <button type="button" class="btn lg full" id="ask-btn" data-act="ask" ${s.question.trim() ? '' : 'disabled'}>질문하기</button>`;
  } else {
    h += `<div class="bubble">${esc(s.question)}</div>`;
  }
  // 응급 안내는 항상 답변보다 먼저 보임
  if (s.emergency && s.qa !== 'idle') h += `<div class="sos" role="alert"><div class="strong15">응급 상황이면 즉시 119에 연락하세요</div><div style="font-size:13px;line-height:1.5;color:var(--cal-body)">약을 많이 삼켰거나 상태가 나쁘면 답변을 기다리지 마세요.</div><a class="btn full" href="tel:119">119 전화하기</a></div>`;
  if (s.qa === 'masking') h += pulse('개인정보를 가리는 중입니다');
  if (s.qa === 'confirm') {
    const targets = [F.clovaText && 'CLOVA', F.claudeReview && 'Claude'].filter(Boolean).join('·');
    h += `<div class="card col" style="gap:12px">
      <div class="strong15">보내기 전에 확인해 주세요</div>
      <div style="font-size:13px;line-height:1.5;color:var(--cal-muted)">아래 문장으로 바뀌어 ${targets}(으)로 전송됩니다.</div>
      <div class="masked">${esc(s.masked)}</div>
      <div class="grid2" style="gap:8px"><button type="button" class="btn sec full" data-act="resetQa">취소</button><button type="button" class="btn full" data-act="confirmSend">이대로 보내기</button></div>
    </div>`;
  }
  if (s.qa === 'running') {
    h += `<div class="panel col" style="gap:10px" role="status">${STEP_LABELS.map((l, i) => {
      const st = i < s.step ? 'done' : i === s.step ? 'now' : '';
      return `<div class="step ${st}"><span class="step-dot"></span><span class="grow">${l}</span><span style="font-size:12px">${st === 'done' ? '완료' : st === 'now' ? '진행 중' : '대기'}</span></div>`;
    }).join('')}</div>`;
  }
  if (s.qa === 'done') {
    if (s.result) {
      h += `<div class="card col" style="gap:12px">
        <div class="row wrap" style="gap:6px">${badge('AI 작성 · ' + WRITER, 'b-pink')}${F.claudeReview ? badge('Claude 검토 완료', 'b-success') : badge('검토하지 않은 답변', 'b-warning')}</div>
        <div class="answer">${esc(s.result.text)}</div>
        <div class="split" style="gap:8px"><div class="sum-t">근거 문단</div>
          ${s.result.ev.map(e => `<div class="ev"><span class="ev-n">[${e.n}]</span><span><strong style="color:var(--cal-ink)">${e.title}</strong> — ${keep(e.body)}</span></div>`).join('')}
        </div>
        <div class="split muted12" style="gap:4px;line-height:1.5">
          <div>규칙 검사 · 단정 표현 0건, 근거 번호 없는 문장 0건</div>
          <div>${F.claudeReview ? 'Claude 검토 · 근거 밖 내용과 단정적 복용 지시를 찾지 못했습니다' : 'Claude 검토 꺼짐 · 코드 규칙 검사만 거친 답변입니다'}</div>
        </div>
      </div>`;
    } else {
      h += `<div class="panel body14"><strong style="color:var(--cal-ink)">공식 자료에 해당 내용이 없습니다.</strong><br>답변을 만들지 않았습니다. 약사에게 확인하세요.</div>`;
    }
    h += `<button type="button" class="btn sec full" data-act="resetQa">다른 질문하기</button>`;
  }
  return `<div class="col" style="gap:14px">${h}</div>`;
}

function detailScreen() {
  const d = DRUGS.find(x => x.id === s.drugId) || DRUGS[0];
  const otc = d.type === 'otc';
  const body = !otc
    ? `<div class="panel col" style="padding:20px;gap:8px"><div class="strong15">처방약은 정보와 질문을 제공하지 않습니다</div><div class="body14">처방한 의사나 약사에게 확인해 주세요. 허가 정보는 의약품안전나라에서 볼 수 있습니다.</div></div>`
    : pills([['summary', '요약'], ['original', '원문'], ['ask', '질문하기']], s.dtab, 'dtab', '약 정보 보기')
      + (s.dtab === 'summary' ? summaryTab(d) : s.dtab === 'original' ? originalTab(DOCS[d.doc] || DOCS.ir) : askTab())
      + '<div class="fine">이 정보는 법적 효력이 없으며 의약품에 관한 모든 내용을 담고 있지 않습니다.<br>복용 전 약사에게 확인하세요.</div>';
  return `<section class="col" style="gap:18px">
    <div class="col" style="gap:8px">
      <div class="row">${badge(otc ? '일반의약품' : '전문의약품', 'kind dot ' + (otc ? 'dot-otc' : 'dot-rx'))}</div>
      <h1 class="title" style="line-height:1.3;letter-spacing:-.3px">${d.name}</h1>
      <div class="row-between muted13"><span>${d.co}</span><a href="https://nedrug.mfds.go.kr" target="_blank" rel="noopener">의약품안전나라에서 보기</a></div>
    </div>
    ${body}
  </section>`;
}

function render() {
  const tab = !F.photoRead && s.tab === 'photo' ? 'manual' : s.tab;
  const screen = s.screen === 'find' ? findScreen(tab) : s.screen === 'results' ? resultsScreen() : detailScreen();
  const cta = s.screen === 'find' && tab === 'manual'
    ? `<div class="cta"><div class="cta-hint" id="cta-hint" aria-live="polite">${missingText()}</div><button type="button" class="btn lg full" id="cta-btn" data-act="search" ${hasCriteria() ? '' : 'disabled'}>후보 찾기</button></div>`
    : s.screen !== 'find' ? '<div class="cta"><button type="button" class="btn lg full mint" data-act="again">다른 알약 찾기</button></div>' : '';
  document.getElementById('app').innerHTML = header() + `<main class="main">${screen}</main>` + cta;
}

// 입력칸은 다시 그리지 않고 딸린 부분만 고침: 다시 그리면 한글 조합 입력이 끊김
function refresh() {
  const $ = id => document.getElementById(id);
  if ($('cta-btn')) $('cta-btn').disabled = !hasCriteria();
  if ($('cta-hint')) $('cta-hint').textContent = missingText();
  if ($('q-count')) $('q-count').textContent = s.question.length;
  if ($('ask-btn')) $('ask-btn').disabled = !s.question.trim();
  if ($('hits')) $('hits').innerHTML = hitsHtml();
}

// ---------- 동작 ----------
function openDrug(id, from) {
  clearTimers();
  set({ drugId: id, screen: 'detail', from, dtab: 'summary', qa: 'idle', question: '', emergency: false, result: null });
  scrollTo(0, 0);
}

function runSteps() {
  const n = STEP_LABELS.length;
  set({ qa: 'running', step: 0 });
  for (let i = 1; i <= n; i++) later(() => set(i === n ? { qa: 'done' } : { step: i }), i * 750);
}

function startAsk() {
  const q = s.question.trim(); if (!q) return;
  const d = DRUGS.find(x => x.id === s.drugId) || DRUGS[0];
  const doc = DOCS[d.doc] || DOCS.ir;
  const emergency = /삼켰|과다|많이 먹|여러 알|한꺼번에/.test(q);
  const hit = QA.find(r => r[0].test(q));
  let result = null;
  if (hit) {
    const sec = doc[hit[1] - 1];
    result = { text: (hit[2] || '공식 자료에는 다음과 같이 적혀 있습니다 [2]. ' + sec[1]) + ' 본인 상황에 맞는지는 약사에게 확인해 주세요.', ev: [{ n: hit[1], title: sec[0], body: sec[1] }] };
  }
  const masked = q.replace(/\d+\s?(살|세)|임신\s?\d*\s?(주|개월)?|고혈압|당뇨|간염|천식|우울증/g, '[가림]');
  Object.assign(s, { emergency, result, masked });
  if (EXTERNAL) { set({ qa: 'masking' }); later(() => set({ qa: 'confirm' }), 900); } // 외부로 나갈 때만 가리고 확인받음
  else runSteps();
}

const ACT = {
  back: () => { clearTimers(); set({ screen: s.screen === 'detail' ? s.from : 'find' }); },
  tab: v => set({ tab: v }),
  imprint: v => set({ imprintMode: v }),
  fillSample: () => set({ imprintMode: 'text', front: 'tylenol', back: '5OO', colors: ['하양'], colorUnknown: false, shape: '장방형' }),
  color: v => set({ colorUnknown: false, colors: s.colors.includes(v) ? s.colors.filter(x => x !== v) : s.colors.concat(v) }),
  custom: () => set({ customOn: !s.customOn, colorUnknown: false }),
  unknown: () => set(s.colorUnknown ? { colorUnknown: false } : { colorUnknown: true, colors: [], customOn: false }),
  shape: v => set({ shape: s.shape === v ? '' : v }),
  capsule: v => set({ capsule: s.capsule === v ? '' : v }),
  clearPhoto: k => { URL.revokeObjectURL(s.photos[k]); set({ photos: { ...s.photos, [k]: null } }); },
  sendPhoto: () => {
    set({ reading: true, photoError: '' });
    later(() => {
      Object.values(s.photos).forEach(u => u && URL.revokeObjectURL(u));
      set({ reading: false, tab: 'manual', imprintMode: 'text', front: 'TYLENOL', back: s.photos.b ? '500' : '', colors: ['하양'], colorUnknown: false, shape: '장방형', filledFromPhoto: true, photos: { f: null, b: null } });
    }, 1500);
  },
  again: () => { clearTimers(); set({ screen: 'find', imprintMode: 'text', front: '', back: '', colors: [], colorUnknown: false, customOn: false, customColor: '', shape: '', capsule: '', filledFromPhoto: false, nameQuery: '' }); scrollTo(0, 0); },
  search: () => { set({ screen: 'results' }); scrollTo(0, 0); },
  open: (v, el) => openDrug(Number(v), el.dataset.from),
  toNameTab: () => set({ screen: 'find', tab: 'name' }),
  dtab: v => set({ dtab: v }),
  suggest: v => set({ question: v }),
  ask: startAsk,
  confirmSend: runSteps,
  resetQa: () => { clearTimers(); set({ qa: 'idle', emergency: false, result: null }); },
};

document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (el && !el.disabled) ACT[el.dataset.act](el.dataset.v, el);
});
document.addEventListener('input', e => {
  const f = e.target.dataset.field;
  if (!f) return;
  s[f] = f === 'question' ? e.target.value.slice(0, 300) : e.target.value;
  refresh();
});
document.addEventListener('change', e => {
  const k = e.target.dataset.photo, file = e.target.files && e.target.files[0];
  if (!k || !file) return;
  if (!file.type.startsWith('image/')) return set({ photoError: '사진 파일만 올릴 수 있습니다.' });
  if (file.size > MAX_PHOTO) return set({ photoError: '사진은 한 장에 5MB까지 올릴 수 있습니다.' });
  set({ photoError: '', photos: { ...s.photos, [k]: URL.createObjectURL(file) } });
});

// 자가 검사: 각인을 소문자·공백·0/O를 바꿔 넣어도 같은 후보(완료 기준 19)
console.assert(norm('tylenol') === norm('TYLEN0L') && norm('5 O-O') === norm('500') && norm('l') === norm('I'), 'norm 규칙');
console.assert(scoreAll({ ...s, front: 'tylenol', back: '5OO' })[0].d.id === 1, '앞뒤 각인 완전 일치가 1위');
console.assert(scoreAll({ ...s, front: '500', back: 'TYLENOL' })[0].d.id === 1, '앞뒤가 바뀌어도 같은 후보');

render();
