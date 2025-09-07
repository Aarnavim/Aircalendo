"""
Aircalendo Cleaning Service Management System

This Flask application provides a comprehensive platform for managing cleaning services,
including booking management, attendance tracking, invoicing, and real-time chat functionality.

Key Features:
- User authentication with role-based access (owner/cleaner)
- Booking management system with calendar integration
- Clock-in/clock-out attendance tracking
- Automated invoice generation based on hours worked
- Real-time chat system for communication
- Profile management for cleaners
- Responsive web interface

Database Schema:
- users: User authentication and role management
- attendance: Clock-in/out records with hours calculation
- bookings: Client booking information
- cleaner_profiles: Cleaner personal and availability information

Author: Aircalendo Development Team
Version: 1.0.0
"""

from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, flash
import sqlite3
import os
from datetime import datetime, timedelta
from calendar import monthrange, month_name

# Application Configuration
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
                    clock_out TIMESTAMP,
                    hours_worked REAL DEFAULT 0
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
            c.execute('''
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    type TEXT DEFAULT 'chat',
                    cleaner TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("Supriti", "Owner@gardenia", "owner"))
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("CleanerM@AC", "Cleaner@AC", "cleaner"))
            conn.commit()
            print("Database initialized.")

# ------------------------
# ROUTES
# ------------------------

@app.route('/debug/attendance')
def debug_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, user_id, username, clock_in, clock_out, hours_worked
            FROM attendance
            WHERE user_id=?
            ORDER BY clock_in DESC
        ''', (session['user_id'],))
        attendance_rows = c.fetchall()

        c.execute('''
            SELECT id, client_name, date, time, cleaner
            FROM bookings
            WHERE cleaner=?
            ORDER BY date DESC
        ''', (session.get('username'),))
        booking_rows = c.fetchall()

        return jsonify({
            'attendance': [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'clock_in': row[3],
                    'clock_out': row[4],
                    'hours_worked': row[5]
                } for row in attendance_rows
            ],
            'bookings': [
                {
                    'id': row[0],
                    'client_name': row[1],
                    'date': row[2],
                    'time': row[3],
                    'cleaner': row[4]
                } for row in booking_rows
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['email']
    password = request.form['password']

    conn = get_db()
    cursor = conn.cursor()
    
    # First check if username exists
    cursor.execute("SELECT id, role, password FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    
    if not user:
        # Username doesn't exist
        return render_template('login.html', error="Invalid username or password")
    
    # Username exists, check password
    stored_password = user[2]
    if password != stored_password:
        # Wrong password
        return render_template('login.html', error="incorrect password, please try again")
    
    # Both username and password are correct
    session['user_id'] = user[0]
    session['username'] = username
    session['role'] = user[1]

    if user[1] == 'owner':
        return redirect(url_for('owner_dashboard'))
    elif user[1] == 'cleaner':
        return redirect(url_for('cleaner_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/owner_dashboard')
def owner_dashboard():
    if session.get('role') == 'owner':
        return render_template('owner_dashboard.html', username=session.get('username'))
    return redirect(url_for('home'))

@app.route('/cleaner_button')
def cleaner_button():
    if session.get('role') == 'owner':
        return render_template('cleaner_button.html')
    return redirect(url_for('home'))

@app.route('/cleaner_dashboard')
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

@app.route('/cleaner')
def cleaner():
    """Alias route for cleaner dashboard"""
    return redirect(url_for('cleaner_dashboard'))

@app.route('/calendar')
def calendar():
    if session.get('role') in ['owner', 'cleaner']:
        # Get month and year from query parameters or default to current
        month = request.args.get('month', default=None, type=int)
        year = request.args.get('year', default=None, type=int)
        today = datetime.today().date()
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
        flash('Changes saved successfully!', 'success')
        return redirect(url_for('owner_bookings'))
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

@app.route('/clockin')
def clock_in():
    if session.get('role') in ['owner', 'cleaner']:
        conn = get_db()
        c = conn.cursor()
        clock_in_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO attendance (user_id, username, clock_in) VALUES (?, ?, ?)", 
                  (session['user_id'], session['username'], clock_in_time))
        conn.commit()
        return redirect(url_for('clock'))
    return redirect(url_for('home'))

@app.route('/clockout')
def clock_out():
    if session.get('role') in ['owner', 'cleaner']:
        try:
            conn = get_db()
            c = conn.cursor()
            clock_out_time = datetime.now()
            # Get the clock_in time for the current attendance record
            c.execute('''
                SELECT clock_in FROM attendance
                WHERE user_id=? AND clock_out IS NULL
                ORDER BY clock_in DESC LIMIT 1
            ''', (session['user_id'],))
            row = c.fetchone()
            if row:
                clock_in_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                duration = clock_out_time - clock_in_time
                hours_worked = duration.total_seconds() / 3600.0
                clock_out_time_str = clock_out_time.strftime('%Y-%m-%d %H:%M:%S')
                c.execute('''
                    UPDATE attendance 
                    SET clock_out=?, hours_worked=?
                    WHERE user_id=? AND clock_out IS NULL
                ''', (clock_out_time_str, hours_worked, session['user_id']))
                conn.commit()
                return jsonify({'message': 'Clocked out successfully', 'hours_worked': hours_worked}), 200
            else:
                return jsonify({'error': 'No active clock-in record found'}), 400
        except Exception as e:
            print(f"Error during clock out: {e}")
            return jsonify({'error': f'Failed to clock out: {e}'}), 500
    return redirect(url_for('home'))

@app.route('/api/total_hours')
def api_total_hours():
    """API endpoint to get total hours worked by the logged-in user"""
    if session.get('role') not in ['owner', 'cleaner']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Calculate total hours worked by the user
        c.execute('''
            SELECT COALESCE(SUM(hours_worked), 0) FROM attendance
            WHERE user_id=?
        ''', (session['user_id'],))
        
        result = c.fetchone()
        total_hours = result[0] if result and result[0] is not None else 0
        
        return jsonify({'total_hours': total_hours})
        
    except Exception as e:
        print(f"Error fetching total hours: {e}")
        return jsonify({'error': 'Failed to fetch total hours'}), 500

@app.route('/clock')
def clock():
    """Clock page for cleaners to clock in/out"""
    if session.get('role') not in ['owner', 'cleaner']:
        return redirect(url_for('home'))
    
    conn = get_db()
    c = conn.cursor()
    
    # Get current booking for the logged-in user
    if session.get('role') == 'cleaner':
        c.execute("SELECT client_name, date, time FROM bookings WHERE cleaner=? ORDER BY date DESC LIMIT 1", 
                 (session['username'],))
    else:
        c.execute("SELECT client_name, date, time FROM bookings ORDER BY date DESC LIMIT 1")
    
    booking = c.fetchone()
    
    return render_template('cleaner_clock.html', booking=booking, username=session['username'])

@app.route('/invoices')
def invoices():
    try:
        role = session.get('role')
        if not role:
            return redirect(url_for('home'))
            
        conn = get_db()
        c = conn.cursor()
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Ensure username is available
        username = session.get('username', 'User')
        
        # Initialize default values
        total_hours_worked = 0
        total_earnings = 0
        invoice_data = []
        cleaners_invoice = []
        hourly_rate = 35
        
        # Calculate total hours worked for the week
        if role in ['owner', 'cleaner']:
            try:
                c.execute('''
                    SELECT COALESCE(SUM(hours_worked), 0) FROM attendance
                    WHERE user_id = ? AND clock_out BETWEEN ? AND ?
                ''', (session['user_id'], week_ago.isoformat() + " 00:00:00", today.isoformat() + " 23:59:59"))
                result = c.fetchone()
                total_hours_worked = result[0] if result and result[0] is not None else 0
                print(f"DEBUG: Found {total_hours_worked} hours worked in the week based on clock_out")
            except Exception as e:
                print(f"Error calculating hours: {e}")
                total_hours_worked = 0
        
        print(f"DEBUG: total_hours_worked={total_hours_worked}, hourly_rate={hourly_rate}")
        total_earnings = float(total_hours_worked) * float(hourly_rate)
        print(f"DEBUG: total_earnings={total_earnings}")
        
        if role == 'cleaner':
            try:
                # Get all bookings for the cleaner (not limited to last 7 days)
                c.execute('''
                    SELECT id, client_name, date, time FROM bookings
                    WHERE cleaner=?
                    ORDER BY date DESC
                ''', (username,))
                bookings = c.fetchall()
                
                invoice_data = []
                for booking in bookings:
                    booking_id, client_name, date_str, time_str = booking
                    try:
                        # Calculate hours for this specific date
                        start_datetime = date_str + " 00:00:00"
                        end_datetime = date_str + " 23:59:59"
                        c.execute('''
                            SELECT id, clock_in, clock_out, hours_worked FROM attendance
                            WHERE user_id = ? AND 
                            (
                                (clock_in BETWEEN ? AND ?) OR
                                (clock_out BETWEEN ? AND ?)
                            )
                        ''', (session['user_id'], start_datetime, end_datetime, start_datetime, end_datetime))
                        attendance_records = c.fetchall()
                        print(f"DEBUG: Booking {booking_id} date: {date_str}")
                        for record in attendance_records:
                            print(f"DEBUG: Attendance record clock_in: {record[1]}, clock_out: {record[2]}, hours_worked: {record[3]}")
                        hours_worked = sum([record[3] for record in attendance_records if record[3] is not None])
                        print(f"DEBUG: Booking {booking_id} hours_worked={hours_worked} (sum of attendance records)")
                        earning = hours_worked * hourly_rate
                        print(f"DEBUG: Booking {booking_id} earning={earning}")
                        
                        invoice_data.append({
                            'client_name': client_name or 'Unknown Client',
                            'date': date_str or '',
                            'time': time_str or '',
                            'hours_worked': hours_worked,
                            'earning': earning
                        })
                    except Exception as e:
                        print(f"Error processing booking {booking_id}: {e}")
                        invoice_data.append({
                            'client_name': client_name or 'Unknown Client',
                            'date': date_str or '',
                            'time': time_str or '',
                            'hours_worked': 0,
                            'earning': 0
                        })
                        
            except Exception as e:
                print(f"Error getting cleaner bookings: {e}")
                invoice_data = []
                
            # Calculate total earnings from all attendance records, not just last 7 days
            c.execute('''
                SELECT COALESCE(SUM(hours_worked), 0) FROM attendance
                WHERE user_id = ?
            ''', (session['user_id'],))
            result = c.fetchone()
            total_hours_worked = result[0] if result and result[0] is not None else 0
            total_earnings = float(total_hours_worked) * float(hourly_rate)
            print(f"DEBUG: Total hours worked (all time): {total_hours_worked}")
            print(f"DEBUG: Total earnings (all time): {total_earnings}")
            
            return render_template('invoice.html', 
                                 username=username, 
                                 invoice_data=invoice_data, 
                                 role=role, 
                                 total_hours_worked=total_hours_worked, 
                                 total_earnings=total_earnings)

        elif role == 'owner':
            try:
                # Get all cleaners
                c.execute("SELECT username FROM users WHERE role='cleaner'")
                cleaners = [row[0] for row in c.fetchall()]
                
                # Calculate total hours for all cleaners (all time, not just last 7 days)
                try:
                    c.execute('''
                        SELECT COALESCE(SUM(hours_worked), 0) FROM attendance
                    ''')
                    total_result = c.fetchone()
                    total_hours_all_cleaners = total_result[0] if total_result and total_result[0] is not None else 0
                    print(f"DEBUG: Found {total_hours_all_cleaners} total hours for all cleaners (all time)")
                except Exception as e:
                    print(f"Error calculating total hours: {e}")
                    total_hours_all_cleaners = 0
                
                # Calculate total earnings directly from total_hours_all_cleaners
                total_earnings = float(total_hours_all_cleaners) * float(hourly_rate)
                
                cleaners_invoice = []
                for cleaner_username in cleaners:
                    try:
                        # Get bookings for this cleaner
                        c.execute('''
                            SELECT id, client_name, date, time FROM bookings
                            WHERE cleaner=? AND date BETWEEN ? AND ?
                            ORDER BY date DESC
                        ''', (cleaner_username, week_ago.isoformat(), today.isoformat()))
                        bookings = c.fetchall()
                        
                        invoice_data = []
                        for booking in bookings:
                            booking_id, client_name, date_str, time_str = booking
                            try:
                                start_datetime = date_str + " 00:00:00"
                                end_datetime = date_str + " 23:59:59"
                                c.execute('''
                                    SELECT COALESCE(SUM(hours_worked), 0) FROM attendance
                                    WHERE LOWER(username)=LOWER(?) AND clock_out BETWEEN ? AND ?
                                ''', (cleaner_username, start_datetime, end_datetime))
                                hours_result = c.fetchone()
                                hours_worked = hours_result[0] if hours_result and hours_result[0] is not None else 0
                                print(f"DEBUG: Cleaner {cleaner_username} Booking {booking_id} hours_worked={hours_worked} (based on clock_out)")
                                earning = hours_worked * hourly_rate
                                print(f"DEBUG: Cleaner {cleaner_username} Booking {booking_id} earning={earning}")
                                
                                invoice_data.append({
                                    'client_name': client_name or 'Unknown Client',
                                    'date': date_str or '',
                                    'time': time_str or '',
                                    'hours_worked': hours_worked,
                                    'earning': earning
                                })
                            except Exception as e:
                                print(f"Error processing cleaner booking: {e}")
                                invoice_data.append({
                                    'client_name': client_name or 'Unknown Client',
                                    'date': date_str or '',
                                    'time': time_str or '',
                                    'hours_worked': 0,
                                    'earning': 0
                                })
                        
                        if invoice_data:  # Only add cleaners with actual bookings
                            cleaners_invoice.append({
                                'cleaner_username': cleaner_username,
                                'invoice_data': invoice_data,
                                'total_hours': sum(b['hours_worked'] for b in invoice_data),
                                'total_earnings': sum(b['earning'] for b in invoice_data)
                            })
                            
                    except Exception as e:
                        print(f"Error processing cleaner {cleaner_username}: {e}")
                        
            except Exception as e:
                print(f"Error getting owner data: {e}")
                cleaners_invoice = []
                
            return render_template('invoice.html', 
                                 username=username, 
                                 cleaners_invoice=cleaners_invoice, 
                                 role=role, 
                                 total_hours_worked=total_hours_all_cleaners, 
                                 total_earnings=total_earnings)

        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"Error in invoices route: {e}")
        # Return a user-friendly error page
        return render_template('invoice.html', 
                             username=session.get('username', 'User'), 
                             invoice_data=[], 
                             cleaners_invoice=[], 
                             role=session.get('role'), 
                             total_hours_worked=0, 
                             total_earnings=0, 
                             error="Unable to load invoice data")

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

@app.route('/cleaner/chat')
def cleaner_chat():
    """Chat page for cleaners to communicate"""
    if session.get('role') not in ['owner', 'cleaner']:
        return redirect(url_for('home'))
    
    messages = get_chat_messages()
    return render_template('cleaner_chat.html', username=session['username'], messages=messages)

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
        
        # Add booking notification to database
        save_message(
            sender=session.get('username', 'Owner'),
            text=f'New booking: {client} on {date} at {time}',
            message_type='booking',
            cleaner=cleaner
        )
        
        return redirect(url_for('bookings'))

    # GET request: render the add booking form with cleaners list
    return render_template('add_booking.html', cleaners=cleaners)

def get_chat_messages():
    """Get all chat messages from database"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT sender, text, type, cleaner, timestamp FROM messages ORDER BY timestamp ASC")
    messages = []
    for row in c.fetchall():
        messages.append({
            'sender': row[0],
            'text': row[1],
            'type': row[2],
            'cleaner': row[3],
            'timestamp': row[4]
        })
    return messages

def save_message(sender, text, message_type='chat', cleaner=None):
    """Save a message to the database"""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, text, type, cleaner) VALUES (?, ?, ?, ?)",
              (sender, text, message_type, cleaner))
    conn.commit()

@app.route('/api/cleaner/notifications')
def cleaner_notifications():
    """API endpoint to fetch notifications for cleaner (owner messages and booking notifications)"""
    if session.get('role') != 'cleaner':
        return jsonify({'error': 'Unauthorized'}), 401
    
    messages = get_chat_messages()
    # Get all messages from owner (chat messages and booking notifications)
    owner_messages = []
    for msg in messages:
        if msg.get('sender') and 'owner' in msg.get('sender').lower():
            # Include all owner messages
            owner_messages.append(msg)
        elif msg.get('type') == 'booking' and msg.get('cleaner') == session['username']:
            # Include booking notifications specifically for this cleaner
            owner_messages.append(msg)
    
    return jsonify({'messages': owner_messages})

@app.route('/owner/chat')
def owner_chat():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    messages = get_chat_messages()
    return render_template('owner_chat.html', username=session.get('username', 'Owner'), messages=messages, role=session.get('role'))

@app.route('/owner/chat/send', methods=['POST'])
def owner_chat_send():
    if session.get('role') != 'owner':
        return redirect(url_for('home'))
    message = request.form.get('message', '').strip()
    if message:
        save_message(session.get('username', 'Owner'), message)
    return redirect(url_for('owner_chat'))

@app.route('/cleaner/chat/send', methods=['POST'])
def cleaner_chat_send():
    """Handle chat message sending for cleaners"""
    if session.get('role') not in ['owner', 'cleaner']:
        return redirect(url_for('home'))
    message = request.form.get('message', '').strip()
    if message:
        save_message(session.get('username', 'User'), message)
    return redirect(url_for('cleaner_chat'))

@app.route('/change_password')
def change_password_form():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id=?", (session['user_id'],))
    user = cursor.fetchone()
    current_email = user[0] if user else ''
    
    return render_template('change_password.html', current_email=current_email, role=session.get('role'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    new_email = request.form.get('new_email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current user info
    cursor.execute("SELECT username, password FROM users WHERE id=?", (session['user_id'],))
    user = cursor.fetchone()
    if not user:
        return render_template('change_password.html', error="User not found")
    
    current_email = user[0]
    current_db_password = user[1]
    
    # Verify current password
    if current_password != current_db_password:
        return render_template('change_password.html', 
                             current_email=current_email, 
                             error="Current password is incorrect")
    
    # Check if email is being changed
    email_changed = new_email and new_email != current_email
    
    # Check if password is being changed
    password_changed = new_password and new_password.strip() != ""
    
    if password_changed:
        if new_password != confirm_password:
            return render_template('change_password.html', 
                                 current_email=current_email, 
                                 error="New passwords do not match")
    
    # Build update query based on what changed
    updates = []
    params = []
    
    if email_changed:
        # Check if new email already exists
        cursor.execute("SELECT id FROM users WHERE username=? AND id!=?", (new_email, session['user_id']))
        if cursor.fetchone():
            return render_template('change_password.html', 
                                 current_email=current_email, 
                                 error="Email already exists")
        updates.append("username=?")
        params.append(new_email)
    
    if password_changed:
        updates.append("password=?")
        params.append(new_password)
    
    if updates:
        query = f"UPDATE users SET {', '.join(updates)} WHERE id=?"
        params.append(session['user_id'])
        cursor.execute(query, params)
        conn.commit()
        
        # Update session username if email changed
        if email_changed:
            session['username'] = new_email
            
        return render_template('change_password.html', 
                           current_email=new_email if email_changed else current_email,
                           success="Account settings updated successfully!")
    
    return render_template('change_password.html', 
                         current_email=current_email,
                         error="No changes detected")

# ------------------------
# MAIN
# ------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
