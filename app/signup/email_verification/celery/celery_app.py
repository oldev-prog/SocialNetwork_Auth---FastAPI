from celery import Celery

celery_app = Celery(
    'social_auth',
    broker='amqp://guest:guest@localhost:5672//',
    include=['app.signup.email_verification.celery.tasks']
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1
)