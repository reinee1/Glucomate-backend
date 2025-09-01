import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_verification_email(to_email: str, verify_url: str):
    subject = "Verify your Glucomate account"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Welcome to Glucomate!</h2>
        <p>Thank you for creating an account. Please verify your email address to get started.</p>
        <p>Click the button below to verify your email:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Verify My Email
            </a>
        </div>
        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all; color: #666; font-size: 14px;">{verify_url}</p>
        <p>If you didn't create this account, please ignore this email.</p>
    </div>
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


def send_password_reset_email(to_email: str, reset_url: str):
    subject = "Reset your Glucomate password"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Password Reset Request</h2>
        <p>We received a request to reset your Glucomate password.</p>
        <p>Click the button below to reset your password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Reset My Password
            </a>
        </div>
        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all; color: #666; font-size: 14px;">{reset_url}</p>
        <p>If you didn't request this password reset, please ignore this email. Your account remains secure.</p>
        <p>This link will expire in 30 minutes for your security.</p>
    </div>
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