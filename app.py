import streamlit as st
import ollama
import json
import os
import uuid
from datetime import datetime

# ==============================
# Cấu hình file lưu lịch sử chat
# ==============================
HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "sessions" in data and "current_session" in data:
                    return data
        except Exception:
            pass
    # Nếu chưa có file hoặc lỗi, tạo cấu trúc mặc định
    sid = str(uuid.uuid4())
    return {
        "sessions": {
            sid: {
                "name": f"Phiên mới {datetime.now().strftime('%H:%M:%S')}",
                "messages": [],
                "updated_at": datetime.now().isoformat()
            }
        },
        "current_session": sid
    }

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def new_session_name():
    return f"Phiên mới {datetime.now().strftime('%H:%M:%S')}"

def new_session_id():
    return str(uuid.uuid4())

# ==============================
# Sidebar Menu
# ==============================
with st.sidebar:
    st.markdown("### Menu")

    # Lấy danh sách model từ Ollama
    try:
        models = [m["model"] for m in ollama.list().get("models", [])]
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        st.stop()

    if not models:
        st.error("Không tìm thấy model trong Ollama. Hãy chạy `ollama pull` trước.")
        st.stop()

    selected_model = st.selectbox("Chọn model", models, index=0, key="sidebar_model")

    # Tải dữ liệu lịch sử
    data = load_history()
    sessions = data.get("sessions", {})
    current_sid = data.get("current_session")

    # Nút tạo phiên mới
    if st.button("Nói cái khác với Hân", use_container_width=True):
        sid = new_session_id()
        data["sessions"][sid] = {
            "name": new_session_name(),
            "messages": [],
            "updated_at": datetime.now().isoformat()
        }
        data["current_session"] = sid
        save_history(data)
        st.session_state.messages = []
        st.rerun()

    # Danh sách phiên
    st.markdown("#### Lịch sử")
    for sid, sess in sessions.items():
        if st.button(sess["name"], key=f"session_{sid}", use_container_width=True):
            data["current_session"] = sid
            save_history(data)
            st.rerun()

    st.markdown("---")
    # 📝 Chỗ này trước kia render nút Đăng xuất
    # if st.button("Đăng xuất", use_container_width=True):
    #     # logic logout
    #     pass

# ==============================
# Main Chat UI
# ==============================
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
            stream = ollama.chat(
                model=st.session_state.get("sidebar_model", models[0]),
                messages=st.session_state.messages,
                stream=True
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
    data = load_history()
    if current_sid in data["sessions"]:
        data["sessions"][current_sid]["messages"] = st.session_state.messages
        data["sessions"][current_sid]["updated_at"] = datetime.now().isoformat()
        save_history(data)

# ==============================
# CSS nền tối
# ==============================
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
        padding: 8px 16px;
        margin-top: 8px;
        transition: background 0.2s;
    }
    .stButton>button:hover {
        background: #8ab4f8 !important;
        color: #131314 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
