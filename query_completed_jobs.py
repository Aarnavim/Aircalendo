import sqlite3

def query_completed_jobs(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM completed_jobs ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    if rows:
        for row in rows:
            print(row)
    else:
        print("No records found in completed_jobs table.")

if __name__ == "__main__":
    query_completed_jobs('users.db')
