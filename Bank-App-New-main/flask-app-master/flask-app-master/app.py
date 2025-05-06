from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import random
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

# File paths
users_file = "users.txt"
transactions_file = "transactions.txt"

# ------------------------ Helper Functions ------------------------

def read_users():
    users = {}
    if os.path.exists(users_file):
        with open(users_file, 'r') as file:
            for line in file:
                user_data = line.strip().split(",")
                if len(user_data) == 8:
                    users[user_data[4]] = {
                        "name": user_data[0],
                        "surname": user_data[1],
                        "phone": user_data[2],
                        "id_number": user_data[3],
                        "balance": float(user_data[5]),
                        "account_number": user_data[6],
                        "password": user_data[7]
                    }
                else:
                    print(f"Skipping malformed line: {line.strip()}")
    return users

def save_users(users):
    with open(users_file, 'w') as file:
        for username, user in users.items():
            file.write(f"{user['name']},{user['surname']},{user['phone']},{user['id_number']},{username},{user['balance']},{user['account_number']},{user['password']}\n")

def read_transactions():
    transactions = []
    if os.path.exists(transactions_file):
        with open(transactions_file, 'r') as file:
            for line in file:
                transaction_data = line.strip().split(",")
                if len(transaction_data) >= 6:
                    transactions.append({
                        'date': transaction_data[0],
                        'type': transaction_data[1],
                        'amount': transaction_data[2],
                        'details': transaction_data[5]
                    })
                else:
                    print(f"Skipping malformed transaction line: {line.strip()}")
    return transactions

def log_transaction(transaction):
    with open(transactions_file, 'a') as file:
        file.write(transaction + "\n")

def is_valid_phone(phone):
    return re.match(r"^\+27\d{9}$", phone) is not None

def is_valid_id(id_number):
    return id_number.isdigit() and len(id_number) == 13

def is_valid_name(name):
    return re.match(r"^[A-Za-z]+$", name) is not None

def is_valid_username(username):
    return re.match(r"^(?!\d+$)[A-Za-z0-9]+$", username) is not None

def generate_account_number():
    return str(random.randint(100000, 999999))

# ------------------------ Routes ------------------------

@app.route('/')
def home():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        id_number = request.form['id_number']
        username = request.form['username']
        password = request.form['password']

        if not is_valid_name(name):
            flash('Name must contain only letters (no numbers or special characters).', 'danger')
            return render_template('register.html')

        if not is_valid_name(surname):
            flash('Surname must contain only letters (no numbers or special characters).', 'danger')
            return render_template('register.html')

        if not is_valid_phone(phone):
            flash('Invalid phone number! Use format +27821234567.', 'danger')
            return render_template('register.html')

        if not is_valid_id(id_number):
            flash('Invalid ID number! Must be a 13-digit number.', 'danger')
            return render_template('register.html')

        if not is_valid_username(username):
            flash('Username must contain at least one letter and cannot be just numbers.', 'danger')
            return render_template('register.html')

        users = read_users()

        if username in users:
            flash('Username already exists, please choose another.', 'danger')
            return render_template('register.html')

        if any(user['id_number'] == id_number for user in users.values()):
            flash('ID number already exists, please use a different one.', 'danger')
            return render_template('register.html')

        account_number = generate_account_number()

        users[username] = {
            'name': name,
            'surname': surname,
            'phone': phone,
            'id_number': id_number,
            'balance': 0.0,
            'account_number': account_number,
            'password': password
        }

        save_users(users)

        flash(f"Account created successfully! Your account number is {account_number}.", 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = read_users()

        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))

        flash('Invalid username or password!', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    users = read_users()
    user = users[username]
    return render_template('dashboard.html', user=user)

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Deposit amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    username = session['username']
    users = read_users()
    users[username]['balance'] += amount
    save_users(users)

    log_transaction(f"{datetime.now()}, Deposit, {amount}, , , Account {users[username]['account_number']} deposited {amount} ZAR")
    flash(f"Deposited {amount} ZAR successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Withdrawal amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    username = session['username']
    users = read_users()

    if users[username]['balance'] < amount:
        flash("Insufficient balance!", "danger")
        return redirect(url_for('dashboard'))

    users[username]['balance'] -= amount
    save_users(users)

    log_transaction(f"{datetime.now()}, Withdrawal, {amount}, , , Account {users[username]['account_number']} withdrew {amount} ZAR")
    flash(f"Withdrew {amount} ZAR successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Transfer amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    recipient_account = request.form['recipient_account']
    username = session['username']
    users = read_users()

    if users[username]['balance'] < amount:
        flash("Insufficient balance!", "danger")
        return redirect(url_for('dashboard'))

    recipient_user = next((user for user in users.values() if user['account_number'] == recipient_account), None)

    if not recipient_user:
        flash("Recipient account not found!", "danger")
        return redirect(url_for('dashboard'))

    users[username]['balance'] -= amount
    recipient_user['balance'] += amount
    save_users(users)

    log_transaction(f"{datetime.now()}, Transfer, {amount}, Account {users[username]['account_number']}, Account {recipient_account}, Account {users[username]['account_number']} transferred {amount} ZAR to Account {recipient_account}")
    flash(f"Transferred {amount} ZAR successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/view_history')
def view_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    users = read_users()
    user_account_number = users[username]['account_number']
    transactions = read_transactions()
    user_transactions = [t for t in transactions if user_account_number in t['details']]
    return render_template('view_history.html', transactions=user_transactions)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
