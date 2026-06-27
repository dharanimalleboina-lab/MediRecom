# ============================================================
# FILE: database/db.py
# PURPOSE: Define database tables for users and predictions
# ============================================================

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Create database object (we attach it to app later)
db = SQLAlchemy()

# ── USER TABLE ───────────────────────────────────────────────
class User(UserMixin, db.Model):
    """
    Stores registered users.
    UserMixin gives us: is_authenticated, is_active etc.
    """
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)  # stored as hash
    allergies  = db.Column(db.String(500), default="")      # comma-separated
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    # One user can have many predictions
    predictions = db.relationship('Prediction', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


# ── PREDICTION TABLE ─────────────────────────────────────────
class Prediction(db.Model):
    """
    Stores every prediction made by a user.
    This powers the history/dashboard page.
    """
    __tablename__ = 'predictions'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    condition    = db.Column(db.String(200), nullable=False)
    top_drug     = db.Column(db.String(200), nullable=False)
    result_json  = db.Column(db.Text,        nullable=False)  # full result as JSON
    had_alerts   = db.Column(db.Boolean,     default=False)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f'<Prediction {self.condition} → {self.top_drug}>'
