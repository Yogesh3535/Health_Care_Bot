"""
Rule-Based Health Chatbot - Core Engine
-----------------------------------------
Regex/keyword rule matching -> health advice + general OTC medicine names.
Also exposes helper to merge in RAG (document-based) answers.

IMPORTANT: Medicine names returned here are GENERAL, COMMONLY-KNOWN OTC
information only (not a prescription, not dosage guidance). Always shown
with a disclaimer. This is for educational/demo purposes.
"""

import re
import random


class HealthChatbot:
    def __init__(self):
        self.name = "HealthBot"

        # Each rule: category, patterns, responses, optional otc medicines list
        self.rules = [
            dict(
                category="greeting",
                patterns=[r"\b(hi|hello|hey|good morning|good evening|good afternoon)\b"],
                responses=[
                    "Hello! I'm {bot}, your health assistant. How can I help you today?",
                    "Hi there! Ask me about symptoms, medicines, nearby doctors, or upload a "
                    "medical PDF and ask me questions about it.",
                ],
            ),
            dict(
                category="farewell",
                patterns=[r"\b(bye|goodbye|see you|exit|quit)\b"],
                responses=["Take care! Remember to consult a doctor for serious concerns. Goodbye!"],
            ),
            dict(
                category="thanks",
                patterns=[r"\b(thanks|thank you|thx)\b"],
                responses=["You're welcome! Let me know if you have any other health questions."],
            ),
            dict(
                category="fever",
                patterns=[r"\bfever\b", r"\btemperature\b.*\bhigh\b"],
                responses=[
                    "For fever: rest, stay hydrated, and monitor your temperature. If it stays "
                    "above 103°F (39.4°C) or lasts more than 3 days, please see a doctor."
                ],
                medicines=["Paracetamol (Acetaminophen)", "Ibuprofen (if no contraindications)"],
            ),
            dict(
                category="headache",
                patterns=[r"\bheadache\b", r"\bmigraine\b"],
                responses=[
                    "For headaches: rest in a quiet, dark room, stay hydrated, and avoid screen time."
                ],
                medicines=["Paracetamol", "Ibuprofen", "Aspirin (adults only)"],
            ),
            dict(
                category="cough_cold",
                patterns=[r"\bcough\b", r"\bcold\b", r"\bsore throat\b"],
                responses=[
                    "For cough/cold: warm fluids, steam inhalation, and rest usually help. See a "
                    "doctor if symptoms persist beyond a week or breathing becomes difficult."
                ],
                medicines=["Cetirizine (antihistamine)", "Dextromethorphan (dry cough)",
                           "Guaifenesin (wet cough/expectorant)", "Throat lozenges"],
            ),
            dict(
                category="stomach",
                patterns=[r"\bstomach\s?ache\b", r"\bstomach\b.*\b(pain|hurt|ache)", r"\bnausea\b", r"\bvomit"],
                responses=[
                    "For stomach discomfort: eat light, bland food, stay hydrated with ORS, and "
                    "avoid oily food. Persistent pain or vomiting with blood needs immediate care."
                ],
                medicines=["ORS (oral rehydration salts)", "Antacids (e.g. Digene, Gelusil)",
                           "Loperamide (short-term diarrhea only)"],
            ),
            dict(
                category="allergy",
                patterns=[r"\ballerg(y|ies|ic)\b", r"\bitching\b", r"\brash\b"],
                responses=[
                    "For mild allergies: avoid the known trigger and consider an antihistamine. "
                    "Seek urgent care if you notice swelling of the face/throat or difficulty breathing."
                ],
                medicines=["Cetirizine", "Loratadine", "Fexofenadine"],
            ),
            dict(
                category="covid",
                patterns=[r"\bcovid\b", r"\bcoronavirus\b"],
                responses=[
                    "Common COVID-19 symptoms include fever, cough, and loss of taste/smell. "
                    "If you suspect exposure, isolate, get tested, and consult a healthcare provider."
                ],
                medicines=["Paracetamol (for fever/aches)"],
            ),
            dict(
                category="diet",
                patterns=[r"\bdiet\b", r"\bnutrition\b", r"\bhealthy eating\b", r"\bweight loss\b"],
                responses=[
                    "A balanced diet includes fruits, vegetables, whole grains, lean protein, and "
                    "adequate water. Avoid excess sugar and processed food."
                ],
            ),
            dict(
                category="exercise",
                patterns=[r"\bexercise\b", r"\bworkout\b", r"\bfitness\b"],
                responses=[
                    "Aim for at least 150 minutes of moderate exercise per week - brisk walking, "
                    "cycling, or swimming - plus strength training twice a week."
                ],
            ),
            dict(
                category="sleep",
                patterns=[r"\bsleep\b", r"\binsomnia\b"],
                responses=[
                    "Adults should aim for 7-9 hours of sleep daily. Keep a consistent schedule, "
                    "avoid caffeine late in the day, and limit screen time before bed."
                ],
            ),
            dict(
                category="mental_health",
                patterns=[r"\bstress(ed)?\b", r"\banxi(ety|ous)\b", r"\bdepressi", r"\bmental health\b"],
                responses=[
                    "Managing stress: try deep breathing, regular exercise, and talking to someone "
                    "you trust. If feelings persist or affect daily life, reach out to a professional."
                ],
            ),
            dict(
                category="medicine_generic",
                patterns=[r"\bmedicine\b", r"\bmedication\b", r"\btablet\b", r"\bdosage\b", r"\bdose\b"],
                responses=[
                    "I can share general OTC medicine names for common symptoms, but I can't give "
                    "dosages or prescriptions. Please confirm with a pharmacist or doctor before taking anything."
                ],
            ),
            dict(
                category="appointment",
                patterns=[r"\bappointment\b", r"\bbook\b.*\bdoctor\b", r"\bschedule\b.*\bvisit\b"],
                responses=[
                    "To book an appointment, please share your preferred date and department "
                    "(e.g. 'General Physician', 'Dermatology'). [Demo flow - connect to a real "
                    "booking system for production use.]"
                ],
            ),
            dict(
                category="nearby_doctor",
                patterns=[r"\bnearby doctor\b", r"\bnear(est)? doctor\b", r"\bdoctor near me\b",
                          r"\bfind.*(doctor|clinic|hospital)\b", r"\bclinic near\b"],
                responses=[
                    "Click the 📍 'Find Nearby Doctors' button above the chat box - I'll use your "
                    "browser location to list nearby doctors, clinics, and hospitals from OpenStreetMap."
                ],
            ),
            dict(
                category="emergency",
                patterns=[r"\bemergency\b", r"\bcan'?t breathe\b", r"\bchest pain\b",
                          r"\bsevere bleeding\b", r"\bunconscious\b"],
                responses=[
                    "⚠️ This sounds like it could be a medical emergency. Please call your local "
                    "emergency number or go to the nearest hospital immediately. I am not a "
                    "substitute for emergency care."
                ],
            ),
            dict(
                category="identity",
                patterns=[r"\bwho are you\b", r"\bwhat are you\b", r"\byour name\b"],
                responses=["I'm {bot}, a rule-based health assistant with document Q&A and nearby-doctor lookup."],
            ),
            dict(
                category="capability",
                patterns=[r"\bwhat can you do\b", r"\bhelp\b$", r"\bmenu\b"],
                responses=[
                    "I can help with: symptoms (fever, cough, headache, stomach issues...), general "
                    "OTC medicine names, diet/exercise/sleep tips, nearby doctor search, and answering "
                    "questions from a medical PDF you upload."
                ],
            ),
        ]

        self.fallback_responses = [
            "I'm not sure I understand. Try asking about a symptom, diet, exercise, medicines, or "
            "upload a PDF and ask about it.",
            "Sorry, I don't have an answer for that yet. Type 'help' to see what I can assist with.",
        ]

        self.medicine_disclaimer = (
            "\n\n⚠️ These are general OTC medicine names for common symptoms, not a prescription. "
            "Always confirm suitability, dosage, and interactions with a licensed pharmacist or doctor "
            "before taking anything - especially for children, pregnancy, or existing conditions."
        )

    def _match_rule(self, text):
        text = text.lower().strip()
        for rule in self.rules:
            for pattern in rule["patterns"]:
                if re.search(pattern, text):
                    return rule
        return None

    def get_response(self, user_input):
        """Rule-based response only (no RAG). Used by CLI / tests."""
        rule = self._match_rule(user_input)
        if rule is None:
            return random.choice(self.fallback_responses)

        response = random.choice(rule["responses"]).format(bot=self.name)
        medicines = rule.get("medicines")
        if medicines:
            response += "\n\n💊 Commonly used OTC options: " + ", ".join(medicines)
            response += self.medicine_disclaimer
        return response


def run_cli():
    bot = HealthChatbot()
    print(f"=== {bot.name}: Rule-Based Health Chatbot (CLI mode - no login/RAG here) ===")
    print("Type 'bye' or 'quit' to exit. For login + PDF Q&A + nearby doctors, run app.py instead.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{bot.name}: Goodbye!")
            break
        if not user_input:
            continue
        print(f"{bot.name}: {bot.get_response(user_input)}")
        if re.search(r"\b(bye|goodbye|exit|quit)\b", user_input.lower()):
            break


if __name__ == "__main__":
    run_cli()
