import sqlite3

def apply_migration(db_path, migration_file):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    with open(migration_file, 'r') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    print(f"Migration {migration_file} applied successfully.")

if __name__ == "__main__":
    apply_migration('users.db', 'db_migration_add_completed_jobs.sql')
