"""
SQL database models (SQLite via SQLAlchemy).

Tables:
- User            : login credentials
- ChatMessage     : per-user conversation history
- Document        : uploaded PDFs metadata (per user)
- DocumentChunk   : chunked text of each PDF, used for RAG retrieval
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship("ChatMessage", backref="user", lazy=True,
                                cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="user", lazy=True,
                                 cascade="all, delete-orphan")

    def set_password(self, raw_password):
        # Explicit method (pbkdf2:sha256) instead of Werkzeug's default,
        # since the default ("scrypt" on newer Werkzeug) can raise on
        # Python builds without scrypt support in hashlib/OpenSSL - that
        # would make registration fail silently and every login look like
        # "invalid username or password" even for a freshly registered user.
        self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256")

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    chunks = db.relationship("DocumentChunk", backref="document", lazy=True,
                              cascade="all, delete-orphan")


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
