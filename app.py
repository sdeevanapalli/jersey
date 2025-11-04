from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
import os
import io
import pandas as pd
from datetime import datetime
from gsheet import GSheetClient
import plotly.express as px
from dotenv import load_dotenv
import logging
import traceback

load_dotenv()

# If the deployment platform doesn't support uploading files, allow the
# full Google credentials JSON to be provided via the `GOOGLE_CREDS_JSON`
# environment variable. On startup we write it to `credentials.json` and
# set `GOOGLE_CREDS_PATH` so existing code can find it.
creds_json = os.environ.get('GOOGLE_CREDS_JSON')
if creds_json and not os.path.exists('credentials.json'):
    with open('credentials.json', 'w') as f:
        f.write(creds_json)
    os.environ['GOOGLE_CREDS_PATH'] = os.path.abspath('credentials.json')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

# Basic logging configuration - ensure logs go to stdout for Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
app.logger.setLevel(logging.INFO)


# Lightweight health check used by the platform liveness probe. Should not
# exercise external services.
@app.route('/health')
def health():
    return 'ok', 200


# Global exception handler: log full traceback so Render logs capture the root cause
@app.errorhandler(Exception)
def handle_exception(err):
    # Log the exception and traceback to both logging and Flask logger
    tb = traceback.format_exc()
    logging.error('Unhandled exception: %s\n%s', err, tb)
    app.logger.error('Unhandled exception: %s\n%s', err, tb)
    # Return a generic 500 response; do not expose internals to clients
    return 'Internal Server Error', 500

# Spreadsheet key must be provided via env SHEET_KEY or edit below
SPREADSHEET_KEY = os.environ.get('SHEET_KEY', None)

# Log basic startup info (mask sensitive values)
sk = SPREADSHEET_KEY or os.environ.get('SHEET_KEY') or 'NOT SET'
masked_sk = sk
if sk != 'NOT SET' and len(str(sk)) > 8:
    masked_sk = str(sk)[:4] + '...' + str(sk)[-4:]
creds_path = os.environ.get('GOOGLE_CREDS_PATH', 'credentials.json')
app.logger.info('Starting app; SHEET_KEY=%s, creds_path=%s', masked_sk, creds_path)


def gsheet_client():
    creds = os.environ.get('GOOGLE_CREDS_PATH', 'credentials.json')
    return GSheetClient(spreadsheet_key=SPREADSHEET_KEY, creds_path=creds)


def get_catalogue():
    gs = gsheet_client()
    df = gs.get_stock_df()
    # Keep original wide format: Team | Kit | S | M | L | XL | XXL | Total | Price
    return df


@app.route('/')
def dashboard():
    gs = gsheet_client()
    sales = gs.get_sales_df()
    stock = gs.get_stock_df()
    # Basic metrics
    total_revenue = 0.0
    total_sales = 0
    top_item = None
    top_buyer = None
    if not sales.empty:
        # ensure numeric
        sales['Total'] = pd.to_numeric(sales.get('Total', 0), errors='coerce').fillna(0)
        total_revenue = float(sales['Total'].sum())
        # Prefer total items sold (sum of Quantity) if available, otherwise fall back to row count
        if 'Quantity' in sales.columns:
            total_sales = int(pd.to_numeric(sales['Quantity'], errors='coerce').fillna(0).sum())
        else:
            total_sales = len(sales)
        grouped = sales.groupby(['Team', 'Kit'])['Quantity'].sum().reset_index()
        if not grouped.empty:
            best = grouped.sort_values('Quantity', ascending=False).iloc[0]
            top_item = f"{best['Team']} - {best['Kit']}"
        buyers = sales.groupby('Buyer Name').size().sort_values(ascending=False)
        if not buyers.empty:
            top_buyer = buyers.index[0]

    # low stock: any size column <=2
    low_stock = []
    size_cols = [c for c in stock.columns if c.strip() in ['S', 'M', 'L', 'XL', 'XXL']]
    for _, r in stock.iterrows():
        for c in size_cols:
            try:
                val = int(r.get(c) or 0)
            except Exception:
                val = 0
            if val <= 2:
                low_stock.append({'Team': r.get('Team'), 'Kit': r.get('Kit'), 'Size': c, 'Qty': val})

    # sample chart: revenue per team
    revenue_chart_html = ''
    try:
        if not sales.empty:
            grp = (
                sales.groupby('Team', group_keys=False)['Total']
                .apply(lambda x: pd.to_numeric(x, errors='coerce').fillna(0).sum())
                .reset_index(name='Revenue')
            )
            fig = px.bar(grp, x='Team', y='Revenue', title='Revenue by Team')
            revenue_chart_html = fig.to_html(full_html=False)
    except Exception:
        revenue_chart_html = ''

    return render_template('dashboard.html', total_revenue=total_revenue, total_sales=total_sales,
                           top_item=top_item, top_buyer=top_buyer, low_stock=low_stock,
                           revenue_chart=revenue_chart_html)


@app.route('/catalogue')
def catalogue():
    df = get_catalogue()
    query = request.args.get('q', '').lower()
    if query:
        df = df[df.apply(lambda r: query in str(r.get('Team','')).lower() or query in str(r.get('Kit','')).lower(), axis=1)]
    return render_template('catalogue.html', table=df.to_dict(orient='records'), columns=list(df.columns))


@app.route('/record-sale', methods=['GET', 'POST'])
def record_sale():
    gs = gsheet_client()
    stock = gs.get_stock_df()
    size_cols = [c for c in stock.columns if c.strip() in ['S', 'M', 'L', 'XL', 'XXL']]

    if request.method == 'POST':
        # Expect arrays for multiple items. Support a single combined select (combined[])
        # where each option value is encoded as "Team|||Kit". Fall back to separate
        # team[] and kit[] fields if present.
        combined = request.form.getlist('combined[]')
        if combined:
            teams = []
            kits = []
            for c in combined:
                if '|||' in c:
                    t, k = c.split('|||', 1)
                else:
                    # fallback: try to split on first space (not ideal) or put whole into team
                    parts = c.split(' - ', 1)
                    if len(parts) == 2:
                        t, k = parts[0], parts[1]
                    else:
                        t, k = c, ''
                teams.append(t)
                kits.append(k)
        else:
            # legacy form fields
            teams = request.form.getlist('team[]')
            kits = request.form.getlist('kit[]')
        sizes = request.form.getlist('size[]')
        qtys = request.form.getlist('quantity[]')
        sold_prices = request.form.getlist('sold_price[]')
        buyer = request.form.get('buyer')
        discount = request.form.get('discount') or 0
        deal_type = request.form.get('deal_type') or ''

        # validate lengths
        items = []
        for i in range(len(teams)):
            try:
                q = int(qtys[i])
            except Exception:
                q = 0
            items.append({'team': teams[i], 'kit': kits[i], 'size': sizes[i], 'qty': q, 'sold_price': sold_prices[i]})

        # validate stock
        errors = []
        for it in items:
            row_idx, rec = gs.find_stock_row(it['team'], it['kit'])
            if rec is None:
                errors.append(f"Item not found: {it['team']} / {it['kit']}")
                continue
            avail = int(rec.get(it['size'], 0) or 0)
            if it['qty'] > avail:
                errors.append(f"Not enough stock for {it['team']} {it['kit']} size {it['size']}: available {avail}")

        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('record_sale'))

        total_order = 0.0
        # perform updates
        for it in items:
            row_idx, rec = gs.find_stock_row(it['team'], it['kit'])
            # decrement
            old = int(rec.get(it['size'], 0) or 0)
            new = old - it['qty']
            # update the cell
            gs.update_stock_cell(row_idx, it['size'], new)
            # update Total column if exists
            try:
                total_old = int(rec.get('Total', 0) or 0)
            except Exception:
                total_old = 0
            gs.update_stock_cell(row_idx, 'Total', total_old - it['qty'])

            sold = float(it['sold_price'] or 0)
            line_total = sold * it['qty'] - float(discount or 0)
            total_order += line_total
            sale_row = {
                'Timestamp': datetime.utcnow().isoformat(),
                'Team': it['team'],
                'Kit': it['kit'],
                'Size': it['size'],
                'Quantity': it['qty'],
                'Sold Price': it['sold_price'],
                'Discount': discount,
                'Deal Type': deal_type,
                'Buyer Name': buyer,
                'Total': line_total,
            }
            gs.add_sale(sale_row)
            # update customer
            gs.upsert_customer(buyer, add_count=it['qty'], add_spent=line_total)

        flash(f'Sale recorded. Total: {total_order}', 'success')
        return render_template('sale_confirmation.html', items=items, total=total_order, buyer=buyer)

    # GET
    # Build combined options from stock rows so the UI can show a single select
    # with entries like "Team Kit" while the value encodes both parts as
    # "Team|||Kit" for reliable server-side parsing.
    combined_options = []
    seen = set()
    for _, r in stock.iterrows():
        team = str(r.get('Team') or '')
        kit = str(r.get('Kit') or '')
        label = f"{team} {kit}".strip()
        value = f"{team}|||{kit}"
        if value not in seen:
            seen.add(value)
            combined_options.append({'value': value, 'label': label})

    return render_template('record_sale.html', combined_options=combined_options, sizes=size_cols)


@app.route('/customers')
def customers():
    gs = gsheet_client()
    df = gs.get_customers_df()
    return render_template('customers.html', customers=df.to_dict(orient='records'), columns=list(df.columns))


@app.route('/export/<which>')
def export_csv(which):
    gs = gsheet_client()
    if which == 'stock':
        df = gs.get_stock_df()
    elif which == 'sales':
        df = gs.get_sales_df()
    else:
        return "Unknown export", 400

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': f'attachment;filename={which}.csv'
    })


@app.route('/debug/sheet')
def debug_sheet():
    """Safe debug endpoint: shows masked SHEET_KEY and tests opening the spreadsheet.

    Does NOT return credentials or any sensitive content. Useful to confirm the key is correct
    and that the service account can access the spreadsheet.
    """
    key = SPREADSHEET_KEY or 'NOT SET'
    masked = key
    if key != 'NOT SET' and len(key) > 8:
        masked = key[:4] + '...' + key[-4:]
    try:
        gs = gsheet_client()
        # attempt to list worksheets
        titles = [ws.title for ws in gs.sheet.worksheets()]
        return {
            'sheet_key': masked,
            'status': 'ok',
            'worksheets': titles,
        }
    except Exception as e:
        return {
            'sheet_key': masked,
            'status': 'error',
            'error': str(e)
        }, 400


if __name__ == '__main__':
    app.run(debug=True, port=8080)
