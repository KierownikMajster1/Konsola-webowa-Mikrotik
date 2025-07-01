import os
import time
import threading
import secrets
from ros_api.api import Api
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

# Flask setup
app = Flask(__name__)

app.config['SECRET_KEY'] = 'super-tajny-klucz-do-sesji'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # lub True przy HTTPS
app.config['SESSION_REFRESH_EACH_REQUEST'] = False
app.config['REGISTRATION_ENABLED'] = False # Rejestracja albo Admin

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Lista MikroTików
mikrotiks = []

# Globalne statusy dla każdego MikroTika
statuses = {}

# Dodaj konfigurację bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://flaskuser:bardzosekrethaslo@localhost/mikrotik_dashboard'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicjalizacja narzędzi
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    mikrotiks = db.relationship('Mikrotik', backref='owner', lazy=True)

class Mikrotik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=True)

# Funkcja sprawdzająca status MikroTik
def check_status(mikrotik):
    try:
        from ros_api.api import Api
        api = Api(
            mikrotik['host'],
            mikrotik['username'],
            mikrotik['password'] if mikrotik['password'] is not None else ""
        )
        interfaces = api.talk(['/interface/print'])

        mac_list = [i.get("mac-address") for sublist in interfaces for i in sublist if "mac-address" in i]
        status = {
            "online": True,
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mac": mac_list[0] if mac_list else None,
            "host": mikrotik['host'], 
            "interfaces": [{"name": i.get("name"), "mac": i.get("mac-address")} for sublist in interfaces for i in sublist],
        }
        return status
    except Exception:
        return {
            "online": False,
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "host": mikrotik['host']  
        }

# Watchdog dla wszystkich MikroTików
def watchdog():
    while True:
        with app.app_context():  # Ustawienie kontekstu aplikacji Flask
            user_mikrotiks = Mikrotik.query.all()
            for mikrotik in user_mikrotiks:
                statuses[mikrotik.id] = check_status({
                    "host": mikrotik.host,
                    "username": mikrotik.username,
                    "password": mikrotik.password
                })
        time.sleep(10)  # Sprawdzanie statusu co 10 sekund

# API: Pobierz statusy MikroTików
@app.route("/status", methods=["GET"])
@login_required
def get_status():
    result = {}
    user_mikrotiks = Mikrotik.query.filter_by(user_id=current_user.id).all()

    for mikrotik in user_mikrotiks:
        mikrotik_id = mikrotik.id
        status = statuses.get(mikrotik_id, {})
        status.update({
            "name": mikrotik.name,
            "host": mikrotik.host,
        })
        result[mikrotik_id] = status

    return jsonify({"mikrotiks": result})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if not app.config['REGISTRATION_ENABLED']:
        flash("Rejestracja jest wyłączona.", "danger")
        return redirect(url_for('login'))

    if current_user.is_authenticated:  # Jeśli użytkownik już zalogowany
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        user = User(username=username, email=email, password_hash=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Rejestracja zakończona sukcesem. Możesz się teraz zalogować.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Użytkownik o takim adresie e-mail lub nazwie użytkownika już istnieje.', 'danger')

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:  # Jeśli użytkownik już zalogowany
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Nieprawidłowy email lub hasło.', 'danger')

    return render_template('login.html')

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not bcrypt.check_password_hash(current_user.password_hash, current_password):
        return jsonify({"success": False, "message": "Obecne hasło jest nieprawidłowe."}), 400

    current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    return jsonify({"success": True, "message": "Hasło zostało zmienione."})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

# API: Dodaj MikroTik
@app.route("/add_mikrotik", methods=["POST"])
@login_required
def add_mikrotik():
    try:
        # Odczyt JSON z żądania
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "Brak danych JSON"}), 400

        # Walidacja danych
        if not data.get("name") or not data.get("host") or not data.get("username"):
            return jsonify({"success": False, "message": "Niekompletne dane"}), 400

        # Dodawanie MikroTik
        mikrotik = Mikrotik(
            user_id=current_user.id,
            name=data["name"],
            host=data["host"],
            username=data["username"],
            password=data.get("password", "")
        )

        db.session.add(mikrotik)
        db.session.commit()

        return jsonify({"success": True, "message": "MikroTik dodany!"})
    except Exception as e:
        print("Błąd serwera:", e)
        return jsonify({"success": False, "message": "Błąd serwera"}), 500

@app.route('/delete_mikrotik/<int:mikrotik_id>', methods=['DELETE'])
@login_required
def delete_mikrotik(mikrotik_id):
    mikrotik = Mikrotik.query.filter_by(id=mikrotik_id, user_id=current_user.id).first()

    if mikrotik:
        db.session.delete(mikrotik)
        db.session.commit()
        return jsonify({"message": "MikroTik został usunięty."}), 200
    else:
        return jsonify({"message": "MikroTik nie istnieje lub nie masz do niego dostępu."}), 404

@app.route("/execute_command", methods=["POST"])
@login_required
def execute_command():
    data = request.json
    command = data.get("command")
    mikrotik_ids = data.get("mikrotik_ids", [])

    if not command or not mikrotik_ids:
        return jsonify({"success": False, "message": "Brak polecenia lub MikroTików"}), 400

    results = {}

    raw_tokens = command.strip().split()

    parsed_cmd = []
    for i, token in enumerate(raw_tokens):
        if i == 0:
            # Ścieżka "/tool/ping"
            parsed_cmd.append(token)
        else:
            # postać "=address=8.8.8.8"
            if '=' in token:
                parsed_cmd.append('=' + token) 
            else:
                parsed_cmd.append(token)

    command_for_talk = [tuple(parsed_cmd)]

    for mikrotik_id in mikrotik_ids:
        mikrotik = Mikrotik.query.filter_by(id=mikrotik_id, user_id=current_user.id).first()
        if not mikrotik:
            results[mikrotik_id] = {"error": "Brak dostępu"}
            continue

        try:
            api = Api(mikrotik.host, mikrotik.username, mikrotik.password or "")
            response = api.talk(command_for_talk)
            results[mikrotik.name] = response
        except Exception as e:
            results[mikrotik.name] = {"error": str(e)}

    return jsonify({"success": True, "results": results})

# Start watchdog w tle
threading.Thread(target=watchdog, daemon=True).start()

# Strona główna
@app.route('/index')
@login_required
def index():
    mikrotiks = Mikrotik.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', mikrotiks=mikrotiks)

# Uruchomienie aplikacji Flask
import threading

def start_watchdog_once():
    if not getattr(app, "_watchdog_started", False):
        threading.Thread(target=watchdog, daemon=True).start()
        app._watchdog_started = True

start_watchdog_once()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = bcrypt.generate_password_hash('admin').decode('utf-8')
        admin_user = User(username='admin', email='admin@example.com', password_hash=hashed_password)
        db.session.add(admin_user)
        db.session.commit()
