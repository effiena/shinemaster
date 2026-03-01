from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import datetime  # <- import at top
import random  # optional for invoice number
import os

app = Flask(__name__)    # Initialize DB 

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
def init_db():
    conn = sqlite3.connect("shinemaster.db")
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

# -----------------------------
# Loyalty Logic
# -----------------------------

def process_loyalty(order):
    car_plate = order["car_plate"].replace(" ", "").upper()
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()

    # Get current paid count
    cur.execute("SELECT paid_count FROM loyalty WHERE car_plate=?", (car_plate,))
    row = cur.fetchone()

    if row:
        paid_count = row[0] + 1
    else:
        paid_count = 1

    # Check free wash (6th visit)
    if paid_count == 6:
        order["price"] = 0.00
        order["loyalty_free"] = 1
        paid_count = 0   # reset counter
    else:
        order["loyalty_free"] = 0

    # Status for display
    order["loyalty_count"] = paid_count
    order["loyalty_status"] = "Eligible" if paid_count >= 5 else "Not Eligible"
    order["loyalty_eligible"] = paid_count >= 5

    # Update loyalty table
    if row:
        cur.execute(
            "UPDATE loyalty SET paid_count=? WHERE car_plate=?",
            (paid_count, car_plate)
        )
    else:
        cur.execute(
            "INSERT INTO loyalty (car_plate, paid_count) VALUES (?, ?)",
            (car_plate, paid_count)
        )

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

    # Get form data
    car_plate = request.form["car_plate"]
    car_type = request.form["car_type"]
    service_type = request.form["service_type"]
    price = float(request.form["price"])
    payment_method = request.form["payment_method"]

    # Create order dictionary FIRST
    order = {
        "car_plate": car_plate,
        "car_type": car_type,
        "service_type": service_type,
        "price": price,
        "payment_method": payment_method,
        "loyalty_status": "Not Eligible"
    }

    # Apply loyalty logic if you have the function
    order = process_loyalty(order)

    # Insert order into database
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()

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

    # Get order ID
    order_id = cur.lastrowid

    # Generate invoice number with DATE
    today = datetime.now().strftime("%Y%m%d")
    invoice_no = f"INV{today}{order_id:04d}"

    # Save invoice number to database
    cur.execute(
        "UPDATE orders SET invoice_no=? WHERE id=?",
        (invoice_no, order_id)
    )

    conn.commit()
    conn.close()

    # Add invoice number to order object
    order["invoice_no"] = invoice_no
    order["id"] = order_id

    return render_template("receipt.html", order=order)

@app.route("/check_loyalty/<car_plate>")
def check_loyalty(car_plate):
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT paid_count FROM loyalty WHERE car_plate=?",
        (car_plate.upper(),)
    )

    row = cur.fetchone()
    conn.close()

    if row:
        paid = row[0]
    else:
        paid = 0

    eligible = paid >= 5

    return {
        "paid": paid,
        "eligible": eligible
    }

@app.route("/new-order", methods=["POST"])
def new_order():
    car_plate = request.form["car_plate"]
    service_type = request.form["service_type"]
    price = float(request.form["price"])
    payment_method = request.form["payment_method"]
    car_type = r@app.route("/create_order", methods=["POST"])
def create_order():
    car_plate = request.form["car_plate"].upper()
    car_type = request.form.get("car_type","-")
    service_type = request.form["service_type"]
    price = float(request.form["price"])
    payment_method = request.form["payment_method"]

    order = {
        "car_plate": car_plate,
        "car_type": car_type,
        "service_type": service_type,
        "price": price,
        "payment_method": payment_method
    }

    # Apply loyalty
    order = process_loyalty(order)

    # Save to DB (example)
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (car_plate, car_type, service_type, price, payment_method, payment_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order["car_plate"], order["car_type"], order["service_type"],
          order["price"], order["payment_method"], "Paid"))
    conn.commit()
    conn.close()

    return render_template("receipt.html", order=order)


    # Apply loyalty logic
    order = process_loyalty(order)

    # Insert order WITHOUT invoice first
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()

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

# Generate invoice with DATE + ORDER ID
    order_id = cur.lastrowid
    today = datetime.now().strftime("%Y%m%d")

    invoice_no = f"INV{today}{order_id:04d}"
    order["invoice_no"] = invoice_no

# Update the order with invoice_no
    cur.execute(
        "UPDATE orders SET invoice_no=? WHERE id=?",
        (invoice_no, order_id)
    )

    conn.commit()
    conn.close()

    return render_template("receipt.html", order=order)



def get_payment_report():
    conn = sqlite3.connect("shinemaster.db")
    cur = conn.cursor()

    # Today’s date
    cur.execute("""
        SELECT SUM(price), COUNT(*)
        FROM orders
        WHERE DATE(created_at) = DATE('now')
    """)
    daily_data = cur.fetchone()
    daily_revenue = daily_data[0] or 0
    daily_orders = daily_data[1] or 0

    # Total revenue overall
    cur.execute("SELECT SUM(price) FROM orders")
    total_revenue = cur.fetchone()[0] or 0

    # Revenue by payment method
    cur.execute("""
        SELECT payment_method, SUM(price)
        FROM orders
        GROUP BY payment_method
    """)
    by_method = cur.fetchall()

    conn.close()

    return {
    	"company": COMPANY_INFO,
    	"report_date": datetime.now().strftime("%d %B %Y"),
    	"daily_revenue": daily_revenue,
    	"daily_orders": daily_orders,
    	"total_revenue": total_revenue,
    	"by_method": by_method
}

@app.route("/payment-report")
def payment_report():
    report = get_payment_report()
    return render_template("payment_report.html", report=report)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 3000))  # default 3000 if PORT not set
    app.run(host="0.0.0.0", port=port)
