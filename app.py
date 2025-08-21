import streamlit as st
from datetime import datetime
import backend
from html import escape

# ===== Helper: safely render text with preserved newlines =====
def html_with_breaks(text: str) -> str:
  """Escape HTML and convert newlines to <br> for safe rendering."""
  if text is None:
    text = ""
  # Normalize CRLF/CR to LF
  text = text.replace("\r\n", "\n").replace("\r", "\n")
  return escape(text).replace("\n", "<br>")

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Chat App", layout="wide")

# ================== STATE INIT ==================
if "data" not in st.session_state:
    st.session_state.data = backend.load_history()
if not st.session_state.data["sessions"]:
    sid = backend.new_session_id()
    st.session_state.data["sessions"][sid] = {"name": backend.new_session_name(), "messages": []}
    st.session_state.data["current_session"] = sid

data = st.session_state.data
sessions = data["sessions"]
current_sid = data["current_session"]

# ================== SIDEBAR ==================
st.sidebar.title("Menu")
if current_sid in sessions:
    st.sidebar.caption(f"Phiên hiện tại: {sessions[current_sid]['name']}")

models = backend.list_models()
model = st.sidebar.selectbox("Chọn model", models)

if st.sidebar.button("➕ Nói chuyện khác với Hàn", use_container_width=True):
    sid = backend.new_session_id()
    data["sessions"][sid] = {"name": backend.new_session_name(), "messages": [], "updated_at": datetime.now().isoformat()}
    data["current_session"] = sid
    backend.save_history(data)
    st.rerun()

with st.sidebar.expander("🕑 Lịch sử", expanded=True):
    for sid, sess in sessions.items():
        col1, col2 = st.columns([0.75, 0.25])

        with col1:
            if st.button(sess["name"], key=f"session_{sid}", use_container_width=True):
                data["current_session"] = sid
                backend.save_history(data)
                st.rerun()

        with col2:
            action = st.selectbox("⋮", ["", "✏️ Rename", "🧹 Clear", "❌ Delete"],
                                  key=f"action_{sid}", label_visibility="collapsed")
            if action == "✏️ Rename":
                new_name = st.text_input("Tên mới", value=sess["name"], key=f"rename_{sid}")
                if st.button("Lưu", key=f"rename_btn_{sid}"):
                    data = backend.rename_session(data, sid, new_name)
                    backend.save_history(data)
                    st.rerun()
            elif action == "🧹 Clear":
                data = backend.clear_session_messages(data, sid)
                backend.save_history(data)
                st.rerun()
            elif action == "❌ Delete":
                if sid in data["sessions"]:
                    del data["sessions"][sid]
                    if sid == current_sid and data["sessions"]:
                        data["current_session"] = list(data["sessions"].keys())[0]
                    elif not data["sessions"]:
                        nsid = backend.new_session_id()
                        data["sessions"][nsid] = {"name": backend.new_session_name(), "messages": []}
                        data["current_session"] = nsid
                    backend.save_history(data)
                    st.rerun()

# ================== MAIN CHAT ==================
st.title("💬 Nói Chuyện Với Hàn")

if current_sid not in sessions:
    st.warning("Chưa có phiên chat nào, tạo mới nhé!")
else:
  session = sessions[current_sid]
  if "messages" not in session:
    session["messages"] = []

  # Hiển thị hội thoại cũ (bọc mỗi tin nhắn trong .chat-msg + class theo role)
  for idx, msg in enumerate(session["messages"]):
    role = msg.get("role", "assistant")
    role_cls = "user" if role == "user" else "assistant"
    with st.chat_message(role):
      safe_html = html_with_breaks(msg.get("content", ""))
      st.markdown(
        f'<div class="chat-msg {role_cls}" id="msg-{idx}">{safe_html}</div>',
        unsafe_allow_html=True
      )

  # Ô nhập prompt
  prompt = st.chat_input("Nhập tin nhắn và nhấn Enter...")

  # Xử lý khi gửi prompt
  if prompt:
    # Chuẩn hóa xuống dòng
    prompt = prompt.replace("\r\n", "\n").replace("\r", "\n")

    # Lưu và hiển thị tin nhắn của người dùng
    session["messages"].append({"role": "user", "content": prompt})
    backend.save_history(data)
    with st.chat_message("user"):
      user_html = html_with_breaks(prompt)
      st.markdown(f'<div class="chat-msg user">{user_html}</div>', unsafe_allow_html=True)

    # Gọi LLM (stream) và hiển thị dần phản hồi
    with st.chat_message("assistant"):
      placeholder = st.empty()
      full_response = ""
      context = [m for m in session["messages"] if not m.get("log_only")]
      try:
        for chunk in backend.chat_with_model(model, context):
          token = chunk["message"]["content"]
          full_response += token
          safe_html = html_with_breaks(full_response)
          placeholder.markdown(
            f'<div class="chat-msg assistant">{safe_html}</div>',
            unsafe_allow_html=True
          )
      except Exception as e:
        full_response = f"⚠️ Lỗi khi gọi model: {e}"
        placeholder.markdown(
          f'<div class="chat-msg assistant">{html_with_breaks(full_response)}</div>',
          unsafe_allow_html=True
        )

    # Lưu phản hồi trợ lý và rerun để ổn định trạng thái
    session["messages"].append({"role": "assistant", "content": full_response})
    backend.save_history(data)
    st.rerun()

# ================== CSS ==================
st.markdown("""
<style>
/* (Đã gỡ UI nhập prompt; bỏ các style liên quan đến stChatInput) */

/* Nền tối, sidebar */
body, .stApp { background-color: #1e1f20 !important; color: #e3e3e3 !important; }
section[data-testid="stSidebar"] {
    background-color: #1e1f20 !important;
    color: #e3e3e3 !important;
    border-right: 1px solid #353739;
}
/* Tin nhắn */
.chat-msg { line-height: 1.6; }

/* FAB điều hướng nhanh bên phải */
.fab-container{
    position:fixed;
    right:20px;
    bottom:96px; /* nhường chỗ cho thanh tùy chọn cố định */
    z-index:9999;
    display:flex;
    flex-direction:column;
}
.fab-container button{
    margin-top:6px;
    border:none;
    border-radius:50%;
    width:42px;
    height:42px;
    background:#353739;
    color:#e3e3e3;
    cursor:pointer;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25);
}
.fab-container button:hover{ background:#8ab4f8; color:#131314; }

/* Đã gỡ thanh tùy chọn cố định; không cần chừa khoảng dưới */
</style>
""", unsafe_allow_html=True)

# ================== FAB + JS (event delegation để không lỗi và luôn hoạt động sau rerun) ==================
st.markdown(
    """
<div class="fab-container">
    <button id="fab-top" title="Lên đầu trang">⬆️</button>
    <button id="fab-prev" title="Câu hỏi trước">🔼</button>
    <button id="fab-next" title="Câu hỏi tiếp theo">🔽</button>
    <button id="fab-bottom" title="Xuống cuối trang">⬇️</button>
</div>

<script>
(function(){
  // --- helpers cuộn (giữ nguyên) ---
  // Thử lấy document & window của trang cha (Streamlit render trong iframe)
  function getDoc(){
    try { return window.parent.document; }
    catch(e){ return document; }
  }
  const doc = getDoc();
  const win = doc.defaultView || window.parent || window;
  const se = doc.scrollingElement || doc.documentElement || doc.body;

  function getUserMsgs(){ return Array.from(doc.querySelectorAll('.chat-msg.user')); }
  function scrollTop(){ win.scrollTo({top:0, behavior:'smooth'}); }
  function scrollBottom(){ win.scrollTo({top: se.scrollHeight, behavior:'smooth'}); }
  function y(){ return win.scrollY || se.scrollTop || 0; }
  function absTop(el){ const r = el.getBoundingClientRect(); return r.top + y(); }
  function closestPrevByTop(elems, curY){ let t=null; for(const el of elems){const top=absTop(el); if(top<curY-8) t=el; else break;} return t; }
  function firstNextByTop(elems, curY){ for(const el of elems){const top=absTop(el); if(top>curY+8) return el;} return null; }
  function scrollPrevQ(){ const msgs=getUserMsgs(); const t=closestPrevByTop(msgs,y()); if(t) t.scrollIntoView({behavior:'smooth',block:'start'}); else scrollTop(); }
  function scrollNextQ(){ const msgs=getUserMsgs(); const t=firstNextByTop(msgs,y()); if(t) t.scrollIntoView({behavior:'smooth',block:'start'}); else scrollBottom(); }

  // --- gắn sự kiện cho 4 nút FAB (giữ nguyên) ---
  if (!window.__FAB_CLICK_BOUND__){
    window.__FAB_CLICK_BOUND__ = true;
    doc.addEventListener('click', function(ev){
      if (!ev.target || !ev.target.id) return;
      switch(ev.target.id){
        case 'fab-top':    scrollTop(); break;
        case 'fab-bottom': scrollBottom(); break;
        case 'fab-prev':   scrollPrevQ(); break;
        case 'fab-next':   scrollNextQ(); break;
      }
    }, {passive:true});
  }
})();
</script>
""",
    unsafe_allow_html=True,
)
