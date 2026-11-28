"""AI Business Chatbot: Flask server.

- Serves the chat page (static/).
- POST /api/chat forwards the conversation to Gemini with the business knowledge.
- The GEMINI_API_KEY is loaded from .env on the server and never sent to the browser.
- Without a key, the bot runs in "demo mode" with simple keyword answers.
"""

import logging
import os
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from chatbot.gemini import GeminiError, generate_reply
from chatbot.knowledge import build_system_prompt, demo_answer, load_business

load_dotenv()  # reads .env (ignored by Git) into environment variables

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()  # fast & cheap: ideal for customer chat
PORT = int(os.getenv("PORT", "5000"))

MAX_MESSAGE_CHARS = 1000   # longest message a visitor can send
MAX_HISTORY_TURNS = 12     # how much of the conversation is sent to the model
RATE_LIMIT = 20            # requests per IP...
RATE_WINDOW_SECONDS = 60   # ...per minute

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chatbot")

BUSINESS = load_business()
SYSTEM_PROMPT = build_system_prompt(BUSINESS)
DEMO_MODE = not API_KEY

app = Flask(__name__, static_folder="static", static_url_path="")

# Simple in-memory rate limiter (good enough for one small server)
_requests_by_ip: dict[str, deque] = defaultdict(deque)


def rate_limited(ip: str) -> bool:
    now = time.time()
    window = _requests_by_ip[ip]
    while window and now - window[0] > RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        return True
    window.append(now)
    return False


def clean_history(raw) -> list[dict] | None:
    """Validate the conversation sent by the browser. Returns None if invalid."""
    if not isinstance(raw, list) or not raw:
        return None
    history = []
    for turn in raw[-MAX_HISTORY_TURNS:]:
        if not isinstance(turn, dict):
            return None
        role, text = turn.get("role"), turn.get("text")
        if role not in ("user", "assistant") or not isinstance(text, str):
            return None
        text = text.strip()[:MAX_MESSAGE_CHARS]
        if text:
            history.append({"role": role, "text": text})
    if not history or history[-1]["role"] != "user":
        return None
    return history


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/info")
def info():
    """Public info for the page header (never includes the API key)."""
    return jsonify(name=BUSINESS["name"], demoMode=DEMO_MODE)


@app.post("/api/chat")
def chat():
    if rate_limited(request.remote_addr or "unknown"):
        return jsonify(error="Too many messages. Please wait a minute."), 429

    body = request.get_json(silent=True) or {}
    history = clean_history(body.get("history"))
    if history is None:
        return jsonify(error="Invalid request."), 400

    if DEMO_MODE:
        return jsonify(reply=demo_answer(history[-1]["text"], BUSINESS), demoMode=True)

    try:
        reply = generate_reply(API_KEY, MODEL, SYSTEM_PROMPT, history)
    except GeminiError as exc:
        log.error("Gemini call failed: %s", exc)
        return jsonify(error="The assistant is unavailable right now. Please try again later."), 502

    return jsonify(reply=reply, demoMode=False)


if __name__ == "__main__":
    if DEMO_MODE:
        log.warning("No GEMINI_API_KEY found: running in DEMO MODE (keyword answers only).")
    else:
        log.info("Gemini model: %s", MODEL)
    # debug=False: never expose the Flask debugger
    app.run(host="127.0.0.1", port=PORT, debug=False)
