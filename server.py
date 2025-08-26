from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from datetime import datetime
import json
import os
import backend
import requests 

app = Flask(__name__, static_folder='static', static_url_path='/static')

def _ollama_ok():
    try:
        requests.get(f"{getattr(backend, 'OLLAMA_HOST', 'http://localhost:11434')}/api/tags", timeout=2)
        return True
    except Exception:
        return False

# ====== STATE: dùng lại backend.load_history/save_history ======
data = backend.load_history()
if not data.get("sessions"):
    sid = backend.new_session_id()
    data["sessions"][sid] = {"name": backend.new_session_name(), "messages": []}
    data["current_session"] = sid
    backend.save_history(data)


def _get_session(sid: str):
    return data["sessions"].get(sid)


# ====== ROUTES: UI ======
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ====== ROUTES: MODELS ======
@app.get("/api/models")
def api_models():
    return jsonify({"models": backend.list_models()})


# ====== ROUTES: HISTORY (toàn bộ) ======
@app.get("/api/history")
def api_history():
    return jsonify(data)


# ====== ROUTES: SESSION CRUD ======
@app.post("/api/session/new")
def api_session_new():
    sid = backend.new_session_id()
    data["sessions"][sid] = {"name": backend.new_session_name(), "messages": [], "updated_at": datetime.now().isoformat()}
    data["current_session"] = sid
    backend.save_history(data)
    return jsonify({"ok": True, "session_id": sid})


@app.post("/api/session/select")
def api_session_select():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    data["current_session"] = sid
    backend.save_history(data)
    return jsonify({"ok": True})


@app.post("/api/session/rename")
def api_session_rename():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    new_name = payload.get("new_name") or ""
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    backend.rename_session(data, sid, new_name)
    backend.save_history(data)
    return jsonify({"ok": True})


@app.post("/api/session/clear")
def api_session_clear():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    backend.clear_session_messages(data, sid)
    backend.save_history(data)
    return jsonify({"ok": True})


@app.post("/api/session/delete")
def api_session_delete():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400

    # Xóa phiên, xử lý chuyển phiên hiện tại
    del data["sessions"][sid]
    if data.get("current_session") == sid:
        if data["sessions"]:
            data["current_session"] = list(data["sessions"].keys())[0]
        else:
            nsid = backend.new_session_id()
            data["sessions"][nsid] = {"name": backend.new_session_name(), "messages": []}
            data["current_session"] = nsid
    backend.save_history(data)
    return jsonify({"ok": True})


# ====== ROUTES: CHAT (stream NDJSON) ======
@app.post("/api/chat")
def api_chat():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    model = payload.get("model")
    prompt = (payload.get("prompt") or "").replace("\r\n", "\n").replace("\r", "\n")

    if sid not in data["sessions"]:
        return jsonify({"error": "invalid session"}), 400

    session = data["sessions"][sid]

    if not model:
        return jsonify({"error": "no model selected"}), 400
    if not _ollama_ok():
        return jsonify({"error": "Ollama offline"}), 503

    # Append user message
    session["messages"].append({"role": "user", "content": prompt})
    backend.save_history(data)

    def generate():
        full_resp = ""
        context = [m for m in session["messages"] if not m.get("log_only")]
        try:
            for chunk in backend.chat_with_model(model, context):
                token = chunk["message"]["content"]
                full_resp += token
                yield json.dumps({"delta": token}).encode() + b"\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}).encode() + b"\n"
        # Save assistant message
        session["messages"].append({"role": "assistant", "content": full_resp})
        session["updated_at"] = datetime.now().isoformat()
        backend.save_history(data)
        yield json.dumps({"done": True}).encode() + b"\n"

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


# ====== ROUTES: optional n8n search ======
@app.post("/api/search_online")
def api_search_online():
    payload = request.get_json(force=True)
    query = payload.get("query") or ""
    result = backend.search_online(query)
    return jsonify({"result": result})

# ====== ROUTES: logs (simple dump for 'Nhật ký') ======
@app.get("/api/logs")
def api_logs():
    try:
        if os.path.exists(backend.LOG_FILE):
            with open(backend.LOG_FILE, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/log")
def api_log():
    payload = request.get_json(force=True)
    message = (payload.get("message") or "").strip()
    sid = payload.get("session_id") or data.get("current_session")
    model = payload.get("model") or None
    if not message:
        return jsonify({"ok": False, "error": "empty message"}), 400
    try:
        backend.log_user_activity(sid or "-", message, model)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")


if __name__ == "__main__":
    # Flask dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
