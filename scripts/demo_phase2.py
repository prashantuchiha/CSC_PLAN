"""Exercise Phase 2 with a disposable SQLite database and the real worker CLI."""

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from alembic import command
from alembic.config import Config

from china_masters.application.commands.jobs import CreateJobs
from china_masters.bootstrap import Container
from china_masters.domain.entities import Professor, ResearchJob, University
from china_masters.domain.enums import JobType
from china_masters.infrastructure.configuration.settings import Settings


def public_record(item: Professor | ResearchJob | University) -> dict[str, object]:
    values = asdict(item)
    values.pop("claim_token", None)
    return values


def run_worker_cli(*args: str, env: dict[str, str]) -> object:
    executable = Path(sys.executable).with_name(
        "china-masters.exe" if sys.platform == "win32" else "china-masters"
    )
    command_line = (
        [str(executable), "worker", *args]
        if executable.exists()
        else [sys.executable, "-m", "china_masters.interfaces.cli.main", "worker", *args]
    )
    result = subprocess.run(command_line, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Worker CLI failed: {result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="china-masters-phase2-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'demo.db').as_posix()}"
        env = os.environ.copy()
        env.update({"CM_DATABASE_URL": database_url, "CM_JOB_LEASE_SECONDS": "2"})
        configuration = Config(str(project / "alembic.ini"))
        configuration.attributes["database_url"] = database_url
        command.upgrade(configuration, "head")
        container = Container(
            Settings(database_url=database_url, job_lease_seconds=2, _env_file=None)
        )
        try:
            university = container.universities.create(
                University(canonical_name="Phase 2 Demo University (synthetic)")
            )
            professor = container.professors.create(
                Professor(university_id=university.id, name_en="Phase 2 Demo Professor")
            )
            (research,) = container.jobs.create(
                CreateJobs(job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(professor.id,))
            )
            queued = container.jobs.get(research.id)
            run_worker_cli("once", env=env)
            completed = container.jobs.get(research.id)

            (retry_job,) = container.jobs.create(
                CreateJobs(
                    job_type=JobType.PROFESSOR_RESEARCH,
                    entity_ids=(professor.id,),
                    payload={"fail_until_attempt": 1},
                )
            )
            run_worker_cli("once", env=env)
            retry_scheduled = container.jobs.get(retry_job.id)
            time.sleep(1.2)
            run_worker_cli("once", env=env)
            retry_completed = container.jobs.get(retry_job.id)

            (review_job,) = container.jobs.create(
                CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH, payload={"review_required": True})
            )
            run_worker_cli("once", env=env)
            waiting = container.jobs.get(review_job.id)
            resumed = container.jobs.resume(review_job.id)
            run_worker_cli("once", env=env)
            review_completed = container.jobs.get(review_job.id)

            (abandoned,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
            claim = container.job_execution.claim_next("simulated-crashed-worker")
            assert claim is not None and claim.job.id == abandoned.id
            time.sleep(2.2)
            run_worker_cli("recover", env=env)
            recovered = container.jobs.get(abandoned.id)
            time.sleep(1.2)
            run_worker_cli("once", env=env)
            recovered_completed = container.jobs.get(abandoned.id)

            print(
                json.dumps(
                    {
                        "university": public_record(university),
                        "professor": public_record(professor),
                        "research_queued": public_record(queued),
                        "research_completed": public_record(completed),
                        "retry_scheduled": public_record(retry_scheduled),
                        "retry_completed": public_record(retry_completed),
                        "waiting_for_review": public_record(waiting),
                        "resumed": public_record(resumed),
                        "review_completed": public_record(review_completed),
                        "abandoned_claim": public_record(claim.job),
                        "lease_recovered": public_record(recovered),
                        "recovered_completed": public_record(recovered_completed),
                    },
                    default=str,
                    indent=2,
                )
            )
        finally:
            container.close()


if __name__ == "__main__":
    main()
