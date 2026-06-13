import os
import sqlite3
import subprocess
import signal
from flask import Flask, request, render_template_string, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = "super_tajny_klucz_sesji_RESET_123_WBUDOWANY_FIX"

# Słownik do trzymania uruchomionych procesów botów per użytkownik
running_bots = {}

# ================= SZABLONY HTML I CSS =================

CSS_THEME = """
<style>
    :root {
        --bg-main: #0f0f11;
        --bg-panel: #18181b;
        --bg-card: #27272a;
        --primary: #ff6600;
        --primary-hover: #ff8533;
        --text-main: #f4f4f5;
        --text-muted: #a1a1aa;
        --border-color: #3f3f46;
        --success: #22c55e;
        --danger: #ef4444;
        --terminal-bg: #050506;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
    body { background-color: var(--bg-main); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
    
    .auth-wrapper { display: flex; width: 100vw; height: 100vh; justify-content: center; align-items: center; }
    .auth-card { background: var(--bg-panel); padding: 40px; border-radius: 12px; border: 1px solid var(--border-color); width: 100%; max-width: 400px; text-align: center; }
    .auth-card h2 { color: var(--text-main); margin-bottom: 20px; font-weight: 800; }
    .auth-card h2 span { color: var(--primary); }
    
    .sidebar { width: 280px; background-color: var(--bg-panel); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 20px 0; }
    .logo-container { padding: 0 24px 30px 24px; font-size: 24px; font-weight: 900; color: var(--text-main); }
    .logo-container span { color: var(--primary); }
    
    .nav-links { list-style: none; display: flex; flex-direction: column; gap: 5px; padding: 0 12px; }
    .nav-links li a { display: flex; align-items: center; padding: 12px 16px; color: var(--text-muted); text-decoration: none; border-radius: 8px; font-weight: 600; transition: 0.2s; }
    .nav-links li a:hover { background-color: var(--bg-card); color: var(--text-main); }
    .nav-links li a.active { background-color: rgba(255, 102, 0, 0.1); color: var(--primary); border-left: 4px solid var(--primary); }
    
    .user-profile-widget { margin-top: auto; padding: 16px; border-top: 1px solid var(--border-color); display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.2); text-decoration: none;}
    .user-profile-widget:hover { background: var(--bg-card); }
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), #cc5200); display: flex; justify-content: center; align-items: center; font-weight: bold; color: #fff; }
    .user-info { display: flex; flex-direction: column; }
    .user-name { font-weight: 700; color: var(--text-main); font-size: 14px; }
    .user-role { font-size: 12px; color: var(--primary); font-weight: 600; }
    
    .main-content { flex: 1; padding: 40px; overflow-y: auto; background-color: var(--bg-main); }
    .page-header { margin-bottom: 30px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
    .page-header h1 { font-size: 28px; font-weight: 800; }
    
    .card { background: var(--bg-panel); border-radius: 12px; padding: 24px; border: 1px solid var(--border-color); margin-bottom: 24px; }
    .card h3 { margin-bottom: 16px; font-size: 18px; }
    
    input[type="text"], input[type="password"] { width: 100%; padding: 12px 16px; margin-bottom: 16px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-main); color: var(--text-main); }
    
    .btn { display: inline-block; padding: 12px 24px; border-radius: 8px; font-weight: 700; font-size: 14px; text-decoration: none; text-align: center; cursor: pointer; transition: 0.2s; border: none; }
    .btn-primary { background-color: var(--primary); color: white; width: 100%; }
    .btn-primary:hover { background-color: var(--primary-hover); }
    .btn-success { background-color: var(--success); color: white; }
    .btn-danger { background-color: transparent; color: var(--danger); border: 1px solid var(--danger); }
    .btn-danger:hover { background-color: var(--danger); color: white; }
    .btn-youtube { background-color: #ff0000; color: white; display: inline-flex; align-items: center; justify-content: center; gap: 8px;}
    .btn-youtube:hover { background-color: #cc0000; }
    
    .alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
    .alert.success { background: rgba(34, 197, 94, 0.1); border: 1px solid var(--success); color: var(--success); }
    .alert.error { background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); color: var(--danger); }

    /* Terminal UI */
    .bot-controls { display: flex; gap: 16px; margin-bottom: 24px; align-items: center;}
    .terminal-container { background: var(--terminal-bg); border-radius: 12px; border: 1px solid var(--border-color); padding: 20px; min-height: 300px; max-height: 450px; overflow-y: auto; }
    .terminal-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
    .terminal-table th { padding: 12px; border-bottom: 2px solid var(--border-color); color: var(--primary); font-weight: 700; }
    .terminal-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge.clean { background: rgba(161, 161, 170, 0.1); color: var(--text-muted); }
    .badge.warn { background: rgba(255, 102, 0, 0.1); color: var(--primary); border: 1px solid var(--primary); }
    .badge.ban { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid var(--danger); }
    
    .notice-box { background: rgba(255, 102, 0, 0.05); border-left: 4px solid var(--primary); padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px; font-size: 14px; line-height: 1.5; }
    .integration-box { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: var(--bg-main); border-radius: 8px; border: 1px solid var(--border-color); }
</style>
"""

HTML_AUTH = CSS_THEME + """
<div class="auth-wrapper">
    <div class="auth-card">
        <h2>ModerAI <span>PRO</span></h2>
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        {% block content %}{% endblock %}
    </div>
</div>
"""

HTML_LOGIN = HTML_AUTH.replace('{% block content %}{% endblock %}', """
    <p style="color: var(--text-muted); margin-bottom: 24px; font-size: 14px;">Zaloguj się do panelu dowodzenia</p>
    <form method="POST">
        <input type="text" name="username" placeholder="Nazwa użytkownika" required>
        <input type="password" name="password" placeholder="Hasło" required>
        <button type="submit" class="btn btn-primary">Zaloguj</button>
    </form>
    <p style="margin-top: 20px; font-size: 13px; color: var(--text-muted);">
        Nie masz konta? <a href="{{ url_for('register') }}" style="color: var(--primary); text-decoration: none; font-weight: bold;">Zarejestruj się</a>
    </p>
""")

HTML_REGISTER = HTML_AUTH.replace('{% block content %}{% endblock %}', """
    <p style="color: var(--text-muted); margin-bottom: 24px; font-size: 14px;">Utwórz nowe konto operatora AI</p>
    <form method="POST">
        <input type="text" name="username" placeholder="Nazwa użytkownika" required>
        <input type="password" name="password" placeholder="Hasło" required>
        <button type="submit" class="btn btn-primary">Zarejestruj</button>
    </form>
    <p style="margin-top: 20px; font-size: 13px; color: var(--text-muted);">
        Masz już konto? <a href="{{ url_for('login') }}" style="color: var(--primary); text-decoration: none; font-weight: bold;">Wróć do logowania</a>
    </p>
""")

HTML_APP_BASE = CSS_THEME + """
    <div class="sidebar">
        <div class="logo-container">ModerAI <span>PRO</span></div>
        <ul class="nav-links">
            <li><a href="{{ url_for('dashboard') }}" class="{% if active_page == 'dashboard' %}active{% endif %}">📱 Dashboard / Terminal</a></li>
            <li><a href="{{ url_for('tutorial') }}" class="{% if active_page == 'tutorial' %}active{% endif %}">📖 Instrukcja obsługi</a></li>
            <li><a href="{{ url_for('profile') }}" class="{% if active_page == 'profile' %}active{% endif %}">⚙️ Twój Profil</a></li>
        </ul>
        <a href="{{ url_for('profile') }}" class="user-profile-widget">
            <div class="avatar">{{ session['username'][0] | upper }}</div>
            <div class="user-info">
                <span class="user-name">{{ session['username'] }}</span>
                <span class="user-role">Operator AI</span>
            </div>
        </a>
    </div>
    <div class="main-content">
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        {% block content %}{% endblock %}
    </div>
"""

HTML_DASHBOARD = HTML_APP_BASE.replace('{% block content %}{% endblock %}', """
    <div class="page-header">
        <h1>Panel Transmisji i Terminal Live</h1>
    </div>
    
    <div class="notice-box">
        <strong>⚠️ WAŻNA NOTKA DOTYCZĄCA MODERACJI:</strong><br>
        Zanim klikniesz przycisk startu, upewnij się, że dodałeś oficjalne konto bota jako <strong>Moderatora zarządzającego (Managing Moderator)</strong> w panelu <strong>YouTube Studio -> Ustawienia -> Społeczność</strong> na swoim kanale.
    </div>
    
    {% if current_channel %}
        <div class="bot-controls">
            {% if bot_running %}
                <a href="{{ url_for('stop_bot') }}" class="btn btn-danger" style="width: auto;">🛑 ZATRZYMAJ BOTA</a>
                <span style="color: var(--success); font-weight: bold;">● BOT PRACUJE W TLE</span>
            {% else %}
                <a href="{{ url_for('start_bot') }}" class="btn btn-success" style="width: auto;">▶ URUCHOM BOTA</a>
                <span style="color: var(--text-muted);">Bot jest wyłączony.</span>
            {% endif %}
        </div>
        
        <div class="card" style="padding: 16px;">
            <h3>Terminal Monitorowania Czatu</h3>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">Podgląd strumienia wiadomości w czasie rzeczywistym.</p>
            
            <div class="terminal-container">
                <table class="terminal-table">
                    <thead>
                        <tr>
                            <th style="width: 15%;">Godzina</th>
                            <th style="width: 20%;">Użytkownik</th>
                            <th style="width: 45%;">Treść Wiadomości</th>
                            <th style="width: 20%;">Stopień / Status</th>
                        </tr>
                    </thead>
                    <tbody id="terminal-logs">
                        <tr>
                            <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 40px;">Brak nowych logów. Uruchom bota lub poczekaj na wiadomości ze streama...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            function fetchLogs() {
                fetch('/get_logs')
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('terminal-logs');
                        if (data.length > 0) {
                            tbody.innerHTML = ''; 
                            data.forEach(log => {
                                let badgeClass = 'clean';
                                let statusText = 'Czysto (OK)';
                                
                                if (log.poziom > 0 && log.poziom <= 2) {
                                    badgeClass = 'warn';
                                    statusText = `MUTE (Lvl ${log.poziom})`;
                                } else if (log.poziom > 2) {
                                    badgeClass = 'ban';
                                    statusText = `BAN (Lvl ${log.poziom})`;
                                }
                                
                                const row = `<tr>
                                    <td style="color: var(--text-muted); font-family: monospace;">${log.godzina}</td>
                                    <td style="font-weight: bold; color: var(--primary);">@${log.user}</td>
                                    <td>${log.tresc}</td>
                                    <td><span class="badge ${badgeClass}">${statusText}</span></td>
                                </tr>`;
                                tbody.innerHTML += row;
                            });
                        }
                    });
            }
            setInterval(fetchLogs, 1000); 
            fetchLogs();
        </script>
    {% else %}
        <div class="card">
            <h3>❌ System Nieuzbrojony</h3>
            <p style="color: var(--text-muted); margin-bottom: 16px;">Aby aktywować terminal i móc odpalić bota, musisz najpierw połączyć swój kanał streamerski.</p>
            <a href="{{ url_for('profile') }}" class="btn btn-primary" style="width: auto;">Przejdź do profilu i połącz konto</a>
        </div>
    {% endif %}
""")

HTML_TUTORIAL = HTML_APP_BASE.replace('{% block content %}{% endblock %}', """
    <div class="page-header">
        <h1>Instrukcja Obsługi</h1>
    </div>
    <div class="card">
        <h3>System działa w pełni automatycznie.</h3>
        <p style="color:var(--text-muted);margin-top:10px;">Podłącz swoje konto YouTube w zakładce Profil, a następnie uruchom bota przyciskiem na Dashboardzie. Skrypt zacznie działać w tle i przesyłać logi do Twojego terminala.</p>
    </div>
""")

HTML_PROFILE = HTML_APP_BASE.replace('{% block content %}{% endblock %}', """
    <div class="page-header">
        <h1>Ustawienia Profilu</h1>
    </div>
    <div class="card">
        <h3>Podpięte Konta Zewnętrzne</h3>
        <p style="color: var(--text-muted); margin-bottom: 24px; font-size: 14px;">Zarządzaj powiązaniami API platform zewnętrznych.</p>
        
        <div class="integration-box">
            <div>
                <h4 style="margin-bottom: 5px;">YouTube Live API</h4>
                {% if current_channel %}
                    <p style="color:var(--success); font-family:monospace; font-size:12px;">Powiązane ID: {{ current_channel }}</p>
                {% else %}
                    <p style="color:var(--text-muted); font-size:13px;">Brak podłączonego kanału.</p>
                {% endif %}
            </div>
            {% if current_channel %}
                <span style="padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid var(--success);">Połączono</span>
            {% else %}
                <a href="{{ url_for('authorize_youtube') }}" class="btn btn-youtube" style="width: auto;">▶ Połącz z YouTube</a>
            {% endif %}
        </div>
    </div>
    
    <div class="card" style="border-color: rgba(239, 68, 68, 0.3);">
        <h3 style="color: var(--danger);">Strefa Bezpieczeństwa</h3>
        <p style="color: var(--text-muted); margin-bottom: 20px;">Zakończenie sesji operatora z panelem WWW.</p>
        <a href="{{ url_for('logout') }}" class="btn btn-danger" style="width: auto;">Wyloguj się z systemu</a>
    </div>
""")

# ================= LOGIKA BAZY DANYCH =================

def setup_db():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, youtube_channel_id TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS terminal_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, godzina TEXT, username TEXT, tresc TEXT, poziom INTEGER
    )""")
    con.commit()
    con.close()

# ================= KONTROLER BOTA =================

@app.route('/start_bot')
def start_bot():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    if uid not in running_bots or running_bots[uid].poll() is not None:
        proc = subprocess.Popen(['python', 'bothead.py', str(uid)], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        running_bots[uid] = proc
        flash("Mózg AI został uruchomiony! System analizuje czat.", "success")
    return redirect(url_for('dashboard'))

@app.route('/stop_bot')
def stop_bot():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    if uid in running_bots and running_bots[uid].poll() is None:
        if os.name == 'nt':
            running_bots[uid].send_signal(signal.CTRL_BREAK_EVENT)
        else:
            running_bots[uid].terminate()
        del running_bots[uid]
        flash("Bot został pomyślnie wyłączony.", "error")
    return redirect(url_for('dashboard'))

@app.route('/get_logs')
def get_logs():
    if 'user_id' not in session: return jsonify([])
    
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT godzina, username, tresc, poziom FROM terminal_logs WHERE user_id = ? ORDER BY id DESC LIMIT 30", (session['user_id'],))
    rows = cur.fetchall()
    con.close()
    
    logs = [{"godzina": r[0], "user": r[1], "tresc": r[2], "poziom": r[3]} for r in rows]
    return jsonify(logs)

# ================= ROUTING =================

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        con = sqlite3.connect("database.db")
        cur = con.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (u, generate_password_hash(p)))
            con.commit()
            flash("Konto utworzone!", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError: flash("Nazwa zajęta!", "error")
        finally: con.close()
    return render_template_string(HTML_REGISTER)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        con = sqlite3.connect("database.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (u,))
        user = cur.fetchone()
        con.close()
        if user and check_password_hash(user['password_hash'], p):
            session['user_id'], session['username'] = user['id'], user['username']
            return redirect(url_for('dashboard'))
        flash("Błędne dane.", "error")
    return render_template_string(HTML_LOGIN)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT youtube_channel_id FROM users WHERE id = ?", (session['user_id'],))
    res = cur.fetchone()
    con.close()
    
    current_channel = res[0] if res else None
    bot_running = (session['user_id'] in running_bots and running_bots[session['user_id']].poll() is None)
    return render_template_string(HTML_DASHBOARD, current_channel=current_channel, bot_running=bot_running, active_page='dashboard')

@app.route('/tutorial')
def tutorial():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_TUTORIAL, active_page='tutorial')

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT youtube_channel_id FROM users WHERE id = ?", (session['user_id'],))
    res = cur.fetchone()
    con.close()
    return render_template_string(HTML_PROFILE, current_channel=res[0] if res else None, active_page='profile')

@app.route('/authorize_youtube')
def authorize_youtube():
    if 'user_id' not in session: return redirect(url_for('login'))
    flow = Flow.from_client_secrets_file('web_secret.json', scopes=['https://www.googleapis.com/auth/youtube.readonly'], redirect_uri='http://127.0.0.1:5000/oauth2callback')
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['oauth_state'] = state
    if hasattr(flow, 'code_verifier'): session['code_verifier'] = flow.code_verifier
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if 'user_id' not in session: return redirect(url_for('login'))
    flow = Flow.from_client_secrets_file('web_secret.json', scopes=['https://www.googleapis.com/auth/youtube.readonly'], state=session.get('oauth_state'), redirect_uri='http://127.0.0.1:5000/oauth2callback')
    if 'code_verifier' in session: flow.code_verifier = session['code_verifier']
    try:
        flow.fetch_token(authorization_response=request.url)
        youtube_api = build('youtube', 'v3', credentials=flow.credentials)
        res_yt = youtube_api.channels().list(part="id", mine=True).execute()
        items = res_yt.get("items", [])
        if items:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute("UPDATE users SET youtube_channel_id = ? WHERE id = ?", (items[0]["id"], session['user_id']))
            con.commit()
            con.close()
            flash("Sukces! Kanał podłączony.", "success")
    except Exception as e: flash(f"Problem: {e}", "error")
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    setup_db()
    app.run(debug=True, port=5000)