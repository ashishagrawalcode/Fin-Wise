from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
import random
import os

app = Flask(__name__)
app.secret_key = 'rupeeverse_secret_key'

# --- CONFIGURATION ---
# Session Persistence (30 Days)
app.permanent_session_lifetime = timedelta(days=30)

# Upload Folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE CONFIGURATION (Supabase) ---
DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': '123Ashish#bmu1',  # New password
    'host': 'db.rklzvrojyxnrzgwqkcej.supabase.co',
    'port': '5432',
    'sslmode': 'require'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            profile_pic TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')
    
    # 2. Transactions
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''')

    # 3. Accounts
    cur.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            institution TEXT NOT NULL,
            account_name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL
        )
    ''')

    # 4. Bills
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            account_id INTEGER,
            bill_name TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'unpaid'
        )
    ''')

    # 5. Game Portfolio
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_portfolio (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            symbol TEXT NOT NULL,
            company_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            avg_price REAL NOT NULL,
            type TEXT DEFAULT 'stock'
        )
    ''')

    # 6. Goals
    cur.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium'
        )
    ''')
    
    # 7. Stock Market
    cur.execute('''
        CREATE TABLE IF NOT EXISTS stock_market (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_price REAL NOT NULL,
            current_price REAL NOT NULL,
            type TEXT NOT NULL,
            sector TEXT
        )
    ''')

    # SEED DATA
    cur.execute('SELECT count(*) FROM stock_market')
    if cur.fetchone()[0] == 0:
        assets = [
            ('RELIANCE', 'Reliance Industries', 2911.22, 'stock', 'Energy'), ('TCS', 'Tata Consultancy Svcs', 3876.99, 'stock', 'IT'), 
            ('HDFCBANK', 'HDFC Bank', 1678.78, 'stock', 'Banking'), ('ZOMATO', 'Zomato Ltd', 165.40, 'stock', 'Tech'), 
            ('PAYTM', 'One 97 Communications', 420.50, 'stock', 'Fintech'), ('TATAMOTORS', 'Tata Motors', 980.40, 'stock', 'Auto'), 
            ('ITC', 'ITC Limited', 430.50, 'stock', 'FMCG'), ('ADANIENT', 'Adani Enterprises', 3150.00, 'stock', 'Metals'), 
            ('INFY', 'Infosys', 1500.00, 'stock', 'IT'), ('WIPRO', 'Wipro', 450.00, 'stock', 'IT'),
            ('SBISMALL', 'SBI Small Cap Fund', 145.20, 'mf', 'Equity'), ('HDFCTOP100', 'HDFC Top 100 Fund', 890.50, 'mf', 'Equity'), 
            ('PARAGFLEXI', 'Parag Parikh Flexi Cap', 65.30, 'mf', 'Equity'), ('QUANTMID', 'Quant Mid Cap Fund', 210.15, 'mf', 'Equity'),
            ('NIFTYBEES', 'Nippon India Nifty 50', 235.40, 'etf', 'Index'), ('GOLDBEES', 'Nippon India Gold', 56.80, 'etf', 'Gold'), 
            ('BANKBEES', 'Nippon India Bank', 480.20, 'etf', 'Banking')
        ]
        for s in assets:
            cur.execute('INSERT INTO stock_market (symbol, name, base_price, current_price, type, sector) VALUES (%s, %s, %s, %s, %s, %s)', 
                        (s[0], s[1], s[2], s[2], s[3], s[4]))
            
    conn.commit()
    cur.close()
    conn.close()

init_db()

# --- FULL LESSON DATA ---
LESSONS = {
    'budgeting-101': {
        'title': 'Budgeting 101: Why It Matters',
        'video_id': 'sVKQn2I4EZM', 
        'content': """<h3>The Foundation</h3><p>A budget is simply a plan for your money. It tells your money where to go instead of wondering where it went.</p>""",
        'quiz': [{'q': 'Budgets are for:', 'options': ['Restriction', 'Planning', 'Banks'], 'correct': 1}]
    },
    'rule-50-30-20': {
        'title': 'The 50/30/20 Rule',
        'video_id': 'HQzoZfc3GwQ',
        'content': """<h3>The Golden Ratio</h3><p>Allocate your income: <b>50% Needs</b> (Rent, Food), <b>30% Wants</b> (Fun, Netflix), <b>20% Savings</b> (Investments).</p>""",
        'quiz': [{'q': 'What % goes to Savings?', 'options': ['50%', '30%', '20%'], 'correct': 2}]
    },
    'emergency-fund': {
        'title': 'Emergency Fund Essentials',
        'video_id': 'C4r-tK5d5s0', 
        'content': """<h3>Why you need it</h3><p>Life is unpredictable. An emergency fund of 3-6 months expenses prevents you from going into debt during a crisis.</p>""",
        'quiz': [{'q': 'How many months of expenses should you save?', 'options': ['1 month', '3-6 months', '1 year'], 'correct': 1}]
    },
    'investing-basics': {
        'title': 'Stock Market Basics',
        'video_id': 'p7HKvqRI_Bo',
        'content': """<h3>Ownership</h3><p>Stocks represent partial ownership in a company. Over the long term (10+ years), equities historically beat inflation.</p>""",
        'quiz': [{'q': 'Stocks represent:', 'options': ['Loans', 'Ownership', 'Gambling'], 'correct': 1}]
    },
    'credit-scores': {
        'title': 'Credit Scores Explained',
        'video_id': '3U1piLk-x3U',
        'content': """<h3>Your Financial Reputation</h3><p>A CIBIL score above 750 gets you cheaper loans. Pay bills on time and keep credit utilization low to boost it.</p>""",
        'quiz': [{'q': 'What is a good CIBIL score?', 'options': ['300', '600', '750+'], 'correct': 2}]
    },
    'indian-tax': {
        'title': 'Indian Tax System Basics',
        'video_id': '7s7xM-X', 
        'content': """<h3>Tax Slabs</h3><p>Understanding Old vs New Regime is crucial. Taxes fund public services, but smart planning (80C, 80D) can save you money.</p>""",
        'quiz': [{'q': 'Which section covers PPF/EPF?', 'options': ['80C', '80D', '90A'], 'correct': 0}]
    },
    'insurance': {
        'title': 'Insurance: Financial Safety Net',
        'video_id': 'X3', 
        'content': """<h3>Risk Transfer</h3><p>Insurance transfers the financial risk of life/health events to a company. Never mix insurance with investment (Endowment).</p>""",
        'quiz': [{'q': 'Primary purpose of insurance?', 'options': ['Investment', 'Risk Protection', 'Tax Saving'], 'correct': 1}]
    }
}

@app.context_processor
def inject_user():
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        cur.close(); conn.close()
        return dict(user=user)
    return dict(user=None)

@app.before_request
def make_session_permanent():
    session.permanent = True

# --- ROUTES ---

@app.route('/')
def home(): return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    user_id = session['user_id']
    
    cur.execute('SELECT * FROM accounts WHERE user_id = %s', (user_id,))
    accounts = cur.fetchall()
    assets = sum(row['balance'] for row in accounts if row['type'] in ['bank', 'pf'])
    liabilities = sum(row['balance'] for row in accounts if row['type'] in ['loan', 'credit'])
    net_worth = assets - liabilities

    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'income'", (user_id,))
    res_inc = cur.fetchone()['sum']
    income = res_inc if res_inc else 0
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'expense'", (user_id,))
    res_exp = cur.fetchone()['sum']
    expense = res_exp if res_exp else 0
    
    cur.close(); conn.close()
    return render_template('dashboard.html', username=session.get('username'), total_balance=f"₹{net_worth:,.0f}", income=f"₹{income:,.0f}", expense=f"₹{expense:,.0f}")

@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor); user_id = session['user_id']
    
    if request.method == 'POST':
        if 'institution' in request.form:
            cur.execute('INSERT INTO accounts (user_id, institution, account_name, type, balance) VALUES (%s, %s, %s, %s, %s)', 
                       (user_id, request.form['institution'], request.form['account_name'], request.form['type'], float(request.form['balance'])))
            conn.commit(); flash('Account added.')
        elif 'trans_type' in request.form:
            cur.execute('INSERT INTO transactions (user_id, type, category, amount, date) VALUES (%s, %s, %s, %s, %s)', 
                       (user_id, request.form['trans_type'], request.form['category'], float(request.form['amount']), request.form['date']))
            conn.commit(); flash('Transaction recorded.')
        elif 'delete_account_id' in request.form:
            cur.execute('DELETE FROM accounts WHERE id = %s AND user_id = %s', (request.form['delete_account_id'], user_id))
            conn.commit()
            
    cur.execute('SELECT * FROM accounts WHERE user_id = %s', (user_id,))
    accounts = cur.fetchall()
    cur.execute('SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 10', (user_id,))
    transactions = cur.fetchall()
    
    assets = sum(row['balance'] for row in accounts if row['type'] in ['bank', 'pf'])
    liabilities = sum(row['balance'] for row in accounts if row['type'] in ['loan', 'credit'])
    net_worth = assets - liabilities
    
    cur.close(); conn.close()
    return render_template('accounts.html', accounts=accounts, transactions=transactions, net_worth=f"₹{net_worth:,.0f}", assets=f"₹{assets:,.0f}", liabilities=f"₹{liabilities:,.0f}", income=f"₹{0:,.0f}", expense=f"₹{0:,.0f}", savings=f"₹{0:,.0f}")

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor); user_id = session['user_id']
    if request.method == 'POST':
        if 'title' in request.form:
            cur.execute('INSERT INTO goals (user_id, title, category, target_amount, current_amount, deadline, priority) VALUES (%s, %s, %s, %s, %s, %s, %s)', 
                       (user_id, request.form['title'], request.form['category'], float(request.form['target_amount']), float(request.form['current_amount']), request.form['deadline'], request.form['priority']))
            conn.commit()
        elif 'delete_goal_id' in request.form:
            cur.execute('DELETE FROM goals WHERE id = %s AND user_id = %s', (request.form['delete_goal_id'], user_id)); conn.commit()
        elif 'update_goal_id' in request.form:
            cur.execute('UPDATE goals SET current_amount = current_amount + %s WHERE id = %s AND user_id = %s', (float(request.form['add_amount']), request.form['update_goal_id'], user_id)); conn.commit()
    
    cur.execute('SELECT * FROM goals WHERE user_id = %s ORDER BY deadline ASC', (user_id,))
    goals_data = cur.fetchall()
    total_target = sum(g['target_amount'] for g in goals_data)
    total_saved = sum(g['current_amount'] for g in goals_data)
    progress_pct = (total_saved / total_target * 100) if total_target > 0 else 0
    
    cur.close(); conn.close()
    return render_template('goals.html', goals=goals_data, total_saved=f"₹{total_saved:,.0f}", progress_pct=round(progress_pct))

@app.route('/simulations')
def simulations():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('simulations.html')

@app.route('/simulations/stock-market')
def stock_market_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('games/stock_market.html')

@app.route('/simulations/job-loss')
def job_loss_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('games/job_loss.html')

@app.route('/simulations/crypto')
def crypto_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('games/crypto.html')

@app.route('/lessons')
def lessons():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('lessons.html')

@app.route('/lesson/<slug>')
def lesson_view(slug):
    if 'user_id' not in session: return redirect(url_for('login'))
    lesson = LESSONS.get(slug)
    if not lesson: return "Lesson not found", 404
    
    vid = lesson['video_id']
    if 'youtube' in vid: vid = vid[-11:]
    lesson['video_id'] = vid
    return render_template('lesson_view.html', lesson=lesson, slug=slug)

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT username, xp, level FROM users ORDER BY xp DESC')
    leaderboard_data = cur.fetchall()
    cur.close(); conn.close()
    return render_template('leaderboard.html', leaderboard=leaderboard_data, current_user=session.get('username'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor); user_id = session['user_id']
    if request.method == 'POST':
        if 'username' in request.form:
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    cur.execute('UPDATE users SET profile_pic = %s WHERE id = %s', (filename, user_id))
            cur.execute('UPDATE users SET username = %s, phone = %s, address = %s WHERE id = %s', (request.form['username'], request.form['phone'], request.form['address'], user_id))
            conn.commit(); session['username'] = request.form['username']; flash('Profile updated!')
    cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close(); conn.close()
    return render_template('profile.html', user=user)

# --- API ENDPOINTS ---
@app.route('/api/market-data')
def market_data():
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM stock_market')
    assets = cur.fetchall()
    updated_assets = []
    for asset in assets:
        volatility = 0.015 if asset['type'] == 'stock' else 0.005
        change_percent = random.uniform(-volatility, volatility)
        new_price = asset['current_price'] * (1 + change_percent)
        cur.execute('UPDATE stock_market SET current_price = %s WHERE symbol = %s', (new_price, asset['symbol']))
        updated_assets.append({'symbol': asset['symbol'], 'name': asset['name'], 'price': round(new_price, 2), 'type': asset['type'], 'change': round((new_price - asset['base_price']), 2), 'change_pct': round(((new_price - asset['base_price']) / asset['base_price']) * 100, 2)})
    conn.commit(); cur.close(); conn.close()
    return {'assets': updated_assets}

@app.route('/api/trade', methods=['POST'])
def place_trade():
    if 'user_id' not in session: return {'error': 'Login required'}, 401
    data = request.json
    symbol = data['symbol']; action = data['action']; quantity = int(data['quantity']); price = float(data['price'])
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor); user_id = session['user_id']
    cur.execute('SELECT * FROM game_portfolio WHERE user_id = %s AND symbol = %s', (user_id, symbol))
    existing = cur.fetchone()
    if action == 'buy':
        if existing:
            new_qty = existing['quantity'] + quantity
            new_avg = ((existing['quantity'] * existing['avg_price']) + (quantity * price)) / new_qty
            cur.execute('UPDATE game_portfolio SET quantity = %s, avg_price = %s WHERE id = %s', (new_qty, new_avg, existing['id']))
        else:
            cur.execute('SELECT name FROM stock_market WHERE symbol = %s', (symbol,))
            stock_info = cur.fetchone()
            cur.execute('INSERT INTO game_portfolio (user_id, symbol, company_name, quantity, avg_price) VALUES (%s, %s, %s, %s, %s)', (user_id, symbol, stock_info['name'], quantity, price))
    elif action == 'sell':
        if not existing or existing['quantity'] < quantity: return {'success': False, 'message': 'Not enough shares!'}
        new_qty = existing['quantity'] - quantity
        if new_qty == 0: cur.execute('DELETE FROM game_portfolio WHERE id = %s', (existing['id'],))
        else: cur.execute('UPDATE game_portfolio SET quantity = %s WHERE id = %s', (new_qty, existing['id']))
    conn.commit()
    cur.execute('SELECT * FROM game_portfolio WHERE user_id = %s', (user_id,))
    updated_portfolio = cur.fetchall()
    p_list = [{'symbol': p['symbol'], 'qty': p['quantity'], 'avg': p['avg_price']} for p in updated_portfolio]
    cur.close(); conn.close()
    return {'success': True, 'portfolio': p_list}

@app.route('/api/earn-xp', methods=['POST'])
def earn_xp():
    if 'user_id' not in session: return {'error': 'Login required'}, 401
    data = request.json
    amount = data.get('amount', 0)
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT xp FROM users WHERE id = %s', (session['user_id'],))
    row = cur.fetchone()
    if row:
        cur_xp = row[0]
        new_xp = cur_xp + amount
        new_level = new_xp // 500 + 1
        cur.execute('UPDATE users SET xp = %s, level = %s WHERE id = %s', (new_xp, new_level, session['user_id']))
        conn.commit()
    cur.close(); conn.close()
    return {'success': True}

# --- AUTH ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']; session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else: flash('Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']; email = request.form['email']; password = request.form['password']
        try:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, generate_password_hash(password)))
            conn.commit(); cur.close(); conn.close(); flash('Account created! Please login.')
            return redirect(url_for('login'))
        except Exception as e: print(e); flash('Email already exists.')
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)