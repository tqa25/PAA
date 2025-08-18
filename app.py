import streamlit as st
import backend
from datetime import datetime

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### Menu")

    # Lấy danh sách model từ Ollama
    try:
        models = [m["model"] for m in backend.ollama.list().get("models", [])]
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        st.stop()

    if not models:
        st.error("Không tìm thấy model trong Ollama. Hãy chạy `ollama pull` trước.")
        st.stop()

    selected_model = st.selectbox("Chọn model", models, index=0, key="sidebar_model")

    # Tải dữ liệu lịch sử
    data = backend.load_history()
    sessions = data.get("sessions", {})
    current_sid = data.get("current_session")

    # Nút tạo phiên mới
    if st.button("➕ Nói chuyện khác với Hân", use_container_width=True):
        sid = backend.new_session_id()
        data["sessions"][sid] = {
            "name": backend.new_session_name(),
            "messages": [],
            "updated_at": datetime.now().isoformat()
        }
        data["current_session"] = sid
        backend.save_history(data)
        st.session_state.messages = []
        st.rerun()

    # -----------------------------
    # Collapse/Expand danh sách history
    # -----------------------------
    with st.expander("🕑 Lịch sử", expanded=True):
        for sid, sess in sessions.items():
            # Dùng CSS custom để đảm bảo không wrap xuống hàng
            st.markdown(
                f"""
                <div class="session-row">
                    <div class="session-name">
                        <form action="?session={sid}" method="get">
                            <button class="session-btn">{sess['name']}</button>
                        </form>
                    </div>
                    <div class="session-menu">
                        """,
                unsafe_allow_html=True,
            )

            # Popover menu ẩn trong nút ⋮
            with st.popover(""):
                st.markdown(f"**Tùy chọn cho {sess['name']}**")

                # Rename
                new_name = st.text_input("Đổi tên", value=sess["name"], key=f"rename_{sid}")
                if st.button("Lưu tên", key=f"rename_btn_{sid}"):
                    data = backend.rename_session(data, sid, new_name)
                    backend.save_history(data)
                    st.rerun()

                # Clear history
                if st.button("Xoá nội dung", key=f"clear_{sid}"):
                    data = backend.clear_session_messages(data, sid)
                    backend.save_history(data)
                    if sid == current_sid:
                        st.session_state.messages = []
                    st.rerun()

                # Delete session
                if st.button("Xoá phiên", key=f"delete_{sid}"):
                    if sid in data["sessions"]:
                        del data["sessions"][sid]
                        if sid == current_sid and data["sessions"]:
                            data["current_session"] = list(data["sessions"].keys())[0]
                        backend.save_history(data)
                        st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)

# -----------------------------
# Main Chat UI
# -----------------------------
# Load messages của phiên hiện tại
if "messages" not in st.session_state or st.session_state.get("last_sid") != current_sid:
    st.session_state.messages = sessions.get(current_sid, {}).get("messages", [])
    st.session_state["last_sid"] = current_sid

st.title("💬 Nói Chuyện Với Hân")

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Ô nhập chat
prompt = st.chat_input("Nhập tin nhắn và nhấn Enter...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        try:
            stream = backend.chat_with_model(
                model=st.session_state.get("sidebar_model", models[0]),
                messages=st.session_state.messages
            )
            for chunk in stream:
                token = chunk["message"]["content"]
                full += token
                placeholder.write(full)
        except Exception as e:
            st.error(f"Lỗi khi gọi model: {e}")
        st.session_state.messages.append({"role": "assistant", "content": full})

    # Giới hạn số lượng message
    MAX_MESSAGES = 200
    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

    # Lưu lịch sử chat
    data = backend.load_history()
    if current_sid in data["sessions"]:
        data["sessions"][current_sid]["messages"] = st.session_state.messages
        data["sessions"][current_sid]["updated_at"] = datetime.now().isoformat()
        backend.save_history(data)

# -----------------------------
# CSS: nền tối + responsive row
# -----------------------------
st.markdown(
    """
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

    /* Giữ session row luôn ngang */
    .session-row {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        gap: 6px;
        white-space: nowrap;
    }
    .session-name {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .session-btn {
        width: 100%;
        background: #353739;
        border: none;
        color: #e3e3e3;
        padding: 6px 10px;
        border-radius: 6px;
        text-align: left;
        cursor: pointer;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .session-btn:hover {
        background: #8ab4f8;
        color: #131314;
    }
    .session-menu {
        flex-shrink: 0;
        display: inline-block;
    }
    /* ép popover nút ⋮ chỉ chiếm vừa icon */
    div[data-baseweb="popover"] {
        display: inline-block !important;
        width: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

