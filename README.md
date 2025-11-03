# Jersey Stall Manager

Small Flask app for recording jersey sales. This README covers running locally, using Docker, and a quick note about deploying to Render.

## Required environment variables
- `SHEET_KEY` - Google sheet ID used by the app.
- `GOOGLE_CREDS_PATH` - path to `credentials.json` (if mounting a file).
- `GOOGLE_CREDS_JSON` - alternatively, the full JSON content of the Google service account credentials (preferred for some hosts). If set, the app writes it to `credentials.json` at startup.
- `FLASK_SECRET` - Flask secret key.

> Do NOT commit your `credentials.json` or any secrets to git.

## Run locally (quick)
1. Create a Python virtualenv and install deps:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Export environment variables and run with gunicorn:
```bash
export SHEET_KEY="your_sheet_key"
export GOOGLE_CREDS_PATH="/path/to/credentials.json"
export FLASK_SECRET="some-secret"
gunicorn --bind 0.0.0.0:8000 --workers 3 app:app
```

## Run with Docker
Build and run (mount `credentials.json` into the container):
```bash
docker build -t jersey-app:latest .
docker run --rm -p 8080:8080 \
  -e SHEET_KEY=your_sheet_key \
  -e FLASK_SECRET=your_secret \
  -e GOOGLE_CREDS_PATH=/app/credentials.json \
  -v /local/path/credentials.json:/app/credentials.json \
  jersey-app:latest
```

If your platform doesn't allow mounting files, set the `GOOGLE_CREDS_JSON` env var to the JSON contents of the credentials; the app will write it to `credentials.json` on startup.

## Deploy to Render (quick)
- Push repo to GitHub and create a new Web Service on Render.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --bind 0.0.0.0:$PORT --workers 3 app:app`
- Add env vars in Render: `SHEET_KEY`, `FLASK_SECRET`. For credentials either upload the file or set `GOOGLE_CREDS_JSON` (secret) containing the JSON.

## Security
- Keep `credentials.json` and any environment secrets out of git. Use the platform's secret store.

If you'd like, I can add a Dockerfile and Procfile to the repo next.
# 🏟️ Jersey Stall Manager

Inventory & Sales Manager built with Flask + Google Sheets

Overview
--------
This is a small Flask app that uses Google Sheets as the backend database. It provides:

- Catalogue management (Stock sheet)
- Sales & billing (Sales sheet)
- Customer tracking (Customers sheet)
- Dashboard analytics (plotly charts)

Setup
-----

1) Google Sheets

Create a spreadsheet with the following sheets and headers (exact names recommended):

- `Stock`: Team | Kit | S | M | L | XL | XXL | Total | Price
- `Sales`: Timestamp | Team | Kit | Size | Quantity | Sold Price | Discount | Deal Type | Buyer Name | Total
- `Customers`: Name | Contact | TotalPurchases | TotalSpent | LastPurchase

Share the spreadsheet with your service account email (Editor access).

Recommended extra sheets (optional):

- `Suppliers` — supplier contact info for bulk orders
- `Returns` — logs for returned items with reason/status
- `PricingHistory` — optional audit of price changes
- `Settings` — small key/value for thresholds like low-stock-alert

These are optional but helpful for scaling the operations. The core app only requires `Stock`, `Sales`, and `Customers`.

2) Google Cloud

Create a GCP project, enable Sheets & Drive APIs, create a Service Account and download the JSON key as `credentials.json`.

3) Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SHEET_KEY="<YOUR_SPREADSHEET_KEY>"
# ensure credentials.json is placed in repo root or set GOOGLE_CREDS_PATH
python app.py
```

Notes
-----

- Do not commit `credentials.json` to source control. Keep it private.
- The app expects the headers to match the names above. If you change column names, update `gsheet.py` accordingly.

Troubleshooting
---------------

- If the app raises a credentials error, ensure `credentials.json` exists and the service account has access to the sheet.
- If imports fail, install dependencies from `requirements.txt` in an activated virtualenv.

