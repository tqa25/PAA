from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from datetime import datetime
import json
import os
import backend
from datetime import date
import csv
from io import StringIO
import requests 

app = Flask(__name__, static_folder='static', static_url_path='/static')

def _ollama_ok():
    try:
        requests.get(f"{getattr(backend, 'OLLAMA_HOST', 'http://localhost:11434')}/api/tags", timeout=2)
        return True
    except Exception:
        return False

# ====== STATE: dùng lại backend.load_history/save_history ======
data = backend.migrate_journals(backend.load_history())  # ensure journals exist
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
    # Prevent renaming pinned journals
    if data["sessions"][sid].get("pinned"):
        return jsonify({"ok": False, "error": "pinned journal cannot be renamed"}), 400
    backend.rename_session(data, sid, new_name)
    backend.save_history(data)
    return jsonify({"ok": True})


@app.post("/api/session/clear")
def api_session_clear():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    if data["sessions"][sid].get("pinned"):
        return jsonify({"ok": False, "error": "pinned journal cannot be cleared"}), 400
    backend.clear_session_messages(data, sid)
    backend.save_history(data)
    return jsonify({"ok": True})


@app.post("/api/session/delete")
def api_session_delete():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    if sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    if data["sessions"][sid].get("pinned"):
        return jsonify({"ok": False, "error": "pinned journal cannot be deleted"}), 400

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

    # If this is a pinned journal session -> do NOT send to LLM. Log into user_logs.json instead.
    if session.get("pinned") and session.get("journal_tag"):
        tag = session.get("journal_tag")
        try:
            backend.log_user_activity(sid, prompt, model=None, tag=tag)
            # Also store in session history (tagged) for in-app viewing
            backend.append_message(session, "user", prompt)
            backend.append_message(session, "assistant", f"✅ Đã lưu nhật ký ({tag})")
            backend.save_history(data)
            def gen_done():
                yield json.dumps({"delta": ""}).encode() + b"\n"
                yield json.dumps({"done": True, "journal": True}).encode() + b"\n"
            return Response(stream_with_context(gen_done()), mimetype="application/x-ndjson")
        except Exception as e:
            backend.append_message(session, "assistant", f"⚠️ Lưu nhật ký thất bại: {e}")
            backend.save_history(data)
            def gen_err():
                yield json.dumps({"error": str(e)}).encode() + b"\n"
                yield json.dumps({"done": True, "journal": True}).encode() + b"\n"
            return Response(stream_with_context(gen_err()), mimetype="application/x-ndjson")

    if not model:
        return jsonify({"error": "no model selected"}), 400
    if not _ollama_ok():
        return jsonify({"error": "Ollama offline"}), 503

    # Append user message (auto-tag if journal)
    backend.append_message(session, "user", prompt)
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
        # Save assistant message (auto-tag if journal)
        backend.append_message(session, "assistant", full_resp)
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
    # Do not log pinned journal sessions into user_logs
    if sid and sid in data["sessions"] and data["sessions"][sid].get("pinned"):
        return jsonify({"ok": False, "error": "pinned journal is already stored in chat history (not logged)"}), 400
    try:
        backend.log_user_activity(sid or "-", message, model)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/journal/log")
def api_journal_log():
    payload = request.get_json(force=True)
    sid = payload.get("session_id")
    message = (payload.get("message") or "").strip()
    if not sid or sid not in data["sessions"]:
        return jsonify({"ok": False, "error": "invalid session"}), 400
    session = data["sessions"][sid]
    if not (session.get("pinned") and session.get("journal_tag")):
        return jsonify({"ok": False, "error": "not a journal session"}), 400
    if not message:
        return jsonify({"ok": False, "error": "empty message"}), 400
    tag = session.get("journal_tag")
    try:
        backend.log_user_activity(sid, message, model=None, tag=tag)
        backend.append_message(session, "user", message)
        backend.append_message(session, "assistant", f"✅ Đã lưu nhật ký ({tag})")
        backend.save_history(data)
        return jsonify({"ok": True, "tag": tag})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ====== JOURNAL EXPORT & SEARCH ======
@app.get("/api/journal/export")
def api_journal_export():
    tag = request.args.get("tag") or None
    from_s = request.args.get("from") or None
    to_s = request.args.get("to") or None
    fmt = (request.args.get("format") or "json").lower()
    from_date = date.fromisoformat(from_s) if from_s else None
    to_date = date.fromisoformat(to_s) if to_s else None
    rows = backend.filter_messages_by_tag_and_date(data, tag, from_date, to_date)
    if fmt == "csv":
        buf = StringIO()
        w = csv.DictWriter(buf, fieldnames=["session_id", "role", "content", "tag", "ts"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})
        return Response(buf.getvalue(), mimetype="text/csv")
    return jsonify(rows)

@app.get("/api/journal/search")
def api_journal_search():
    keyword = request.args.get("q") or ""
    session_id = request.args.get("session_id") or None
    tag = request.args.get("tag") or None
    if not keyword:
        return jsonify([])
    results = backend.search_messages(data, keyword, session_id=session_id, tag=tag)
    return jsonify(results)

@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")


if __name__ == "__main__":
    # Flask dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
