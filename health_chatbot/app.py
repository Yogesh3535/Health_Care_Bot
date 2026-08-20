"""
Main Flask application.

Routes:
  GET/POST /register       - create a new user account
  GET/POST /login          - log in
  GET      /logout         - log out
  GET      /                - chat page (login required)
  POST     /chat            - send a chat message, get bot reply (login required)
  POST     /upload          - upload a PDF for RAG (login required)
  POST     /nearby-doctors  - find nearby doctors/clinics via geolocation (login required)
  GET      /history         - view stored chat history for the logged-in user

Each user's data (chat history, uploaded documents, document chunks) is
stored in a SQLite database (health_chatbot.db) and scoped strictly to
that user's account.
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename

from models import db, User, ChatMessage, Document, DocumentChunk
from chatbot import HealthChatbot
from rag import extract_text_from_pdf, chunk_text, build_rag_answer
from doctor_finder import find_nearby_medical

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
if app.config["SECRET_KEY"] == "dev-secret-change-me" and os.environ.get("PORT"):
    # PORT being set is a strong signal we're running on a hosting platform
    # (Render/Railway both inject it) rather than locally - warn if the
    # SECRET_KEY env var wasn't configured there, since sessions/cookies
    # aren't safely signed with the default dev key in production.
    print("[HealthBot] WARNING: SECRET_KEY env var is not set - using the "
          "insecure default. Set a real SECRET_KEY in your platform's "
          "environment variables before going live.")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "instance", "health_chatbot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db.init_app(app)

# Create tables on import, regardless of how the app is launched
# (python app.py, flask run, gunicorn, etc.) - this was previously only
# done inside `if __name__ == "__main__"`, which meant `flask run` never
# created the `users` table, causing registration to silently fail and
# login to always report "invalid username or password".
with app.app_context():
    db.create_all()

# Print the exact database file being used every time the app starts, so
# it's obvious if two different copies of the project (or two different
# working directories) end up pointing at two different .db files.
print(f"[HealthBot] Using database file: {app.config['SQLALCHEMY_DATABASE_URI']}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

bot = HealthChatbot()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("chat_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already registered.", "error")
            return redirect(url_for("register"))

        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f"Registration failed: {exc}", "error")
            return redirect(url_for("register"))

        print(f"[HealthBot] Registered new user id={user.id} username={user.username!r}")
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("chat_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is None:
            print(f"[HealthBot] Login attempt for unknown username={username!r}. "
                  f"Total users in DB: {User.query.count()}")
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        if not user.check_password(password):
            print(f"[HealthBot] Login attempt for username={username!r}: password did not match.")
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("chat_page"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --------------------------------------------------------------------
# Chat + RAG + doctor lookup (all require login)
# --------------------------------------------------------------------

@app.route("/")
@login_required
def chat_page():
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template("chat.html", bot_name=bot.name, username=current_user.username,
                            documents=documents)


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"reply": "Please type a message."})

    # 1) Try RAG over this user's uploaded document chunks first.
    chunk_rows = (
        DocumentChunk.query
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.user_id == current_user.id)
        .all()
    )
    chunk_texts = [c.chunk_text for c in chunk_rows]
    rag_answer = build_rag_answer(user_message, chunk_texts) if chunk_texts else None

    # 2) Rule-based response.
    rule_answer = bot.get_response(user_message)

    if rag_answer:
        reply = rag_answer + "\n\n---\n" + rule_answer
    else:
        reply = rule_answer

    # 3) Persist conversation turn.
    db.session.add(ChatMessage(user_id=current_user.id, sender="user", message=user_message))
    db.session.add(ChatMessage(user_id=current_user.id, sender="bot", message=reply))
    db.session.commit()

    return jsonify({"reply": reply})


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("pdf_file")
    if file is None or file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    filename = secure_filename(file.filename)
    user_upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    save_path = os.path.join(user_upload_dir, filename)
    file.save(save_path)

    try:
        text = extract_text_from_pdf(save_path)
    except Exception as exc:
        return jsonify({"error": f"Could not read PDF: {exc}"}), 400

    chunks = chunk_text(text)
    if not chunks:
        return jsonify({"error": "No extractable text found in this PDF (it may be a scanned image)."}), 400

    document = Document(user_id=current_user.id, filename=filename)
    db.session.add(document)
    db.session.flush()  # get document.id before commit

    for idx, chunk in enumerate(chunks):
        db.session.add(DocumentChunk(document_id=document.id, chunk_index=idx, chunk_text=chunk))

    db.session.commit()

    return jsonify({"message": f"Uploaded '{filename}' - {len(chunks)} chunks indexed. "
                                f"You can now ask questions about it."})


@app.route("/nearby-doctors", methods=["POST"])
@login_required
def nearby_doctors():
    data = request.get_json(force=True)
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "Location not provided."}), 400

    try:
        results = find_nearby_medical(float(lat), float(lon))
    except Exception as exc:
        return jsonify({"error": f"Could not fetch nearby facilities (check internet access): {exc}"}), 502

    if not results:
        return jsonify({"results": [], "message": "No facilities found nearby. Try a larger radius."})

    return jsonify({"results": results})


@app.route("/history")
@login_required
def history():
    messages = (
        ChatMessage.query
        .filter_by(user_id=current_user.id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    return render_template("history.html", messages=messages, username=current_user.username)


if __name__ == "__main__":
    # PORT/FLASK_DEBUG are read from the environment so this same code works
    # locally (defaults: port 5000, debug on) and on hosting platforms like
    # Render/Railway, which inject their own PORT and expect binding to
    # 0.0.0.0 (not just 127.0.0.1) so their router can reach the app.
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", debug=debug_mode, port=port)
