import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_verification_email(to_email: str, verify_url: str):
  
    subject = "Verify your Glucomate account"
    body = f"""
    <p>Welcome to Glucomate!</p>
    <p>Please verify your email by clicking the link below:</p>
    <p><a href="{verify_url}">Verify my email</a></p>
    """
    
    msg = MIMEMultipart("alternative")
    msg["From"] = current_app.config["SMTP_USER"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(current_app.config["SMTP_HOST"], current_app.config["SMTP_PORT"]) as server:
        server.starttls()
        server.login(current_app.config["SMTP_USER"], current_app.config["SMTP_PASS"])
        server.sendmail(current_app.config["SMTP_USER"], to_email, msg.as_string())


