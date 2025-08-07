from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import sqlite3
from resume_parser import ResumeParser
import os
import csv
import io 
from mail_sender import send_email
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_super_secret_key_change_later'

# --- NEW: Login required decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    return redirect(url_for('apply'))

@app.route('/apply')
def apply():
    return render_template('apply.html')
    
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

# --- NEW: Login and Logout Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('ats.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('show_candidates'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- HR Routes (now protected) ---
@app.route('/hr')
@login_required
def hr_dashboard():
    return redirect(url_for('show_candidates'))

@app.route('/candidates')
@login_required
def show_candidates():
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, i.id as interview_id 
        FROM candidates c
        LEFT JOIN interviews i ON c.id = i.candidate_id
        GROUP BY c.id
        ORDER BY c.id DESC
    """)
    candidates = cursor.fetchall()
    conn.close()
    return render_template('candidates.html', candidates=candidates)

@app.route('/upload_results', methods=['POST'])
@login_required
def upload_results():
    # ... (function body remains the same)
    if 'results_file' not in request.files or request.files['results_file'].filename == '':
        flash("Please upload a valid CSV file.", "error")
        return redirect(url_for('show_candidates'))
    file = request.files['results_file']
    if not file.filename.endswith('.csv'):
        flash("Invalid file type. Please upload a CSV file.", "error")
        return redirect(url_for('show_candidates'))
    PASSING_SCORE = 70
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_reader = csv.DictReader(stream)
    conn = sqlite3.connect('ats.db')
    cursor = conn.cursor()
    for row in csv_reader:
        email = row['email']
        score = int(row['score'])
        result = 'Cleared' if score >= PASSING_SCORE else 'Not Cleared'
        new_status = 'Test Cleared' if result == 'Cleared' else 'Test Failed'
        cursor.execute("""
            UPDATE candidates 
            SET aptitude_score = ?, aptitude_result = ?, status = ?
            WHERE email = ?
        """, (score, result, new_status, email))
    conn.commit()
    conn.close()
    flash("Test results uploaded and statuses updated successfully.", "success")
    return redirect(url_for('show_candidates'))
    
@app.route('/update_status/<int:candidate_id>', methods=['POST'])
@login_required
def update_status(candidate_id):
    # ... (function body remains the same)
    new_status = request.form['status']
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    if candidate:
        candidate_email = candidate['email']
        candidate_name = candidate['name']
        cursor.execute("UPDATE candidates SET status = ? WHERE id = ?", (new_status, candidate_id))
        conn.commit()
        if new_status == 'Shortlisted':
            subject = "Next Steps in Your Application"
            body = "Hello,\n\nThank you for your interest. We are pleased to inform you that you have been shortlisted for the next round.\n\nPlease complete the aptitude test at the following link: [Insert Test Link Here]\n\nBest regards,\nHR Team"
            send_email(candidate_email, subject, body)
        elif new_status == 'Hired':
            subject = f"Congratulations! Offer of Employment"
            body = f"Dear {candidate_name},\n\nFollowing your recent interviews, we are delighted to offer you the position.\n\nWe were very impressed with your skills and experience and believe you will be a great asset to our team. A formal offer letter with details on your role, compensation, and start date will be sent shortly.\n\nWelcome aboard!\n\nBest regards,\nHR Team"
            send_email(candidate_email, subject, body)
    conn.close()
    flash(f"Candidate status updated to '{new_status}'.", "success")
    return redirect(url_for('show_candidates'))

@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    # ... (function body remains the same)
    conn = sqlite3.connect('ats.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interviews WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    conn.commit()
    conn.close()
    flash(f"Candidate #{candidate_id} has been deleted.", "success")
    return redirect(url_for('show_candidates'))

@app.route('/schedule_form/<int:candidate_id>')
@login_required
def schedule_form(candidate_id):
    # ... (function body remains the same)
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    conn.close()
    return render_template('schedule_form.html', candidate=candidate, candidate_id=candidate_id)

@app.route('/schedule_interview/<int:candidate_id>', methods=['POST'])
@login_required
def schedule_interview(candidate_id):
    # ... (function body remains the same)
    interviewer_name = request.form['interviewer']
    interview_date = request.form['date']
    interview_time = request.form['time']
    interviewer_email = 'interviewer@example.com' 
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    candidate_name = candidate['name']
    candidate_email = candidate['email']
    cursor.execute("""
        INSERT INTO interviews (candidate_id, interviewer_name, interview_date, interview_time)
        VALUES (?, ?, ?, ?)
    """, (candidate_id, interviewer_name, interview_date, interview_time))
    cursor.execute("UPDATE candidates SET status = ? WHERE id = ?", ('Interview Scheduled', candidate_id))
    conn.commit()
    conn.close()
    candidate_subject = "Interview Scheduled"
    candidate_body = f"Hello {candidate_name},\n\nThis is to confirm that your interview has been scheduled with {interviewer_name} on {interview_date} at {interview_time}.\n\nBest regards,\nHR Team"
    send_email(candidate_email, candidate_subject, candidate_body)
    interviewer_subject = f"Interview Scheduled with {candidate_name}"
    interviewer_body = f"Hello {interviewer_name},\n\nYou are scheduled to interview the candidate, {candidate_name}, on {interview_date} at {interview_time}.\n\nPlease be prepared.\n\nBest regards,\nATS System"
    send_email(interviewer_email, interviewer_subject, interviewer_body)
    flash(f"Interview scheduled for {candidate_name}.", "success")
    return redirect(url_for('show_candidates'))

@app.route('/feedback_form/<int:candidate_id>')
@login_required
def feedback_form(candidate_id):
    # ... (function body remains the same)
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    conn.close()
    return render_template('feedback_form.html', candidate=candidate, candidate_id=candidate_id)

@app.route('/submit_feedback/<int:candidate_id>', methods=['POST'])
@login_required
def submit_feedback(candidate_id):
    # ... (function body remains the same)
    comments = request.form['comments']
    interview_result = request.form['result']
    conn = sqlite3.connect('ats.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM interviews WHERE candidate_id = ?", (candidate_id,))
    interview = cursor.fetchone()
    if not interview:
        cursor.execute("INSERT INTO interviews (candidate_id) VALUES (?)", (candidate_id,))
        conn.commit()
    cursor.execute("UPDATE interviews SET comments = ? WHERE candidate_id = ?", (comments, candidate_id))
    new_status = 'Interview Cleared' if interview_result == 'Cleared' else 'Interview Failed'
    cursor.execute("UPDATE candidates SET status = ? WHERE id = ?", (new_status, candidate_id))
    conn.commit()
    conn.close()
    flash("Interview feedback submitted successfully.", "success")
    return redirect(url_for('show_candidates'))

# --- Unprotected Public Routes ---
@app.route('/upload', methods=['POST'])
def upload_resume():
    # ... (function body remains the same)
    if 'resume' not in request.files or request.files['resume'].filename == '':
        flash("No resume file selected.", "error")
        return redirect(url_for('apply'))
    file = request.files['resume']
    candidate_name_form = request.form['name']
    candidate_email_form = request.form['email']
    if file:
        filepath = os.path.join("./temp_resumes", file.filename)
        file.save(filepath)
        parser = ResumeParser()
        resume_text = parser.extract_text_from_pdf(filepath)
        parsed_data = parser.parse(resume_text)
        conn = sqlite3.connect('ats.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO candidates (name, email, phone, education_qualifications, total_experience_years, skills, experience_summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Applied')
            ''', (
                candidate_name_form,
                candidate_email_form,
                parsed_data.get('phone'),
                ', '.join(parsed_data.get('education_qualifications', [])),
                parsed_data.get('total_experience_years'),
                ', '.join(parsed_data.get('skills', [])),
                '\n'.join(parsed_data.get('experience_summary', []))
            ))
            conn.commit()
            subject = "Application Received"
            body = f"Hello {candidate_name_form},\n\nThank you for applying. We have successfully received your resume.\n\nOur team will review your application and contact you if your qualifications meet our needs.\n\nBest regards,\nHR Team"
            send_email(candidate_email_form, subject, body)
            return redirect(url_for('thank_you'))
        except sqlite3.IntegrityError:
            flash(f"A candidate with the email '{candidate_email_form}' already exists.", "error")
            return redirect(url_for('apply'))
        finally:
            conn.close()
            os.remove(filepath)

@app.route('/api/candidates')
def api_candidates():
    # ... (function body remains the same)
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, i.id as interview_id 
        FROM candidates c
        LEFT JOIN interviews i ON c.id = i.candidate_id
        GROUP BY c.id
        ORDER BY c.id ASC
    """)
    candidates = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in candidates])

if __name__ == '__main__':
    if not os.path.exists("./temp_resumes"):
        os.makedirs("./temp_resumes")
    app.run(debug=True)