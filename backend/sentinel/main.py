from contextlib import asynccontextmanager
from pathlib import Path
import secrets
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from .assistant import explain
from .config import settings
from .importer import parse_url, ImportFailure
from .models import Analysis, Base, Session, engine
from .pipeline import markdown
from .tasks import analyze_job

@asynccontextmanager
async def lifespan(app):
    # SQLite is a local development convenience; PostgreSQL uses Alembic.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    yield

app = FastAPI(title="SENTINEL AI", version="0.1.0", lifespan=lifespan)

def authorize(authorization: str = Header(default="")):
    if not settings.api_token or not secrets.compare_digest(authorization.encode("utf-8"), ("Bearer " + settings.api_token).encode("utf-8")):
        raise HTTPException(401, "A configured API bearer token is required.")

class ImportRequest(BaseModel):
    url: str = Field(max_length=250)

class ExplainRequest(BaseModel):
    finding_id: str = Field(max_length=500)
    use_llm: bool = False

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/demo")
def demo():
    import json
    path = Path(__file__).with_name("demo.json")
    if not path.exists():
        raise HTTPException(503, "Generate the fixture report first.")
    return json.loads(path.read_text())

@app.post("/analyses", status_code=202, dependencies=[Depends(authorize)])
def create_analysis(body: ImportRequest):
    try:
        parse_url(body.url)
    except ImportFailure as error:
        raise HTTPException(422, str(error)) from None
    identifier = str(uuid4())
    with Session() as session:
        # Bounded single-owner queue; completed history is capped separately by operator retention.
        active = session.scalars(select(Analysis).where(Analysis.status.in_(["queued", "running"]))).all()
        if len(active) >= 3:
            raise HTTPException(429, "Three jobs are already active.")
        session.add(Analysis(id=identifier, repository=body.url, status="queued"))
        session.commit()
    try:
        if settings.sync_jobs:
            analyze_job(identifier)
        else:
            analyze_job.delay(identifier)
    except Exception:
        with Session() as session:
            job = session.get(Analysis, identifier)
            job.status = "failed"
            job.error = "Analysis queue unavailable."
            session.commit()
        raise HTTPException(503, "Analysis queue unavailable.") from None
    return {"id": identifier, "status": "queued"}

@app.get("/analyses", dependencies=[Depends(authorize)])
def history():
    with Session() as session:
        return [{"id": job.id, "repository": job.repository, "status": job.status, "created_at": job.created_at, "risk_score": job.report.get("risk_score") if job.report else None} for job in session.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(50))]

def get_job(identifier):
    with Session() as session:
        job = session.get(Analysis, identifier)
        if not job:
            raise HTTPException(404, "Analysis not found.")
        return job

@app.get("/analyses/{identifier}", dependencies=[Depends(authorize)])
def get_analysis(identifier: str):
    job = get_job(identifier)
    return {"id": job.id, "status": job.status, "error": job.error, "report": job.report}

@app.get("/analyses/{identifier}/report", response_class=PlainTextResponse, dependencies=[Depends(authorize)])
def export(identifier: str):
    job = get_job(identifier)
    if not job.report:
        raise HTTPException(409, "Report not ready.")
    return PlainTextResponse(markdown(job.report), media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=sentinel-report.md"})

@app.post("/analyses/{identifier}/explain", dependencies=[Depends(authorize)])
async def explanation(identifier: str, body: ExplainRequest):
    job = get_job(identifier)
    item = next((item for item in (job.report or {}).get("findings", []) if item["id"] == body.finding_id), None)
    if not item:
        raise HTTPException(404, "Finding not found.")
    try:
        return await explain(item, body.use_llm)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    except Exception:
        raise HTTPException(502, "LLM provider unavailable.") from None
