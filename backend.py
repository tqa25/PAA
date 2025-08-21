import json
import os
from datetime import datetime

try:
    import ollama  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    ollama = None

try:  # Optional dependency for n8n integration
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    requests = None

DATA_FILE = "chat_history.json"
LOG_FILE = "user_logs.json"
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")

# ================== HISTORY ==================

def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": {}, "current_session": None}

def save_history(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def new_session_id():
    return str(datetime.now().timestamp())

def new_session_name():
    return f"Phiên mới {datetime.now().strftime('%H:%M:%S')}"

def rename_session(data, sid, new_name):
    if sid in data["sessions"]:
        data["sessions"][sid]["name"] = new_name
    return data

def clear_session_messages(data, sid):
    if sid in data["sessions"]:
        data["sessions"][sid]["messages"] = []
    return data


# ================== LOGGING ==================

def log_user_activity(session_id: str, message: str, model: str | None = None) -> None:
    """Append a user action to the log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "model": model,
        "message": message,
    }

    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []

    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


# ================== OLLAMA ==================

def list_models():
    """Trả về danh sách model có trong Ollama với multiple fallback methods."""

    # Method 1: Thử ollama.list() API nếu thư viện tồn tại
    if ollama is not None:
        try:
            result = ollama.list()

            # Case 1: Result is dict with 'models' key
            if isinstance(result, dict) and "models" in result:
                models = []
                for model in result["models"]:
                    if isinstance(model, dict):
                        # Thử các key có thể có: name, model, id
                        model_name = model.get("name") or model.get("model") or model.get("id")
                        if model_name:
                            models.append(model_name)
                    elif isinstance(model, str):
                        models.append(model)

                if models:
                    return models

            # Case 2: Result has .models attribute
            elif hasattr(result, "models"):
                models = []
                for model in result.models:
                    if hasattr(model, "name"):
                        models.append(model.name)
                    elif isinstance(model, dict):
                        model_name = model.get("name") or model.get("model")
                        if model_name:
                            models.append(model_name)

                if models:
                    return models

        except Exception as e:
            print(f"ollama.list() failed: {e}")
    
    # Method 2: Fallback to command line
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            models = []
            
            # Parse output: "NAME    ID    SIZE    MODIFIED"
            for line in lines[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]  # First column
                    if model_name and model_name != "NAME":
                        models.append(model_name)
            
            if models:
                return models
                
    except Exception as e:
        print(f"CLI fallback failed: {e}")
    
    # Method 3: Default models
    return ["llama3.2:3b", "llama3.1:8b"]



def chat_with_model(model, messages):
    """Stream phản hồi từ LLM."""
    if ollama is None:
        yield {"message": {"role": "assistant", "content": "⚠️ Lỗi: thư viện ollama chưa được cài đặt"}}
        return
    try:
        response = ollama.chat(model=model, messages=messages, stream=True)
        for chunk in response:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk
    except Exception as e:
        yield {"message": {"role": "assistant", "content": f"⚠️ Lỗi: {e}"}}


# ================== N8N SEARCH ==================

def search_online(query: str) -> str:
    """Search online via n8n self-host webhook."""
    if not N8N_WEBHOOK_URL:
        return "⚠️ N8N_WEBHOOK_URL chưa được cấu hình"
    payload = {"query": query}
    try:
        if requests is not None:
            resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        else:  # Fallback to urllib if requests is missing
            import urllib.request
            req = urllib.request.Request(
                N8N_WEBHOOK_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as f:  # type: ignore[attr-defined]
                data = json.load(f)
        return data.get("result") or data.get("text") or json.dumps(data)
    except Exception as e:  # pragma: no cover - network operations
        return f"⚠️ Search failed: {e}"
