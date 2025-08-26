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
  list.innerHTML = '';
  const entries = Object.entries(DATA.sessions || {});
  const filtered = filterText
    ? entries.filter(([_, s]) => (s.name||'').toLowerCase().includes(filterText.toLowerCase()))
    : entries;

  filtered.sort((a,b)=>((b[1].updated_at||'') > (a[1].updated_at||''))?1:-1);

  for (const [sid, sess] of filtered) {
    const div = document.createElement('div');
    div.className = 'chat-item';
    div.dataset.sid = sid;
    div.title = sess.name || '(untitled)';
    const safeName = escapeHTML(sess.name || '(untitled)');
    div.innerHTML = `<span class="title">${safeName}</span><button class="chat-more" title="More" aria-haspopup="true" aria-expanded="false">⋮</button>`;
    if (sid === CURRENT_SID) div.style.background = 'var(--hover)';
    list.appendChild(div);
  }

  // Delegated handlers (bind once per list)
  if (!list.dataset.boundClicks){
    list.dataset.boundClicks = '1';
    list.addEventListener('click', async (e)=>{
      const moreBtn = e.target.closest('.chat-more');
      if (moreBtn) {
        e.stopPropagation();
        const item = e.target.closest('.chat-item'); if(!item) return;
        SELECTED_CHAT_ITEM = item;
        openCtxMenu(e.pageX, e.pageY);
        return;
      }
      const item = e.target.closest('.chat-item'); if(!item) return;
      const sid = item.dataset.sid;
      await api('/api/session/select', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: sid})});
      const hist = await api('/api/history');
      DATA = hist; CURRENT_SID = hist.current_session;
      renderChatList();
      renderMessages();
    });
  }
  if (!list.dataset.boundContext){
    list.dataset.boundContext = '1';
    list.addEventListener('contextmenu', (e)=>{
      const item = e.target.closest('.chat-item'); if(!item) return;
      e.preventDefault();
      SELECTED_CHAT_ITEM = item;
      openCtxMenu(e.pageX, e.pageY);
    });
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
  const input = $('#chatInput');
  const text = input.value;
  if (!text.trim()) return;

  // Nhật ký mode: save and exit
  if (LOG_MODE) {
    try{
      const model = $('#modelSelect').value || undefined;
      const res = await api('/api/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: CURRENT_SID, message: text, model})});
      if (res.ok){
        const container = $('#messages');
        const div = document.createElement('div');
        div.className = 'msg assistant';
        div.innerHTML = nl2br('✅ Đã lưu vào nhật ký');
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

  // Optimistic append
  const sess = DATA.sessions[CURRENT_SID];
  sess.messages.push({role:'user', content:text});
  renderMessages();
  input.value = '';

  // Assistant placeholder
  const container = $('#messages');
  const holder = document.createElement('div');
  holder.className = 'msg assistant';
  holder.innerHTML = '';
  container.appendChild(holder);
  container.scrollTop = container.scrollHeight;

  // Stream call
  const res = await fetch('/api/chat', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({session_id: CURRENT_SID, model, prompt: text})
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let full = '';

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
      }catch(_){}
    }
  }

  // Sync server history
  const hist = await api('/api/history');
  DATA = hist; CURRENT_SID = hist.current_session;
  renderChatList();
  renderMessages();
}

// ---------- Prompt menu & global bindings ----------
function bindGlobal(){
  // Sidebar toggle
  $('#toggleSidebar').addEventListener('click', ()=>{
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    $('#toggleSidebar').setAttribute('aria-label', collapsed ? 'Open sidebar' : 'Close sidebar');
    $('#toggleSidebar').title = collapsed ? 'Open sidebar' : 'Close sidebar';
  });

  // New chat
  $('#btnNewChat').addEventListener('click', async ()=>{
    await api('/api/session/new', {method:'POST'});
    const hist = await api('/api/history');
    DATA = hist; CURRENT_SID = hist.current_session;
    renderChatList();
    renderMessages();
    $('#chatInput').focus();
  });

  // Search chats (simple prompt filter)
  $('#btnSearchChats').addEventListener('click', ()=>{
    const q = prompt('Tìm trong tiêu đề phiên:');
    renderChatList(q || "");
  });

  // Plus menu toggle
  const promptWrap = $('#prompt');
  const addBtn = $('#addMenuBtn');
  const addMenu = $('#addMenu');

  function openMenu(){
    // Decide whether to open above or below based on available space
    const btnRect = addBtn.getBoundingClientRect();
    const menuRect = addMenu.getBoundingClientRect();
    const spaceBelow = window.innerHeight - btnRect.bottom;
    const spaceAbove = btnRect.top;
    const needUp = spaceBelow < (menuRect.height + 12) && spaceAbove > spaceBelow;
    promptWrap.classList.toggle('menu-up', !!needUp);
    promptWrap.classList.add('menu-open');
    addBtn.setAttribute('aria-expanded','true');
  }
  function closeMenu(){
    promptWrap.classList.remove('menu-open');
    promptWrap.classList.remove('menu-up');
    addBtn.setAttribute('aria-expanded','false');
  }

  addBtn.addEventListener('click', (e)=>{
    e.stopPropagation();
    promptWrap.classList.contains('menu-open') ? closeMenu() : openMenu();
  });
  document.addEventListener('click', (e)=>{
    if (!promptWrap.contains(e.target)) closeMenu();
  });
  document.addEventListener('keydown', (e)=>{
    if (e.key === 'Escape') closeMenu();
  });
  const obs = new ResizeObserver(()=>{
    const rect = addMenu.getBoundingClientRect();
    const overflowR = rect.right - window.innerWidth;
    addMenu.style.left = overflowR > 0 ? (Math.max(8 - overflowR - 12, 8) + 'px') : '8px';
  });
  obs.observe(addMenu);

  // Re-evaluate placement on resize if menu is open
  window.addEventListener('resize', ()=>{
    if (promptWrap.classList.contains('menu-open')) {
      openMenu();
    }
  });

  // Handle plus-menu actions
  addMenu.addEventListener('click', async (e)=>{
    const a = e.target.closest('a.menu-item');
    if (!a) return;
    const act = a.dataset.act;
    closeMenu();
    if (act === 'log') {
      // Toggle nhật ký mode; actual save happens on Enter in sendMessage()
      LOG_MODE = !LOG_MODE;
      const promptWrap = $('#prompt');
      const input = $('#chatInput');
      if (LOG_MODE) {
        promptWrap.classList.add('mode-log');
        if (input.dataset.placeholder === undefined) {
          input.dataset.placeholder = input.getAttribute('placeholder') || '';
        }
        input.setAttribute('placeholder', 'Nhập nội dung để lưu nhật ký, rồi nhấn Enter...');
        input.focus();
      } else {
        promptWrap.classList.remove('mode-log');
        if (input.dataset.placeholder !== undefined) input.setAttribute('placeholder', input.dataset.placeholder);
      }
    } else if (act === 'search') {
      // Placeholder: feature not fully available without self-hosted n8n
      const container = $('#messages');
      const div = document.createElement('div');
      div.className = 'msg assistant';
      div.innerHTML = nl2br('ℹ️ Web search chưa khả dụng: bạn chưa self-host n8n.');
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }
  });

  // Send
  $('#btnSend').addEventListener('click', sendMessage);
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
