import sqlite3

conn = sqlite3.connect('ats.db')
cursor = conn.cursor()

# --- Create the candidates table ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, phone TEXT,
    education_qualifications TEXT, total_experience_years REAL, skills TEXT,
    experience_summary TEXT, status TEXT, aptitude_score INTEGER, aptitude_result TEXT
);
''')

# --- Create the interviews table ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS interviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER, interviewer_name TEXT,
    interview_date TEXT, interview_time TEXT, comments TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates (id)
);
''')

# --- NEW: Create the users table for HR login ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
''')

# --- NEW: Insert a default HR user ---
try:
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('hr', 'password'))
except sqlite3.IntegrityError:
    pass # User already exists

conn.commit()
conn.close()

print("Database 'ats.db' with all tables created successfully.")