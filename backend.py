import json
import os
from datetime import datetime, date
from typing import Dict, Any, List

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

# ====== Pinned journal session definitions (fixed IDs) ======
JOURNAL_DEFS = [
    {"id": "journal_workout", "name": "🏋️ Workout Journal", "journal_tag": "workout"},
    {"id": "journal_eat", "name": "🍽️ Eat Journal", "journal_tag": "eat"},
    {"id": "journal_daily", "name": "📓 Daily Journal", "journal_tag": "daily"},
]
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


# ================== JOURNAL SEED / MIGRATION ==================
def migrate_journals(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure 3 pinned journal sessions exist. Do not overwrite existing messages.
    Adds metadata: pinned=True, journal_tag=<tag>."""
    sessions = data.setdefault("sessions", {})
    changed = False
    for jd in JOURNAL_DEFS:
        sid = jd["id"]
        if sid not in sessions:
            # Create new pinned journal session
            sessions[sid] = {
                "name": jd["name"],
                "messages": [],
                "pinned": True,
                "journal_tag": jd["journal_tag"],
                "updated_at": datetime.now().isoformat(),
            }
            changed = True
        else:
            # Ensure metadata exists
            sess = sessions[sid]
            if not sess.get("pinned"):
                sess["pinned"] = True; changed = True
            if sess.get("journal_tag") != jd["journal_tag"]:
                sess["journal_tag"] = jd["journal_tag"]; changed = True
            if not sess.get("name"):
                sess["name"] = jd["name"]; changed = True
    if changed:
        save_history(data)
    return data


def is_journal_session(session: Dict[str, Any]) -> bool:
    return bool(session.get("pinned") and session.get("journal_tag"))


def append_message(session: Dict[str, Any], role: str, content: str):
    """Helper to append a message with timestamp (+ tag if journal)."""
    msg = {"role": role, "content": content, "ts": datetime.now().isoformat()}
    if is_journal_session(session):  # auto tag
        msg["tag"] = session.get("journal_tag")
    session.setdefault("messages", []).append(msg)
    # update updated_at for sorting (also journals)
    session["updated_at"] = msg["ts"]


def iter_messages(data: Dict[str, Any], tag: str | None = None):
    """Iterate all messages across sessions optionally filtered by tag."""
    for sid, sess in data.get("sessions", {}).items():
        for m in sess.get("messages", []):
            if tag and m.get("tag") != tag:
                continue
            yield sid, m


def filter_messages_by_tag_and_date(data: Dict[str, Any], tag: str | None, from_date: date | None, to_date: date | None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sid, m in iter_messages(data, tag):
        ts = m.get("ts")
        if not ts:
            continue
        try:
            d = datetime.fromisoformat(ts).date()
        except Exception:
            continue
        if from_date and d < from_date:
            continue
        if to_date and d > to_date:
            continue
        row = {"session_id": sid, **m}
        out.append(row)
    return out


def search_messages(data: Dict[str, Any], keyword: str, session_id: str | None = None, tag: str | None = None) -> List[Dict[str, Any]]:
    key = keyword.lower()
    results: List[Dict[str, Any]] = []
    sessions_iter = (
        ((session_id, data["sessions"].get(session_id)) ,) if session_id and session_id in data.get("sessions", {}) else data.get("sessions", {}).items()
    )
    for sid, sess in sessions_iter:
        if not sess:
            continue
        for idx, m in enumerate(sess.get("messages", [])):
            if tag and m.get("tag") != tag:
                continue
            if key in (m.get("content") or "").lower():
                results.append({"session_id": sid, "index": idx, **m})
    return results


# ================== LOGGING ==================

def log_user_activity(session_id: str, message: str, model: str | None = None, tag: str | None = None) -> None:
    """Append a user action (journal or generic) to the log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "model": model,
        "message": message,
        **({"tag": tag} if tag else {}),
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
