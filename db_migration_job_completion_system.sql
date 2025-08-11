-- Migration script for job completion system
-- This script adds the necessary tables and columns to implement automatic job completion and invoice generation

-- Step 1: Add booking_id to attendance table to link clock events to specific jobs
ALTER TABLE attendance ADD COLUMN booking_id INTEGER;

-- Step 2: Add status column to bookings table to track job completion
ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled'));

-- Step 3: Add completed_at timestamp to bookings
ALTER TABLE bookings ADD COLUMN completed_at TIMESTAMP;

-- Step 4: Create completed_jobs table for tracking finished jobs
CREATE TABLE IF NOT EXISTS completed_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    cleaner_username TEXT NOT NULL,
    client_name TEXT NOT NULL,
    date_completed DATE NOT NULL,
    hours_worked REAL NOT NULL,
    payment_amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- Step 5: Create invoice_items table for detailed invoice entries
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    completed_job_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    hours_worked REAL NOT NULL,
    rate_per_hour REAL NOT NULL,
    total_amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (completed_job_id) REFERENCES completed_jobs(id)
);

-- Step 6: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_attendance_booking_id ON attendance(booking_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_completed_jobs_cleaner ON completed_jobs(cleaner_username);
CREATE INDEX IF NOT EXISTS idx_completed_jobs_date ON completed_jobs(date_completed);
