"""
Tests for the rule-based engine and the RAG retrieval module.
These do NOT require the Flask app, login, or internet access.

Run with: python test_chatbot.py
"""

from chatbot import HealthChatbot
from rag import chunk_text, retrieve_relevant_chunks, build_rag_answer


def test_rules():
    bot = HealthChatbot()
    # (input, expected rule category) - checked against the matched rule's
    # category rather than substring-matching the response text, since
    # several rules have multiple randomly-chosen response variants.
    cases = [
        ("Hi there", "greeting"),
        ("I have a fever", "fever"),
        ("I have a headache", "headache"),
        ("I have a cough", "cough_cold"),
        ("my stomach hurts", "stomach"),
        ("tell me about covid symptoms", "covid"),
        ("give me diet tips", "diet"),
        ("what medicine should I take", "medicine_generic"),
        ("find a doctor near me", "nearby_doctor"),
        ("I have chest pain", "emergency"),
        ("asdkjqwe random text", None),
    ]

    passed = 0
    for user_input, expected_category in cases:
        matched_rule = bot._match_rule(user_input)
        actual_category = matched_rule["category"] if matched_rule else None
        ok = actual_category == expected_category
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        response_preview = bot.get_response(user_input)[:70]
        print(f"[{status}] '{user_input}' -> ({actual_category}) {response_preview}...")

    print(f"\nRule engine: {passed}/{len(cases)} tests passed.\n")
    return passed == len(cases)


def test_rag():
    sample_text = (
        "Diabetes management requires regular blood sugar monitoring. "
        "Patients should follow a low-sugar diet and exercise regularly. "
        "Metformin is a commonly prescribed medication for type 2 diabetes. "
        "Hypertension, or high blood pressure, is managed with lifestyle changes "
        "and medications such as ACE inhibitors. Regular checkups are important "
        "for both diabetes and hypertension patients to avoid complications."
    )

    chunks = chunk_text(sample_text, chunk_size=100, overlap=20)
    assert len(chunks) > 1, "Chunking should produce multiple chunks for this text"

    results = retrieve_relevant_chunks("what medication treats diabetes?", chunks)
    found_metformin = any("metformin" in c.lower() for c, _ in results)

    answer = build_rag_answer("how is hypertension managed?", chunks)
    ok = found_metformin and answer is not None and "blood pressure" in answer.lower()

    print(f"[{'PASS' if ok else 'FAIL'}] RAG retrieval finds relevant chunks")
    print(f"\nRAG module: {'PASS' if ok else 'FAIL'}\n")
    return ok


if __name__ == "__main__":
    r1 = test_rules()
    r2 = test_rag()
    print("ALL TESTS PASSED" if (r1 and r2) else "SOME TESTS FAILED")
