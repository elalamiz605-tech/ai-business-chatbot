"""Business data, system prompt and demo-mode answers."""

import pytest

from chatbot.knowledge import build_system_prompt, demo_answer, load_business


def test_business_file_has_every_field_the_prompt_needs(business):
    for key in ("name", "type", "city", "address", "phone", "email", "website",
                "hours", "kitchen_note", "reservations", "menu", "policies"):
        assert business[key], f"missing or empty: {key}"


def test_load_business_reads_a_custom_file(tmp_path, business):
    custom = tmp_path / "shop.json"
    custom.write_text('{"name": "Café Luna"}', encoding="utf-8")
    assert load_business(custom) == {"name": "Café Luna"}


def test_system_prompt_contains_the_facts_and_the_rules(business):
    prompt = build_system_prompt(business)
    assert business["name"] in prompt
    assert business["phone"] in prompt
    for day, hours in business["hours"].items():
        assert f"{day}: {hours}" in prompt
    for item in business["menu"]["Mains"]:
        assert item in prompt
    assert "Never invent prices" in prompt
    assert "same language as the customer" in prompt


@pytest.mark.parametrize("question, expected", [
    ("What are your opening hours?", "opening hours"),
    ("¿Cuál es el horario?", "opening hours"),
    ("Quelle heure ouvrez-vous ?", "opening hours"),
    ("Can I book a table?", "book"),
    ("Do you have vegan dishes?", "vegan"),
    ("Where are you located?", "Calle"),
    ("Can I bring my dog?", "Dogs are welcome"),
    ("Do you take card?", "card"),
])
def test_demo_mode_answers_common_questions(business, question, expected):
    assert expected in demo_answer(question, business)


def test_demo_mode_vegan_answer_only_lists_tagged_dishes(business):
    reply = demo_answer("vegan options?", business)
    assert "Lamb skewers" not in reply


def test_demo_mode_falls_back_to_the_phone_number(business):
    reply = demo_answer("Tell me a joke", business)
    assert "demo mode" in reply
    assert business["phone"] in reply
