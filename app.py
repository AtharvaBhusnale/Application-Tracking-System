from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from resume_parser import ResumeParser # Your enhanced parser
import os
import smtplib
from email.mime.text import MIMEText
import csv
import io # Needed to read the uploaded file in memory

app = Flask(__name__)

# --- Email Configuration ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_SENDER = 'your_email@gmail.com'  # Your email address
EMAIL_PASSWORD = 'your_gmail_app_password' # Your 16-digit App Password

@app.route('/apply')
def apply():
    # This function just shows the new application page
    return render_template('apply.html')
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')
def send_email(recipient, subject, body):
    """A simple function to send an email."""
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [recipient], msg.as_string())
        print(f"Email sent successfully to {recipient}")
    except Exception as e:
        print(f"Error sending email: {e}")

# --- Routes ---

@app.route('/')
def index():
    # Redirect to the main candidates page by default
    return redirect(url_for('show_candidates'))

@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return "No file part", 400
    
    # --- Get data from the form ---
    file = request.files['resume']
    candidate_name_form = request.form['name']
    candidate_email_form = request.form['email']
    
    if file.filename == '':
        return "No selected file", 400

    if file:
        filepath = os.path.join("./temp_resumes", file.filename)
        file.save(filepath)
        
        # --- Run the parser for additional details ---
        parser = ResumeParser()
        resume_text = parser.extract_text_from_pdf(filepath)
        parsed_data = parser.parse(resume_text)

        conn = sqlite3.connect('ats.db')
        cursor = conn.cursor()

        try:
            # --- Use form data for name/email, and parser data for the rest ---
            cursor.execute('''
            INSERT INTO candidates (name, email, phone, education_qualifications, total_experience_years, skills, experience_summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Applied')
            ''', (
                candidate_name_form,   # Use name from form
                candidate_email_form,  # Use email from form
                parsed_data.get('phone'), # Get phone from parser
                ', '.join(parsed_data.get('education_qualifications', [])),
                parsed_data.get('total_experience_years'),
                ', '.join(parsed_data.get('skills', [])),
                '\n'.join(parsed_data.get('experience_summary', []))
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            # This happens if the email already exists
            pass
        finally:
            conn.close()
        
        os.remove(filepath)

        return redirect(url_for('thank_you'))
    
@app.route('/upload_results', methods=['POST'])
def upload_results():
    if 'results_file' not in request.files:
        return "No results file part", 400
    
    file = request.files['results_file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return "Please upload a valid CSV file", 400

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

    return redirect(url_for('show_candidates'))

@app.route('/candidates')
def show_candidates():
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, i.id as interview_id 
        FROM candidates c
        LEFT JOIN interviews i ON c.id = i.candidate_id AND c.status = 'Interview Scheduled'
        GROUP BY c.id
        ORDER BY c.id DESC
    """)
    candidates = cursor.fetchall()
    conn.close()
    return render_template('candidates.html', candidates=candidates)

@app.route('/update_status/<int:candidate_id>', methods=['POST'])
def update_status(candidate_id):
    new_status = request.form['status']
    
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, email FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    candidate_email = candidate['email']
    candidate_name = candidate['name']

    cursor.execute("UPDATE candidates SET status = ? WHERE id = ?", (new_status, candidate_id))
    conn.commit()
    conn.close()
    
    # --- MERGED EMAIL LOGIC ---
    if new_status == 'Shortlisted':
        subject = "Next Steps in Your Application"
        body = "Hello,\n\nThank you for your interest. We are pleased to inform you that you have been shortlisted for the next round.\n\nPlease complete the aptitude test at the following link: [Insert Test Link Here]\n\nBest regards,\nHR Team"
        send_email(candidate_email, subject, body)
    
    elif new_status == 'Hired':
        subject = f"Congratulations! Offer of Employment"
        body = f"Dear {candidate_name},\n\nFollowing your recent interviews, we are delighted to offer you the position.\n\nWe were very impressed with your skills and experience and believe you will be a great asset to our team. A formal offer letter with details on your role, compensation, and start date will be sent shortly.\n\nWelcome aboard!\n\nBest regards,\nHR Team"
        send_email(candidate_email, subject, body)

    return redirect(url_for('show_candidates'))

@app.route('/schedule_form/<int:candidate_id>')
def schedule_form(candidate_id):
    conn = sqlite3.connect('ats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
    candidate = cursor.fetchone()
    conn.close()
    return render_template('schedule_form.html', candidate=candidate, candidate_id=candidate_id)

@app.route('/schedule_interview/<int:candidate_id>', methods=['POST'])
def schedule_interview(candidate_id):
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

    return redirect(url_for('show_candidates'))

@app.route('/feedback_form/<int:interview_id>')
def feedback_form(interview_id):
    return render_template('feedback_form.html', interview_id=interview_id)

@app.route('/submit_feedback/<int:interview_id>', methods=['POST'])
def submit_feedback(interview_id):
    comments = request.form['comments']
    interview_result = request.form['result']

    conn = sqlite3.connect('ats.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE interviews SET comments = ? WHERE id = ?", (comments, interview_id))

    cursor.execute("SELECT candidate_id FROM interviews WHERE id = ?", (interview_id,))
    candidate_id = cursor.fetchone()[0]

    new_status = 'Interview Cleared' if interview_result == 'Cleared' else 'Interview Failed'
    cursor.execute("UPDATE candidates SET status = ? WHERE id = ?", (new_status, candidate_id))

    conn.commit()
    conn.close()

    return redirect(url_for('show_candidates'))

if __name__ == '__main__':
    if not os.path.exists("./temp_resumes"):
        os.makedirs("./temp_resumes")
    app.run(debug=True)