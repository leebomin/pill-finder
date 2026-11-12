'use strict';
// 후보 찾기·이름 검색은 식약처 낱알식별 자료, 화면 3(원문·요약·질문)은 e약은요 자료로 동작. 사진·CLOVA·Claude 단계는 서버 스위치(/api/config)를 따름

const known = new Map(); // 서버에서 받은 약(식별 번호 → 약), 화면 3에서 다시 찾을 때 씀
const COLORS = [['하양', '#ffffff'], ['노랑', '#fde68a'], ['주황', '#fdba74'], ['분홍', '#f9a8d4'], ['빨강', '#f87171'], ['초록', '#86efac'], ['파랑', '#93c5fd'], ['갈색', '#b08968']];
const SHAPES = [['원형', 18, 18, '50%'], ['타원형', 26, 16, '50%'], ['장방형', 28, 13, '9999px'], ['기타', 18, 18, '4px']];
const SUGGESTIONS = ['하루에 몇 알까지 먹을 수 있나요?', '저는 27살이고 고혈압이 있는데, 술 마신 날 먹어도 되나요?', '아이가 약을 여러 알 삼켰어요'];
const MAX_PHOTO = 5 * 1024 * 1024;

// 비용 스위치: 시작할 때 서버 환경변수 값(/api/config)으로 채움. 못 받으면 모두 끔(무료 모드)
const F = { photoRead: false, clovaText: false, claudeReview: false };
const external = () => F.clovaText || F.claudeReview;

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// 자료의 색은 '노랑, 투명'처럼 여러 개일 수 있어 첫 색으로 그림
const hexOf = c => (COLORS.find(v => v[0] === (c || '').split(', ')[0]) || COLORS[0])[1];
const api = async (path, params, post) => {
  const r = await fetch(path + (params ? '?' + new URLSearchParams(params) : ''),
    post ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(post) } : undefined);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '서버에 연결할 수 없습니다. 잠시 뒤 다시 시도해 주세요.');
  return body;
};
const remember = list => list.forEach(d => known.set(d.id, d));
const typeLabel = d => d.type === 'otc' ? '일반' : '전문';

const s = {
  screen: 'find', tab: 'manual', imprintMode: 'text', front: '', back: '', colors: [], colorUnknown: false, customOn: false, customColor: '',
  shape: '', capsule: '', photos: { f: null, b: null }, photoError: '', reading: false, filledFromPhoto: false, nameQuery: '',
  drugId: null, from: 'find', dtab: 'summary', question: '', qa: 'idle', masked: '', result: null, emergency: false,
  searching: false, searchError: '', cands: [], source: {}, hits: [], hitsError: '',
  doc: null, docError: '', summary: null, summaryState: 'idle', summaryError: '', steps: {},
};
const askSteps = () => [['search', '공식 자료에서 근거 찾기'], ['write', '답변 작성'], ['check', '규칙 검사']].concat(F.claudeReview ? [['review', 'Claude 검토']] : []);
const STEP_TEXT = { start: '진행 중', done: '완료', skip: '건너뜀', fail: '실패' };
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

// 각인 비교·점수는 서버(app.py search)가 함
async function runSearch() {
  set({ searching: true, searchError: '' });
  try {
    const r = await api('/api/search', { mode: s.imprintMode, front: s.front, back: s.back, colors: pickedColors(s).join('+'), shape: s.shape, capsule: s.capsule });
    remember(r.cands.map(c => c.d));
    set({ searching: false, screen: 'results', cands: r.cands, source: r.source });
    scrollTo(0, 0);
  } catch (e) { set({ searching: false, searchError: e.message }); }
}

let nameReq = 0; // 늦게 온 이전 검색 결과가 새 결과를 덮지 않게 함
async function searchNames() {
  const id = ++nameReq, q = s.nameQuery.trim();
  if (!q) { s.hits = []; s.hitsError = ''; return refresh(); }
  try {
    const r = await api('/api/names', { q });
    if (id !== nameReq) return;
    remember(r.hits); s.hits = r.hits; s.hitsError = '';
  } catch (e) { if (id === nameReq) s.hitsError = e.message; }
  refresh();
}
let nameTimer;

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
    ${F.clovaCapped ? '<div class="note">이번 달 CLOVA 사용 한도에 도달해 사진 읽기 없이 직접 입력으로 찾고, 요약·답변은 Local LLM이 작성합니다.</div>' : ''}
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
  const url = s.photos[k] && s.photos[k].url;
  if (!url) return `<label class="slot"><input type="file" accept="image/*" class="sr-only" data-photo="${k}" aria-label="${label} 사진 올리기">${ICON_CAM}<span style="font-weight:600;color:var(--cal-ink)">${label} 사진</span><span style="font-size:12px">눌러서 올리기</span></label>`;
  return `<div class="slot added" data-slot="${k}"><img src="${url}" alt="${label}면 사진 미리보기"><span class="crop" data-crop="${k}" tabindex="0" role="group"
    aria-label="${label} 사진 자르기 영역. 끌어서 옮기고 오른쪽 아래 점으로 크기를 바꿉니다. 화살표 키로 이동, Shift와 화살표 키로 크기 조절" style="${cropStyle(s.photos[k].crop)}"><span class="crop-handle" data-handle aria-hidden="true"></span></span><span class="slot-tag">자르기 영역</span><button type="button" class="slot-clear" data-act="clearPhoto" data-v="${k}" aria-label="${label} 사진 지우기">지우기</button></div>`;
}

function photoTab() {
  return `<div class="col" style="gap:16px">
    <div class="grid2">${slot('f', '앞')}${slot('b', '뒤')}</div>
    ${s.photos.f || s.photos.b ? '<div class="muted12" style="margin-top:-8px">점선 상자를 끌어 알약만 들어가게 맞춰 주세요. 상자 안만 보냅니다.</div>' : ''}
    ${s.photoError ? `<div class="note" role="alert">${esc(s.photoError)}</div>` : ''}
    ${s.reading ? pulse('각인·색·모양을 읽는 중입니다') : ''}
    <button type="button" class="btn lg full" data-act="sendPhoto" ${s.reading || !(s.photos.f || s.photos.b) ? 'disabled' : ''}>사진으로 각인 읽기</button>
    <div class="muted12" style="text-align:center;margin-top:-8px">위치 정보를 지운 뒤 CLOVA로 보내 읽고, 사진은 저장하지 않습니다.</div>
    <div class="tip">${ICON_BULB}<strong style="font-size:14px">촬영 팁</strong><span class="tip-sep"></span><strong>알약만 보이게 찍어 주세요</strong><span style="font-size:11px;color:var(--cal-muted)">(손·얼굴·처방 봉투 X)</span></div>
  </div>`;
}

function hitsHtml() {
  if (s.hitsError) return `<div class="empty" role="alert">${esc(s.hitsError)}</div>`;
  if (!s.nameQuery.trim()) return '';
  if (!s.hits.length) return '<div class="empty">일치하는 약을 찾지 못했습니다.</div>';
  return s.hits.map(d => `<button type="button" class="hit" data-act="open" data-v="${d.id}" data-from="find">
    <span class="col grow" style="gap:2px"><span class="hit-n">${esc(d.name)}</span><span class="hit-c">${esc(d.co)}</span></span>${badge(typeLabel(d), d.type === 'otc' ? 'b-otc' : 'b-rx')}
  </button>`).join('');
}

function nameTab() {
  return `<div class="col" style="gap:12px">
    <input class="input" type="search" aria-label="약 이름" placeholder="약 이름을 입력하세요" data-field="nameQuery" value="${esc(s.nameQuery)}" autocomplete="off">
    <div class="col" id="hits" aria-live="polite">${hitsHtml()}</div>
  </div>`;
}

function sourceBox() {
  const m = s.source;
  return `<div class="src">
  <div class="row-between" style="align-items:center"><span class="src-h">출처</span>${m.last_ok === false ? badge('마지막 갱신 실패', 'b-warning dot') : badge('마지막 갱신 성공', 'b-success dot')}</div>
  <div>식품의약품안전처 · 의약품 낱알식별 정보</div>
  <div>자료 기준 시점: ${esc(m.fetched_at || '-')}</div>
  ${m.last_ok === false ? `<div>마지막 갱신 시도: ${esc(m.last_attempt)}</div>` : ''}
  <div class="soft">알약 그림은 값으로 그린 도식이며 실제 사진이 아닙니다.</div>
</div>`;
}

function candidate({ d, matches }) {
  const sh = SHAPES.find(v => v[0] === d.shape) || SHAPES[3];
  const color = [d.color, d.color2].filter(Boolean).join(' / ');
  return `<button type="button" class="card cand" data-act="open" data-v="${d.id}" data-from="results">
    <span class="row" style="gap:14px">
      <span class="pill-pic" aria-hidden="true"><span style="width:${sh[1] * 1.9}px;height:${sh[2] * 1.9}px;border-radius:${sh[3]};background:${hexOf(d.color)}">${esc(d.f.replace(/마크|분할선/g, ''))}</span></span>
      <span class="col grow" style="gap:3px;min-width:0"><span class="cand-n">${esc(d.name)}</span><span class="hit-c">${esc(d.co)}</span><span class="cand-o">${esc(d.f || '없음')} / ${esc(d.b || '없음')} · ${esc(color)} · ${esc(d.shape)}</span></span>
      ${badge(typeLabel(d), d.type === 'otc' ? 'b-otc' : '')}
    </span>
    <span class="row wrap" style="gap:6px">${matches.map(([l, c]) => badge(l, 'b-' + c)).join('')}</span>
  </button>`;
}

function resultsScreen() {
  const cands = s.cands;
  return `<section class="col" style="gap:16px">
    <div class="col" style="gap:6px"><h1 class="title lg">${cands.length ? '후보 ' + cands.length + '개' : '후보 없음'}</h1><p class="sub" style="font-size:14px">검색한 약의 후보입니다.<br>확정된 결과가 아니니 복용 전 약사에게 확인해 주세요.</p></div>
    <div class="query">${esc(querySummary())}</div>
    ${cands.map(candidate).join('')}
    ${cands.length ? '' : `<div class="panel col" style="padding:24px;gap:14px;align-items:flex-start"><div class="strong15">일치하는 약을 찾지 못했습니다</div><button type="button" class="btn sec" data-act="toNameTab">이름으로 찾기</button></div>`}
    ${sourceBox()}
  </section>`;
}

function summaryTab() {
  if (s.summaryState === 'loading') return pulse('쉬운 말 요약을 만드는 중입니다. 처음 여는 약은 1분쯤 걸릴 수 있습니다.');
  if (s.summaryState === 'error') return `<div class="panel col" style="gap:12px;align-items:flex-start"><div class="body14">${esc(s.summaryError)}</div><button type="button" class="btn sec" data-act="dtab" data-v="original">원문 보기</button></div>`;
  if (!s.summary) return '';
  return `<div class="col" style="gap:12px">
    <div class="row">${badge('AI 작성 · ' + esc(s.summary.model), 'b-pink')}</div>
    ${s.summary.bad_numbers && s.summary.bad_numbers.length ? `<div class="note" role="alert">요약에 원문에 없는 숫자(${esc(s.summary.bad_numbers.join(', '))})가 있습니다. 복용량·횟수는 원문 탭에서 확인해 주세요.</div>` : ''}
    ${s.summary.parts.map(([t, b]) => `<div class="panel col" style="gap:6px"><div class="sum-t row" style="gap:6px">${SUM_ICON[t] || ''}${esc(t)}</div><div class="sum-b">${keep(esc(b))}</div></div>`).join('')}
  </div>`;
}

function originalTab() {
  if (s.docError) return `<div class="panel body14">${esc(s.docError)}</div>`;
  if (!s.doc) return pulse('공식 원문을 불러오는 중입니다');
  const src = s.doc.source || {};
  return `<div class="col">
    ${s.doc.sections.map(([t, b], i) => `<div class="sec-row"><span class="num">${i + 1}</span><div class="col" style="gap:4px"><div style="font-size:14px;font-weight:600">${esc(t)}</div><div class="body14" style="line-height:1.6">${keep(esc(b))}</div></div></div>`).join('')}
    <div class="src" style="margin-top:14px;display:block"><span class="src-h">출처</span><br>식품의약품안전처 · 의약품개요정보(e약은요)<br>수정일 ${esc(s.doc.updateDe || '-')} · 받은 시각 ${esc(src.fetched_at || '-')}</div>
  </div>`;
}

const reviewBadge = r => r.reviewed ? (r.review.ok ? badge('Claude 검토 완료', 'b-success') : badge('Claude 검토 주의', 'b-warning'))
  : r.review_error ? badge(esc(r.review_error), 'b-warning') : badge('검토하지 않은 답변', 'b-warning');
const evidenceHtml = ev => `<div class="split" style="gap:8px"><div class="sum-t">근거 문단</div>
  ${ev.map((e, i) => `<div class="ev"><span class="ev-n">[${i + 1}]</span><span><strong style="color:var(--cal-ink)">${esc(e.title)}</strong> — ${keep(esc(e.body))}</span></div>`).join('')}
</div>`;

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
  // 서버가 SSE로 알려 주는 단계(검색 → 답변 → 검사 → 검토)를 그대로 표시
  if (s.qa === 'running') {
    h += `<div class="panel col" style="gap:10px" role="status">${askSteps().map(([k, l]) => {
      const st = s.steps[k], cls = st === 'done' || st === 'skip' ? 'done' : st === 'start' ? 'now' : '';
      return `<div class="step ${cls}"><span class="step-dot"></span><span class="grow">${l}</span><span style="font-size:12px">${STEP_TEXT[st] || '대기'}</span></div>`;
    }).join('')}</div>`;
  }
  if (s.qa === 'done') {
    const r = s.result || {};
    if (r.answer) {
      const c = r.checks, flagged = c.assertive + c.uncited + c.bad_refs > 0;
      h += `<div class="card col" style="gap:12px">
        <div class="row wrap" style="gap:6px">${badge('AI 작성 · ' + esc(r.model), 'b-pink')}${reviewBadge(r)}</div>
        <div class="answer">${esc(r.answer)}</div>
        ${r.reviewed && r.review.issues.length ? `<div class="note" role="alert"><strong>Claude 검토에서 확인이 필요한 부분</strong><br>${r.review.issues.map(esc).join('<br>')}</div>` : ''}
        <div class="muted12">본인 상황에 맞는지는 약사에게 확인해 주세요.</div>
        ${evidenceHtml(r.evidence)}
        <div class="split muted12" style="gap:4px;line-height:1.5">
          <div${flagged ? ' style="color:var(--cal-ink);font-weight:600"' : ''}>규칙 검사 · 단정 표현 ${c.assertive}건, 근거 번호 없는 문장 ${c.uncited}건${c.bad_refs ? `, 없는 근거 번호 ${c.bad_refs}건` : ''}</div>
          <div>${r.reviewed ? (r.review.ok ? 'Claude 검토 · 근거 밖 내용과 단정적 복용 지시를 찾지 못했습니다' : 'Claude 검토 · 위 부분을 공식 원문과 비교해 주세요')
            : r.review_error ? 'Claude 검토 실패 · 코드 규칙 검사만 거친 답변입니다' : 'Claude 검토 꺼짐 · 코드 규칙 검사만 거친 답변입니다'}</div>
        </div>
      </div>`;
    } else if (r.error) {
      h += `<div class="panel col" style="gap:12px"><div class="body14"><strong style="color:var(--cal-ink)">${esc(r.error)}</strong></div>${r.evidence && r.evidence.length ? evidenceHtml(r.evidence) : ''}</div>`;
    } else {
      h += `<div class="panel body14"><strong style="color:var(--cal-ink)">공식 자료에 해당 내용이 없습니다.</strong><br>답변을 만들지 않았습니다. 약사에게 확인하세요.</div>`;
    }
    h += `<button type="button" class="btn sec full" data-act="resetQa">다른 질문하기</button>`;
  }
  return `<div class="col" style="gap:14px">${h}</div>`;
}

function detailScreen() {
  const d = known.get(s.drugId);
  if (!d) return '<section class="col"><div class="empty">약 정보를 찾을 수 없습니다. 다시 검색해 주세요.</div></section>';
  const otc = d.type === 'otc';
  const body = !otc
    ? `<div class="panel col" style="padding:20px;gap:8px"><div class="strong15">처방약은 정보와 질문을 제공하지 않습니다</div><div class="body14">처방한 의사나 약사에게 확인해 주세요. 허가 정보는 의약품안전나라에서 볼 수 있습니다.</div></div>`
    : !d.doc
    ? `<div class="panel col" style="padding:20px;gap:8px"><div class="strong15">공식 정보(e약은요)에 없는 약입니다</div><div class="body14">허가 정보는 의약품안전나라에서 볼 수 있습니다. 복용 전 약사에게 확인하세요.</div></div>`
    : pills([['summary', '요약'], ['original', '원문'], ['ask', '질문하기']], s.dtab, 'dtab', '약 정보 보기')
      + (s.dtab === 'summary' ? summaryTab() : s.dtab === 'original' ? originalTab() : askTab())
      + '<div class="fine">이 정보는 법적 효력이 없으며 의약품에 관한 모든 내용을 담고 있지 않습니다.<br>복용 전 약사에게 확인하세요.</div>';
  return `<section class="col" style="gap:18px">
    <div class="col" style="gap:8px">
      <div class="row">${badge(otc ? '일반의약품' : '전문의약품', 'kind dot ' + (otc ? 'dot-otc' : 'dot-rx'))}</div>
      <h1 class="title" style="line-height:1.3;letter-spacing:-.3px">${esc(d.name)}</h1>
      <div class="row-between muted13"><span>${esc(d.co)}</span><a href="https://nedrug.mfds.go.kr/pbp/CCBBB01/getItemDetail?itemSeq=${encodeURIComponent(d.seq)}" target="_blank" rel="noopener">의약품안전나라에서 보기</a></div>
    </div>
    ${body}
  </section>`;
}

function render() {
  const tab = !F.photoRead && s.tab === 'photo' ? 'manual' : s.tab;
  const screen = s.screen === 'find' ? findScreen(tab) : s.screen === 'results' ? resultsScreen() : detailScreen();
  const cta = s.screen === 'find' && tab === 'manual'
    ? `<div class="cta"><div class="cta-hint" id="cta-hint" aria-live="polite">${esc(s.searchError || missingText())}</div><button type="button" class="btn lg full" id="cta-btn" data-act="search" ${hasCriteria() && !s.searching ? '' : 'disabled'}>${s.searching ? '찾는 중' : '후보 찾기'}</button></div>`
    : s.screen !== 'find' ? '<div class="cta"><button type="button" class="btn lg full mint" data-act="again">다른 알약 찾기</button></div>' : '';
  document.getElementById('app').innerHTML = header() + `<main class="main">${screen}</main>` + cta;
}

// 입력칸은 다시 그리지 않고 딸린 부분만 고침: 다시 그리면 한글 조합 입력이 끊김
function refresh() {
  const $ = id => document.getElementById(id);
  if ($('cta-btn')) $('cta-btn').disabled = !hasCriteria() || s.searching;
  if ($('cta-hint')) $('cta-hint').textContent = s.searchError || missingText();
  if ($('q-count')) $('q-count').textContent = s.question.length;
  if ($('ask-btn')) $('ask-btn').disabled = !s.question.trim();
  if ($('hits')) $('hits').innerHTML = hitsHtml();
}

// ---------- 동작 ----------
// ---------- 사진 자르기 ----------
// 자르기 영역은 사진 칸 크기에 대한 비율(0~1). 새 사진을 올리면 기본값으로 시작
const CROP_DEFAULT = { x: 0.08, y: 0.13, w: 0.84, h: 0.74 }, CROP_MIN = 0.15;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
// dx·dy(비율)만큼 옮기거나(resize=false) 오른쪽 아래 모서리를 끌어 크기를 바꿈. 칸 밖으로 나가지 않음
const moveCrop = (c, dx, dy, resize) => resize
  ? { ...c, w: clamp(c.w + dx, CROP_MIN, 1 - c.x), h: clamp(c.h + dy, CROP_MIN, 1 - c.y) }
  : { ...c, x: clamp(c.x + dx, 0, 1 - c.w), y: clamp(c.y + dy, 0, 1 - c.h) };
const cropStyle = c => `left:${c.x * 100}%;top:${c.y * 100}%;width:${c.w * 100}%;height:${c.h * 100}%`;
// 끄는 동안에는 화면 전체를 다시 그리지 않고 상자 위치만 바꿈 (다시 그리면 끌기가 끊김)
const placeCrop = (k, el) => { el.style.cssText = cropStyle(s.photos[k].crop); };

let drag = null;
document.addEventListener('pointerdown', e => {
  const box = e.target.closest('[data-crop]');
  if (!box) return;
  const r = box.parentElement.getBoundingClientRect(), k = box.dataset.crop;
  drag = { k, box, resize: !!e.target.closest('[data-handle]'), x: e.clientX, y: e.clientY, c: s.photos[k].crop, W: r.width, H: r.height };
  box.setPointerCapture(e.pointerId);
  e.preventDefault();
});
document.addEventListener('pointermove', e => {
  if (!drag || !s.photos[drag.k]) return;
  s.photos[drag.k].crop = moveCrop(drag.c, (e.clientX - drag.x) / drag.W, (e.clientY - drag.y) / drag.H, drag.resize);
  placeCrop(drag.k, drag.box);
});
['pointerup', 'pointercancel'].forEach(t => document.addEventListener(t, () => { drag = null; }));
document.addEventListener('keydown', e => {
  const box = e.target.closest && e.target.closest('[data-crop]'), d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
  if (!box || !d) return;
  const k = box.dataset.crop;
  s.photos[k].crop = moveCrop(s.photos[k].crop, d[0] * 0.02, d[1] * 0.02, e.shiftKey);
  placeCrop(k, box);
  e.preventDefault();
});

// 자르기 상자 안에 보이는 부분만 잘라 JPEG로 만듦. 캔버스로 다시 그려 위치 정보(EXIF)도 빠짐
async function cropped(k) {
  const el = document.querySelector(`[data-slot="${k}"]`);
  if (!el) throw new Error('사진을 다시 올려 주세요.');
  const img = await createImageBitmap(s.photos[k].file, { imageOrientation: 'from-image' });
  const w = el.clientWidth, h = el.clientHeight, scale = Math.max(w / img.width, h / img.height); // object-fit: cover와 같은 배율
  const c0 = s.photos[k].crop;
  const sx = (c0.x * w + (img.width * scale - w) / 2) / scale, sy = (c0.y * h + (img.height * scale - h) / 2) / scale;
  const sw = c0.w * w / scale, sh = c0.h * h / scale, f = Math.min(1, 2048 / Math.max(sw, sh));
  const c = document.createElement('canvas');
  c.width = Math.round(sw * f); c.height = Math.round(sh * f);
  c.getContext('2d').drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
  return new Promise(ok => c.toBlob(ok, 'image/jpeg', 0.9));
}

async function sendPhoto() {
  set({ reading: true, photoError: '' });
  try {
    const form = new FormData();
    for (const k of ['f', 'b']) if (s.photos[k]) form.append('files', await cropped(k), k + '.jpg');
    const r = await fetch('/api/photo', { method: 'POST', body: form });
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof v.detail === 'string' ? v.detail : '각인을 읽지 못했습니다. 직접 입력하거나 다시 찍어 주세요.');
    Object.values(s.photos).forEach(p => p && URL.revokeObjectURL(p.url));
    const known8 = v.colors.filter(c => COLORS.some(x => x[0] === c)), extra = v.colors.filter(c => !known8.includes(c));
    set({ reading: false, tab: 'manual', imprintMode: 'text', front: v.front, back: v.back, colors: known8, colorUnknown: false,
      customOn: extra.length > 0, customColor: extra.join('+'), shape: v.shape, capsule: v.capsule, filledFromPhoto: true, photos: { f: null, b: null } });
  } catch (e) { set({ reading: false, photoError: e.message }); }
}

let openSeq = 0, askSeq = 0; // 다른 약·다른 질문으로 넘어간 뒤 늦게 온 응답은 버림
// 늦게 온 응답은 그 탭을 보고 있을 때만 다시 그림: 질문칸에 쓰는 중에 다시 그리면 한글 조합 입력이 끊김
const setTab = (tab, patch) => { Object.assign(s, patch); if (s.screen === 'detail' && s.dtab === tab) render(); };

function openDrug(id, from) {
  const d = known.get(id), n = ++openSeq;
  askSeq++;
  set({ drugId: id, screen: 'detail', from, dtab: 'summary', qa: 'idle', question: '', emergency: false, result: null,
    doc: null, docError: '', summary: null, summaryState: 'idle', summaryError: '' });
  scrollTo(0, 0);
  if (!d || d.type !== 'otc' || !d.doc) return;
  api('/api/doc/' + encodeURIComponent(d.seq)).then(r => n === openSeq && setTab('original', { doc: r }), e => n === openSeq && setTab('original', { docError: e.message }));
  loadSummary();
}

function loadSummary() {
  const d = known.get(s.drugId), n = openSeq;
  if (!d || !d.doc || s.summary || s.summaryState === 'loading') return;
  set({ summaryState: 'loading' });
  api('/api/summary/' + encodeURIComponent(d.seq)).then(r => n === openSeq && setTab('summary', { summary: r, summaryState: 'done' }),
    e => n === openSeq && setTab('summary', { summaryState: 'error', summaryError: e.message }));
}

function startAsk() {
  const q = s.question.trim(); if (!q) return;
  // 응급 표현 감지(항상): 답변을 기다리지 않고 119 안내를 먼저 보임
  const emergency = /삼켰|과다|과량|많이 먹|여러 알|한꺼번에|다 먹었|다 먹어 ?버|잘못 먹|통째/.test(q);
  Object.assign(s, { emergency, result: null, masked: '' });
  if (external()) maskAsk(q); // 외부(CLOVA·Claude)로 나갈 때만 가리고 사용자 확인을 받음
  else sendAsk();
}

async function maskAsk(q) {
  const n = ++askSeq;
  set({ qa: 'masking' });
  try {
    const r = await api('/api/mask', null, { question: q });
    if (n === askSeq) setTab('ask', { qa: 'confirm', masked: r.masked });
  } catch (e) { if (n === askSeq) setTab('ask', { qa: 'done', result: { error: e.message, evidence: [] } }); }
}

// SSE 읽기: 질문을 주소에 넣지 않으려고 EventSource(GET) 대신 POST 응답 본문을 읽음
async function readEvents(r, onStep) {
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = '', result = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = (block.match(/^event: (.*)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.*)$/m) || [])[1] || '{}');
      if (ev === 'step') onStep(data);
      else if (ev === 'result') result = data;
      else if (ev === 'error') throw new Error(data.detail);
    }
  }
  if (!result) throw new Error('답변을 받는 중에 연결이 끊겼습니다. 다시 질문해 주세요.');
  return result;
}

async function sendAsk() {
  const d = known.get(s.drugId), n = ++askSeq;
  set({ qa: 'running', steps: {} });
  let result;
  try {
    const r = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(external() ? { seq: d.seq, question: s.masked, masked: true } : { seq: d.seq, question: s.question.trim() }) });
    if (!r.ok) {
      const b = await r.json().catch(() => ({}));
      throw new Error(typeof b.detail === 'string' ? b.detail : '서버에 연결할 수 없습니다. 잠시 뒤 다시 시도해 주세요.');
    }
    result = await readEvents(r, ({ step, status }) => { if (n === askSeq) setTab('ask', { steps: { ...s.steps, [step]: status } }); });
  } catch (e) { result = { error: e.message, evidence: [] }; }
  if (n === askSeq) setTab('ask', { qa: 'done', result });
}

const ACT = {
  back: () => { openSeq++; askSeq++; set({ screen: s.screen === 'detail' ? s.from : 'find' }); },
  tab: v => set({ tab: v }),
  imprint: v => set({ imprintMode: v }),
  fillSample: () => set({ imprintMode: 'text', front: 'tylenol', back: '5OO', colors: ['하양'], colorUnknown: false, shape: '장방형' }),
  color: v => set({ colorUnknown: false, colors: s.colors.includes(v) ? s.colors.filter(x => x !== v) : s.colors.concat(v) }),
  custom: () => set({ customOn: !s.customOn, colorUnknown: false }),
  unknown: () => set(s.colorUnknown ? { colorUnknown: false } : { colorUnknown: true, colors: [], customOn: false }),
  shape: v => set({ shape: s.shape === v ? '' : v }),
  capsule: v => set({ capsule: s.capsule === v ? '' : v }),
  clearPhoto: k => { URL.revokeObjectURL(s.photos[k].url); set({ photos: { ...s.photos, [k]: null } }); },
  sendPhoto,
  again: () => { openSeq++; askSeq++; set({ screen: 'find', imprintMode: 'text', front: '', back: '', colors: [], colorUnknown: false, customOn: false, customColor: '', shape: '', capsule: '', filledFromPhoto: false, nameQuery: '', hits: [], hitsError: '', searchError: '' }); scrollTo(0, 0); },
  search: runSearch,
  open: (v, el) => openDrug(v, el.dataset.from),
  toNameTab: () => set({ screen: 'find', tab: 'name' }),
  dtab: v => { set({ dtab: v }); if (v === 'summary') loadSummary(); },
  suggest: v => set({ question: v }),
  ask: startAsk,
  confirmSend: sendAsk,
  resetQa: () => { askSeq++; set({ qa: 'idle', emergency: false, result: null }); },
};

document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (el && !el.disabled) ACT[el.dataset.act](el.dataset.v, el);
});
document.addEventListener('input', e => {
  const f = e.target.dataset.field;
  if (!f) return;
  s[f] = f === 'question' ? e.target.value.slice(0, 300) : e.target.value;
  if (f !== 'question' && f !== 'nameQuery') s.searchError = '';
  if (f === 'nameQuery') { clearTimeout(nameTimer); nameTimer = setTimeout(searchNames, 250); }
  refresh();
});
document.addEventListener('change', e => {
  const k = e.target.dataset.photo, file = e.target.files && e.target.files[0];
  if (!k || !file) return;
  if (!file.type.startsWith('image/')) return set({ photoError: '사진 파일만 올릴 수 있습니다.' });
  if (file.size > MAX_PHOTO) return set({ photoError: '사진은 한 장에 5MB까지 올릴 수 있습니다.' });
  set({ photoError: '', photos: { ...s.photos, [k]: { url: URL.createObjectURL(file), file, crop: { ...CROP_DEFAULT } } } });
});

// 각인 비교 자가 검사는 서버 쪽 test_search.py로 옮김
render();
api('/api/config', {}).then(c => { Object.assign(F, c); render(); }).catch(() => {});
