# ============================================================
# FILE: app.py
# PURPOSE: Main Flask app — routes, auth, API endpoints
# ============================================================

import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db, User, Prediction
from model.predict import get_recommendations

# ── CREATE FLASK APP ─────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']        = 'medirecom-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medirecom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── ATTACH DATABASE ──────────────────────────────────────────
db.init_app(app)

# ── SETUP LOGIN MANAGER ──────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirect here if not logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── CREATE TABLES ────────────────────────────────────────────
with app.app_context():
    db.create_all()
    print("✅ Database tables created!")

# ============================================================
# ROUTES
# ============================================================

# ── HOME PAGE ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── REGISTER ─────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username  = request.form.get('username').strip()
        email     = request.form.get('email').strip()
        password  = request.form.get('password')
        allergies = request.form.get('allergies', '').strip()

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken. Choose another.', 'error')
            return redirect(url_for('register'))

        # Hash password and save user
        hashed_pw = generate_password_hash(password)
        new_user  = User(
            username  = username,
            email     = email,
            password  = hashed_pw,
            allergies = allergies
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ── LOGIN ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email').strip()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('login.html')

# ── LOGOUT ───────────────────────────────────────────────────
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ── DASHBOARD ────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    # Get last 10 predictions for this user
    history = Prediction.query.filter_by(user_id=current_user.id)\
                              .order_by(Prediction.created_at.desc())\
                              .limit(10).all()
    return render_template('dashboard.html', user=current_user, history=history)

# ── PREDICT API ──────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    data      = request.get_json()
    condition = data.get('condition', '').strip()
    allergies = data.get('allergies', '')

    # Use user's saved allergies + any extra ones entered
    user_allergies = []
    if current_user.allergies:
        user_allergies += [a.strip() for a in current_user.allergies.split(',')]
    if allergies:
        user_allergies += [a.strip() for a in allergies.split(',')]

    # Get recommendations
    result = get_recommendations(condition, user_allergies=user_allergies)

    # Save to database if successful
    if result['status'] == 'success' and result['recommendations']:
        top_drug = result['recommendations'][0]['drug_name']
        pred = Prediction(
            user_id     = current_user.id,
            condition   = condition,
            top_drug    = top_drug,
            result_json = json.dumps(result),
            had_alerts  = result['total_alerts'] > 0
        )
        db.session.add(pred)
        db.session.commit()

    return jsonify(result)

# ── RESULT PAGE ──────────────────────────────────────────────
@app.route('/result')
@login_required
def result():
    return render_template('result.html')

# ── UPDATE ALLERGIES ─────────────────────────────────────────
@app.route('/update-allergies', methods=['POST'])
@login_required
def update_allergies():
    allergies = request.form.get('allergies', '').strip()
    current_user.allergies = allergies
    db.session.commit()
    flash('Allergies updated successfully!', 'success')
    return redirect(url_for('dashboard'))

# ── RUN APP ──────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
