Render deployment notes

Start command (Procfile):

web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 3 --worker-class gthread --threads 4 --timeout 120

Environment variables to set in Render dashboard:
- SHEET_KEY: your Google Sheets key (or URL)
- GOOGLE_CREDS_JSON: (optional) full credentials JSON content if not uploading credentials.json
- FLASK_SECRET: secret key for Flask sessions

Recommendations:
- Use the `/health` endpoint for Render health checks (it is lightweight and does not call Google APIs).
- Check Render logs for any logged tracebacks emitted by the global exception handler.
- If you see memory OOMs, consider reducing worker count or upgrading the plan.
- Add retries/backoff around gspread calls if you see transient Google API errors (429/5xx).
