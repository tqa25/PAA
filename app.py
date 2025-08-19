import streamlit as st
from datetime import datetime
import backend

# ================== UI CONFIG ==================
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
                        sid = backend.new_session_id()
                        data["sessions"][sid] = {"name": backend.new_session_name(), "messages": []}
                        data["current_session"] = sid
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

    # Hiển thị hội thoại cũ
    for msg in session["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Tùy chọn bổ sung
    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        save_log = st.checkbox("\ud83d\udcdd Lưu nhật ký", key="save_log")
    with opt_col2:
        online_search = st.checkbox("\ud83d\udd0d Search online", key="online_search")

    # Nhập prompt mới
    if prompt := st.chat_input("Nhập tin nhắn và nhấn Enter..."):
        session["messages"].append({"role": "user", "content": prompt})
        if save_log:
            backend.log_user_activity(current_sid, prompt, model)
        backend.save_history(data)

        # Hiển thị input user ngay lập tức
        with st.chat_message("user"):
            st.markdown(prompt)

        if online_search:
            result = backend.search_online(prompt)
            with st.chat_message("assistant"):
                st.markdown(result)
            session["messages"].append({"role": "assistant", "content": result})
            backend.save_history(data)
            st.rerun()
        else:
            # Assistant stream
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_response = ""

                for chunk in backend.chat_with_model(model, session["messages"]):
                    token = chunk["message"]["content"]
                    full_response += token
                    placeholder.markdown(full_response)

            session["messages"].append({"role": "assistant", "content": full_response})
            backend.save_history(data)
            st.rerun()

# ================== CSS ==================
st.markdown("""
<style>
body, .stApp { background-color: #1e1f20 !important; color: #e3e3e3 !important; }
section[data-testid="stSidebar"] {
    background-color: #1e1f20 !important;
    color: #e3e3e3 !important;
    border-right: 1px solid #353739;
}
.stButton>button {
    background: #353739 !important;
    color: #e3e3e3 !important;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    margin-top: 6px;
    transition: background 0.2s;
    font-size: 14px;
    text-align: left;
}
.stButton>button:hover {
    background: #8ab4f8 !important;
    color: #131314 !important;
}
</style>
""", unsafe_allow_html=True)
