import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'sifat_secret_key'

# অ্যাডমিন ডিটেইলস
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "sifat123"


# ১. ডাটাবেজ টেবিল সেটআপ (সঠিক কলাম সিরিয়ালসহ)
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # ইউজার টেবিল
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           username TEXT, 
                           phone TEXT UNIQUE, 
                           password TEXT, 
                           balance INTEGER DEFAULT 0,
                           plan TEXT DEFAULT 'None',
                           tasks_done INTEGER DEFAULT 0)''')

    # ডিপোজিট টেবিল (সিরিয়াল একদম ঠিক রাখা হয়েছে)
    cursor.execute('''CREATE TABLE IF NOT EXISTS deposits 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           user_id INTEGER, 
                           amount INTEGER, 
                           phone TEXT, 
                           trxid TEXT UNIQUE, 
                           status TEXT DEFAULT 'Pending')''')

    # উইথড্র টেবিল
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdraws 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           user_id INTEGER, 
                           amount INTEGER, 
                           phone TEXT, 
                           method TEXT, 
                           status TEXT DEFAULT 'Pending')''')

    conn.commit()
    conn.close()


init_db()


# ২. সাধারণ পেজসমূহ
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/plans')
def plans():
    return render_template('plans.html')


# ৩. ইউজার ফাংশনসমূহ
@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_id = request.args.get('ref')
    if request.method == 'POST':
        name = request.form.get('username')
        phone = request.form.get('phone')
        password = request.form.get('password')
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, phone, password, balance, plan, tasks_done) VALUES (?, ?, ?, ?, ?, ?)',
                (name, phone, password, 0, 'None', 0))
            if ref_id:
                cursor.execute("UPDATE users SET balance = balance + 10 WHERE id = ?", (ref_id,))
            conn.commit()
            conn.close()
            return "রেজিস্ট্রেশন সফল! এখন লগইন করুন।"
        except Exception as e:
            return "এই নাম্বার দিয়ে আগেই অ্যাকাউন্ট খোলা হয়েছে!"
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ? AND password = ?', (phone, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))
        return "ভুল নাম্বার বা পাসওয়ার্ড!"
    return render_template('login.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, phone, password, balance, plan FROM users WHERE id = ?', (session['user_id'],))
    user_info = cursor.fetchone()
    conn.close()
    return render_template('profile.html', user=user_info)


# ৪. ডিপোজিট এবং উইথড্র (Fix করা হয়েছে)
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if 'user_id' not in session: return redirect(url_for('login'))

    if request.method == 'POST':
        if 'trxid' in request.form:
            amount = request.form.get('amount')
            trxid = request.form.get('trxid')
            phone = request.form.get('phone')

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            try:
                # কলাম সিরিয়াল: user_id, amount, phone, trxid, status
                cursor.execute('''INSERT INTO deposits (user_id, amount, phone, trxid, status) 
                                  VALUES (?, ?, ?, ?, ?)''',
                               (session['user_id'], amount, phone, trxid, 'Pending'))
                conn.commit()
                conn.close()
                return "আপনার ডিপোজিট রিকোয়েস্ট সফল হয়েছে!"
            except Exception as e:
                return "Transaction ID টি সঠিক নয় অথবা ডাটাবেজে সমস্যা হয়েছে।"

        amount = request.form.get('amount')
        method = request.form.get('method')
        return render_template('payment_details.html', amount=amount, method=method)

    return render_template('deposit.html')


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        amount_input = request.form.get('amount')
        phone = request.form.get('phone')
        method = request.form.get('method')
        if not amount_input: return "টাকার পরিমাণ দিন!"
        amount = int(amount_input)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],))
        user_balance = cursor.fetchone()[0]

        if user_balance >= amount:
            # কলাম সিরিয়াল: user_id, amount, phone, method, status
            cursor.execute("INSERT INTO withdraws (user_id, amount, phone, method, status) VALUES (?, ?, ?, ?, ?)",
                           (session['user_id'], amount, phone, method, 'Pending'))
            cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, session['user_id']))
            conn.commit()
            conn.close()
            return "উইথড্র রিকোয়েস্ট সফল!"
        conn.close()
        return "পর্যাপ্ত ব্যালেন্স নেই!"
    return render_template('withdraw.html')


# ৫. অ্যাডমিন লজিক (Fix করা হয়েছে)
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        return "ভুল ইউজারনেম বা পাসওয়ার্ড!"
    return render_template('admin_dashboard.html')


@app.route('/admin-sifat-secret')
def admin_panel():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # পেন্ডিং লিস্ট আনা (অ্যাডমিন ড্যাশবোর্ডের জন্য)
    cursor.execute("SELECT * FROM deposits WHERE status = 'Pending'")
    deps = cursor.fetchall()
    cursor.execute("SELECT * FROM withdraws WHERE status = 'Pending'")
    wits = cursor.fetchall()

    # স্ট্যাটাস ক্যালকুলেশন
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM deposits WHERE status = 'Approved'")
    total_dep_res = cursor.fetchone()[0]
    total_deposits = total_dep_res if total_dep_res else 0
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE status = 'Paid'")
    total_wit_res = cursor.fetchone()[0]
    total_withdraws = total_wit_res if total_wit_res else 0

    conn.close()
    return render_template('admin_dashboard.html', deposits=deps, withdraws=wits, t_users=total_users,
                           t_dep=total_deposits, t_wit=total_withdraws)


@app.route('/approve_deposit/<int:id>')
def approve_deposit(id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount FROM deposits WHERE id = ?", (id,))
    res = cursor.fetchone()
    if res:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (res[1], res[0]))
        cursor.execute("UPDATE deposits SET status = 'Approved' WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))


@app.route('/approve_withdraw/<int:id>')
def approve_withdraw(id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE withdraws SET status = 'Paid' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))


# ৬. টাস্ক লজিক
@app.route('/task')
def task():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT plan, tasks_done FROM users WHERE id = ?", (session['user_id'],))
    user_data = cursor.fetchone()
    conn.close()

    plan = user_data[0] if user_data[0] else "None"
    done = user_data[1]
    limit = 0

    # এখানে আমরা চেক করছি ইউজারের কোন VIP প্ল্যান আছে
    if 'VIP1' in plan:
        limit = 5
    elif 'VIP2' in plan:
        limit = 10
    elif 'VIP3' in plan:
        limit = 20

    # এই লাইনেই তোমার স্ক্রিনশটের ভুলটি ছিল। এখানে 'limit=limit' যোগ করা হয়েছে।
    return render_template('task.html', plan=plan, done=done, limit=limit)


@app.route('/complete_task')
def complete_task():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT plan, tasks_done FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    plan, done = user[0], user[1]
    limit = 0
    if 'Basic' in plan:
        limit = 2
    elif 'Silver' in plan:
        limit = 5
    elif 'Gold' in plan:
        limit = 15
    if done < limit:
        cursor.execute("UPDATE users SET balance = balance + 5, tasks_done = tasks_done + 1 WHERE id = ?",
                       (session['user_id'],))
        conn.commit()
        conn.close()
        return "টাস্ক সম্পন্ন! ৫ টাকা যোগ হয়েছে।"
    conn.close()
    return "আজকের লিমিট শেষ!"


@app.route('/reset_all_tasks')
def reset_tasks():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET tasks_done = 0")
    conn.commit()
    conn.close()
    return "সবার ডেইলি টাস্ক রিসেট করা হয়েছে!"


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/transactions')
def transactions():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # ইউজারের ডিপোজিট হিস্ট্রি আনা
    cursor.execute("SELECT amount, trxid, status FROM deposits WHERE user_id = ? ORDER BY id DESC", (user_id,))
    deps = cursor.fetchall()
    # ইউজারের উইথড্র হিস্ট্রি আনা
    cursor.execute("SELECT amount, method, status FROM withdraws WHERE user_id = ? ORDER BY id DESC", (user_id,))
    wits = cursor.fetchall()
    conn.close()
    return render_template('history.html', deposits=deps, withdraws=wits)

@app.route('/refer')
def refer():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    # তোমার লোকাল হোস্ট লিঙ্ক (সার্ভারে আপলোড করলে ডোমেইন নাম হবে)
    refer_link = f"http://127.0.0.1:5000/register?ref={user_id}"
    return render_template('refer.html', link=refer_link)


@app.route('/buy_plan/<string:plan_name>/<int:price>')
def buy_plan(plan_name, price):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # ইউজারের বর্তমান ব্যালেন্স এবং প্ল্যান চেক করা
    cursor.execute("SELECT balance, plan FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    balance = user_data[0]
    old_plans = user_data[1]

    if balance >= price:
        new_balance = balance - price
        # যদি আগে কোনো প্ল্যান না থাকে তবে শুধু নতুনটা বসবে, থাকলে কমা দিয়ে যোগ হবে
        new_plan_list = plan_name if old_plans == "None" or not old_plans else old_plans + ", " + plan_name

        cursor.execute("UPDATE users SET balance = ?, plan = ? WHERE id = ?", (new_balance, new_plan_list, user_id))
        conn.commit()
        conn.close()
        return f"অভিনন্দন! আপনি সফলভাবে {plan_name} কিনেছেন। আপনার বর্তমান ব্যালেন্স: {new_balance} টাকা।"

    conn.close()
    return "আপনার পর্যাপ্ত ব্যালেন্স নেই! দয়া করে ডিপোজিট করুন।"


# অ্যাডমিন প্যানেলের ডেইলি ইনকাম ডিস্ট্রিবিউট ফাংশন
@app.route('/run_daily_income')
def run_daily_income():
    # চেক করা হচ্ছে অ্যাডমিন লগইন আছে কি না
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # VIP 1 ইউজারদের জন্য ১০ টাকা (তোমার প্ল্যান অনুযায়ী পরিবর্তন করতে পারো)
    cursor.execute("UPDATE users SET balance = balance + 10 WHERE plan LIKE '%VIP1%'")

    # VIP 2 ইউজারদের জন্য ৭০ টাকা
    cursor.execute("UPDATE users SET balance = balance + 70 WHERE plan LIKE '%VIP2%'")

    # VIP 3 ইউজারদের জন্য ১০০ টাকা
    cursor.execute("UPDATE users SET balance = balance + 100 WHERE plan LIKE '%VIP3%'")

    conn.commit()
    conn.close()

    return "সফলভাবে সবার অ্যাকাউন্টে ডেইলি ইনকাম যোগ করা হয়েছে!"

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
