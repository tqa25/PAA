import streamlit as st
import ollama
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
import json
import os

# ==============================
# 🔒 Lấy mật khẩu từ secrets
# ==============================
PASSWORD = st.secrets.get("app_password", None)
COOKIE_KEY = st.secrets.get("cookie_key", None)

if not PASSWORD:
    st.error("Không tìm thấy 'app_password' trong secrets.toml")
    st.stop()

if not COOKIE_KEY:
    st.error("Không tìm thấy 'cookie_key' trong secrets.toml")
    st.stop()

# Hash mật khẩu
hashed_passwords = Hasher.hash_list([PASSWORD])

# ==============================
# 🛠 Cấu hình xác thực
# ==============================
config = {
    "credentials": {
        "usernames": {
            "user": {
                "name": "User",
                "password": hashed_passwords[0]
            }
        }
    },
    "cookie": {
        "name": "assistant_ai_cookie",
        "key": COOKIE_KEY,
        "expiry_days": 1
    }
}

# Khởi tạo Authenticator
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

# ==============================
# 🚪 Login
# ==============================
authenticator.login(location="main")
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if auth_status:
    # Sidebar menu
    with st.sidebar:
        st.markdown(
            """
            <style>
            /* Đảm bảo sidebar đủ rộng và các phần tử full width */
            .sidebar-title {font-size: 20px; font-weight: bold; margin-bottom: 16px;}
            .sidebar-menu {list-style: none; padding-left: 0;}
            .sidebar-menu li {
                width: 100% !important;
                box-sizing: border-box;
                padding: 0 0 0 0 !important;
                border-radius: 6px;
                margin-bottom: 12px;
                cursor: pointer;
                color: #131314;
                background: #8ab4f8;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                font-weight: 500;
                transition: background 0.2s;
                margin-left: 0 !important;
            }
            .sidebar-menu li.active, .sidebar-menu li:hover {
                background-color: #8ab4f8 !important;
                color: #131314 !important;
            }
            /* Đồng bộ chiều ngang với selectbox */
            .stSelectbox, .stSelectbox>div {
                width: 100% !important;
                min-width: 0 !important;
            }
            /* Ẩn label selectbox nếu muốn */
            label[for="sidebar_model"] {display: none;}
            /* Canh lề trái cho cả selectbox và menu */
            .stSelectbox, .sidebar-menu {margin-left: 0 !important;}
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown('<div class="sidebar-title"><i class="fas fa-robot"></i> Menu </div>', unsafe_allow_html=True)

        # Chọn model - chuyển vào đây
        try:
            models = [m["model"] for m in ollama.list().get("models", [])]
        except Exception as e:
            st.error(f"Lỗi lấy danh sách model: {e}")
            st.stop()

        if not models:
            st.error("Không tìm thấy model trong Ollama. Hãy chạy `ollama pull` trước.")
            st.stop()

        selected_model = st.selectbox("Chọn model", models, index=0, key="sidebar_model")

        st.markdown(
            """
            <ul class="sidebar-menu">
                <li class="active"><i class="fas fa-comment-dots"></i> Nói cái khác với Hân</li>
            </ul>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div class="sidebar-history">
                <h3>Lịch sử</h3>
                <ul>
                    <li class="active">Cập Nhật UI Và Lỗi</li>
                    <li>Office Leasing Data Req...</li>
                    <li>Từ Chối Dịch Vụ Nội Thất...</li>
                    <li>Công Thức Xác Định Cấp...</li>
                    <li>Cuộc gọi bán hàng bất đ...</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("---")
        st.button("Đăng xuất", on_click=lambda: authenticator.logout("main"))

    st.title("💬 Nói Chuyện Với Hân")

    # Load lịch sử chat
    history_file = st.secrets.get("history_file", "chat_history.json")
    if "messages" not in st.session_state:
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
        else:
            st.session_state.messages = []

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

        # Giới hạn số lượng message để tránh file quá nặng (vd 200 tin cuối)
        MAX_MESSAGES = 200
        if len(st.session_state.messages) > MAX_MESSAGES:
            st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

        # Lưu lịch sử chat
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

    # Nút đăng xuất
    authenticator.logout(location="main")

elif auth_status is False:
    st.error("Sai tài khoản hoặc mật khẩu")
elif auth_status is None:
    st.warning("Vui lòng nhập thông tin đăng nhập")

st.markdown(
    """
    <style>
    /* Màu nền tổng thể cho toàn bộ app */
    body, .stApp {
        background-color: #1e1f20 !important;
        color: #e3e3e3 !important;
    }
    /* Sidebar đồng bộ màu */
    section[data-testid="stSidebar"] {
        background-color: #1e1f20 !important;
        color: #e3e3e3 !important;
        border-right: 1px solid #353739;
    }
    /* Các phần tử trong sidebar */
    .sidebar-title, .sidebar-menu li, .sidebar-history li {
        color: #e3e3e3 !important;
    }
    .sidebar-menu li.active, .sidebar-menu li:hover {
        background-color: #8ab4f8 !important;
        color: #131314 !important;
    }
    .sidebar-history li.active, .sidebar-history li:hover {
        background-color: #353739 !important;
        color: #fff !important;
    }
    /* Nút đăng xuất */
    .stButton>button {
        background: #353739 !important;
        color: #e3e3e3 !important;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        margin-top: 16px;
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
