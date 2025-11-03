import os
import re
import pandas as pd
from datetime import datetime

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except Exception:
    gspread = None


class GSheetClient:
    """Wrapper around gspread for Stock, Sales, Customers sheets.

    Expects a `credentials.json` file in the repo root (or path set by
    GOOGLE_APPLICATION_CREDENTIALS). Also expects an environment variable
    SHEET_KEY or that the app user will pass a spreadsheet key.
    """

    def __init__(self, spreadsheet_key=None, creds_path="credentials.json"):
        self.creds_path = creds_path
        self.spreadsheet_key = spreadsheet_key or os.environ.get("SHEET_KEY")
        self.gc = None
        self.sheet = None
        if gspread is None:
            raise RuntimeError("gspread or oauth2client not installed")
        self._connect()

    def _connect(self):
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive',
        ]
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(
                f"Service account credentials not found at {self.creds_path}. Place your credentials.json there."
            )
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
        self.gc = gspread.authorize(creds)
        if not self.spreadsheet_key:
            raise RuntimeError("Spreadsheet key not provided. Set SHEET_KEY env or pass spreadsheet_key.")
        # Accept either a raw spreadsheet ID or a full Google Sheets URL.
        key_to_use = self.spreadsheet_key
        # If user passed a URL containing '/d/<id>/', extract the id
        m = re.search(r'/d/([a-zA-Z0-9-_]+)', key_to_use)
        if m:
            key_to_use = m.group(1)

        # Try opening the spreadsheet and provide a clearer error if it fails.
        try:
            self.sheet = self.gc.open_by_key(key_to_use)
        except Exception as e:
            # Common causes: wrong spreadsheet id, service account not shared, API not enabled
            msg = (
                f"Unable to open spreadsheet with key '{self.spreadsheet_key}' (attempted id '{key_to_use}'). "
                "Common causes: wrong spreadsheet id, the service account email was not shared with the sheet, "
                "or Sheets API is not enabled for the project. \nOriginal error: " + repr(e)
            )
            raise RuntimeError(msg) from e

    # ---- Stock operations (sheet named 'Stock') ----
    def get_stock_df(self):
        ws = self.sheet.worksheet('Stock')
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # normalize column names
        return df

    def update_stock_cell(self, row_index, col_name, value):
        ws = self.sheet.worksheet('Stock')
        # find column index
        headers = ws.row_values(1)
        try:
            col_idx = headers.index(col_name) + 1
        except ValueError:
            raise KeyError(f"Column {col_name} not found in Stock sheet")
        ws.update_cell(row_index + 1, col_idx, str(value))

    def find_stock_row(self, team, kit):
        ws = self.sheet.worksheet('Stock')
        records = ws.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get('Team')) == str(team) and str(r.get('Kit')) == str(kit):
                return i - 1, r  # zero-based df index, record
        return None, None

    def add_stock_item(self, item_dict):
        ws = self.sheet.worksheet('Stock')
        # Append row in the same column order as header
        headers = ws.row_values(1)
        row = [item_dict.get(h, '') for h in headers]
        ws.append_row(row)

    def set_stock_row(self, row_index, record_dict):
        ws = self.sheet.worksheet('Stock')
        headers = ws.row_values(1)
        row = [record_dict.get(h, '') for h in headers]
        ws.update(f'A{row_index+1}:{chr(65+len(headers)-1)}{row_index+1}', [row])

    # ---- Sales operations ----
    def add_sale(self, sale_dict):
        ws = self.sheet.worksheet('Sales')
        headers = ws.row_values(1)
        row = [sale_dict.get(h, '') for h in headers]
        ws.append_row(row)

    def get_sales_df(self):
        ws = self.sheet.worksheet('Sales')
        data = ws.get_all_records()
        return pd.DataFrame(data)

    # ---- Customers ----
    def get_customers_df(self):
        ws = self.sheet.worksheet('Customers')
        data = ws.get_all_records()
        return pd.DataFrame(data)

    def upsert_customer(self, customer_name, contact='', add_count=0, add_spent=0.0):
        ws = self.sheet.worksheet('Customers')
        records = ws.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get('Name')).strip().lower() == str(customer_name).strip().lower():
                # update counts
                total_purchases = int(r.get('TotalPurchases', 0)) + int(add_count)
                total_spent = float(r.get('TotalSpent', 0.0)) + float(add_spent)
                ws.update_cell(i, ws.row_values(1).index('TotalPurchases') + 1, str(total_purchases))
                ws.update_cell(i, ws.row_values(1).index('TotalSpent') + 1, str(total_spent))
                ws.update_cell(i, ws.row_values(1).index('LastPurchase') + 1, datetime.utcnow().isoformat())
                return
        # not found -> append
        headers = ws.row_values(1)
        row = {h: '' for h in headers}
        row['Name'] = customer_name
        row['Contact'] = contact
        row['TotalPurchases'] = add_count
        row['TotalSpent'] = add_spent
        row['LastPurchase'] = datetime.utcnow().isoformat()
        ws.append_row([row.get(h, '') for h in headers])
