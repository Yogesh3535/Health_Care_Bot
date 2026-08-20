"""
Diagnostic script - run this if registration/login is misbehaving.
It talks directly to the SQLite file and the User model, bypassing the
web server entirely, so it tells you exactly what's actually stored.

Usage:
    python debug_check_db.py                  # list all users
    python debug_check_db.py alice mypassword  # test a specific login
"""

import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "health_chatbot.db")

print(f"Looking for database at: {DB_PATH}")
print(f"File exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"File size: {os.path.getsize(DB_PATH)} bytes")
print("-" * 60)

from app import app
from models import User

with app.app_context():
    users = User.query.all()
    print(f"Total users found: {len(users)}\n")
    for u in users:
        print(f"  id={u.id}  username={u.username!r}  email={u.email!r}  "
              f"created_at={u.created_at}  hash_prefix={u.password_hash[:20]}...")

    if len(sys.argv) == 3:
        test_username, test_password = sys.argv[1], sys.argv[2]
        print("-" * 60)
        print(f"Testing login for username={test_username!r} ...")
        user = User.query.filter_by(username=test_username).first()
        if user is None:
            print("  -> RESULT: no user with that username exists in the DB above.")
        elif not user.check_password(test_password):
            print("  -> RESULT: username exists, but that password does NOT match "
                  "the stored hash. Double-check for typos/extra spaces.")
        else:
            print("  -> RESULT: username + password are correct. Login should succeed.")
