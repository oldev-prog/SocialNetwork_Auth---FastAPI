from celery import Celery

celery_app = Celery(
    'app.signup.email_verification.celery.celery_app',
    broker='amqp://guest:guest@localhost:5672//'
)