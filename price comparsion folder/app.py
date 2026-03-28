from flask import Flask, render_template, request, redirect, session
import requests
import random
import sqlite3

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

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            return "User already exists!"

        conn.close()
        return redirect('/login')

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------------- SEARCH ----------------
@app.route('/search', methods=['POST'])
def search():
    query = request.form['search']

    url = f"https://dummyjson.com/products/search?q={query}"
    response = requests.get(url)
    data = response.json()

    products = data.get('products', [])
    results = []

    for item in products:
        base_price = item['price'] * 80

        prices = [
            {"site": "Amazon", "price": int(base_price + random.randint(0, 2000))},
            {"site": "Flipkart", "price": int(base_price - random.randint(0, 2000))},
            {"site": "Croma", "price": int(base_price + random.randint(500, 3000))}
        ]

        min_price = min(p["price"] for p in prices)

        results.append({
            "name": item['title'],
            "image": item['thumbnail'],
            "rating": item['rating'],
            "prices": prices,
            "min_price": min_price
        })

    return render_template('results.html', results=results)

# ---------------- ADD TO WISHLIST ----------------
@app.route('/wishlist', methods=['POST'])
def wishlist():
    if 'user' not in session:
        return redirect('/login')

    product_name = request.form['product']
    user = session['user']

    if 'wishlists' not in session:
        session['wishlists'] = {}

    if user not in session['wishlists']:
        session['wishlists'][user] = []

    session['wishlists'][user].append(product_name)
    session.modified = True

    return redirect('/view_wishlist')

# ---------------- VIEW WISHLIST ----------------
@app.route('/view_wishlist')
def view_wishlist():
    if 'user' not in session:
        return redirect('/login')

    user = session['user']
    wishlists = session.get('wishlists', {})
    wishlist = wishlists.get(user, [])

    return render_template('wishlist.html', wishlist=wishlist)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)