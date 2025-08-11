import sqlite3

def inspect_completed_jobs(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cleaner_username, date_completed FROM completed_jobs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    if rows:
        for row in rows:
            print(f"ID: {row[0]}, Cleaner: {row[1]}, Date Completed: {row[2]}")
    else:
        print("No records found in completed_jobs table.")

if __name__ == "__main__":
    inspect_completed_jobs('users.db')
