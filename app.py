import os
import random
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- 1. CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'rupeeverse_secret_key'
app.permanent_session_lifetime = timedelta(days=30)

# Uploads
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database Selector (Auto-Detect)
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    def get_db():
        return psycopg2.connect(DATABASE_URL)
    db_type = 'postgres'
else:
    import sqlite3
    def get_db():
        conn = sqlite3.connect('finwise.db')
        conn.row_factory = sqlite3.Row
        return conn
    db_type = 'sqlite'

# --- 2. UNIVERSAL DB QUERY FUNCTION ---
def query_db(query, args=(), one=False):
    conn = get_db()
    
    if db_type == 'postgres':
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
        query = query.replace('%s', '?').replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
    
    try:
        cur.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"DB Error: {e}")
        return None

# --- 3. INITIALIZATION & SEEDING ---
def init_db():
    # Tables
    query_db('''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, email TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, profile_pic TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1)''')
    query_db('''CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id INTEGER, type TEXT, category TEXT, amount REAL, date TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS accounts (id SERIAL PRIMARY KEY, user_id INTEGER, institution TEXT, account_name TEXT, type TEXT, balance REAL)''')
    query_db('''CREATE TABLE IF NOT EXISTS goals (id SERIAL PRIMARY KEY, user_id INTEGER, title TEXT, category TEXT, target_amount REAL, current_amount REAL, deadline TEXT, priority TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS stock_market (symbol TEXT PRIMARY KEY, name TEXT, base_price REAL, current_price REAL, type TEXT, sector TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS game_portfolio (id SERIAL PRIMARY KEY, user_id INTEGER, symbol TEXT, quantity INTEGER, avg_price REAL)''')

    # Seed Stocks
    if not query_db('SELECT * FROM stock_market LIMIT 1', one=True):
        assets = [
            ('RELIANCE', 'Reliance Industries', 2911.22, 'stock', 'Energy'), ('TCS', 'Tata Consultancy', 3876.99, 'stock', 'IT'),
            ('HDFCBANK', 'HDFC Bank', 1678.78, 'stock', 'Banking'), ('ZOMATO', 'Zomato', 165.40, 'stock', 'Tech'),
            ('SBISMALL', 'SBI Small Cap', 145.20, 'mf', 'Equity'), ('NIFTYBEES', 'Nifty 50 ETF', 235.40, 'etf', 'Index')
        ]
        for a in assets:
            query_db('INSERT INTO stock_market (symbol, name, base_price, current_price, type, sector) VALUES (%s, %s, %s, %s, %s, %s)', a)
        print("Stocks Seeded")

    # Seed Bots
    if not query_db('SELECT * FROM users LIMIT 1', one=True):
        bots = [('Aarav_Tech', 2500), ('Diya_Invests', 2100), ('Kabir_07', 1800)]
        for name, xp in bots:
            query_db('INSERT INTO users (username, email, password, xp, level) VALUES (%s, %s, %s, %s, %s)', (name, f"{name}@bot.com", "pass", xp, xp//500+1))
        print("Bots Seeded")

# Run Init
if not os.environ.get('VERCEL'):
    init_db()

# --- 4. CONTEXT & HELPERS ---
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = query_db('SELECT * FROM users WHERE id = %s', (session['user_id'],), one=True)
        return dict(user=user)
    return dict(user=None)

@app.before_request
def make_session_permanent():
    session.permanent = True

# --- 5. ROUTES ---

# AUTH
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = query_db('SELECT * FROM users WHERE email = %s', (request.form['email'],), one=True)
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            query_db('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                    (request.form['username'], request.form['email'], generate_password_hash(request.form['password'])))
            flash('Account created!')
            return redirect(url_for('login'))
        except: flash('Email exists')
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    # Financials
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,))
    assets = sum(a['balance'] for a in accts if a['type'] in ['bank','pf'])
    liabilities = sum(a['balance'] for a in accts if a['type'] in ['loan','credit'])
    
    # Cash Flow
    inc = query_db("SELECT SUM(amount) as s FROM transactions WHERE user_id=%s AND type='income'", (uid,), one=True)
    exp = query_db("SELECT SUM(amount) as s FROM transactions WHERE user_id=%s AND type='expense'", (uid,), one=True)
    income = inc['s'] if inc and inc['s'] else 0
    expense = exp['s'] if exp and exp['s'] else 0

    return render_template('dashboard.html', username=session['username'], 
                          total_balance=f"₹{assets-liabilities:,.0f}", income=f"₹{income:,.0f}", expense=f"₹{expense:,.0f}")

# ACCOUNTS
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'institution' in request.form:
            query_db('INSERT INTO accounts (user_id, institution, account_name, type, balance) VALUES (%s,%s,%s,%s,%s)',
                    (uid, request.form['institution'], request.form['account_name'], request.form['type'], float(request.form['balance'])))
        elif 'trans_type' in request.form:
            query_db('INSERT INTO transactions (user_id, type, category, amount, date) VALUES (%s,%s,%s,%s,%s)',
                    (uid, request.form['trans_type'], request.form['category'], float(request.form['amount']), request.form['date']))
    
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,))
    trans = query_db('SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 5', (uid,))
    
    assets = sum(a['balance'] for a in accts if a['type'] in ['bank','pf'])
    liab = sum(a['balance'] for a in accts if a['type'] in ['loan','credit'])
    
    return render_template('accounts.html', accounts=accts, transactions=trans, 
                          net_worth=f"₹{assets-liab:,.0f}", assets=f"₹{assets:,.0f}", liabilities=f"₹{liab:,.0f}")

# GOALS
@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'title' in request.form:
            query_db('INSERT INTO goals (user_id, title, category, target_amount, current_amount, deadline, priority) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                    (uid, request.form['title'], request.form['category'], float(request.form['target_amount']), float(request.form['current_amount']), request.form['deadline'], request.form['priority']))
        elif 'add_amount' in request.form:
             query_db('UPDATE goals SET current_amount = current_amount + %s WHERE id=%s', (float(request.form['add_amount']), request.form['update_goal_id']))
    
    goals = query_db('SELECT * FROM goals WHERE user_id = %s ORDER BY deadline', (uid,))
    saved = sum(g['current_amount'] for g in goals)
    target = sum(g['target_amount'] for g in goals)
    pct = (saved/target*100) if target > 0 else 0
    return render_template('goals.html', goals=goals, total_saved=f"₹{saved:,.0f}", progress_pct=int(pct))

# SIMULATIONS
@app.route('/simulations')
def simulations(): return render_template('simulations.html')

@app.route('/simulations/stock-market')
def stock_market_game(): return render_template('games/stock_market.html')

@app.route('/simulations/job-loss')
def job_loss_game(): return render_template('games/job_loss.html')

@app.route('/simulations/crypto')
def crypto_game(): return render_template('games/crypto.html')

# LEADERBOARD
@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Get top users
    users = query_db('SELECT username, xp, level FROM users ORDER BY xp DESC LIMIT 10')
    return render_template('leaderboard.html', leaderboard=users, current_user=session.get('username'))

# PROFILE
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'username' in request.form:
            query_db('UPDATE users SET username=%s, phone=%s, address=%s WHERE id=%s', 
                    (request.form['username'], request.form['phone'], request.form['address'], uid))
            session['username'] = request.form['username']
            
            if 'profile_pic' in request.files:
                f = request.files['profile_pic']
                if f.filename:
                    fname = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    query_db('UPDATE users SET profile_pic=%s WHERE id=%s', (fname, uid))
            flash('Updated!')
    
    user = query_db('SELECT * FROM users WHERE id=%s', (uid,), one=True)
    return render_template('profile.html', user=user)

# LESSONS
LESSONS = {
    'budgeting-101': {'title': 'Budgeting 101', 'video_id': 'sVKQn2I4EZM', 'content': '<p>Content...</p>', 'quiz': []},
    'investing-basics': {'title': 'Stock Market Basics', 'video_id': 'p7HKvqRI_Bo', 'content': '<p>Content...</p>', 'quiz': []}
    # Add other lessons similarly
}

@app.route('/lessons')
def lessons(): return render_template('lessons.html')

@app.route('/lesson/<slug>')
def lesson_view(slug):
    if 'user_id' not in session: return redirect(url_for('login'))
    lesson = LESSONS.get(slug, {'title': 'Lesson', 'video_id': '', 'content': 'Coming soon', 'quiz': []})
    return render_template('lesson_view.html', lesson=lesson, slug=slug)

@app.route('/coach')
def coach(): return render_template('coach.html', username=session.get('username'))

# API
@app.route('/api/market-data')
def market_data():
    assets = query_db('SELECT * FROM stock_market')
    data = []
    for a in assets:
        # Simulate movement
        move = (random.random() - 0.5) * 0.02 * a['base_price']
        new_p = a['current_price'] + move
        query_db('UPDATE stock_market SET current_price=%s WHERE symbol=%s', (new_p, a['symbol']))
        change = new_p - a['base_price']
        data.append({
            'symbol': a['symbol'], 'name': a['name'], 'price': new_p, 'type': a['type'],
            'change': round(change, 2), 'change_pct': round((change/a['base_price'])*100, 2)
        })
    return {'assets': data}

@app.route('/api/trade', methods=['POST'])
def api_trade():
    uid = session['user_id']
    data = request.json
    qty = int(data['quantity'])
    price = float(data['price'])
    symbol = data['symbol']
    
    existing = query_db('SELECT * FROM game_portfolio WHERE user_id=%s AND symbol=%s', (uid, symbol), one=True)
    
    if data['action'] == 'buy':
        if existing:
            new_q = existing['quantity'] + qty
            new_avg = ((existing['quantity']*existing['avg_price']) + (qty*price)) / new_q
            query_db('UPDATE game_portfolio SET quantity=%s, avg_price=%s WHERE id=%s', (new_q, new_avg, existing['id']))
        else:
            name = query_db('SELECT name FROM stock_market WHERE symbol=%s', (symbol,), one=True)['name']
            query_db('INSERT INTO game_portfolio (user_id, symbol, company_name, quantity, avg_price) VALUES (%s,%s,%s,%s,%s)', (uid, symbol, name, qty, price))
    else:
        new_q = existing['quantity'] - qty
        if new_q <= 0: query_db('DELETE FROM game_portfolio WHERE id=%s', (existing['id'],))
        else: query_db('UPDATE game_portfolio SET quantity=%s WHERE id=%s', (new_q, existing['id']))
    
    port = query_db('SELECT * FROM game_portfolio WHERE user_id=%s', (uid,))
    return {'success': True, 'portfolio': [{'symbol': p['symbol'], 'qty': p['quantity'], 'avg': p['avg_price']} for p in port]}

@app.route('/api/earn-xp', methods=['POST'])
def api_xp():
    uid = session['user_id']
    amt = request.json.get('amount', 0)
    user = query_db('SELECT xp FROM users WHERE id=%s', (uid,), one=True)
    new_xp = user['xp'] + amt
    query_db('UPDATE users SET xp=%s, level=%s WHERE id=%s', (new_xp, new_xp//500+1, uid))
    return {'success': True}

if __name__ == '__main__':
    app.run(debug=True)