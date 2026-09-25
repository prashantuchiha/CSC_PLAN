import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from china_masters.application.commands.jobs import CreateJobs
from china_masters.domain.enums import JobStatus, JobType


def test_api_resume_and_worker_owned_transition(client):
    response = client.post(
        "/jobs",
        json={"job_type": "GENERAL_CSC_RESEARCH", "payload_json": {"review_required": True}},
    )
    assert response.status_code == 201
    job_id = response.json()[0]["id"]
    worker = client.app.state.container.create_worker()
    assert worker.once().status == JobStatus.WAITING_FOR_REVIEW
    response = client.post(f"/jobs/{job_id}/resume")
    assert response.status_code == 200
    assert response.json()["payload_json"]["review_approved"] is True
    assert worker.once().status == JobStatus.COMPLETED
    assert client.post(f"/jobs/{job_id}/resume").status_code == 422


def test_api_does_not_complete_worker_owned_job(client):
    response = client.post("/jobs", json={"job_type": "GENERAL_CSC_RESEARCH"})
    job_id = response.json()[0]["id"]
    execution = client.app.state.container.job_execution
    assert execution.claim_next("worker-a") is not None
    assert client.get(f"/jobs/{job_id}").json()["worker_id"] == "worker-a"
    assert (
        client.post(
            f"/jobs/{job_id}/transition", json={"status": "COMPLETED", "result_json": {}}
        ).status_code
        == 422
    )
    assert client.post(f"/jobs/{job_id}/cancel").status_code == 200
    assert client.get(f"/jobs/{job_id}").json()["status"] == "CANCELLED"


def test_upgrade_preserves_phase_one_queued_and_recovers_unleased_running(tmp_path):
    path = tmp_path / "legacy.db"
    url = f"sqlite:///{path.as_posix()}"
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, "506a9dad4b92")
    queued_id, running_id = uuid4(), uuid4()
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            for identity, status, attempts in (
                (queued_id, "QUEUED", 0),
                (running_id, "RUNNING", 1),
            ):
                connection.execute(
                    text(
                        "INSERT INTO research_jobs "
                        "(id,job_type,status,priority,payload_json,attempts,created_at,revision) "
                        "VALUES (:id,'GENERAL_CSC_RESEARCH',:status,0,:payload,:attempts,"
                        "'2026-01-01 00:00:00',0)"
                    ),
                    {
                        "id": identity.hex,
                        "status": status,
                        "payload": json.dumps({"demo": True}),
                        "attempts": attempts,
                    },
                )
    finally:
        engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT id,status,attempts,revision,worker_id,lease_expires_at "
                        "FROM research_jobs ORDER BY id"
                    )
                )
                .mappings()
                .all()
            )
            assert len(rows) == 2
            assert all(row["status"] == "QUEUED" for row in rows)
            assert {row["attempts"] for row in rows} == {0, 1}
            recovered = next(row for row in rows if row["id"] == running_id.hex)
            assert recovered["revision"] == 1
            assert recovered["worker_id"] is recovered["lease_expires_at"] is None
    finally:
        engine.dispose()


def test_phase_one_manual_transition_keeps_a_lease(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    running = container.jobs.transition(job.id, JobStatus.RUNNING)
    assert running.worker_id == "manual"
    assert running.claim_token is not None
    assert running.lease_expires_at > running.started_at
    completed = container.jobs.transition(job.id, JobStatus.COMPLETED, result={"manual": True})
    assert completed.status == JobStatus.COMPLETED
    assert completed.worker_id is completed.claim_token is completed.lease_expires_at is None


def test_database_rejects_running_without_a_lease(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    with pytest.raises(IntegrityError):
        with container.engine.begin() as connection:
            connection.execute(
                text("UPDATE research_jobs SET status='RUNNING' WHERE id=:id"),
                {"id": job.id.hex},
            )
    assert container.jobs.get(job.id).status == JobStatus.QUEUED
