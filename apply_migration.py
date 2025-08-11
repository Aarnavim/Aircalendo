import sqlite3

def apply_migration(db_path, sql_file):
    try:
        print(f"Applying migration from file: {sql_file}")
        with open(sql_file, 'r') as f:
            sql_script = f.read()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        print("Migration applied successfully.")
    except Exception as e:
        print(f"Error applying migration: {e}")

if __name__ == "__main__":
    db_path = "users.db"
    sql_file = "db_migration_add_booking_id.sql"
    apply_migration(db_path, sql_file)
