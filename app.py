from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

CATALOGUE_URL   = os.environ.get("CATALOGUE_URL",   "https://creds.curtin.edu.au")
CATALOGUE_TOKEN = os.environ.get("CATALOGUE_TOKEN", "d3ca3e2dd2048c80f46898a36c43f46a")
HEADERS = {"Authorization": f'Token token="{CATALOGUE_TOKEN}"'}


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "token_set": bool(CATALOGUE_TOKEN)})


@app.route("/enrolments")
def enrolments():
    if not CATALOGUE_TOKEN:
        return jsonify({"error": "CATALOGUE_TOKEN not set"}), 500

    # Accept optional page param so frontend can fetch in chunks
    page     = request.args.get("page", 1, type=int)
    per_page = 100
    url      = f"{CATALOGUE_URL}/api/v1/enrollments?per_page={per_page}&page={page}"

    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=25)
        if r.status_code == 401:
            return jsonify({"error": "Invalid API token"}), 401
        r.raise_for_status()
        data = r.json()
        page_data = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), []
        )
        # Check if there's a next page
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
