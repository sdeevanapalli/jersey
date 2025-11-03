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

