import json
import os
import uuid
from datetime import datetime
import ollama

HISTORY_FILE = "chat_history.json"

# -----------------------------
# Quản lý lịch sử chat
# -----------------------------
def load_history():
    """Đọc dữ liệu chat_history.json từ file.
    Nếu file không tồn tại hoặc hỏng → tạo mới."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "sessions" in data and "current_session" in data:
                    return data
        except Exception:
            pass
    # Tạo dữ liệu mặc định
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
    """Ghi dữ liệu chat vào file JSON."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def new_session_name():
    """Tạo tên mặc định cho phiên mới."""
    return f"Phiên mới {datetime.now().strftime('%H:%M:%S')}"

def new_session_id():
    """Sinh UUID mới cho session ID."""
    return str(uuid.uuid4())

# -----------------------------
# Hành động trên session
# -----------------------------
def clear_session_messages(data, sid):
    """Xoá toàn bộ message trong một session."""
    if sid in data["sessions"]:
        data["sessions"][sid]["messages"] = []
        data["sessions"][sid]["updated_at"] = datetime.now().isoformat()
    return data

def rename_session(data, sid, new_name):
    """Đổi tên session hiện tại."""
    if sid in data["sessions"]:
        data["sessions"][sid]["name"] = new_name
        data["sessions"][sid]["updated_at"] = datetime.now().isoformat()
    return data

# -----------------------------
# Gọi model Ollama
# -----------------------------
def chat_with_model(model, messages):
    """Trả về phản hồi từ model Ollama (streaming)."""
    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True
    )
    return stream
