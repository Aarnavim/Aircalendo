import sqlite3

def print_attendance_schema():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(attendance);")
    columns = cursor.fetchall()
    print("Attendance table schema:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    print_attendance_schema()
