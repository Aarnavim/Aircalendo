from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'aircalendo_secret_key'
DATABASE = 'users.db'

# ------------------------
# DATABASE CONNECTION
# ------------------------

def get_db():
    if '_database' not in g:
        g._database = sqlite3.connect(DATABASE, check_same_thread=False)
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()

# ------------------------
# DATABASE SETUP
# ------------------------

# Removed update_user_credentials function to avoid undefined reference error

# ------------------------
# ROUTES
# ------------------------

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['email']
    password = request.form['password']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]
        session['username'] = username
        session['role'] = user[1]

        if user[1] == 'owner':
            return redirect(url_for('owner_dashboard'))
        elif user[1] == 'cleaner':
            return redirect(url_for('cleaner_dashboard'))
    else:
        return render_template('login.html', error="Invalid username or password")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/owner')
def owner_dashboard():
    if session.get('role') == 'owner':
        return render_template('owner_dashboard.html', username=session.get('username'))
    return redirect(url_for('home'))

@app.route('/cleaner')
def cleaner_dashboard():
    if session.get('role') == 'cleaner':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT client_name, date FROM bookings WHERE cleaner=?", (session['username'],))
        bookings = c.fetchall()
        # Map bookings to jobs with payment placeholder
        jobs = [{'client_name': b[0], 'date': b[1], 'payment': '$$$$'} for b in bookings]
        return render_template('cleaner_dashboard.html', username=session['username'], jobs=jobs)
    return redirect(url_for('home'))

from calendar import monthrange, month_name
from datetime import date as dt_date

@app.route('/calendar')
def calendar():
    if session.get('role') in ['owner', 'cleaner']:
        # Get month and year from query parameters or default to current
        month = request.args.get('month', default=None, type=int)
        year = request.args.get('year', default=None, type=int)
        today = dt_date.today()
        if not month or not year:
            month = today.month
            year = today.year

        conn = get_db()
        c = conn.cursor()
        if session.get('role') == 'owner':
            c.execute("SELECT id, date, client_name FROM bookings")
        else:
            c.execute("SELECT id, date, client_name FROM bookings WHERE cleaner=?", (session['username'],))
        bookings = c.fetchall()
        # Organize bookings by date for easy lookup in template
        bookings_by_date = {}
        bookings_by_id = {}
        for booking_id, date_str, client_name in bookings:
            if date_str not in bookings_by_date:
                bookings_by_date[date_str] = []
            bookings_by_date[date_str].append(client_name)
            bookings_by_id[booking_id] = (date_str, client_name)

        # Generate calendar data for the month
        first_weekday, num_days = monthrange(year, month)
        # Create list of weeks, each week is list of day numbers or None for empty days
        weeks = []
        week = [None]*first_weekday
        day = 1
        while day <= num_days:
            week.append(day)
            if len(week) == 7:
                weeks.append(week)
                week = []
            day += 1
        if week:
            while len(week) < 7:
                week.append(None)
            weeks.append(week)

        month_name_str = month_name[month]

        if session.get('role') == 'owner':
            return render_template('owner_calendar.html', username=session['username'], role=session['role'],
                                   bookings=bookings_by_date, weeks=weeks, month=month, year=year, month_name=month_name_str)
        else:
            return render_template('cleaner_calendar.html', username=session['username'], role=session['role'],
                                   bookings=bookings_by_date, weeks=weeks, month=month, year=year, month_name=month_name_str)
    return redirect(url_for('home'))


@app.route('/booking/<int:booking_id>')
def booking_detail(booking_id):
    if session.get('role') not in ['owner', 'cleaner']:
        return redirect(url_for('home'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT client_name, date, time, location, cleaner FROM bookings WHERE id=?", (booking_id,))
    booking = c.fetchone()
    if not booking:
        return "Booking not found", 404
    return render_template('booking_detail.html', booking=booking)

@app.route('/booking/<int:booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        client = request.form['client']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']
        cleaner = request.form['cleaner']
        c.execute('''
            UPDATE bookings
            SET client_name=?, date=?, time=?, location=?, cleaner=?
            WHERE id=?
        ''', (client, date, time, location, cleaner, booking_id))
        conn.commit()
        return redirect(url_for('booking_detail', booking_id=booking_id))
    else:
        c.execute("SELECT client_name, date, time, location, cleaner FROM bookings WHERE id=?", (booking_id,))
        booking = c.fetchone()
        if not booking:
            return "Booking not found", 404
        return render_template('edit_booking.html', booking=booking, booking_id=booking_id)

@app.route('/booking/<int:booking_id>/delete', methods=['POST'])
def delete_booking(booking_id):
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    conn.commit()
    return redirect(url_for('bookings'))

@app.route('/clock')
def clock():
    if session.get('role') == 'owner':
        return render_template('clock.html', username=session['username'], role=session['role'])
    elif session.get('role') == 'cleaner':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT client_name, date, time FROM bookings WHERE cleaner=? AND date >= date('now') ORDER BY date ASC LIMIT 1", (session['username'],))
        upcoming_booking = c.fetchone()
        return render_template('cleaner_clock.html', username=session['username'], role=session['role'], booking=upcoming_booking)
    return redirect(url_for('home'))

@app.route('/clockin')
def clock_in():
    if session.get('role') in ['owner', 'cleaner']:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO attendance (user_id, username, clock_in) VALUES (?, ?, ?)", 
                  (session['user_id'], session['username'], datetime.now()))
        conn.commit()
        return redirect(url_for('clock'))
    return redirect(url_for('home'))

@app.route('/clockout')
def clock_out():
    if session.get('role') in ['owner', 'cleaner']:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            UPDATE attendance 
            SET clock_out=? 
            WHERE user_id=? AND clock_out IS NULL
        ''', (datetime.now(), session['user_id']))
        conn.commit()
        return redirect(url_for('clock'))
    return redirect(url_for('home'))

@app.route('/invoices')
def invoices():
    if session.get('role') == 'owner':
        return render_template('invoices.html', username=session['username'])
    return redirect(url_for('home'))

@app.route('/cleaner/profile', methods=['GET', 'POST'])
def cleaner_profile():
    if session.get('role') != 'cleaner':
        return redirect(url_for('home'))

    conn = get_db()
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        availability = request.form['availability']

        c.execute('''
            INSERT INTO cleaner_profiles (user_id, name, phone, availability)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, phone=excluded.phone, availability=excluded.availability
        ''', (session['user_id'], name, phone, availability))
        conn.commit()
        return redirect(url_for('cleaner_profile'))

    c.execute("SELECT name, phone, availability FROM cleaner_profiles WHERE user_id=?", (session['user_id'],))
    profile = c.fetchone()
    return render_template('cleaner_profile.html', profile=profile, username=session['username'])

@app.route('/bookings')
def bookings():
    role = session.get('role')
    if role == 'owner':
        return redirect(url_for('owner_bookings'))
    elif role == 'cleaner':
        return redirect(url_for('cleaner_bookings'))
    else:
        return redirect(url_for('home'))

@app.route('/owner/bookings')
def owner_bookings():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    all_bookings = c.fetchall()
    return render_template('owner_bookings.html', bookings=all_bookings, username=session['username'], role=session['role'])

@app.route('/cleaner/bookings')
def cleaner_bookings():
    if session.get('role') != 'cleaner':
        return redirect(url_for('home'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bookings WHERE cleaner=?", (session['username'],))
    cleaner_bookings = c.fetchall()
    return render_template('cleaner_bookings.html', bookings=cleaner_bookings, username=session['username'])

@app.route('/bookings/add', methods=['GET', 'POST'])
def add_booking():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE role='cleaner'")
    cleaners = [row[0] for row in c.fetchall()]

    if request.method == 'POST':
        client = request.form['client']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']
        cleaner = request.form['cleaner']

        c.execute("INSERT INTO bookings (client_name, date, time, location, cleaner) VALUES (?, ?, ?, ?, ?)",
                  (client, date, time, location, cleaner))
        conn.commit()
        return redirect(url_for('bookings'))

    # GET request: render the add booking form with cleaners list
    return render_template('add_booking.html', cleaners=cleaners)

# In-memory message store for demonstration
chat_messages = []

@app.route('/owner/chat')
def owner_chat():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    return render_template('owner_chat.html', username=session.get('username', 'Owner'), messages=chat_messages, role=session.get('role'))

@app.route('/owner/chat/send', methods=['POST'])
def owner_chat_send():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    message = request.form.get('message', '').strip()
    if message:
        chat_messages.append({'sender': session.get('username', 'Owner'), 'text': message})
    return redirect(url_for('owner_chat'))

# ------------------------
# MAIN
# ------------------------

def init_db():
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT CHECK(role IN ('owner', 'cleaner')) NOT NULL
                )
            ''')
            c.execute('''
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    clock_in TIMESTAMP,
                    clock_out TIMESTAMP
                )
            ''')
            c.execute('''
                CREATE TABLE bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT,
                    date TEXT,
                    time TEXT,
                    location TEXT,
                    cleaner TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE cleaner_profiles (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    availability TEXT
                )
            ''')
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("Supriti", "Owner@gardenia", "owner"))
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("bob", "5678", "cleaner"))
            conn.commit()
            print("Database initialized.")

from flask import jsonify

@app.route('/api/bookings')
def api_bookings():
    role = session.get('role')
    username = session.get('username')
    print(f"API /api/bookings called by user: {username} with role: {role}")
    if role not in ['owner', 'cleaner']:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    c = conn.cursor()
    if role == 'owner':
        c.execute("SELECT * FROM bookings")
    else:
        c.execute("SELECT * FROM bookings WHERE cleaner=?", (username,))
    bookings = c.fetchall()
    print(f"Bookings fetched for user {username}: {bookings}")
    bookings_list = []
    for b in bookings:
        booking_dict = {
            'id': b[0],
            'client_name': b[1],
            'date': b[2],
            'time': b[3],
            'location': b[4],
            'cleaner': b[5]
        }
        bookings_list.append(booking_dict)
    return jsonify(bookings_list)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
