/* Chat front-end: sends the conversation to OUR server (/api/chat).
   The browser never sees or sends the Gemini API key. */

const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = form.querySelector("button");
const suggestions = document.getElementById("suggestions");

const history = []; // [{ role: "user" | "assistant", text }]

/* Add a chat bubble. textContent (not innerHTML) prevents HTML injection. */
function addMessage(role, text, isError = false) {
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "user" : "bot"}${isError ? " error" : ""}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.innerHTML = '<span class="typing" aria-label="Assistant is typing"><span></span><span></span><span></span></span>';
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

async function send(text) {
  text = text.trim();
  if (!text) return;

  addMessage("user", text);
  history.push({ role: "user", text });
  input.value = "";
  sendBtn.disabled = true;
  suggestions.hidden = true;
  const typing = showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history }),
    });
    const data = await res.json().catch(() => ({}));
    typing.remove();

    if (!res.ok || !data.reply) {
      addMessage("assistant", data.error || "Something went wrong. Please try again.", true);
      history.pop(); // let the user retry the same question
      return;
    }
    addMessage("assistant", data.reply);
    history.push({ role: "assistant", text: data.reply });
  } catch {
    typing.remove();
    addMessage("assistant", "Connection error. Is the server running?", true);
    history.pop();
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value);
});

suggestions.addEventListener("click", (e) => {
  if (e.target.matches("button")) send(e.target.textContent);
});

/* Greeting + demo-mode badge + deep links.
   A link like /?q=Do+you+have+vegan+dishes%3F asks that question on load
   (several ?q= are asked in order), so a website can link straight to an answer. */
(async function init() {
  addMessage("assistant", "Hi! 👋 I'm the Ember & Olive assistant. Ask me about our menu, opening hours or reservations.");
  try {
    const info = await (await fetch("/api/info")).json();
    document.getElementById("mode-badge").hidden = !info.demoMode;
  } catch { /* server offline: the first message will show the error */ }

  const questions = new URLSearchParams(location.search).getAll("q").slice(0, 3);
  for (const q of questions) await send(q.slice(0, 1000));
})();
