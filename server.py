"""Nova Bot - your own AI chat app.

Runs a small local server that shows the chat window (./app) and talks to
whichever AI "brain" you pick: free cloud AIs (Gemini, Groq, OpenRouter) or
models running on this PC through Ollama.

Your API keys, settings and chats are saved in %APPDATA%\\Nova Bot, never in
this folder, so they can't end up on GitHub.

    python server.py          start the server
    python server.py --open   start it and open the Nova Bot window
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.0.0"
HOST = "127.0.0.1"
PORT = 8765
OLLAMA = "http://127.0.0.1:11434"
HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
DATA_DIR = os.path.join(os.environ.get("APPDATA", HERE), "Nova Bot")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

DEFAULT_PERSONALITY = (
    "You are Nova, a personal AI assistant made by Nova Studios. "
    "Be direct and genuinely useful: answer what was asked, fully, without "
    "lecturing, moralising or piling on disclaimers. If you don't know "
    "something, say so plainly. Match the user's tone and keep answers as "
    "short as the question allows. Use Markdown for code and lists."
)

# Cloud AIs that speak the OpenAI chat format. Each has a free tier.
PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_url": "https://aistudio.google.com/apikey",
        "default_models": ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-2.5-pro", "gemini-3.5-flash-lite"],
    },
    "groq": {
        "name": "Groq",
        "base": "https://api.groq.com/openai/v1",
        "key_url": "https://console.groq.com/keys",
        "default_models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3-32b"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base": "https://openrouter.ai/api/v1",
        "key_url": "https://openrouter.ai/settings/keys",
        "default_models": [],
    },
}

# Model-name words that mean "not a chat model" (speech, images, embeddings...).
NOT_CHAT = ("tts", "image", "embedding", "live", "transcribe", "translate", "robotics",
            "veo", "lyria", "imagen", "whisper", "guard", "aqa", "banana", "audio", "omni")

_lock = threading.Lock()


# ---------- saved data ----------

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def load_settings():
    s = load_json(SETTINGS_FILE, {})
    s.setdefault("keys", {})
    s.setdefault("personality", DEFAULT_PERSONALITY)
    s.setdefault("temperature", 0.7)
    s.setdefault("model", "")
    s.setdefault("think", False)  # thinking is smarter but much slower on a home PC
    look = s.setdefault("look", {})
    look.setdefault("background", "art")
    look.setdefault("see", 0.65)   # 0 = solid panels, 1 = fully see-through
    look.setdefault("blur", 6)   # px of frosted-glass blur
    return s


def public_settings(s):
    """Settings for the window. Keys are only shown as 'set or not'."""
    return {
        "version": VERSION,
        "personality": s["personality"],
        "default_personality": DEFAULT_PERSONALITY,
        "temperature": s["temperature"],
        "model": s["model"],
        "think": s["think"],
        "look": s["look"],
        "providers": {
            pid: {"name": p["name"], "key_url": p["key_url"],
                  "has_key": bool(s["keys"].get(pid)),
                  "key_hint": ("..." + s["keys"][pid][-4:]) if s["keys"].get(pid) else ""}
            for pid, p in PROVIDERS.items()
        },
    }


# ---------- Ollama (models on this PC) ----------

def ollama_running():
    try:
        urllib.request.urlopen(OLLAMA + "/api/version", timeout=2)
        return True
    except Exception:
        return False


def start_ollama():
    if ollama_running():
        return
    exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if not os.path.exists(exe):
        exe = "ollama"
    try:
        subprocess.Popen([exe, "serve"],
                         creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return
    for _ in range(30):
        if ollama_running():
            return
        time.sleep(0.5)


# ---------- talking to the AIs ----------

def http_json(url, data=None, headers=None, timeout=20, method=None):
    req = urllib.request.Request(url, method=method or ("POST" if data is not None else "GET"))
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "NovaBot/" + VERSION)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    body = json.dumps(data).encode() if data is not None else None
    return urllib.request.urlopen(req, data=body, timeout=timeout)


def error_text(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            raw = e.read().decode("utf-8", "replace")
            j = json.loads(raw)
            if isinstance(j, list) and j:
                j = j[0]
            err = j.get("error", j)
            msg = err.get("message") if isinstance(err, dict) else str(err)
        except Exception:
            msg = e.reason
        if e.code == 429:
            return f"Daily/minute limit reached for this AI ({msg}). Try again later or pick another model."
        if e.code in (401, 403) or (e.code == 400 and "key" in str(msg).lower()):
            return f"The API key was refused ({msg}). Check it in Settings."
        return f"Error {e.code}: {msg}"
    if isinstance(e, urllib.error.URLError):
        return f"Couldn't connect ({e.reason}). Check your internet, or that Ollama is running."
    return str(e)


def list_models(settings):
    """Every model you can pick, grouped by where it runs."""
    groups = []

    def fetch_cloud(pid, p, key):
        try:
            with http_json(p["base"] + "/models", headers={"Authorization": "Bearer " + key}) as r:
                ids = [m.get("id", "") for m in json.load(r).get("data", [])]
            ids = [i.removeprefix("models/") for i in ids]
            ids = [i for i in ids if not any(w in i.lower() for w in NOT_CHAT)]
            if pid == "openrouter":
                ids = [i for i in ids if i.endswith(":free")]
            if pid == "gemini":
                ids = [i for i in ids if i.startswith("gemini")]
            # Put the recommended models first.
            ids = [m for m in p["default_models"] if m in ids] + sorted(i for i in ids if i not in p["default_models"])
            return {"id": pid, "name": p["name"], "models": ids or p["default_models"], "error": ""}
        except Exception as e:
            return {"id": pid, "name": p["name"], "models": p["default_models"], "error": error_text(e)}

    results = {}
    threads = []
    for pid, p in PROVIDERS.items():
        key = settings["keys"].get(pid)
        if key:
            t = threading.Thread(target=lambda pid=pid, p=p, key=key: results.__setitem__(pid, fetch_cloud(pid, p, key)))
            t.start()
            threads.append(t)

    local = {"id": "ollama", "name": "This PC (Ollama)", "models": [], "error": ""}
    try:
        with http_json(OLLAMA + "/api/tags", timeout=3) as r:
            local["models"] = sorted(m["name"] for m in json.load(r).get("models", []))
    except Exception:
        local["error"] = "Ollama isn't running."

    for t in threads:
        t.join()
    for pid in PROVIDERS:
        if pid in results:
            groups.append(results[pid])
    groups.append(local)
    return groups


def stream_chat(req, emit):
    """Send the conversation to the chosen AI and pass each piece back via emit()."""
    settings = load_settings()
    provider = req.get("provider")
    model = req.get("model")
    messages = [{"role": m["role"], "content": m["content"]} for m in req.get("messages", [])
                if m.get("role") in ("user", "assistant") and m.get("content")]
    personality = settings["personality"].strip()
    if personality:
        messages.insert(0, {"role": "system", "content": personality})
    temperature = float(settings["temperature"])

    if provider == "ollama":
        start_ollama()
        # Thinking models think by default, so say so either way.
        body = {"model": model, "messages": messages, "stream": True,
                "think": bool(settings["think"]), "options": {"temperature": temperature}}
        try:
            resp = http_json(OLLAMA + "/api/chat", body, timeout=900)
        except urllib.error.HTTPError as e:
            # Some models can't "think" at all; try again without the setting.
            if e.code == 400 and body.pop("think", None) is not None:
                resp = http_json(OLLAMA + "/api/chat", body, timeout=900)
            else:
                raise
        with resp:
            for line in resp:
                if not line.strip():
                    continue
                j = json.loads(line)
                if j.get("error"):
                    raise RuntimeError(j["error"])
                msg = j.get("message", {})
                if msg.get("thinking"):
                    emit({"type": "thinking", "content": msg["thinking"]})
                if msg.get("content"):
                    emit({"type": "text", "content": msg["content"]})
        return

    p = PROVIDERS.get(provider)
    if not p:
        raise RuntimeError("Pick a model first.")
    key = settings["keys"].get(provider)
    if not key:
        raise RuntimeError(f"Add your free {p['name']} key in Settings first.")
    body = {"model": model, "messages": messages, "stream": True, "temperature": temperature}
    headers = {"Authorization": "Bearer " + key}
    if provider == "openrouter":
        headers.update({"HTTP-Referer": "https://github.com/Acuz3D/nova-bot", "X-Title": "Nova Bot"})
    with http_json(p["base"] + "/chat/completions", body, headers=headers, timeout=900) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            j = json.loads(data)
            if j.get("error"):
                err = j["error"]
                raise RuntimeError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
            for choice in j.get("choices", []):
                delta = choice.get("delta", {})
                thinking = delta.get("reasoning") or delta.get("reasoning_content")
                if thinking:
                    emit({"type": "thinking", "content": thinking})
                if delta.get("content"):
                    emit({"type": "text", "content": delta["content"]})


def stream_pull(model, emit):
    """Download a model to this PC through Ollama, reporting progress."""
    start_ollama()
    with http_json(OLLAMA + "/api/pull", {"model": model, "stream": True}, timeout=None) as resp:
        for line in resp:
            if not line.strip():
                continue
            j = json.loads(line)
            if j.get("error"):
                raise RuntimeError(j["error"])
            emit({"type": "progress", "status": j.get("status", ""),
                  "completed": j.get("completed", 0), "total": j.get("total", 0)})


# ---------- first start: download a free, unlimited model that fits this PC ----------

AUTO = {"state": "idle", "model": "", "completed": 0, "total": 0, "error": ""}


def graphics_memory_gb():
    """Memory on the NVIDIA graphics card in GB, or 0 if there isn't one."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
        return max(int(x) for x in out.split()) / 1024
    except Exception:
        return 0


def best_model_for_this_pc():
    gb = graphics_memory_gb()
    if gb >= 22:
        return "qwen3.5:27b"
    if gb >= 7:
        return "qwen3.5:9b"
    return "qwen3.5:4b"


def auto_download():
    """If nothing is on this PC yet, download the best model for it, once."""
    start_ollama()
    if not ollama_running() or load_settings().get("auto_downloaded"):
        return
    try:
        with http_json(OLLAMA + "/api/tags", timeout=5) as r:
            if json.load(r).get("models"):
                return
    except Exception:
        return
    model = best_model_for_this_pc()
    AUTO.update(state="downloading", model=model, completed=0, total=0, error="")

    def progress(ev):
        if ev.get("total"):
            AUTO.update(completed=ev["completed"], total=ev["total"])

    try:
        stream_pull(model, progress)
    except Exception as e:
        AUTO.update(state="error", error=error_text(e))
        return
    with _lock:
        s = load_settings()
        s["auto_downloaded"] = True
        if not s["model"] or not any(s["keys"].values()):
            s["model"] = "ollama|" + model
        save_json(SETTINGS_FILE, s)
    AUTO.update(state="done")


# ---------- web server ----------

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def stream(self, work):
        """Send newline-separated JSON events while work(emit) runs.
        The reply simply ends when the connection closes (plain HTTP/1.0)."""
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()

        def emit(event):
            self.wfile.write((json.dumps(event) + "\n").encode())
            self.wfile.flush()

        try:
            work(emit)
            emit({"type": "done"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return  # the window pressed Stop
        except Exception as e:
            try:
                emit({"type": "error", "content": error_text(e)})
            except OSError:
                return

    def do_GET(self):
        if self.path == "/nova/settings":
            return self.send_json(public_settings(load_settings()))
        if self.path == "/nova/models":
            return self.send_json(list_models(load_settings()))
        if self.path == "/nova/chats":
            return self.send_json(load_json(CHATS_FILE, []))
        if self.path == "/nova/status":
            return self.send_json({"auto": AUTO, "ollama": ollama_running()})
        return super().do_GET()

    def do_POST(self):
        if self.path == "/nova/settings":
            changes = self.read_body()
            with _lock:
                s = load_settings()
                for pid, key in changes.get("keys", {}).items():
                    if pid in PROVIDERS:
                        key = (key or "").strip()
                        if key:
                            s["keys"][pid] = key
                        else:
                            s["keys"].pop(pid, None)
                for field in ("personality", "temperature", "model", "think", "look"):
                    if field in changes:
                        s[field] = changes[field]
                save_json(SETTINGS_FILE, s)
            return self.send_json(public_settings(s))
        if self.path == "/nova/chats":
            chats = self.read_body()
            with _lock:
                save_json(CHATS_FILE, chats)
            return self.send_json({"ok": True})
        if self.path == "/nova/chat":
            req = self.read_body()
            return self.stream(lambda emit: stream_chat(req, emit))
        if self.path == "/nova/pull":
            model = self.read_body().get("model", "").strip()
            return self.stream(lambda emit: stream_pull(model, emit))
        if self.path == "/nova/delete-model":
            model = self.read_body().get("model", "")
            try:
                http_json(OLLAMA + "/api/delete", {"model": model}, method="DELETE").close()
                return self.send_json({"ok": True})
            except Exception as e:
                return self.send_json({"error": error_text(e)}, 500)
        self.send_error(404)


def port_in_use():
    with socket.socket() as s:
        return s.connect_ex((HOST, PORT)) == 0


def open_window():
    url = f"http://{HOST}:{PORT}"
    for edge in EDGE_PATHS:
        if os.path.exists(edge):
            subprocess.Popen([edge, f"--app={url}", "--window-size=1200,840"])
            return
    import webbrowser
    webbrowser.open(url)


def main():
    want_window = "--open" in sys.argv
    if port_in_use():
        # Nova Bot is already running, so just open another window.
        if want_window:
            open_window()
        return
    threading.Thread(target=auto_download, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    if want_window:
        threading.Timer(0.6, open_window).start()
    print(f"Nova Bot {VERSION} running at http://{HOST}:{PORT}  (close this window to stop it)")
    server.serve_forever()


if __name__ == "__main__":
    main()
