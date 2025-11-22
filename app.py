import os
import random
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rupeeverse_secret_key')
app.permanent_session_lifetime = timedelta(days=30)

# --- FIX FOR VERCEL (Read-Only System) ---
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- DATABASE SELECTOR ---
DATABASE_URL = os.environ.get('DATABASE_URL')

# FIX: Convert postgres:// to postgresql:// for compatibility
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

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

# --- UNIVERSAL QUERY FUNCTION ---
def query_db(query, args=(), one=False, commit=False):
    conn = get_db()
    if db_type == 'postgres':
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
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
        conn.close()  # FIX: Always close connection on error
        return None

# --- INIT DB (FIXED game_portfolio table) ---
def init_db():
    tables = [
        '''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, email TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, profile_pic TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1)''',
        '''CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id INTEGER, type TEXT, category TEXT, amount REAL, date TEXT)''',
        '''CREATE TABLE IF NOT EXISTS accounts (id SERIAL PRIMARY KEY, user_id INTEGER, institution TEXT, account_name TEXT, type TEXT, balance REAL)''',
        # FIX: Added company_name column to match INSERT statement
        '''CREATE TABLE IF NOT EXISTS game_portfolio (id SERIAL PRIMARY KEY, user_id INTEGER, symbol TEXT, company_name TEXT, quantity INTEGER, avg_price REAL)''',
        '''CREATE TABLE IF NOT EXISTS goals (id SERIAL PRIMARY KEY, user_id INTEGER, title TEXT, category TEXT, target_amount REAL, current_amount REAL, deadline TEXT, priority TEXT)''',
        '''CREATE TABLE IF NOT EXISTS stock_market (symbol TEXT PRIMARY KEY, name TEXT, base_price REAL, current_price REAL, type TEXT, sector TEXT)'''
    ]
    for t in tables: query_db(t, commit=True)

    existing = query_db('SELECT count(*) as c FROM stock_market', one=True)
    if existing is None:
        return  # Table might not exist yet
    count = existing['c'] if db_type == 'postgres' else existing[0]
    
    if count == 0:
        assets = [
            ('RELIANCE', 'Reliance Industries', 2911.22, 'stock', 'Energy'), ('TCS', 'Tata Consultancy', 3876.99, 'stock', 'IT'),
            ('HDFCBANK', 'HDFC Bank', 1678.78, 'stock', 'Banking'), ('ZOMATO', 'Zomato', 165.40, 'stock', 'Tech'),
            ('PAYTM', 'Paytm', 420.50, 'stock', 'Fintech'), ('TATAMOTORS', 'Tata Motors', 980.40, 'stock', 'Auto'),
            ('SBISMALL', 'SBI Small Cap', 145.20, 'mf', 'Equity'), ('HDFCTOP100', 'HDFC Top 100', 890.50, 'mf', 'Equity'),
            ('NIFTYBEES', 'Nifty 50 ETF', 235.40, 'etf', 'Index'), ('GOLDBEES', 'Gold ETF', 56.80, 'etf', 'Gold')
        ]
        for a in assets:
            query_db('INSERT INTO stock_market (symbol, name, base_price, current_price, type, sector) VALUES (%s, %s, %s, %s, %s, %s)', a, commit=True)

if not DATABASE_URL:
    init_db()

@app.route('/setup')
def setup():
    try:
        init_db()
        return "<h1>Database Initialized Successfully! ✅</h1>"
    except Exception as e:
        return f"<h1>Error: {e}</h1>"

# --- LESSON CONTENT ---
LESSONS = {
    'budgeting-101': {'title': 'Budgeting 101: Why It Matters', 'video_id': 'sVKQn2I4EZM', 'content': """<h3>The Foundation</h3><p>A budget is simply a plan for your money.</p>""", 'quiz': [{'q': 'Budgets are for:', 'options': ['Restriction', 'Planning', 'Banks'], 'correct': 1}]},
    'rule-50-30-20': {'title': 'The 50/30/20 Rule', 'video_id': 'HQzoZfc3GwQ', 'content': """<h3>The Golden Ratio</h3><p>Allocate: 50% Needs, 30% Wants, 20% Savings.</p>""", 'quiz': [{'q': 'What % goes to Savings?', 'options': ['50%', '30%', '20%'], 'correct': 2}]},
    'emergency-fund': {'title': 'Emergency Fund Essentials', 'video_id': 'C4r-tK5d5s0', 'content': """<h3>Why you need it</h3><p>3-6 months expenses prevents debt during crisis.</p>""", 'quiz': [{'q': 'How many months?', 'options': ['1 month', '3-6 months', '1 year'], 'correct': 1}]},
    'investing-basics': {'title': 'Stock Market Basics', 'video_id': 'p7HKvqRI_Bo', 'content': """<h3>Ownership</h3><p>Stocks = partial ownership in a company.</p>""", 'quiz': [{'q': 'Stocks represent:', 'options': ['Loans', 'Ownership', 'Gambling'], 'correct': 1}]},
    'credit-scores': {'title': 'Credit Scores Explained', 'video_id': '3U1piLk-x3U', 'content': """<h3>Your Financial Reputation</h3><p>CIBIL 750+ gets cheaper loans.</p>""", 'quiz': [{'q': 'Good CIBIL score?', 'options': ['300', '600', '750+'], 'correct': 2}]},
    'indian-tax': {'title': 'Indian Tax System Basics', 'video_id': '7s7xM-X', 'content': """<h3>Tax Slabs</h3><p>80C, 80D save money.</p>""", 'quiz': [{'q': 'Which section covers PPF?', 'options': ['80C', '80D', '90A'], 'correct': 0}]},
    'insurance': {'title': 'Insurance: Financial Safety Net', 'video_id': 'X3', 'content': """<h3>Risk Transfer</h3><p>Never mix insurance with investment.</p>""", 'quiz': [{'q': 'Purpose of insurance?', 'options': ['Investment', 'Risk Protection', 'Tax Saving'], 'correct': 1}]}
}

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = query_db('SELECT * FROM users WHERE id = %s', (session['user_id'],), one=True)
        return dict(user=user)
    return dict(user=None)

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def home(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = query_db('SELECT * FROM users WHERE email = %s', (request.form['email'],), one=True)
        # FIX: Check if user exists before accessing fields
        if user is None:
            flash('Invalid credentials')
            return render_template('login.html')
        
        pass_hash = user['password'] if isinstance(user, dict) else user[3]
        uid = user['id'] if isinstance(user, dict) else user[0]
        uname = user['username'] if isinstance(user, dict) else user[1]

        if check_password_hash(pass_hash, request.form['password']):
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
        except Exception as e:
            print(f"Signup error: {e}")
            flash('Email exists')
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,)) or []
    assets = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['bank','pf'])
    liab = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['loan','credit'])
    
    trans = query_db('SELECT type, amount FROM transactions WHERE user_id = %s', (uid,)) or []
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
        elif 'delete_account_id' in request.form:
            query_db('DELETE FROM accounts WHERE id=%s AND user_id=%s', (request.form['delete_account_id'], uid), commit=True)
    
    accts = query_db('SELECT * FROM accounts WHERE user_id = %s', (uid,)) or []
    trans = query_db('SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 5', (uid,)) or []
    assets = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['bank','pf'])
    liab = sum(a['balance'] if isinstance(a, dict) else a[5] for a in accts if (a['type'] if isinstance(a, dict) else a[4]) in ['loan','credit'])
    
    return render_template('accounts.html', accounts=accts, transactions=trans, net_worth=f"₹{assets-liab:,.0f}", assets=f"₹{assets:,.0f}", liabilities=f"₹{liab:,.0f}")

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
    
    goals_list = query_db('SELECT * FROM goals WHERE user_id = %s ORDER BY deadline', (uid,)) or []
    saved = sum(g['current_amount'] if isinstance(g, dict) else g[5] for g in goals_list)
    target = sum(g['target_amount'] if isinstance(g, dict) else g[4] for g in goals_list)
    pct = (saved/target*100) if target > 0 else 0
    return render_template('goals.html', goals=goals_list, total_saved=f"₹{saved:,.0f}", progress_pct=int(pct))

@app.route('/simulations')
def simulations(): return render_template('simulations.html') if 'user_id' in session else redirect(url_for('login'))
@app.route('/simulations/stock-market')
def stock_market_game(): return render_template('games/stock_market.html') if 'user_id' in session else redirect(url_for('login'))
@app.route('/simulations/job-loss')
def job_loss_game(): return render_template('games/job_loss.html') if 'user_id' in session else redirect(url_for('login'))
@app.route('/simulations/crypto')
def crypto_game(): return render_template('games/crypto.html') if 'user_id' in session else redirect(url_for('login'))
@app.route('/lessons')
def lessons(): return render_template('lessons.html') if 'user_id' in session else redirect(url_for('login'))

@app.route('/lesson/<slug>')
def lesson_view(slug):
    if 'user_id' not in session: return redirect(url_for('login'))
    lesson = LESSONS.get(slug)
    if not lesson: return "Lesson not found", 404
    return render_template('lesson_view.html', lesson=lesson, slug=slug)

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    users = query_db('SELECT username, xp, level FROM users ORDER BY xp DESC LIMIT 10') or []
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
            flash('Updated!')
    user = query_db('SELECT * FROM users WHERE id=%s', (uid,), one=True)
    return render_template('profile.html', user=user)

@app.route('/coach')
def coach(): return render_template('coach.html', username=session.get('username'))

@app.route('/api/market-data')
def market_data():
    assets = query_db('SELECT * FROM stock_market') or []
    data = []
    for a in assets:
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
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}, 401
    uid = session['user_id']
    data = request.json
    qty = int(data['quantity']); price = float(data['price']); symbol = data['symbol']
    
    existing = query_db('SELECT * FROM game_portfolio WHERE user_id=%s AND symbol=%s', (uid, symbol), one=True)
    eid = existing['id'] if isinstance(existing, dict) else existing[0] if existing else None
    eqty = existing['quantity'] if isinstance(existing, dict) else existing[4] if existing else 0
    eavg = existing['avg_price'] if isinstance(existing, dict) else existing[5] if existing else 0

    if data['action'] == 'buy':
        if existing:
            new_q = eqty + qty
            new_avg = ((eqty*eavg) + (qty*price)) / new_q
            query_db('UPDATE game_portfolio SET quantity=%s, avg_price=%s WHERE id=%s', (new_q, new_avg, eid), commit=True)
        else:
            sdata = query_db('SELECT name FROM stock_market WHERE symbol=%s', (symbol,), one=True)
            sname = sdata['name'] if isinstance(sdata, dict) else sdata[1] if sdata else symbol
            query_db('INSERT INTO game_portfolio (user_id, symbol, company_name, quantity, avg_price) VALUES (%s,%s,%s,%s,%s)', (uid, symbol, sname, qty, price), commit=True)
    else:
        new_q = eqty - qty
        if new_q <= 0: query_db('DELETE FROM game_portfolio WHERE id=%s', (eid,), commit=True)
        else: query_db('UPDATE game_portfolio SET quantity=%s WHERE id=%s', (new_q, eid), commit=True)
    
    port = query_db('SELECT * FROM game_portfolio WHERE user_id=%s', (uid,)) or []
    p_list = []
    for p in port:
        p_list.append({
            'symbol': p['symbol'] if isinstance(p, dict) else p[2],
            'qty': p['quantity'] if isinstance(p, dict) else p[4],
            'avg': p['avg_price'] if isinstance(p, dict) else p[5]
        })
    return {'success': True, 'portfolio': p_list}

@app.route('/api/earn-xp', methods=['POST'])
def api_xp():
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}, 401
    uid = session['user_id']
    amt = request.json.get('amount', 0)
    user = query_db('SELECT xp FROM users WHERE id=%s', (uid,), one=True)
    cur_xp = user['xp'] if isinstance(user, dict) else user[0] if user else 0
    new_xp = cur_xp + amt
    query_db('UPDATE users SET xp=%s, level=%s WHERE id=%s', (new_xp, new_xp//500+1, uid), commit=True)
    return {'success': True}

if __name__ == '__main__':
    app.run(debug=True)