from fastapi.testclient import TestClient
from sentinel.main import app
from sentinel.models import Analysis, Session, Base, engine
HEADERS={"Authorization":"Bearer test-only-token"}

def test_auth_and_validation():
    with TestClient(app) as client:
        assert client.get("/health").status_code==200
        assert client.get("/analyses").status_code==401
        assert client.post("/analyses",headers=HEADERS,json={"url":"https://localhost/internal"}).status_code==422
        assert client.get("/analyses/missing",headers=HEADERS).status_code==404

def test_job_lifecycle_and_export(monkeypatch):
    import sentinel.tasks as tasks
    fake={"repository":{"name":"acme/repo","commit":"a"*40},"risk_score":0,"coverage_complete":False,"coverage":[],"findings":[],"test_execution":"disabled"}
    monkeypatch.setattr(tasks,"analyze_public",lambda _:fake)
    with TestClient(app) as client:
        response=client.post("/analyses",headers=HEADERS,json={"url":"https://github.com/acme/repo"})
        assert response.status_code==202
        identifier=response.json()["id"]
        job=client.get("/analyses/"+identifier,headers=HEADERS).json()
        assert job["status"]=="completed"
        export=client.get(f"/analyses/{identifier}/report",headers=HEADERS)
        assert "Coverage complete: False" in export.text
        assert client.get("/analyses",headers=HEADERS).json()[0]["id"]==identifier

def test_job_errors_are_sanitized(monkeypatch):
    import sentinel.tasks as tasks
    def fail(_):
        raise RuntimeError("secret-private-value")
    monkeypatch.setattr(tasks,"analyze_public",fail)
    with TestClient(app) as client:
        identifier=client.post("/analyses",headers=HEADERS,json={"url":"https://github.com/acme/repo"}).json()["id"]
        job=client.get("/analyses/"+identifier,headers=HEADERS).json()
        assert job["status"]=="failed"
        assert "secret-private-value" not in str(job)

def test_assistant_without_key():
    import asyncio
    from sentinel.assistant import explain
    item={"title":"Dynamic eval","remediation":"Avoid eval"}
    result=asyncio.run(explain(item))
    assert result["mode"]=="deterministic" and result["verified"] is False
