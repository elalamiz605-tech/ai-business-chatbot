"""Minimal Gemini API client (REST, server-side only).

The API key is read from the environment by app.py and passed in here.
It is sent to Google in a request header, never to the browser."""

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    """Raised when the Gemini API call fails or returns no text."""


def generate_reply(api_key: str, model: str, system_prompt: str, history: list[dict], timeout: int = 30) -> str:
    """Send the conversation to Gemini and return the assistant's text reply.

    history: list of {"role": "user" | "assistant", "text": "..."} ending with the user's message.
    """
    contents = [
        {"role": "model" if turn["role"] == "assistant" else "user", "parts": [{"text": turn["text"]}]}
        for turn in history
    ]
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }

    try:
        response = requests.post(
            API_URL.format(model=model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        # Keep the API's message for the server log; the browser gets a generic error.
        raise GeminiError(f"Gemini API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError) as exc:
        raise GeminiError(f"Unexpected response: {str(data)[:300]}") from exc

    if not text:
        raise GeminiError("Empty reply from Gemini")
    return text
