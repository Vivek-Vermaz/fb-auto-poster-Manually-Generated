import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_alert(subject, body):
    sender_email = os.environ.get("GMAIL_ADDRESS")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient_email = os.environ.get("ALERT_RECIPIENT_EMAIL", sender_email)

    if not sender_email or not sender_password:
        print("Gmail credentials not set. Skipping email alert.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email alert sent successfully: {subject}")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

if __name__ == "__main__":
    # Test
    # send_email_alert("Test Alert", "<h1>This is a test from the FB Auto Poster</h1>")
    pass
