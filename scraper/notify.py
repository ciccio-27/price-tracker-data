import os
import smtplib
from email.mime.text import MIMEText

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")             # the Gmail account sending it
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")   # Gmail "app password", not your normal password
EMAIL_TO = os.environ.get("EMAIL_TO")                       # where alerts should land (can be the same address)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(subject: str, message: str):
    if not all([EMAIL_ADDRESS, EMAIL_APP_PASSWORD, EMAIL_TO]):
        print("[notify] Email not configured, skipping. Message was:")
        print(f"{subject}\n{message}")
        return

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:
        print(f"[notify] Failed to send email: {exc}")
