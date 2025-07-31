import sqlite3

# Connect to the database (this will create the file if it doesn't exist)
conn = sqlite3.connect('ats.db')
cursor = conn.cursor()

# --- Create the candidates table with all final columns ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    education_qualifications TEXT,
    total_experience_years REAL,
    skills TEXT,
    experience_summary TEXT,
    status TEXT,
    aptitude_score INTEGER,
    aptitude_result TEXT
);
''')

# --- Create the interviews table ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS interviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    interviewer_name TEXT,
    interview_date TEXT,
    interview_time TEXT,
    comments TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates (id)
);
''')


# Save the changes and close the connection
conn.commit()
conn.close()

print("Database 'ats.db' with all tables created successfully.")