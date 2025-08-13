import streamlit as st
import ollama
import json
import os

HISTORY_FILE = "chat_history.json"

# --- Hàm lưu & tải lịch sử ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Lỗi lưu lịch sử: {e}")

# --- Hàm lấy danh sách model ---
def get_models():
    try:
        models_info = ollama.list()
        return [m["model"] for m in models_info["models"]]
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        return []

# --- Hàm preload model ---
def preload_model(model_name):
    try:
        ollama.chat(model=model_name, messages=[{"role": "system", "content": "Hi"}])
    except Exception as e:
        st.error(f"Lỗi preload model: {e}")

# --- Cấu hình trang ---
st.set_page_config(page_title="Assistant", layout="centered")

# --- Load lịch sử ---
if "messages" not in st.session_state:
    st.session_state.messages = load_history()

st.title("💬 Assistant (Streaming)")

# --- Dropdown chọn model ---
model_list = get_models()
if not model_list:
    st.stop()

selected_model = st.selectbox("Chọn model", model_list, index=0)

# Preload khi đổi model
if "last_model" not in st.session_state or st.session_state.last_model != selected_model:
    preload_model(selected_model)
    st.session_state.last_model = selected_model

# --- Hiển thị chat history ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- Ô nhập prompt ---
prompt = st.chat_input("Nhập tin nhắn...")

if prompt:
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            stream = ollama.chat(
                model=selected_model,
                messages=st.session_state.messages,
                stream=True
            )
            for chunk in stream:
                token = chunk["message"]["content"]
                full_response += token
                placeholder.write(full_response)
        except Exception as e:
            st.error(f"Lỗi khi gọi model: {e}")

        st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Lưu lịch sử
    save_history(st.session_state.messages)

# --- Nút xóa lịch sử ---
if st.button("🗑 Xóa lịch sử chat"):
    st.session_state.messages = []
    save_history([])
    st.experimental_rerun()
