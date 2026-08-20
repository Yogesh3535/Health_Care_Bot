# Rule-Based Health Chatbot (with Login, SQL Storage, PDF RAG, Medicines & Nearby Doctors)

An intelligent health FAQ chatbot that:

- Answers common health queries using **rule-based** (regex) pattern matching
- Suggests **general OTC medicine names** for common symptoms (with a safety disclaimer)
- Finds **nearby doctors/clinics/hospitals/pharmacies** using your browser location
  (via the free OpenStreetMap Overpass API — no API key needed)
- Lets each user **upload a PDF** (e.g. a medical report) and ask questions about
  it using a local **RAG (Retrieval-Augmented Generation)** pipeline — TF-IDF based
  retrieval, fully offline, no LLM API key required
- Requires **user login** (register/login/logout) — each user only sees their own
  chat history and documents
- Stores everything (users, chat history, documents, document chunks) in a
  **SQLite** database via SQLAlchemy

---

## Project Structure

```
health_chatbot/
├── app.py                # Flask app: routes for auth, chat, upload, nearby doctors
├── chatbot.py             # Rule-based engine + OTC medicine suggestions (+ CLI mode)
├── models.py               # SQLAlchemy models: User, ChatMessage, Document, DocumentChunk
├── rag.py                   # PDF text extraction, chunking, TF-IDF retrieval (RAG)
├── doctor_finder.py          # Nearby doctor/clinic lookup via OpenStreetMap Overpass API (server-side fallback)
├── debug_check_db.py          # Standalone script to inspect the users table directly
├── test_chatbot.py             # Offline tests for rule engine + RAG (no login/DB needed)
├── requirements.txt
├── Procfile                     # Start command for Render/Railway (gunicorn)
├── runtime.txt                   # Python version pin for hosting platforms
├── DEPLOYMENT.md                  # Step-by-step Render/Railway deployment guide
├── templates/
│   ├── base.html               # Shared layout + nav
│   ├── login.html
│   ├── register.html
│   ├── chat.html                # Main chat UI + PDF upload + nearby doctors button (client-side lookup)
│   └── history.html              # Per-user chat history
├── static/
│   └── style.css
├── uploads/                # Uploaded PDFs are stored here (per user sub-folder)
└── instance/                # SQLite DB file (health_chatbot.db) is created here
```

---

## Requirements

- Python 3.9+
- pip
- Internet access **only** for the "Find Nearby Doctors" feature (it calls the
  free OpenStreetMap Overpass API). Everything else — chat, login, RAG — works
  fully offline.

---

## Step-by-Step: How to Run

### 1. Unzip the project
Extract `health_chatbot.zip` and open a terminal inside the `health_chatbot/` folder.

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```
This automatically creates the SQLite database (`instance/health_chatbot.db`)
with all required tables the first time it runs.

### 5. Open in your browser
Go to: **http://127.0.0.1:5000**

### 6. Register an account
Click **Register**, create a username/email/password, then **Login**.

### 7. Use the chatbot
- Type health questions in the chat box (e.g. *"I have a fever"*, *"give me diet
  tips"*, *"what medicine should I take for a cough"*).
- Click **📄 Upload PDF** in the sidebar to upload a medical report/document,
  then ask questions about it (e.g. *"what medication was prescribed?"*) — the
  bot will retrieve and quote the most relevant part(s) of your document.
- Click **📍 Find Nearby Doctors** — your browser will ask permission to share
  your location, then a list of nearby doctors/clinics/hospitals/pharmacies
  (from OpenStreetMap) will appear, sorted by distance.
- Click **History** in the nav bar to see your full stored conversation log.

### 8. (Optional) Run the offline tests
Verifies the rule engine and RAG retrieval without needing the server, login, or internet:
```bash
python test_chatbot.py
```

### 9. (Optional) CLI-only mode (no login/RAG/doctors, just rules)
```bash
python chatbot.py
```

---

## How Each Feature Works

| Feature | How it works |
|---|---|
| **Rule-based Q&A** | `chatbot.py` matches user text against regex rules (fever, cough, diet, stress, etc.) and returns a curated response. |
| **Medicine names** | Each symptom rule has an attached list of common OTC medicine names, always shown with a "consult a pharmacist/doctor" disclaimer. Not a prescription. |
| **Login / accounts** | `Flask-Login` + `Werkzeug` password hashing. Passwords are never stored in plain text. |
| **SQL storage** | `Flask-SQLAlchemy` models (`User`, `ChatMessage`, `Document`, `DocumentChunk`) persisted to SQLite at `instance/health_chatbot.db`. |
| **PDF RAG** | On upload, `rag.py` extracts text (`pypdf`), splits it into overlapping chunks, and stores chunks per user in SQL. On each chat message, it TF-IDF-vectorizes the question against that user's chunks and returns the most relevant snippet(s) — classic sparse-vector retrieval, no external LLM call required. If no chunk clears the confidence threshold but there's still some word overlap, it shows the closest match labeled "low confidence" rather than going silent. |
| **Nearby doctors** | Your browser's `navigator.geolocation` API gets your lat/long, then JavaScript queries the free OpenStreetMap **Overpass API** directly from the browser (3 mirror servers tried in turn). This avoids relying on the backend server's network, which can be more restricted (firewalls, sandboxed hosting). If the browser can't reach any mirror either, it falls back to asking the Flask backend (`doctor_finder.py`) to try, and if that also fails, shows a "Open in Google Maps" link as a last resort. |

---

## Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| "Invalid username or password" right after registering | The `users` table wasn't created (e.g. app launched via `flask run` before the fix) or password hashing failed silently. Delete `instance/health_chatbot.db`, restart with `python app.py`, and check the terminal — it now prints the DB path and logs the specific reason for any login failure. Run `python debug_check_db.py` to inspect the DB directly. |
| Nearby Doctors gives a network/timeout error | Usually the backend server's network is restricted. This is already handled: the lookup runs in your **browser** first (bypassing the backend), only falling back to the server if that also fails. Fully offline networks will still fail — use the "Open in Google Maps" link shown in that case. |
| Document Q&A gives generic answers, not your PDF's content | TF-IDF matches on shared *words*, not meaning — phrase your question using words likely to appear in the PDF itself (e.g. "What does it say about Metformin?" rather than "what pills should I take"). Very short/scanned PDFs may also extract little or no text — check the upload confirmation message for the chunk count. |

---

## Deploying This Project

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for a step-by-step guide to
deploying this app to Render or Railway's free tier, including the
`Procfile`/`gunicorn` setup already included in this project.

## Extending the Project

- **Swap extractive RAG for generative RAG**: in `rag.py` / `app.py`, take the
  retrieved chunks and pass them as context to an LLM API (e.g. the Anthropic
  or OpenAI API) to generate a natural-language answer instead of showing raw
  snippets.
- **Add more medicine categories**: edit the `medicines` list on any rule in
  `chatbot.py`.
- **Switch to Postgres/MySQL**: change `SQLALCHEMY_DATABASE_URI` in `app.py`
  (SQLAlchemy supports this with no other code changes).
- **Add password reset / email verification**: extend `models.py` (`User`)
  and add new routes in `app.py`.

---

## Important Disclaimer

This chatbot provides **general health information and commonly known OTC
medicine names only** — it is **not** a substitute for professional medical
advice, diagnosis, treatment, or prescription. Always consult a qualified
healthcare provider or licensed pharmacist before taking any medication, and
call your local emergency number in urgent situations. The "nearby doctors"
feature uses public OpenStreetMap data, which may be incomplete or outdated —
always verify details (hours, availability) before visiting.
