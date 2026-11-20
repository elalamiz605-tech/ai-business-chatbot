"""Business knowledge: loads data/business.json and turns it into
(1) a system prompt for Gemini and (2) simple offline answers for demo mode."""

import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "business.json"


def load_business(path: Path = DATA_FILE) -> dict:
    """Read the business profile (name, hours, menu, policies...)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(biz: dict) -> str:
    """Instructions given to the model: who it is, what it knows, and its limits."""
    hours = "\n".join(f"- {day}: {time}" for day, time in biz["hours"].items())
    menu = "\n".join(
        f"{section}:\n" + "\n".join(f"  - {item}" for item in items)
        for section, items in biz["menu"].items()
    )
    policies = "\n".join(f"- {p}" for p in biz["policies"])

    return f"""You are the friendly customer assistant of {biz['name']}, a {biz['type']} in {biz['city']}.

RULES
- Answer ONLY with the information below. If the answer is not there, say you don't know and
  suggest contacting the restaurant by phone ({biz['phone']}) or email ({biz['email']}).
- Never invent prices, dishes, opening hours, discounts or availability.
- You cannot make or confirm reservations yourself: explain how to book.
- Politely refuse questions unrelated to the restaurant.
- Reply in the same language as the customer (English, Spanish, French...).
- Keep answers short (1 to 4 sentences, or a short list). Plain text only, no markdown.

BUSINESS INFORMATION
Address: {biz['address']}
Phone: {biz['phone']}
Email: {biz['email']}
Website: {biz['website']}

Opening hours:
{hours}
{biz['kitchen_note']}

Reservations: {biz['reservations']}

Menu (prices in euros):
{menu}

Policies:
{policies}
"""


# ---------------------------------------------------------------------------
# Demo mode: keyword-based answers used when no GEMINI_API_KEY is configured,
# so the project can be tried (and screenshotted) without an API key.
# ---------------------------------------------------------------------------
def demo_answer(message: str, biz: dict) -> str:
    text = message.lower()

    def has(*words: str) -> bool:
        return any(w in text for w in words)

    if has("hour", "open", "close", "horario", "abierto", "heure", "ouvert"):
        lines = ", ".join(f"{d}: {t}" for d, t in biz["hours"].items())
        return f"Our opening hours are: {lines}. {biz['kitchen_note']}"
    if has("book", "reserv", "table"):
        return biz["reservations"]
    if has("vegan", "vegetarian", "gluten", "allerg", "végé", "vegano"):
        options = [i for items in biz["menu"].values() for i in items if "vegan" in i or "vegetarian" in i]
        return "Vegetarian and vegan options include: " + "; ".join(options) + ". Please tell our staff about any allergies."
    if has("menu", "dish", "food", "eat", "price", "carta", "plat"):
        mains = "; ".join(biz["menu"]["Mains"])
        return f"Our mains are: {mains}. We also have starters, desserts and drinks."
    if has("where", "address", "locat", "metro", "dónde", "adresse"):
        return f"We are at {biz['address']}."
    if has("dog", "pet", "perro", "chien"):
        return "Dogs are welcome on our terrace."
    if has("pay", "card", "cash", "tarjeta", "carte"):
        return "We accept card and contactless payments."
    return (
        "I'm running in demo mode (no AI key configured), so I can only answer simple questions "
        "about opening hours, the menu, reservations, location and dietary options. "
        f"For anything else, please call {biz['phone']}."
    )
