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
    st.title("💬 Assistant (Ollama, Streaming)")

    # Lấy danh sách model
    try:
        models = [m["model"] for m in ollama.list().get("models", [])]
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        st.stop()

    if not models:
        st.error("Không tìm thấy model trong Ollama. Hãy chạy `ollama pull` trước.")
        st.stop()

    selected_model = st.selectbox("Chọn model", models, index=0)

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
                    model=selected_model,
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
