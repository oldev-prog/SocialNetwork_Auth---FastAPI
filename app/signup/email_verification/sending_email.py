from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib
import logging
from app.data.config import settings

logger = logging.getLogger(__name__)

username = settings.GMAIL_USER
password = settings.GMAIL_APP_PASSWORD

async def send_verification_email(
        recipient_email: str,
        subject: str,
        plain_text: str,
        html_content: str = '',
):
    admin_email = username
    message = MIMEMultipart('alternative')
    message['From'] = admin_email
    message['To'] = recipient_email
    message['Subject'] = subject

    plain_text_message = MIMEText(
        plain_text,
        'plain',
        'utf-8'
    )

    message.attach(plain_text_message)

    if html_content:
        html_message = MIMEText(
            html_content,
            'html',
            'utf-8'
        )
        message.attach(html_message)
    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            username=username,
            password=password,
            use_tls=False,
            start_tls=True,
            timeout=30, )
    except Exception as e:
        logger.exception('Error sending email: %s', e)
        raise
