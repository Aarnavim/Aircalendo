import sqlite3

def main():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM attendance LIMIT 5")
    rows = c.fetchall()
    if rows:
        print("Attendance records found:")
        for row in rows:
            print(row)
    else:
        print("No attendance records found.")
    conn.close()

if __name__ == "__main__":
    main()
