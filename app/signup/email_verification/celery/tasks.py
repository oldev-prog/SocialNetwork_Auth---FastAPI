from app.signup.email_verification.celery.celery_app import celery_app
from app.signup.email_verification.sending_email import send_verification_email
import asyncio

@celery_app.task(bind=True)
def sending_email_verification(self, recipient_email, subject, plain_content):
    result = asyncio.run(send_verification_email(recipient_email, subject, plain_content))