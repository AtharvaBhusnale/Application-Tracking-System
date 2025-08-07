import smtplib
from email.mime.text import MIMEText
import os

# --- Email Configuration ---
# Reads credentials from environment variables for security
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

def send_email(recipient, subject, body):
    """A simple function to send an email."""
    # Check if credentials are set
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Error: Email credentials are not set in the environment.")
        return

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