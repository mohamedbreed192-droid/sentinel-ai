from celery import Celery
from .config import settings
from .models import Analysis, Session
from .pipeline import analyze_public

celery = Celery("sentinel", broker=settings.redis_url)
celery.conf.update(task_serializer="json", accept_content=["json"], worker_concurrency=2, task_soft_time_limit=540, task_time_limit=600, task_acks_late=True, worker_prefetch_multiplier=1)

@celery.task(name="sentinel.analyze")
def analyze_job(identifier: str):
    with Session() as session:
        job = session.get(Analysis, identifier)
        if job is None or job.status == "completed":
            return
        job.status = "running"
        session.commit()
        try:
            job.report = analyze_public(job.repository)
            job.status = "completed"
        except Exception:
            # Third-party exceptions may embed source/secrets: never persist raw messages.
            job.status = "failed"
            job.error = "Analysis could not complete. Check repository availability, snapshot limits, or scanner configuration."
        session.commit()
