# email_utils.py

import smtplib
from email.mime.text import MIMEText
from flask import current_app # Import current_app to access Flask config


def send_status_email(recipient_email, subject, body):
    """
    Sends a plain text email using configured SMTP settings.
    Requires Flask application context to access config.
    """
    # Access config from the Flask app via current_app
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_port = current_app.config.get('MAIL_PORT')
    mail_use_tls = current_app.config.get('MAIL_USE_TLS', False) # Default to False if not set
    mail_use_ssl = current_app.config.get('MAIL_USE_SSL', False) # Default to False if not set
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD') # Use App Password for Gmail
    mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', mail_username) # Default sender

    # Basic validation for required config
    if not all([mail_server, mail_port, mail_username, mail_password]):
        print("Email sending skipped: SMTP credentials not fully configured.")
        # Log this more severely in a real application
        return False

    # Create the email message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mail_default_sender
    msg['To'] = recipient_email

    try:
        # Connect to the SMTP server
        if mail_use_ssl:
             server = smtplib.SMTP_SSL(mail_server, mail_port)
        else:
             server = smtplib.SMTP(mail_server, mail_port)
             if mail_use_tls:
                 server.starttls() # Secure the connection

        # Log in to the account
        server.login(mail_username, mail_password)

        # Send the email
        server.sendmail(mail_default_sender, [recipient_email], msg.as_string())

        # Quit the server
        server.quit()

        print(f"Email sent successfully to {recipient_email}")
        return True # Indicate success

    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        # Log the error properly in a real application
        return False # Indicate failure