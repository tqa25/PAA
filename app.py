import streamlit as st
import ollama
import json
import os

# ==========================
# 🔒 Đọc cấu hình bảo mật từ secrets
# ==========================
PASSWORD = st.secrets.get("app_password", None)
HISTORY_FILE = st.secrets.get("history_file", "chat_history.json")

st.set_page_config(page_title="Assistant", layout="centered")

# Nếu chưa cấu hình mật khẩu -> chặn chạy
if not PASSWORD:
    st.error("Chưa cấu hình mật khẩu. Thêm app_password vào .streamlit/secrets.toml rồi chạy lại.")
    st.stop()

# ==========================
# 🔐 Màn hình đăng nhập
# ==========================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔑 Đăng nhập")
    pwd = st.text_input("Nhập mật khẩu:", type="password")
    if st.button("Đăng nhập", type="primary"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Sai mật khẩu!")
    st.stop()

# ==========================
# 📂 Lịch sử chat (lưu file JSON)
# ==========================
def load_history(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(path, history):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Lỗi lưu lịch sử: {e}")

# ==========================
# 🧠 Model list & preload
# ==========================
def get_models():
    try:
        info = ollama.list()
        return [m["model"] for m in info.get("models", [])]
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        return []

def preload_model(model_name):
    try:
        # ping nhẹ để model warm-up
        ollama.chat(model=model_name, messages=[{"role": "system", "content": "ping"}])
    except Exception as e:
        st.error(f"Lỗi preload model: {e}")

# ==========================
# 🚀 UI chính
# ==========================
if "messages" not in st.session_state:
    st.session_state.messages = load_history(HISTORY_FILE)

st.title("💬 Assistant (Ollama, Streaming)")

# Chọn model đang có
models = get_models()
if not models:
    st.error("Không tìm thấy model trong Ollama. Hãy chạy ollama pull trước.")
    st.stop()

selected_model = st.selectbox("Chọn model", models, index=0)

# Preload khi đổi model
if st.session_state.get("last_model") != selected_model:
    preload_model(selected_model)
    st.session_state.last_model = selected_model

# Hiển thị lịch sử
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Ô nhập prompt (Enter để gửi)
prompt = st.chat_input("Nhập tin nhắn và nhấn Enter...")

if prompt:
    # Lưu và hiển thị tin nhắn người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Stream phản hồi
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

    # Lưu lịch sử ra file
    save_history(HISTORY_FILE, st.session_state.messages)

# Thanh tiện ích
col1, col2 = st.columns(2)
with col1:
    if st.button("🗑 Xóa lịch sử chat"):
        st.session_state.messages = []
        save_history(HISTORY_FILE, [])
        st.rerun()
with col2:
    if st.button("🚪 Đăng xuất"):
        st.session_state.authenticated = False
        st.rerun()
