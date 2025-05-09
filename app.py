from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
from mysql.connector import Error
import bcrypt
import json

app = Flask(__name__)
app.secret_key = 'srm12345'  # Replace with a random string for session security

# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",  # Replace with your MySQL username
            password="medusa",  # Replace with your MySQL password
            database="coldstoredb"
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Login page
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT UserID, Password FROM user WHERE Username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['Password'].encode('utf-8')):
            session['user_id'] = user['UserID']
            return jsonify({"message": "Login successful", "redirect": url_for('dashboard')})
        return jsonify({"error": "Invalid credentials"}), 401
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Middleware to protect routes
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard_stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM warehouse")
    warehouses = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM product")
    products = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM customer_order")
    orders = cursor.fetchone()['total']
    cursor.close()
    conn.close()
    
    return jsonify({
        "warehouses": warehouses,
        "products": products,
        "orders": orders
    })

# Warehouse Management
@app.route('/warehouses')
@login_required
def warehouses():
    return render_template('warehouses.html')

@app.route('/api/warehouses', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_warehouses():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT WID, Name, Location, Capacity, Temperature_Range FROM warehouse")
        warehouses = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(warehouses)
    
    elif request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO warehouse (Name, Location, Capacity, Temperature_Range)
            VALUES (%s, %s, %s, %s)
        """, (data['Name'], data['Location'], data['Capacity'], data['Temperature_Range']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Warehouse added"})
    
    elif request.method == 'PUT':
        data = request.json
        cursor.execute("""
            UPDATE warehouse SET Name = %s, Location = %s, Capacity = %s, Temperature_Range = %s
            WHERE WID = %s
        """, (data['Name'], data['Location'], data['Capacity'], data['Temperature_Range'], data['WID']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Warehouse updated"})
    
    elif request.method == 'DELETE':
        wid = request.args.get('wid')
        cursor.execute("DELETE FROM warehouse WHERE WID = %s", (wid,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Warehouse deleted"})

# Product Management
@app.route('/products')
@login_required
def products():
    return render_template('products.html')

@app.route('/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_products():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("""
            SELECT p.ProductID, p.Name, p.Description, p.Price, p.Temp_Requirement, s.Name AS Supplier
            FROM product p JOIN supplier s ON p.SupplierID = s.SupplierID
        """)
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(products)
    
    elif request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO product (Name, Description, Price, Temp_Requirement, SupplierID)
            VALUES (%s, %s, %s, %s, %s)
        """, (data['Name'], data['Description'], data['Price'], data['Temp_Requirement'], data['SupplierID']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Product added"})
    
    elif request.method == 'PUT':
        data = request.json
        cursor.execute("""
            UPDATE product SET Name = %s, Description = %s, Price = %s, Temp_Requirement = %s, SupplierID = %s
            WHERE ProductID = %s
        """, (data['Name'], data['Description'], data['Price'], data['Temp_Requirement'], data['SupplierID'], data['ProductID']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Product updated"})
    
    elif request.method == 'DELETE':
        pid = request.args.get('pid')
        cursor.execute("DELETE FROM product WHERE ProductID = %s", (pid,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Product deleted"})

# Order Management
@app.route('/orders')
@login_required
def orders():
    return render_template('orders.html')
@app.route('/api/orders', methods=['GET', 'PUT', 'POST'])
@login_required
def manage_orders():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        status = request.args.get('status', 'all')
        if status == 'active':
            cursor.execute("SELECT OrderID, CustomerName, Order_Date, Total_Amount, Status FROM activeorders")
        elif status == 'completed':
            cursor.execute("SELECT OrderID, CustomerName, Order_Date, Total_Amount, Status FROM completedorders")
        else:
            cursor.execute("""
                SELECT co.OrderID, c.Name AS CustomerName, co.Order_Date, co.Total_Amount, co.Status
                FROM customer_order co JOIN customer c ON co.CustomerID = c.CustomerID
            """)
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(orders)
    
    elif request.method == 'PUT':
        data = request.json
        cursor.execute("""
            UPDATE customer_order SET Status = %s WHERE OrderID = %s
        """, (data['Status'], data['OrderID']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Order status updated"})
    
    elif request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO customer_order (CustomerID, Order_Date, Total_Amount, Status)
            VALUES (%s, NOW(), %s, 'Pending')
        """, (data['CustomerID'], data['Total_Amount']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Order added"})
    
# Inventory Log
@app.route('/inventory')
@login_required
def inventory():
    return render_template('inventory.html')

@app.route('/api/inventory_logs', methods=['GET'])
@login_required
def get_inventory_logs():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT il.InventoryLogID, p.Name AS Product, w.Name AS Warehouse, il.Change_Quantity, il.Log_Date, il.Note
        FROM inventorylog il
        JOIN product p ON il.ProductID = p.ProductID
        JOIN warehouse w ON il.WarehouseID = w.WID
    """
    params = []
    if 'search' in request.args:
        query += " WHERE p.Name LIKE %s OR w.Name LIKE %s"
        params = [f"%{request.args['search']}%", f"%{request.args['search']}%"]
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(logs)

# Temperature Log
@app.route('/temperature')
@login_required
def temperature():
    return render_template('temperature.html')

@app.route('/api/temperature_logs', methods=['GET'])
@login_required
def get_temperature_logs():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT t.LogID, t.SensorID, t.Recorded_Temp, t.Timestamp, w.Name AS Warehouse
        FROM temperature_log t
        JOIN temperature_sensor ts ON t.SensorID = ts.SensorID
        JOIN warehouse w ON ts.WarehouseID = w.WID
    """
    params = []
    if 'max_temp' in request.args:
        query += " WHERE t.Recorded_Temp <= %s"
        params = [float(request.args['max_temp'])]
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(logs)

# Feedback
@app.route('/feedback')
@login_required
def feedback():
    return render_template('feedback.html')

@app.route('/api/feedback', methods=['GET', 'POST'])
@login_required
def manage_feedback():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT FeedbackID, Comment, Rating, Feedback_Date FROM feedback WHERE UserID = %s", (session['user_id'],))
        feedback = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(feedback)
    
    elif request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO feedback (UserID, Comment, Rating, Feedback_Date)
            VALUES (%s, %s, %s, NOW())
        """, (session['user_id'], data['Comment'], data['Rating']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Feedback submitted"})
@app.route('/api/stock_summary', methods=['GET'])
@login_required
def get_stock_summary():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT StockID, Product, Warehouse, Quantity
        FROM stocksummary
        WHERE Quantity > 0
        ORDER BY Quantity DESC
        LIMIT 10
    """)
    stock = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(stock)

if __name__ == '__main__':
    app.run(debug=True)