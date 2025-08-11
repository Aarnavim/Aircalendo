#!/usr/bin/env python3
"""
Migration script to apply job completion system changes to the database.
This script will add the necessary tables and columns for automatic job completion and invoice generation.
"""

import sqlite3
import os

DATABASE = 'users.db'

def apply_migration():
    """Apply the job completion system migration."""
    
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found. Please run the main application first to initialize the database.")
        return
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        print("Applying job completion system migration...")
        
        # Step 1: Add booking_id to attendance table
        try:
            cursor.execute("ALTER TABLE attendance ADD COLUMN booking_id INTEGER")
            print("✓ Added booking_id column to attendance table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("✓ booking_id column already exists in attendance table")
            else:
                raise e
        
        # Step 2: Add status column to bookings table
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled'))")
            print("✓ Added status column to bookings table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("✓ status column already exists in bookings table")
            else:
                raise e
        
        # Step 3: Add completed_at timestamp to bookings
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN completed_at TIMESTAMP")
            print("✓ Added completed_at column to bookings table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("✓ completed_at column already exists in bookings table")
            else:
                raise e
        
        # Step 4: Create completed_jobs table
        cursor.execute('''
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
            )
        ''')
        print("✓ Created completed_jobs table")
        
        # Step 5: Create invoice_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_job_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                hours_worked REAL NOT NULL,
                rate_per_hour REAL NOT NULL,
                total_amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (completed_job_id) REFERENCES completed_jobs(id)
            )
        ''')
        print("✓ Created invoice_items table")
        
        # Step 6: Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_booking_id ON attendance(booking_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_completed_jobs_cleaner ON completed_jobs(cleaner_username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_completed_jobs_date ON completed_jobs(date_completed)")
        print("✓ Created performance indexes")
        
        # Update existing bookings to have 'active' status
        cursor.execute("UPDATE bookings SET status = 'active' WHERE status IS NULL")
        print("✓ Updated existing bookings with active status")
        
        conn.commit()
        print("\n🎉 Migration completed successfully!")
        print("The job completion system is now ready to use.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
