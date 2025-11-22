import os
import random
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rupeeverse_secret_key')
app.permanent_session_lifetime = timedelta(days=30)

# Uploads: Use /tmp on Vercel, else static/uploads
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- DATABASE SELECTOR (THE FIX) ---
# If DATABASE_URL env var exists (Vercel), use Postgres. Otherwise SQLite.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    def get_db():
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    db_type = 'postgres'
else:
    import sqlite3
    def get_db():
        conn = sqlite3.connect('finwise.db')
        conn.row_factory = sqlite3.Row
        return conn
    db_type = 'sqlite'

# --- UNIVERSAL QUERY HELPER ---
def query_db(query, args=(), one=False, commit=False):
    conn = get_db()
    if db_type == 'postgres':
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
        # Convert Postgres Syntax to SQLite
        query = query.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        query = query.replace('%s', '?')
    
    try:
        cur.execute(query, args)
        rv = None
        if not commit:
            rv = cur.fetchall()
            rv = (rv[0] if rv else None) if one else rv
        else:
            conn.commit()
        cur.close()
        conn.close()
        return rv
    except Exception as e:
        print(f"DB Error: {e}")
        return None

# --- INIT DB ---
def init_db():
    # Create Tables
    query_db('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, email TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, profile_pic TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1)', commit=True)
    query_db('CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id INTEGER, type TEXT, category TEXT, amount REAL, date TEXT)', commit=True)
    query_db('CREATE TABLE IF NOT EXISTS accounts (id SERIAL PRIMARY KEY, user_id INTEGER, institution TEXT, account_name TEXT, type TEXT, balance REAL)', commit=True)
    query_db('CREATE TABLE IF NOT EXISTS goals (id SERIAL PRIMARY KEY, user_id INTEGER, title TEXT, category TEXT, target_amount REAL, current_amount REAL, deadline TEXT, priority TEXT)', commit=True)
    query_db('CREATE TABLE IF NOT EXISTS stock_market (symbol TEXT PRIMARY KEY, name TEXT, base_price REAL, current_price REAL, type TEXT, sector TEXT)', commit=True)
    query_db('CREATE TABLE IF NOT EXISTS game_portfolio (id SERIAL PRIMARY KEY, user_id INTEGER, symbol TEXT, quantity INTEGER, avg_price REAL)', commit=True)

    # Seed Stocks
    if not query_db('SELECT * FROM stock_market LIMIT 1', one=True):
        assets = [
            ('RELIANCE', 'Reliance Industries', 2911.22, 'stock', 'Energy'), ('TCS', 'Tata Consultancy', 3876.99, 'stock', 'IT'),
            ('HDFCBANK', 'HDFC Bank', 1678.78, 'stock', 'Banking'), ('ZOMATO', 'Zomato', 165.40, 'stock', 'Tech'),
            ('PAYTM', 'Paytm', 420.50, 'stock', 'Fintech'), ('TATAMOTORS', 'Tata Motors', 980.40, 'stock', 'Auto'),
            ('SBISMALL', 'SBI Small Cap', 145.20, 'mf', 'Equity'), ('HDFCTOP100', 'HDFC Top 100', 890.50, 'mf', 'Equity'),
            ('NIFTYBEES', 'Nifty 50 ETF', 235.40, 'etf', 'Index'), ('GOLDBEES', 'Gold ETF', 56.80, 'etf', 'Gold')
        ]
        for a in assets:
            query_db('INSERT INTO stock_market (symbol, name, base_price, current_price, type, sector) VALUES (%s, %s, %s, %s, %s, %s)', a, commit=True)
        print("Stocks Seeded")

    # Seed Bots
    if not query_db('SELECT * FROM users LIMIT 1', one=True):
        bots = [('Aarav_Tech', 2500), ('Diya_Invests', 2100), ('Kabir_07', 1800)]
        for name, xp in bots:
            query_db('INSERT INTO users (username, email, password, xp, level) VALUES (%s, %s, %s, %s, %s)', (name, f"{name}@bot.com", generate_password_hash("pass"), xp, xp//500+1), commit=True)
        print("Bots Seeded")

# Run Init Locally
init_db()

# --- DATA ---
LESSONS = {
    'budgeting-101': {'title': 'Budgeting 101', 'video_id': 'sVKQn2I4EZM', 'content': '...', 'quiz': []},
    'investing-basics': {'title': 'Stock Market Basics', 'video_id': 'p7HKvqRI_Bo', 'content': '...', 'quiz': []}
}

# --- CONTEXT ---
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = query_db('SELECT * FROM users WHERE id = %s', (session['user_id'],), one=True)
        return dict(user=user)
    return dict(user=None)

# --- ROUTES ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = query_db('SELECT * FROM users WHERE email = %s', (request.form['email'],), one=True)
        pass_hash = user['password'] if isinstance(user, dict) else user[3]
        uid = user['id'] if isinstance(user, dict) else user[0]
        uname = user['username'] if isinstance(user, dict) else user[1]

        if user and check_password_hash(pass_hash, request.form['password']):
            session['user_id'] = uid
            session['username'] = uname
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            query_db('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                    (request.form['username'], request.form['email'], generate_password_hash(request.form['password'])), commit=True)
            flash('Created! Login now.')
            return redirect(url_for('login'))
        except: flash('Email exists')
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,))
    # Handle empty list safely
    assets = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['bank','pf'])
    liab = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['loan','credit'])
    
    # Simple check for income/expense
    trans = query_db('SELECT type, amount FROM transactions WHERE user_id = %s', (uid,))
    income = sum(t['amount'] if isinstance(t, dict) else t[1] for t in trans if (t['type'] if isinstance(t, dict) else t[0]) == 'income')
    expense = sum(t['amount'] if isinstance(t, dict) else t[1] for t in trans if (t['type'] if isinstance(t, dict) else t[0]) == 'expense')

    return render_template('dashboard.html', username=session['username'], 
                          total_balance=f"₹{assets-liab:,.0f}", income=f"₹{income:,.0f}", expense=f"₹{expense:,.0f}")

@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'institution' in request.form:
            query_db('INSERT INTO accounts (user_id, institution, account_name, type, balance) VALUES (%s,%s,%s,%s,%s)',
                    (uid, request.form['institution'], request.form['account_name'], request.form['type'], float(request.form['balance'])), commit=True)
        elif 'trans_type' in request.form:
            query_db('INSERT INTO transactions (user_id, type, category, amount, date) VALUES (%s,%s,%s,%s,%s)',
                    (uid, request.form['trans_type'], request.form['category'], float(request.form['amount']), request.form['date']), commit=True)
    
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,))
    trans = query_db('SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 5', (uid,))
    
    assets = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['bank','pf'])
    liab = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['loan','credit'])
    
    return render_template('accounts.html', accounts=accts, transactions=trans, 
                          net_worth=f"₹{assets-liab:,.0f}", assets=f"₹{assets:,.0f}", liabilities=f"₹{liab:,.0f}")

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'title' in request.form:
            query_db('INSERT INTO goals (user_id, title, category, target_amount, current_amount, deadline, priority) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                    (uid, request.form['title'], request.form['category'], float(request.form['target_amount']), float(request.form['current_amount']), request.form['deadline'], request.form['priority']), commit=True)
        elif 'add_amount' in request.form:
             query_db('UPDATE goals SET current_amount = current_amount + %s WHERE id=%s', (float(request.form['add_amount']), request.form['update_goal_id']), commit=True)
    
    goals = query_db('SELECT * FROM goals WHERE user_id = %s ORDER BY deadline', (uid,))
    saved = sum(g['current_amount'] if isinstance(g, dict) else g[5] for g in goals)
    target = sum(g['target_amount'] if isinstance(g, dict) else g[4] for g in goals)
    pct = (saved/target*100) if target > 0 else 0
    return render_template('goals.html', goals=goals, total_saved=f"₹{saved:,.0f}", progress_pct=int(pct))

# SIMULATIONS & LESSONS
@app.route('/simulations')
def simulations(): return render_template('simulations.html') if 'user_id' in session else redirect(url_for('login'))

@app.route('/simulations/stock-market')
def stock_market_game(): return render_template('games/stock_market.html')

@app.route('/simulations/job-loss')
def job_loss_game(): return render_template('games/job_loss.html')

@app.route('/simulations/crypto')
def crypto_game(): return render_template('games/crypto.html')

@app.route('/lessons')
def lessons(): return render_template('lessons.html')

@app.route('/lesson/<slug>')
def lesson_view(slug):
    if 'user_id' not in session: return redirect(url_for('login'))
    lesson = LESSONS.get(slug, {'title': 'Lesson', 'video_id': '', 'content': 'Loading...', 'quiz': []})
    return render_template('lesson_view.html', lesson=lesson, slug=slug)

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    users = query_db('SELECT username, xp, level FROM users ORDER BY xp DESC LIMIT 10')
    return render_template('leaderboard.html', leaderboard=users, current_user=session.get('username'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    if request.method == 'POST':
        if 'username' in request.form:
            query_db('UPDATE users SET username=%s, phone=%s, address=%s WHERE id=%s', 
                    (request.form['username'], request.form['phone'], request.form['address'], uid), commit=True)
            session['username'] = request.form['username']
            
            if 'profile_pic' in request.files:
                f = request.files['profile_pic']
                if f.filename:
                    fname = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    query_db('UPDATE users SET profile_pic=%s WHERE id=%s', (fname, uid), commit=True)
            flash('Updated!')
    
    user = query_db('SELECT * FROM users WHERE id=%s', (uid,), one=True)
    return render_template('profile.html', user=user)

@app.route('/coach')
def coach(): return render_template('coach.html', username=session.get('username'))

# API
@app.route('/api/market-data')
def market_data():
    assets = query_db('SELECT * FROM stock_market')
    data = []
    for a in assets:
        # Handle tuple/dict access
        price = a['current_price'] if isinstance(a, dict) else a[3]
        base = a['base_price'] if isinstance(a, dict) else a[2]
        symbol = a['symbol'] if isinstance(a, dict) else a[0]
        name = a['name'] if isinstance(a, dict) else a[1]
        atype = a['type'] if isinstance(a, dict) else a[4]
        
        move = (random.random() - 0.5) * 0.02 * base
        new_p = price + move
        query_db('UPDATE stock_market SET current_price=%s WHERE symbol=%s', (new_p, symbol), commit=True)
        
        change = new_p - base
        data.append({
            'symbol': symbol, 'name': name, 'price': round(new_p, 2), 'type': atype,
            'change': round(change, 2), 'change_pct': round((change/base)*100, 2)
        })
    return {'assets': data}

@app.route('/api/trade', methods=['POST'])
def api_trade():
    uid = session['user_id']
    data = request.json
    qty = int(data['quantity']); price = float(data['price']); symbol = data['symbol']
    
    existing = query_db('SELECT * FROM game_portfolio WHERE user_id=%s AND symbol=%s', (uid, symbol), one=True)
    # Handle dict vs tuple
    eid = existing['id'] if isinstance(existing, dict) else existing[0] if existing else None
    eqty = existing['quantity'] if isinstance(existing, dict) else existing[4] if existing else 0
    eavg = existing['avg_price'] if isinstance(existing, dict) else existing[5] if existing else 0

    if data['action'] == 'buy':
        if existing:
            new_q = eqty + qty
            new_avg = ((eqty * eavg) + (qty*price)) / new_q
            query_db('UPDATE game_portfolio SET quantity=%s, avg_price=%s WHERE id=%s', (new_q, new_avg, eid), commit=True)
        else:
            # Fetch name
            sdata = query_db('SELECT name FROM stock_market WHERE symbol=%s', (symbol,), one=True)
            sname = sdata['name'] if isinstance(sdata, dict) else sdata[1]
            query_db('INSERT INTO game_portfolio (user_id, symbol, company_name, quantity, avg_price) VALUES (%s,%s,%s,%s,%s)', (uid, symbol, sname, qty, price), commit=True)
    else:
        new_q = eqty - qty
        if new_q <= 0: query_db('DELETE FROM game_portfolio WHERE id=%s', (eid,), commit=True)
        else: query_db('UPDATE game_portfolio SET quantity=%s WHERE id=%s', (new_q, eid), commit=True)
    
    port = query_db('SELECT * FROM game_portfolio WHERE user_id=%s', (uid,))
    # Handle tuple list
    p_list = []
    for p in port:
        p_sym = p['symbol'] if isinstance(p, dict) else p[2]
        p_qty = p['quantity'] if isinstance(p, dict) else p[4]
        p_avg = p['avg_price'] if isinstance(p, dict) else p[5]
        p_list.append({'symbol': p_sym, 'qty': p_qty, 'avg': p_avg})
        
    return {'success': True, 'portfolio': p_list}

@app.route('/api/earn-xp', methods=['POST'])
def api_xp():
    uid = session['user_id']
    amt = request.json.get('amount', 0)
    user = query_db('SELECT xp FROM users WHERE id=%s', (uid,), one=True)
    cur_xp = user['xp'] if isinstance(user, dict) else user[7]
    new_xp = cur_xp + amt
    query_db('UPDATE users SET xp=%s, level=%s WHERE id=%s', (new_xp, new_xp//500+1, uid), commit=True)
    return {'success': True}

if __name__ == '__main__':
    app.run(debug=True)