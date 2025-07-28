import sqlite3
from typing import Dict, List, Optional

class ResumeDatabase:
    def __init__(self, db_name: str = "resumes.db"):
        self.db_name = db_name
        self.create_tables()

    def create_tables(self):
        """Create tables for storing resume data."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER,
                    details TEXT,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER,
                    title TEXT,
                    company TEXT,
                    dates TEXT,
                    description TEXT,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER,
                    skill TEXT,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id)
                )
            ''')
            conn.commit()

    def insert_resume(self, parsed_data: Dict) -> int:
        """Insert parsed resume data into the database and return resume_id."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO resumes (name, email, phone) VALUES (?, ?, ?)",
                (
                    parsed_data.get("name", "Unknown"),
                    parsed_data.get("email", ""),
                    parsed_data.get("phone", ""),
                ),
            )
            cursor.execute("SELECT id FROM resumes WHERE email = ?", (parsed_data.get("email", ""),))
            resume_id = cursor.fetchone()[0]
            conn.commit()

            # Insert education
            for edu in parsed_data.get("education", []):
                cursor.execute(
                    "INSERT INTO education (resume_id, details) VALUES (?, ?)",
                    (resume_id, edu),
                )

            # Insert experience
            for exp in parsed_data.get("experience", []):
                description = " ".join(exp.get("description", []))
                cursor.execute(
                    "INSERT INTO experience (resume_id, title, company, dates, description) VALUES (?, ?, ?, ?, ?)",
                    (
                        resume_id,
                        exp.get("title", ""),
                        exp.get("company", ""),
                        exp.get("dates", ""),
                        description,
                    ),
                )

            # Insert skills
            for skill in parsed_data.get("skills", []):
                cursor.execute(
                    "INSERT INTO skills (resume_id, skill) VALUES (?, ?)",
                    (resume_id, skill),
                )

            conn.commit()
            return resume_id

    def get_resume(self, resume_id: int) -> Optional[Dict]:
        """Retrieve resume data by ID."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
            resume = cursor.fetchone()
            if not resume:
                return None

            cursor.execute("SELECT details FROM education WHERE resume_id = ?", (resume_id,))
            education = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT title, company, dates, description FROM experience WHERE resume_id = ?",
                (resume_id,),
            )
            experience = [
                {"title": row[0], "company": row[1], "dates": row[2], "description": row[3]}
                for row in cursor.fetchall()
            ]
            cursor.execute("SELECT skill FROM skills WHERE resume_id = ?", (resume_id,))
            skills = [row[0] for row in cursor.fetchall()]

            return {
                "id": resume[0],
                "name": resume[1],
                "email": resume[2],
                "phone": resume[3],
                "created_at": resume[4],
                "education": education,
                "experience": experience,
                "skills": skills,
            }

    def get_all_resumes(self) -> List[Dict]:
        """Retrieve all resumes."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM resumes")
            resume_ids = [row[0] for row in cursor.fetchall()]
            return [self.get_resume(resume_id) for resume_id in resume_ids]