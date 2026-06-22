# Deploy SFL Enrolment Web App to Render

## What this is
A secure Flask web app serving the SFL Monthly Enrolment Report behind a
login page. Staff enter a shared password to access the dashboard.

## Steps

### 1 — Push to GitHub
Create/update your GitHub repo (e.g. sfl-enrolment-api) with these files:
- app.py
- dashboard.html
- requirements.txt
- Procfile
- render.yaml

### 2 — Set environment variables in Render
Go to your Render service → Environment tab and set:

  CATALOGUE_TOKEN  = your Canvas Catalogue API token
  CATALOGUE_URL    = https://creds.curtin.edu.au
  ACCESS_PASSWORD  = your chosen staff password (e.g. SFL2026!)
  SECRET_KEY       = any long random string (for session encryption)

To generate a good SECRET_KEY, run this in Terminal:
  python3 -c "import secrets; print(secrets.token_hex(32))"

### 3 — Deploy
Push to GitHub — Render auto-redeploys.
Your app will be at: https://sfl-monthly-report-1.onrender.com

### 4 — Share with staff
Send staff the URL and password. They log in once per browser session.
To sign out, click "Sign out" in the top right corner.

### Changing the password
Update ACCESS_PASSWORD in Render environment variables.
All staff will need the new password on their next login.

### Security notes
- The password is stored as an environment variable, never in code
- Sessions use a secure signed cookie (SECRET_KEY)
- The Canvas API token is never sent to the browser
- The dashboard is only accessible after authentication
