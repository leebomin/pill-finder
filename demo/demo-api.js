// 데모: 서버 대신 녹화한 응답(demo-data.js)으로 /api/* 요청에 답함. app.js는 실제 앱과 같은 파일.
(() => {
  const D = window.DEMO, realFetch = window.fetch.bind(window);
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const fail = (detail, status = 400) => json({ detail }, status);
  const ONLY_SAMPLE = "데모에서는 '예시 값 채우기'로 넣은 값(tylenol / 5OO · 하양 · 장방형)만 찾을 수 있습니다.";
  const ONLY_SUGGEST = '데모에서는 타이레놀정500·게보린정·베아제정의 예시 질문 버튼만 답할 수 있습니다.';
  const NO_DRUG = '데모에 저장되지 않은 약입니다. 타이레놀정500·게보린정·베아제정을 열어 보세요.';
  const norm = v => String(v ?? '').toLowerCase().replace(/[\s-]/g, '');
  // 단계마다 잠깐 멈춰 실제처럼 진행 표시가 바뀌게 함
  const stream = events => new Response(new ReadableStream({
    async start(c) {
      const enc = new TextEncoder();
      for (const [ev, data] of events) {
        await wait(ev === 'step' && data.status === 'start' ? 900 : 150);
        c.enqueue(enc.encode(`event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`));
      }
      c.close();
    }
  }), { headers: { 'Content-Type': 'text/event-stream' } });

  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    const path = url.pathname.replace(/^.*?(\/api\/)/, '/api/');
    if (!path.startsWith('/api/')) return realFetch(input, init);
    const q = Object.fromEntries(url.searchParams), body = typeof init.body === 'string' ? JSON.parse(init.body) : null;
    const seq = decodeURIComponent(path.split('/')[3] || '');
    await wait(200);
    if (path === '/api/config') return json({ photoRead: true, clovaText: true, claudeReview: true, clovaCapped: false });
    if (path === '/api/search') {
      const hit = Object.entries(D.search).find(([k]) => { const p = JSON.parse(k); return Object.keys(p).every(f => norm(p[f]) === norm(q[f])); });
      return hit ? json(hit[1]) : fail(ONLY_SAMPLE);
    }
    if (path === '/api/names') return json({ hits: D.names.filter(h => norm(h.name).includes(norm(q.q))).slice(0, 20) });
    if (path.startsWith('/api/doc/')) return D.doc[seq] ? json(D.doc[seq]) : fail(NO_DRUG, 404);
    if (path.startsWith('/api/summary/')) { await wait(1200); return D.summary[seq] ? json(D.summary[seq]) : fail(NO_DRUG, 404); }
    if (path === '/api/mask') { await wait(900); return D.mask[body.question] ? json({ masked: D.mask[body.question] }) : fail(ONLY_SUGGEST); }
    if (path === '/api/ask') { const ev = D.ask[body.seq + '|' + body.question]; return ev ? stream(ev) : fail(ONLY_SUGGEST); }
    // 사진: 어떤 사진이든 같은 예시 값 (실제 앱은 자른 사진을 CLOVA HCX-005로 읽음)
    if (path === '/api/photo') { await wait(1500); return json({ front: 'TYLENOL', back: '500', colors: ['하양'], shape: '장방형', capsule: 'n' }); }
    return fail('데모에서 지원하지 않는 요청입니다.', 404);
  };
})();
