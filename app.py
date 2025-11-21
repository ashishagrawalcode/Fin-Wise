from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # For image upload
import random
import os

app = Flask(__name__)
app.secret_key = 'finwise_secret_key'

# Configure Upload Folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Create folder if not exists

def get_db_connection():
    conn = sqlite3.connect('finwise.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # 1. Users (UPDATED with new columns)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # ... (Keep other tables: transactions, accounts, bills, game_portfolio, goals, stock_market) ...
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, date TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, institution TEXT NOT NULL, account_name TEXT NOT NULL, type TEXT NOT NULL, balance REAL NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS bills (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, account_id INTEGER, bill_name TEXT NOT NULL, amount REAL NOT NULL, due_date TEXT NOT NULL, status TEXT DEFAULT 'unpaid', FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS game_portfolio (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, company_name TEXT NOT NULL, quantity INTEGER DEFAULT 0, avg_price REAL NOT NULL, type TEXT DEFAULT 'stock')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL, target_amount REAL NOT NULL, current_amount REAL DEFAULT 0, deadline TEXT NOT NULL, priority TEXT DEFAULT 'Medium', FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stock_market (symbol TEXT PRIMARY KEY, name TEXT NOT NULL, base_price REAL NOT NULL, current_price REAL NOT NULL, type TEXT NOT NULL, sector TEXT)''')
    
    # Seed Data (Same as before)
    try:
        cur = conn.execute('SELECT count(*) FROM users')
        if cur.fetchone()[0] <= 1:
            bots = [('Aarav_Tech', 'aarav@test.com', 2500), ('Diya_Invests', 'diya@test.com', 2100), ('Kabir_07', 'kabir@test.com', 1800), ('Isha_Dreams', 'isha@test.com', 1500), ('Rohan_Trader', 'rohan@test.com', 1200), ('Sara_Finance', 'sara@test.com', 900)]
            for name, email, xp in bots:
                try: conn.execute('INSERT INTO users (username, email, password, xp) VALUES (?, ?, ?, ?)', (name, email, generate_password_hash('password'), xp))
                except: pass
    except: pass

    try:
        cur = conn.execute('SELECT count(*) FROM stock_market')
        if cur.fetchone()[0] == 0:
            assets = [('RELIANCE', 'Reliance Industries', 2911.22, 'stock', 'Energy'), ('TCS', 'Tata Consultancy Svcs', 3876.99, 'stock', 'IT'), ('HDFCBANK', 'HDFC Bank', 1678.78, 'stock', 'Banking'), ('ZOMATO', 'Zomato Ltd', 165.40, 'stock', 'Tech'), ('PAYTM', 'One 97 Communications', 420.50, 'stock', 'Fintech'), ('TATAMOTORS', 'Tata Motors', 980.40, 'stock', 'Auto'), ('ITC', 'ITC Limited', 430.50, 'stock', 'FMCG'), ('ADANIENT', 'Adani Enterprises', 3150.00, 'stock', 'Metals'), ('INFY', 'Infosys', 1500.00, 'stock', 'IT'), ('WIPRO', 'Wipro', 450.00, 'stock', 'IT'), ('SBISMALL', 'SBI Small Cap Fund', 145.20, 'mf', 'Equity'), ('HDFCTOP100', 'HDFC Top 100 Fund', 890.50, 'mf', 'Equity'), ('PARAGFLEXI', 'Parag Parikh Flexi Cap', 65.30, 'mf', 'Equity'), ('QUANTMID', 'Quant Mid Cap Fund', 210.15, 'mf', 'Equity'), ('NIFTYBEES', 'Nippon India Nifty 50', 235.40, 'etf', 'Index'), ('GOLDBEES', 'Nippon India Gold', 56.80, 'etf', 'Gold'), ('BANKBEES', 'Nippon India Bank', 480.20, 'etf', 'Banking')]
            for s in assets: conn.execute('INSERT INTO stock_market (symbol, name, base_price, current_price, type, sector) VALUES (?, ?, ?, ?, ?, ?)', (s[0], s[1], s[2], s[2], s[3], s[4]))
    except: pass

    conn.commit()
    conn.close()

init_db()

@app.context_processor
def inject_user():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        return dict(user=user)
    return dict(user=None)

# --- XP UPDATE API ---
@app.route('/api/earn-xp', methods=['POST'])
def earn_xp():
    if 'user_id' not in session: return {'error': 'Login required'}, 401
    data = request.json
    amount = data.get('amount', 0)
    
    conn = get_db_connection()
    # Get current XP
    cur_xp = conn.execute('SELECT xp FROM users WHERE id = ?', (session['user_id'],)).fetchone()[0]
    new_xp = cur_xp + amount
    new_level = new_xp // 500 + 1 # Simple logic: Level up every 500 XP
    
    conn.execute('UPDATE users SET xp = ?, level = ? WHERE id = ?', (new_xp, new_level, session['user_id']))
    conn.commit()
    conn.close()
    return {'success': True, 'new_xp': new_xp, 'new_level': new_level}

# --- ROUTES ---
# (Keep home, dashboard, accounts, goals, simulations, lessons, stock_market, job_loss, leaderboard, api, auth routes AS IS)
# ... [Paste all previous routes here or keep them if editing locally] ...
# FOR BREVITY, I am only showing the NEW Profile Route below. Ensure you keep the others!

@app.route('/')
def home(): return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    user_id = session['user_id']
    income = conn.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'income'", (user_id,)).fetchone()[0] or 0
    expense = conn.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'expense'", (user_id,)).fetchone()[0] or 0
    conn.close()
    return render_template('dashboard.html', username=session.get('username'), total_balance=f"₹{income-expense:,.0f}", income=f"₹{income:,.0f}", expense=f"₹{expense:,.0f}")

@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    user_id = session['user_id']
    if request.method == 'POST':
        if 'institution' in request.form:
            conn.execute('INSERT INTO accounts (user_id, institution, account_name, type, balance) VALUES (?, ?, ?, ?, ?)', (user_id, request.form['institution'], request.form['account_name'], request.form['type'], float(request.form['balance'])))
            conn.commit()
            flash('Account added.')
        elif 'trans_type' in request.form:
            conn.execute('INSERT INTO transactions (user_id, type, category, amount, date) VALUES (?, ?, ?, ?, ?)', (user_id, request.form['trans_type'], request.form['category'], float(request.form['amount']), request.form['date']))
            conn.commit()
            flash('Transaction recorded.')
        elif 'delete_account_id' in request.form:
            conn.execute('DELETE FROM accounts WHERE id = ? AND user_id = ?', (request.form['delete_account_id'], user_id))
            conn.commit()
    accounts = conn.execute('SELECT * FROM accounts WHERE user_id = ?', (user_id,)).fetchall()
    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 10', (user_id,)).fetchall()
    conn.close()
    assets = sum(row['balance'] for row in accounts if row['type'] in ['bank', 'pf'])
    liabilities = sum(row['balance'] for row in accounts if row['type'] in ['loan', 'credit'])
    return render_template('accounts.html', accounts=accounts, transactions=transactions, net_worth=f"₹{assets-liabilities:,.0f}", assets=f"₹{assets:,.0f}", liabilities=f"₹{liabilities:,.0f}")

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    user_id = session['user_id']
    if request.method == 'POST':
        if 'title' in request.form:
            conn.execute('INSERT INTO goals (user_id, title, category, target_amount, current_amount, deadline, priority) VALUES (?, ?, ?, ?, ?, ?, ?)', (user_id, request.form['title'], request.form['category'], float(request.form['target_amount']), float(request.form['current_amount']), request.form['deadline'], request.form['priority']))
            conn.commit()
        elif 'delete_goal_id' in request.form:
            conn.execute('DELETE FROM goals WHERE id = ? AND user_id = ?', (request.form['delete_goal_id'], user_id))
            conn.commit()
        elif 'update_goal_id' in request.form:
            conn.execute('UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND user_id = ?', (float(request.form['add_amount']), request.form['update_goal_id'], user_id))
            conn.commit()
    goals_data = conn.execute('SELECT * FROM goals WHERE user_id = ? ORDER BY deadline ASC', (user_id,)).fetchall()
    conn.close()
    total_target = sum(g['target_amount'] for g in goals_data)
    total_saved = sum(g['current_amount'] for g in goals_data)
    progress_pct = (total_saved / total_target * 100) if total_target > 0 else 0
    return render_template('goals.html', goals=goals_data, total_saved=f"₹{total_saved:,.0f}", progress_pct=round(progress_pct))

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    leaderboard_data = conn.execute('SELECT username, xp, level FROM users ORDER BY xp DESC').fetchall()
    conn.close()
    return render_template('leaderboard.html', leaderboard=leaderboard_data, current_user=session.get('username'))

@app.route('/simulations')
def simulations():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('simulations.html')

@app.route('/lessons')
def lessons():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('lessons.html')

@app.route('/simulations/stock-market')
def stock_market_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('games/stock_market.html')

@app.route('/simulations/job-loss')
def job_loss_game():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('games/job_loss.html')

@app.route('/api/market-data')
def market_data():
    conn = get_db_connection()
    assets = conn.execute('SELECT * FROM stock_market').fetchall()
    updated_assets = []
    for asset in assets:
        volatility = 0.015 if asset['type'] == 'stock' else 0.005
        change_percent = random.uniform(-volatility, volatility)
        new_price = asset['current_price'] * (1 + change_percent)
        conn.execute('UPDATE stock_market SET current_price = ? WHERE symbol = ?', (new_price, asset['symbol']))
        updated_assets.append({'symbol': asset['symbol'], 'name': asset['name'], 'price': round(new_price, 2), 'type': asset['type'], 'change': round((new_price - asset['base_price']), 2), 'change_pct': round(((new_price - asset['base_price']) / asset['base_price']) * 100, 2)})
    conn.commit()
    conn.close()
    return {'assets': updated_assets}

@app.route('/api/trade', methods=['POST'])
def place_trade():
    if 'user_id' not in session: return {'error': 'Login required'}, 401
    data = request.json
    symbol = data['symbol']; action = data['action']; quantity = int(data['quantity']); price = float(data['price'])
    conn = get_db_connection(); user_id = session['user_id']
    existing = conn.execute('SELECT * FROM game_portfolio WHERE user_id = ? AND symbol = ?', (user_id, symbol)).fetchone()
    if action == 'buy':
        if existing:
            new_qty = existing['quantity'] + quantity
            new_avg = ((existing['quantity'] * existing['avg_price']) + (quantity * price)) / new_qty
            conn.execute('UPDATE game_portfolio SET quantity = ?, avg_price = ? WHERE id = ?', (new_qty, new_avg, existing['id']))
        else:
            stock_info = conn.execute('SELECT name FROM stock_market WHERE symbol = ?', (symbol,)).fetchone()
            conn.execute('INSERT INTO game_portfolio (user_id, symbol, company_name, quantity, avg_price) VALUES (?, ?, ?, ?, ?)', (user_id, symbol, stock_info['name'], quantity, price))
    elif action == 'sell':
        if not existing or existing['quantity'] < quantity: return {'success': False, 'message': 'Not enough shares!'}
        new_qty = existing['quantity'] - quantity
        if new_qty == 0: conn.execute('DELETE FROM game_portfolio WHERE id = ?', (existing['id'],))
        else: conn.execute('UPDATE game_portfolio SET quantity = ? WHERE id = ?', (new_qty, existing['id']))
    conn.commit()
    updated_portfolio = conn.execute('SELECT * FROM game_portfolio WHERE user_id = ?', (user_id,)).fetchall()
    p_list = [{'symbol': p['symbol'], 'qty': p['quantity'], 'avg': p['avg_price']} for p in updated_portfolio]
    conn.close()
    return {'success': True, 'portfolio': p_list}

# --- PROFILE ROUTE (NEW) ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Update Details
        if 'username' in request.form:
            username = request.form['username']
            phone = request.form['phone']
            address = request.form['address']
            
            # Handle Profile Pic
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (filename, user_id))
            
            conn.execute('UPDATE users SET username = ?, phone = ?, address = ? WHERE id = ?', (username, phone, address, user_id))
            conn.commit()
            session['username'] = username # Update session name
            flash('Profile updated!')
        
        # Change Password
        elif 'current_password' in request.form:
            current = request.form['current_password']
            new_pass = request.form['new_password']
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            
            if check_password_hash(user['password'], current):
                conn.execute('UPDATE users SET password = ? WHERE id = ?', (generate_password_hash(new_pass), user_id))
                conn.commit()
                flash('Password changed successfully!')
            else:
                flash('Incorrect current password!')

    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        conn = get_db_connection(); user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone(); conn.close()
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
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, generate_password_hash(password)))
            conn.commit(); conn.close(); flash('Account created! Please login.')
            return redirect(url_for('login'))
        except: flash('Email already exists.')
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

# --- LESSON DATA STORE ---
LESSONS = {
    'budgeting-101': {
        'title': 'Budgeting 101: Why It Matters',
        'video_id': 'dQw4w9WgXcQ', # YouTube Video ID
        'content': """
            <h3>What is a Budget?</h3>
            <p>A budget is simply a plan for your money. It's not about restricting what you spend; it's about giving your money permission to go where you want it to go.</p>
            <h3>The 50/30/20 Rule</h3>
            <p>The most popular way to budget is the 50/30/20 rule:</p>
            <ul>
                <li><b>50% Needs:</b> Rent, Groceries, Utilities.</li>
                <li><b>30% Wants:</b> Dining out, Hobbies, Netflix.</li>
                <li><b>20% Savings:</b> Emergency Fund, Investments, Debt Repayment.</li>
            </ul>
            <h3>Why most people fail</h3>
            <p>Most people fail because they make their budget too strict. Leave room for fun! If you cut out everything you enjoy, you will eventually binge-spend.</p>
        """,
        'quiz': [
            {'q': 'What percentage of income should go to "Needs"?', 'options': ['30%', '50%', '20%'], 'correct': 1},
            {'q': 'Which of these is a "Want"?', 'options': ['Rent', 'Electricity Bill', 'Netflix Subscription'], 'correct': 2},
            {'q': 'What is the primary purpose of a budget?', 'options': ['To stop you from having fun', 'To give every dollar a job', 'To impress your bank'], 'correct': 1}
        ]
    },
    'investing-basics': {
        'title': 'Stock Market Basics',
        'video_id': 'p7HKvqRI_Bo',
        'content': """
            <h3>What is a Stock?</h3>
            <p>A stock represents partial ownership in a company. When you buy a share of Apple, you actually own a tiny piece of Apple.</p>
            <h3>Why do prices move?</h3>
            <p>In the short term, prices move based on news and sentiment (fear/greed). In the long term, they move based on how much profit the company makes.</p>
            <h3>Risk vs Reward</h3>
            <p>Stocks are volatile. They go up and down. Cash is safe but loses value to inflation. Over 10+ years, stocks historically beat inflation significantly.</p>
        """,
        'quiz': [
            {'q': 'What does owning a stock mean?', 'options': ['You loaned money to the company', 'You own a piece of the company', 'You are an employee'], 'correct': 1},
            {'q': 'In the short term, stock prices are driven by:', 'options': ['Company Profits', 'Sentiment & News', 'Government Decree'], 'correct': 1},
            {'q': 'Which asset class historically beats inflation best over 10 years?', 'options': ['Cash under mattress', 'Savings Account', 'Stocks'], 'correct': 2}
        ]
    }
}

@app.route('/coach')
def coach():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('coach.html', username=session.get('username'))

@app.route('/lesson/<slug>')
def lesson_view(slug):
    if 'user_id' not in session: return redirect(url_for('login'))
    lesson = LESSONS.get(slug)
    if not lesson:
        return "Lesson not found", 404
    return render_template('lesson_view.html', lesson=lesson, slug=slug)

if __name__ == '__main__':
    app.run(debug=True)