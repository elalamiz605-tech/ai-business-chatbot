"""Gemini REST client, with the network replaced by a fake."""

import pytest
import requests

from chatbot import gemini
from chatbot.gemini import GeminiError, generate_reply

HISTORY = [
    {"role": "user", "text": "Hi"},
    {"role": "assistant", "text": "Hello!"},
    {"role": "user", "text": "Menu?"},
]


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


def reply_with(parts):
    return {"candidates": [{"content": {"parts": parts}}]}


@pytest.fixture
def fake_post(monkeypatch):
    sent = {}

    def install(response=None, error=None):
        def post(url, headers, json, timeout):
            sent.update(url=url, headers=headers, json=json, timeout=timeout)
            if error:
                raise error
            return response

        monkeypatch.setattr(gemini.requests, "post", post)
        return sent

    return install


def test_builds_the_request_and_returns_the_text(fake_post):
    sent = fake_post(FakeResponse(data=reply_with([{"text": "Here is "}, {"text": "our menu. "}])))

    assert generate_reply("secret", "gemini-test", "SYSTEM", HISTORY) == "Here is our menu."

    assert sent["url"].endswith("/models/gemini-test:generateContent")
    assert sent["headers"]["x-goog-api-key"] == "secret"
    assert "secret" not in sent["url"]  # key goes in a header, never in the URL
    assert sent["json"]["system_instruction"]["parts"][0]["text"] == "SYSTEM"
    assert [c["role"] for c in sent["json"]["contents"]] == ["user", "model", "user"]
    assert sent["timeout"] == 30


def test_http_errors_raise_gemini_error(fake_post):
    fake_post(FakeResponse(status_code=429, text="quota exceeded"))
    with pytest.raises(GeminiError, match="429"):
        generate_reply("k", "m", "s", HISTORY)


def test_network_errors_raise_gemini_error(fake_post):
    fake_post(error=requests.ConnectionError("offline"))
    with pytest.raises(GeminiError, match="Network error"):
        generate_reply("k", "m", "s", HISTORY)


@pytest.mark.parametrize("data", [{}, {"candidates": []}, reply_with([{"text": "   "}])])
def test_empty_or_malformed_replies_raise_gemini_error(fake_post, data):
    fake_post(FakeResponse(data=data))
    with pytest.raises(GeminiError):
        generate_reply("k", "m", "s", HISTORY)
