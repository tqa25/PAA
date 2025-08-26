// ---------- Utils ----------
const $ = (sel, root=document)=>root.querySelector(sel);
const $$ = (sel, root=document)=>Array.from(root.querySelectorAll(sel));
const escapeHTML = (s="") => s
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const nl2br = (s="") => escapeHTML(s).replace(/\n/g,"<br>");

let DATA = null;
let CURRENT_SID = null;
let SELECTED_CHAT_ITEM = null; // for context menu
let LOG_MODE = false; // nhật ký mode: when true, Enter saves to logs
let STREAMING = false; // whether LLM response is streaming
let STREAM_ABORT = null; // AbortController for current stream
let SEND_BTN_ORIG_HTML = null; // cache original send button icon
// NOTE: Voice button feature (btnVoice) tạm thời bị ẩn trong index.html; không có logic JS hiện tại.

function setSendButtonState(streaming){
  const btn = $('#btnSend');
  if (!btn) return;
  if (SEND_BTN_ORIG_HTML === null) SEND_BTN_ORIG_HTML = btn.innerHTML;
  if (streaming){
    btn.classList.add('is-streaming');
    btn.setAttribute('title','Stop');
    btn.setAttribute('aria-label','Stop streaming');
    btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="6" y="6" width="12" height="12" rx="2" stroke="currentColor" stroke-width="2"/></svg>';
  } else {
    btn.classList.remove('is-streaming');
    btn.setAttribute('title','Send');
    btn.setAttribute('aria-label','Send message');
    if (SEND_BTN_ORIG_HTML) btn.innerHTML = SEND_BTN_ORIG_HTML;
  }
}

async function api(path, opts={}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get('content-type') || "";
  return ct.includes('application/json') ? res.json() : res.text();
}

// ---------- Initial load ----------
async function loadAll() {
  const [models, hist] = await Promise.all([
    api('/api/models').catch(()=>({models:[]})),
    api('/api/history')
  ]);
  DATA = hist;
  CURRENT_SID = hist.current_session;
  renderModels(models.models || []);
  renderChatList();
  renderMessages();
  bindGlobal();
}

// ---------- Models ----------
function renderModels(models=[]) {
  const sel = $('#modelSelect');
  const label = $('#modelLabel');

  if (!models.length) {
    sel.innerHTML = `<option value="">— Ollama offline —</option>`;
    sel.disabled = true;
    label.textContent = 'Model';
  } else {
    sel.disabled = false;
    sel.innerHTML = models.map(m=>`<option value="${m}">${m}</option>`).join('');
    // Keep previous selection if possible
    if (localStorage.getItem('model')) {
      const prev = localStorage.getItem('model');
      if ([...sel.options].some(o=>o.value===prev)) sel.value = prev;
    }
    label.textContent = 'Model';
  }

  sel.addEventListener('change', ()=>{
    localStorage.setItem('model', sel.value || '');
  });
}

// ---------- Sessions (sidebar) ----------
function renderChatList(filterText="") {
  const list = $('#chatList');
  const pinnedList = $('#pinnedList');
  if (!list) return;
  list.innerHTML=''; if (pinnedList) pinnedList.innerHTML='';
  const entries = Object.entries(DATA.sessions || {});
  const filtered = filterText ? entries.filter(([_,s]) => (s.name||'').toLowerCase().includes(filterText.toLowerCase())) : entries;
  const pinned=[], normal=[];
  for (const pair of filtered){
    const sess=pair[1];
    if (sess.pinned && sess.journal_tag) pinned.push(pair); else normal.push(pair);
  }
  normal.sort((a,b)=>((b[1].updated_at||'') > (a[1].updated_at||''))?1:-1);
  const orderPinnedIds=['journal_workout','journal_eat','journal_daily'];
  pinned.sort((a,b)=>orderPinnedIds.indexOf(a[0]) - orderPinnedIds.indexOf(b[0]));
  function addItem(target,sid,sess,isPinned){
    const div=document.createElement('div');
    div.className='chat-item'+(isPinned?' pinned':'');
    div.dataset.sid=sid; div.title=sess.name||'(untitled)';
    const safeName=escapeHTML(sess.name||'(untitled)');
    const moreBtn=isPinned?'':'<button class="chat-more" title="More" aria-haspopup="true" aria-expanded="false">⋮</button>';
    div.innerHTML=`<span class=\"title\">${safeName}</span>${moreBtn}`;
    if (sid===CURRENT_SID) div.style.background='var(--hover)';
    target.appendChild(div);
  }
  if (pinnedList) for (const [sid,sess] of pinned) addItem(pinnedList,sid,sess,true);
  for (const [sid,sess] of normal) addItem(list,sid,sess,false);
  const bindTargets=[list]; if (pinnedList) bindTargets.push(pinnedList);
  for (const tgt of bindTargets){
    if (!tgt.dataset.boundClicks){
      tgt.dataset.boundClicks='1';
      tgt.addEventListener('click', async e=>{
        const more=e.target.closest('.chat-more');
        if (more){ e.stopPropagation(); const item=e.target.closest('.chat-item'); if(!item) return; SELECTED_CHAT_ITEM=item; openCtxMenu(e.pageX,e.pageY); return; }
        const item=e.target.closest('.chat-item'); if(!item) return;
        const sid=item.dataset.sid;
        await api('/api/session/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid})});
        const hist=await api('/api/history'); DATA=hist; CURRENT_SID=hist.current_session; renderChatList(); renderMessages();
      });
    }
    if (!tgt.dataset.boundContext){
      tgt.dataset.boundContext='1';
      tgt.addEventListener('contextmenu', e=>{ const item=e.target.closest('.chat-item'); if(!item) return; if (item.classList.contains('pinned')) return; e.preventDefault(); SELECTED_CHAT_ITEM=item; openCtxMenu(e.pageX,e.pageY); });
    }
  }
}

function openCtxMenu(x,y){
  const m = $('#ctxMenu');
  m.style.left = x + 'px';
  m.style.top = y + 'px';
  m.setAttribute('aria-hidden','false');

  const onDocClick = (e)=> {
    if (!m.contains(e.target)) {
      m.setAttribute('aria-hidden','true');
      document.removeEventListener('click', onDocClick);
    }
  };
  document.addEventListener('click', onDocClick);

  m.onclick = async (e)=>{
    const act = e.target.closest('button')?.dataset?.act;
    if (!act || !SELECTED_CHAT_ITEM) return;
    const sid = SELECTED_CHAT_ITEM.dataset.sid;

    if (act==='rename') {
      const newName = prompt('Tên mới', DATA.sessions[sid]?.name || '');
      if (newName!=null) {
        await api('/api/session/rename', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: sid, new_name: newName})});
      }
    } else if (act==='clear') {
      if (confirm('Xóa toàn bộ tin nhắn của phiên này?')) {
        await api('/api/session/clear', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: sid})});
      }
    } else if (act==='delete') {
      if (confirm('Xóa phiên này?')) {
        await api('/api/session/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: sid})});
      }
    }
    const hist = await api('/api/history');
    DATA = hist; CURRENT_SID = hist.current_session;
    renderChatList();
    renderMessages();
    $('#ctxMenu').setAttribute('aria-hidden','true');
  };
}

// ---------- Messages ----------
function renderMessages() {
  const container = $('#messages');
  container.innerHTML = '';
  const sess = DATA.sessions[CURRENT_SID];
  const hasMsgs = !!(sess && (sess.messages||[]).length);

  $('#emptyState').style.display = hasMsgs ? 'none' : 'block';

  if (!hasMsgs) return;
  for (const m of sess.messages) {
    const div = document.createElement('div');
    div.className = `msg ${m.role==='user'?'user':'assistant'}`;
    div.innerHTML = nl2br(m.content || '');
    container.appendChild(div);
  }
  container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
  if (STREAMING) return; // ignore while streaming
  const input = $('#chatInput');
  const text = input.value;
  if (!text.trim()) return;

  // Nhật ký internal log mode (not for pinned journals)
  if (LOG_MODE) {
    try{
      const model = $('#modelSelect').value || undefined;
      const res = await api('/api/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: CURRENT_SID, message: text, model})});
      if (res.ok){
        const container = $('#messages');
        const div = document.createElement('div');
        div.className = 'msg assistant';
        div.innerHTML = nl2br('✅ Đã lưu vào user_logs.json');
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        input.value = '';
        LOG_MODE = false;
        const promptWrap = $('#prompt');
        promptWrap.classList.remove('mode-log');
        if (input.dataset.placeholder !== undefined) input.setAttribute('placeholder', input.dataset.placeholder);
      } else {
        alert('Không lưu được nhật ký: ' + (res.error || 'unknown'));
      }
    }catch(err){
      alert('Lỗi tiến trình: không lưu được nhật ký');
    }
    return;
  }

  const sel = $('#modelSelect');
  const model = sel.value;
  if (!model) { alert('Chưa có model. Hãy chạy Ollama, kéo model và F5.'); return; }

  // Optimistic append (UI immediate)
  const sess = DATA.sessions[CURRENT_SID];
  if (sess && sess.pinned && sess.journal_tag){
    // Journal: call journal log endpoint; no streaming
    try {
      const res = await api('/api/journal/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: CURRENT_SID, message: text})});
      if (res.ok){
        // Sync history to display saved entry & confirmation
        const hist = await api('/api/history');
        DATA = hist; CURRENT_SID = hist.current_session;
        renderChatList();
        renderMessages();
        input.value='';
      } else {
        const container = $('#messages');
        const div = document.createElement('div');
        div.className='msg assistant';
        div.innerHTML = nl2br('⚠️ Lưu nhật ký thất bại: ' + (res.error||'unknown'));
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
      }
    } catch(err){
      const container = $('#messages');
      const div = document.createElement('div');
      div.className='msg assistant';
      div.innerHTML = nl2br('⚠️ Lỗi: ' + err.message);
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }
    return;
  } else {
    sess.messages.push({role:'user', content:text});
    renderMessages();
    input.value = '';
  }

  // Assistant placeholder
  const container = $('#messages');
  const holder = document.createElement('div');
  holder.className = 'msg assistant';
  holder.innerHTML = '';
  container.appendChild(holder);
  container.scrollTop = container.scrollHeight;

  // Stream call with abort support
  STREAM_ABORT = new AbortController();
  STREAMING = true;
  setSendButtonState(true);
  let full = '';
  try {
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: CURRENT_SID, model, prompt: text}),
      signal: STREAM_ABORT.signal
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, {stream:true});
      for (const line of chunk.split('\n')) {
        const s = line.trim(); if (!s) continue;
        try{
          const obj = JSON.parse(s);
          if (obj.delta !== undefined) {
            full += obj.delta;
            holder.innerHTML = nl2br(full);
            container.scrollTop = container.scrollHeight;
          } else if (obj.error) {
            holder.innerHTML = nl2br('⚠️ Lỗi: ' + obj.error);
          }
        }catch(_){/* ignore parse errors */}
      }
    }
  } catch (err){
    if (err.name === 'AbortError') {
      holder.innerHTML = nl2br(full + '\n⏹ Đã dừng.');
    } else {
      holder.innerHTML = nl2br('⚠️ Lỗi: ' + err.message);
    }
  } finally {
    STREAMING = false;
    STREAM_ABORT = null;
    setSendButtonState(false);
  }

  // Sync server history (to get assistant message with tag if journal)
  const hist = await api('/api/history');
  DATA = hist; CURRENT_SID = hist.current_session;
  renderChatList();
  renderMessages();
}

// ---------- Prompt menu & global bindings ----------
function bindGlobal(){
  // Sidebar toggle
  $('#toggleSidebar').addEventListener('click', ()=>{
    const opened = document.body.classList.toggle('drawer-open');
    $('#toggleSidebar').setAttribute('aria-label', opened ? 'Close sidebar' : 'Open sidebar');
    $('#toggleSidebar').title = opened ? 'Close sidebar' : 'Open sidebar';
  });
  const overlay = document.querySelector('.drawer-overlay');
  if (overlay && !overlay.dataset.bound){
    overlay.dataset.bound='1';
    overlay.addEventListener('click', ()=>{
      document.body.classList.remove('drawer-open');
    }, {passive:true});
  }

  // New chat
  $('#btnNewChat').addEventListener('click', async ()=>{
    await api('/api/session/new', {method:'POST'});
    const hist = await api('/api/history');
    DATA = hist; CURRENT_SID = hist.current_session;
    renderChatList();
    renderMessages();
    $('#chatInput').focus();
  });

  // Collapse chats
  const collapseBtn = $('#btnCollapseChats');
  if (collapseBtn && !collapseBtn.dataset.bound){
    collapseBtn.dataset.bound='1';
    collapseBtn.addEventListener('click', ()=>{
      const wrap = $('#chatListWrap');
      if (!wrap) return;
      wrap.classList.toggle('collapsed');
      collapseBtn.textContent = wrap.classList.contains('collapsed') ? '+' : '−';
    });
  }

  // Search chats (simple prompt filter)
  $('#btnSearchChats').addEventListener('click', ()=>{
    const q = prompt('Tìm trong tiêu đề phiên:');
    renderChatList(q || "");
  });

  // Plus menu toggle
  const promptWrap = $('#prompt');
  const addBtn = $('#addMenuBtn');
  const addMenu = $('#addMenu');
  // (Plus menu logic already defined earlier outside bindGlobal)
  addBtn.addEventListener('click', (e)=>{
    e.stopPropagation();
    promptWrap.classList.toggle('menu-open');
  });
  document.addEventListener('click', (e)=>{
    if (!promptWrap.contains(e.target)) promptWrap.classList.remove('menu-open');
  });
  // Send button logic (abort vs send)
  $('#btnSend').addEventListener('click', ()=>{
    if (STREAMING){ if (STREAM_ABORT) STREAM_ABORT.abort(); return; }
    sendMessage();
  });
  const ta = $('#chatInput');
  // Auto-resize textarea
  const autoresize = ()=>{
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  };
  ta.addEventListener('input', autoresize);
  autoresize();
  // Enter to send, Shift+Enter for newline
  ta.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

// ---------- Start ----------
loadAll().catch(err=>{
  console.error(err);
});
