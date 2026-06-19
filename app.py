from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)  # Allow all origins — security handled by API token on Canvas side

# ─────────────────────────────────────────────
#  CONFIGURATION — set as environment variables on Render
# ─────────────────────────────────────────────
CATALOGUE_URL   = os.environ.get("CATALOGUE_URL",   "https://creds.curtin.edu.au")
CATALOGUE_TOKEN = os.environ.get("CATALOGUE_TOKEN", "")
ACCOUNT_ID      = os.environ.get("ACCOUNT_ID",      "1")
# ─────────────────────────────────────────────

HEADERS = {"Authorization": f'Token token="{CATALOGUE_TOKEN}"'}


def get_all_pages(url):
    results = []
    while url:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=30)
        if r.status_code == 401:
            return None, "Invalid API token"
        if r.status_code == 403:
            return None, "Insufficient permissions"
        r.raise_for_status()
        data = r.json()
        page = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), []
        )
        results.extend(page)
        links = {
            p.split(";")[1].strip().strip('rel="'): p.split(";")[0].strip().strip("<>")
            for p in r.headers.get("Link", "").split(",") if ";" in p
        }
        url = links.get("next")
    return results, None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/enrolments")
def enrolments():
    data, err = get_all_pages(f"{CATALOGUE_URL}/api/v1/enrollments?per_page=100")
    if err:
        return jsonify({"error": err}), 401
    return jsonify({"enrollments": data})


@app.route("/users/<int:canvas_user_id>")
def user_profile(canvas_user_id):
    r = requests.get(
        f"{CATALOGUE_URL}/api/v1/users?canvas_user_id={canvas_user_id}",
        headers=HEADERS, verify=False, timeout=30
    )
    if r.status_code == 200:
        data = r.json()
        users = data if isinstance(data, list) else data.get("users", [])
        return jsonify({"user": users[0] if users else {}})
    return jsonify({"user": {}}), r.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
