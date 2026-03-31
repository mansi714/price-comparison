
from flask import Flask, render_template, request, redirect, session, flash, jsonify
import requests
import random
import sqlite3
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        product_name TEXT,
        product_image TEXT,
        product_price INTEGER,
        product_rating REAL
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HELPERS ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Please login first.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hash_password(password))
            )
            conn.commit()
            flash('Account created! Please login.', 'success')
            return redirect('/login')
        except:
            flash('Username already exists!', 'error')
            return render_template('register.html')
        finally:
            conn.close()

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/')

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            flash('All fields are required.', 'error')
            return render_template('login.html')

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hash_password(password))
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            flash(f'Welcome back, {username}! 🎉', 'success')
            return redirect('/')
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    username = session.get('user', '')
    session.pop('user', None)
    flash(f'Goodbye, {username}! See you soon.', 'info')
    return redirect('/login')

# ---------------- SEARCH ----------------
@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('search', '').strip()

    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect('/')

    try:
        url = f"https://dummyjson.com/products/search?q={query}&limit=20"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        flash('Search timed out. Please try again.', 'error')
        return redirect('/')
    except Exception as e:
        flash('Something went wrong. Please try again.', 'error')
        return redirect('/')

    products = data.get('products', [])

    if not products:
        flash(f'No products found for "{query}".', 'warning')
        return render_template('results.html', results=[], query=query)

    results = []

    for item in products:
        base_price = item['price'] * 80

        prices = [
            {"site": "Amazon",   "price": int(base_price + random.randint(0, 2000)),    "color": "#FF9900", "icon": "🟠"},
            {"site": "Flipkart", "price": int(base_price - random.randint(0, 2000)),    "color": "#2874F0", "icon": "🔵"},
            {"site": "Croma",    "price": int(base_price + random.randint(500, 3000)),  "color": "#E31E24", "icon": "🔴"},
        ]

        # Make sure no negative prices
        for p in prices:
            if p['price'] < 100:
                p['price'] = 100

        min_price   = min(p["price"] for p in prices)
        max_price   = max(p["price"] for p in prices)
        savings     = max_price - min_price
        best_store  = next(p["site"] for p in prices if p["price"] == min_price)

        # Mark cheapest
        for p in prices:
            p['is_cheapest'] = (p['price'] == min_price)

        results.append({
            "name":        item['title'],
            "image":       item['thumbnail'],
            "rating":      item['rating'],
            "category":    item.get('category', 'General').title(),
            "description": item.get('description', '')[:100] + '...',
            "prices":      prices,
            "min_price":   min_price,
            "max_price":   max_price,
            "savings":     savings,
            "best_store":  best_store,
            "brand":       item.get('brand', 'Unknown'),
            "stock":       item.get('stock', 0),
        })

    # Sort by min_price lowest first
    results.sort(key=lambda x: x['min_price'])

    return render_template('results.html', results=results, query=query)

# ---------------- ADD TO WISHLIST ----------------
@app.route('/wishlist', methods=['POST'])
@login_required
def wishlist():
    product_name   = request.form.get('product', '')
    product_image  = request.form.get('image', '')
    product_price  = request.form.get('price', 0)
    product_rating = request.form.get('rating', 0)
    user           = session['user']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Check if already in wishlist
    cursor.execute(
        "SELECT id FROM wishlist WHERE username=? AND product_name=?",
        (user, product_name)
    )
    existing = cursor.fetchone()

    if not existing:
        cursor.execute(
            "INSERT INTO wishlist (username, product_name, product_image, product_price, product_rating) VALUES (?, ?, ?, ?, ?)",
            (user, product_name, product_image, product_price, product_rating)
        )
        conn.commit()
        flash(f'"{product_name}" added to wishlist! ❤️', 'success')
    else:
        flash(f'"{product_name}" is already in your wishlist.', 'info')

    conn.close()
    return redirect('/view_wishlist')

# ---------------- REMOVE FROM WISHLIST ----------------
@app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_wishlist(item_id):
    user = session['user']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM wishlist WHERE id=? AND username=?",
        (item_id, user)
    )
    conn.commit()
    conn.close()

    flash('Item removed from wishlist.', 'info')
    return redirect('/view_wishlist')

# ---------------- VIEW WISHLIST ----------------
@app.route('/view_wishlist')
@login_required
def view_wishlist():
    user = session['user']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, product_name, product_image, product_price, product_rating FROM wishlist WHERE username=?",
        (user,)
    )
    rows = cursor.fetchall()
    conn.close()

    wishlist = [
        {
            'id':      row[0],
            'name':    row[1],
            'image':   row[2],
            'price':   row[3],
            'rating':  row[4],
        }
        for row in rows
    ]

    return render_template('wishlist.html', wishlist=wishlist)

# ---------------- API SEARCH (AJAX) ----------------
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'No query'}), 400

    try:
        url      = f"https://dummyjson.com/products/search?q={query}&limit=10"
        response = requests.get(url, timeout=8)
        data     = response.json()
        products = data.get('products', [])
        titles   = [p['title'] for p in products[:5]]
        return jsonify({'suggestions': titles})
    except:
        return jsonify({'suggestions': []})

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
