from flask import Flask, jsonify, request, session, redirect, url_for, render_template_string
from flask_cors import CORS
import requests
import urllib3
import os
import hashlib
import secrets

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
CORS(app)

# ─────────────────────────────────────────────
#  CONFIGURATION — set as environment variables on Render
# ─────────────────────────────────────────────
CATALOGUE_URL   = os.environ.get("CATALOGUE_URL",   "https://creds.curtin.edu.au")
CATALOGUE_TOKEN = os.environ.get("CATALOGUE_TOKEN", "d3ca3e2dd2048c80f46898a36c43f46a")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "SFL2026!")  # Set this in Render
# ─────────────────────────────────────────────

HEADERS = {"Authorization": f'Token token="{CATALOGUE_TOKEN}"'}

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SFL — Sign In</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#111;color:#f0f0f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
.card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:2.5rem;width:100%;max-width:400px}
.header{display:flex;align-items:center;gap:10px;margin-bottom:2rem}
.header-divider{width:1px;height:20px;background:#333}
.header-title{font-size:12px;color:#999;letter-spacing:.02em}
h1{font-size:20px;font-weight:600;margin-bottom:6px;letter-spacing:-.02em}
.subtitle{font-size:13px;color:#888;margin-bottom:1.75rem;line-height:1.5}
label{display:block;font-size:11px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
input[type=password]{width:100%;padding:10px 12px;background:#222;border:1px solid #333;border-radius:8px;font-size:14px;color:#f0f0f0;outline:none;font-family:inherit;margin-bottom:1rem}
input[type=password]:focus{border-color:#cfa050}
button{width:100%;padding:11px;background:#cfa050;color:#111;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
button:hover{background:#d9aa60}
.error{background:rgba(224,85,85,.1);border:1px solid rgba(224,85,85,.3);border-radius:8px;padding:10px 14px;font-size:13px;color:#e05555;margin-bottom:1rem}
.footer{text-align:center;font-size:11px;color:#444;margin-top:1.5rem}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <span style="font-size:18px;font-weight:800;color:#f0f0f0;letter-spacing:-.5px">CURTIN</span>
    <span style="display:inline-block;width:2px;height:18px;background:#cfa050;margin:0 6px;vertical-align:middle;border-radius:1px"></span>
    <span style="font-size:10px;font-weight:600;color:#cfa050;letter-spacing:.12em;text-transform:uppercase">SHORT FORM LEARNING</span>
    <div class="header-divider"></div>
    <span class="header-title">Enrolment Report</span>
  </div>
  <h1>Sign in</h1>
  <p class="subtitle">Enter the access password to view the SFL Monthly Enrolment Report.</p>
  {% if error %}
  <div class="error">Incorrect password. Please try again.</div>
  {% endif %}
  <form method="POST" action="/login">
    <label for="password">Password</label>
    <input type="password" id="password" name="password" placeholder="Enter access password" autofocus/>
    <button type="submit">Sign in</button>
  </form>
  <div class="footer">Curtin University — Short Form Learning</div>
</div>
</body>
</html>"""


def check_auth():
    return session.get("authenticated") is True


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500


# ── Auth routes ──────────────────────────────

@app.route("/")
def index():
    if not check_auth():
        return redirect(url_for("login"))
    # Serve the dashboard HTML
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = False
    if request.method == "POST":
        password = request.form.get("password", "")
        if ACCESS_PASSWORD and hash_password(password) == hash_password(ACCESS_PASSWORD):
            session["authenticated"] = True
            session.permanent = True
            return redirect(url_for("dashboard"))
        else:
            error = True
    return render_template_string(LOGIN_PAGE, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not check_auth():
        return redirect(url_for("login"))
    # Read and serve the dashboard HTML file
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path) as f:
            return f.read()
    return "<h1>Dashboard not found</h1><p>Please upload dashboard.html to the repo.</p>", 404


# ── API routes (require auth) ─────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "token_set": bool(CATALOGUE_TOKEN), "auth": check_auth()})


@app.route("/enrolments")
def enrolments():
    if not check_auth():
        return jsonify({"error": "Not authenticated"}), 401
    if not CATALOGUE_TOKEN:
        return jsonify({"error": "CATALOGUE_TOKEN not set"}), 500

    page     = request.args.get("page", 1, type=int)
    url      = f"{CATALOGUE_URL}/api/v1/enrollments?per_page=100&page={page}"

    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=25)
        if r.status_code == 401:
            return jsonify({"error": "Invalid API token"}), 401
        r.raise_for_status()
        data = r.json()
        page_data = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), []
        )
        links = {
            p.split(";")[1].strip().strip('rel="'): p.split(";")[0].strip().strip("<>")
            for p in r.headers.get("Link", "").split(",") if ";" in p
        }
        has_next = "next" in links
        return jsonify({"enrollments": page_data, "has_next": has_next, "page": page})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request to Canvas timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
