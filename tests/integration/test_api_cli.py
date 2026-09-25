import json
from uuid import uuid4

from typer.testing import CliRunner

from china_masters.interfaces.cli.main import app


def test_api_full_workflow(client):
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/universities", json={"canonical_name": "API Demo"})
    assert response.status_code == 201
    university = response.json()
    assert client.get(f"/universities/{university['id']}").json() == university
    faculty = []
    for name in ["One", "Two"]:
        response = client.post(
            "/professors", json={"name_en": name, "university_id": university["id"]}
        )
        assert response.status_code == 201
        faculty.append(response.json())
    assert len(client.get(f"/universities/{university['id']}/professors").json()) == 2
    assert client.post(f"/professors/{faculty[0]['id']}/workspace").status_code == 200
    source = client.post(
        "/sources", json={"url": "https://example.invalid", "source_type": "OFFICIAL_FACULTY"}
    ).json()
    response = client.post(
        "/research-facts",
        json={
            "entity_type": "PROFESSOR",
            "entity_id": faculty[0]["id"],
            "field_name": "research_summary",
            "value": "Fixture",
            "source_id": source["id"],
            "verification_status": "VERIFIED_OFFICIAL",
        },
    )
    assert response.status_code == 201
    assert response.json()["verified_at"].endswith("Z")
    response = client.post(
        "/jobs", json={"job_type": "PROFESSOR_RESEARCH", "entity_ids": [p["id"] for p in faculty]}
    )
    assert response.status_code == 201
    assert len(response.json()) == 2
    job = response.json()[0]
    assert client.get(f"/jobs/{job['id']}").json() == job
    assert client.post(f"/jobs/{job['id']}/cancel").json()["status"] == "CANCELLED"
    assert len(client.get("/jobs?status=QUEUED").json()) == 1
    assert client.get("/openapi.json").status_code == 200


def test_api_input_and_reference_errors(client):
    assert client.post("/universities", json={"canonical_name": " "}).status_code == 422
    assert (
        client.post("/universities", json={"canonical_name": "A", "secret": True}).status_code
        == 422
    )
    assert (
        client.post(
            "/universities", json={"canonical_name": "A", "official_website": "file:///a"}
        ).status_code
        == 422
    )
    assert client.get(f"/universities/{uuid4()}").status_code == 404
    assert client.get("/universities/not-a-uuid").status_code == 422
    assert client.get("/jobs?limit=501").status_code == 422
    assert (
        client.post(
            "/professors", json={"name_en": "Orphan", "university_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.post("/jobs", json={"job_type": "PROFESSOR_RESEARCH", "entity_ids": []}).status_code
        == 422
    )
    assert (
        client.post(
            "/jobs",
            json={
                "job_type": "PROFESSOR_RESEARCH",
                "entity_id": str(uuid4()),
                "entity_ids": [str(uuid4())],
            },
        ).status_code
        == 422
    )
    job = client.post("/jobs", json={"job_type": "INBOX_SYNC"}).json()[0]
    assert (
        client.post(f"/jobs/{job['id']}/transition", json={"status": "COMPLETED"}).status_code
        == 422
    )


def test_cli_uses_persistent_application_services(settings, monkeypatch):
    monkeypatch.setenv("CM_DATABASE_URL", settings.database_url)
    monkeypatch.setenv("CM_WORKSPACE_ROOT", str(settings.workspace_root))
    runner = CliRunner()
    assert runner.invoke(app, ["health"]).exit_code == 0
    result = runner.invoke(app, ["university", "create", "CLI University"])
    assert result.exit_code == 0, result.output
    university = json.loads(result.output)
    result = runner.invoke(app, ["university", "list"])
    assert json.loads(result.output)[0]["id"] == university["id"]
    result = runner.invoke(app, ["professor", "create", university["id"], "CLI Professor"])
    assert result.exit_code == 0, result.output
    professor = json.loads(result.output)
    result = runner.invoke(
        app, ["job", "create", "PROFESSOR_RESEARCH", "--entity-id", professor["id"]]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["entity_id"] == professor["id"]
    assert runner.invoke(app, ["university", "get", str(uuid4())]).exit_code == 1
