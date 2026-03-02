from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

COMPANY_INFO = {
    "name": "SHINEMASTER AUTO",
    "address": "No.68 JALAN PUTRA 1, TAMAN TAN SRI YAACOB, 81300 SKUDAI, JOHOR BAHRU",
    "contact": "018-2096907"
}

@app.context_processor
def inject_company():
    return dict(company=COMPANY_INFO)

# -----------------------------
# Initialize Database
# -----------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "shinemaster.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Orders table
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_plate TEXT,
            contact_number TEXT,
            address TEXT,
            service_type TEXT,
            price REAL,
            payment_method TEXT,
            payment_status TEXT,
            loyalty_status TEXT DEFAULT 'Not Eligible',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            car_type TEXT,
            invoice_no TEXT
        )
    """)
    # Loyalty table
    c.execute("""
        CREATE TABLE IF NOT EXISTS loyalty (
            car_plate TEXT PRIMARY KEY,
            paid_count INTEGER
        )
    """)
    conn.commit()
    conn.close()

# run database initialization
    init_db()

@app.route("/favicon.ico")
def favicon():
    return redirect("/static/images/favicon.ico")

# -----------------------------
# Loyalty Logic
# -----------------------------
def process_loyalty(order):
    car_plate = order["car_plate"].replace(" ", "").upper()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT paid_count FROM loyalty WHERE car_plate=?", (car_plate,))
    row = cur.fetchone()

    if row:
        paid_count = row[0] + 1
    else:
        paid_count = 1

    # Free wash on 6th visit
    if paid_count == 6:
        order["price"] = 0.0
        order["loyalty_free"] = 1
        paid_count = 0
    else:
        order["loyalty_free"] = 0

    order["loyalty_count"] = paid_count
    order["loyalty_status"] = "Eligible" if paid_count >= 5 else "Not Eligible"
    order["loyalty_eligible"] = paid_count >= 5

    if row:
        cur.execute("UPDATE loyalty SET paid_count=? WHERE car_plate=?", (paid_count, car_plate))
    else:
        cur.execute("INSERT INTO loyalty (car_plate, paid_count) VALUES (?, ?)", (car_plate, paid_count))

    conn.commit()
    conn.close()

    return order

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("new_order.html")

@app.route("/create_order", methods=["POST"])
def create_order():
    car_plate = request.form["car_plate"].upper()
    car_type = request.form.get("car_type", "-")
    service_type = request.form["service_type"]
    price = float(request.form["price"])
    payment_method = request.form["payment_method"]

    order = {
        "car_plate": car_plate,
        "car_type": car_type,
        "service_type": service_type,
        "price": price,
        "payment_method": payment_method,
        "loyalty_status": "Not Eligible"
    }

    order = process_loyalty(order)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert order
    cur.execute("""
        INSERT INTO orders
        (car_plate, car_type, service_type, price, payment_method, payment_status, loyalty_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        order["car_plate"],
        order["car_type"],
        order["service_type"],
        order["price"],
        order["payment_method"],
        "Paid",
        order["loyalty_status"]
    ))

    conn.commit()
    order_id = cur.lastrowid

    # Generate invoice
    today = datetime.now().strftime("%Y%m%d")
    invoice_no = f"INV{today}{order_id:04d}"

    cur.execute("UPDATE orders SET invoice_no=? WHERE id=?", (invoice_no, order_id))
    conn.commit()
    conn.close()

    order["invoice_no"] = invoice_no
    order["id"] = order_id

    return render_template("receipt.html", order=order)

@app.route("/check_loyalty/<car_plate>")
def check_loyalty(car_plate):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT paid_count FROM loyalty WHERE car_plate=?", (car_plate.upper(),))
    row = cur.fetchone()
    conn.close()

    paid = row[0] if row else 0
    eligible = paid >= 5

    return {"paid": paid, "eligible": eligible}

@app.route("/payment-report")
def payment_report():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Daily revenue
    cur.execute("SELECT SUM(price), COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')")
    daily_data = cur.fetchone()
    daily_revenue = daily_data[0] or 0
    daily_orders = daily_data[1] or 0

    # Total revenue
    cur.execute("SELECT SUM(price) FROM orders")
    total_revenue = cur.fetchone()[0] or 0

    # Revenue by payment method
    cur.execute("SELECT payment_method, SUM(price) FROM orders GROUP BY payment_method")
    by_method = cur.fetchall()

    conn.close()

    report = {
        "company": COMPANY_INFO,
        "report_date": datetime.now().strftime("%d %B %Y"),
        "daily_revenue": daily_revenue,
        "daily_orders": daily_orders,
        "total_revenue": total_revenue,
        "by_method": by_method
    }

    return render_template("payment_report.html", report=report)

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
