from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify

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
# ROUTES
# ------------------------

@app.route('/debug/completed_jobs')
def debug_completed_jobs():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM completed_jobs")
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    jobs = []
    for row in rows:
        job = dict(zip(columns, row))
        jobs.append(job)
    return jsonify(jobs)
