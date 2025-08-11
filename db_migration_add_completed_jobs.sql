-- Migration script to add completed_jobs table

CREATE TABLE IF NOT EXISTS completed_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER,
    cleaner_username TEXT,
    client_name TEXT,
    date_completed TEXT,
    hours_worked REAL,
    payment_amount REAL
);
