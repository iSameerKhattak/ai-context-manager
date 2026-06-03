from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from contextclaw.db.engine import close_engine, init_engine
from contextclaw.integrations.github import verify_webhook_signature

from app.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_engine()
    yield
    await close_engine()


app = FastAPI(
    title="ContextClaw Webhook Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/v1")


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Receive GitHub App webhook events."""
    body = await request.body()
    sig = request.headers.get("x-hub-signature-256", "")
    event = request.headers.get("x-github-event", "")

    if not verify_webhook_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    import json
    payload = json.loads(body)

    # Route to handler based on event type
    handler = _get_handler(event)
    if handler:
        await handler(payload)

    return {"status": "ok", "event": event}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "webhook-service", "version": "0.1.0"}


@app.get("/readyz")
async def readyz():
    return {"status": "ok"}


# ── Event Handlers ──────────────────────────────────────────────────

async def _handle_push(payload: dict) -> None:
    """Handle push event — trigger reindex for the repo."""
    import asyncio
    from sqlalchemy import select
    from contextclaw.db.engine import get_session
    from contextclaw.db.models import Repository
    from contextclaw.indexer.index import index_repository
    from contextclaw.queue.rabbitmq import IndexingJobMessage, QueuePublisher
    from contextclaw.settings import settings

    repo_full_name = payload["repository"]["full_name"]
    ref = payload["ref"]
    after = payload.get("after", "")
    print(f"[webhook] push: {repo_full_name} {ref}: ..{after[:7]}")

    session_gen = get_session()
    async with session_gen as session:
        result = await session.execute(
            select(Repository).where(Repository.full_name == repo_full_name)
        )
        repo = result.scalar_one_or_none()

    if repo is None:
        print(f"[webhook] repo not found in DB: {repo_full_name}")
        return

    # Prefer RabbitMQ; fall back to direct inline index
    if settings.rabbitmq_url and settings.rabbitmq_url != "amqp://guest:guest@localhost:5672/":
        pub = QueuePublisher()
        await pub.connect()
        await pub.publish_indexing(
            IndexingJobMessage(
                repository_id=str(repo.id),
                project_id=str(repo.project_id),
                clone_url=repo.clone_url or f"https://github.com/{repo.full_name}.git",
                ref=ref,
                commit_sha=after or None,
            )
        )
        await pub.close()
        print(f"[webhook] published indexing job for {repo_full_name}")
    else:
        def _run_index():
            return index_repository(repo, commit_sha=after or None)
        loop = asyncio.get_running_loop()
        summary = await loop.run_in_executor(None, _run_index)
        print(f"[webhook] index complete for {repo_full_name}: {summary}")


async def _handle_pull_request(payload: dict) -> None:
    """Handle PR event — analyze and link to issues."""
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    print(f"[webhook] pull_request: {repo.get('full_name')} #{pr.get('number')} ({action})")
    # TODO: ingest PR → knowledge graph


async def _handle_issues(payload: dict) -> None:
    """Handle issue event — ingest as documents."""
    action = payload.get("action", "")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    print(f"[webhook] issues: {repo.get('full_name')} #{issue.get('number')} ({action})")


async def _handle_installation(payload: dict) -> None:
    """Handle installation event — add/remove repos."""
    import asyncio
    from sqlalchemy import select
    from contextclaw.db.engine import get_session
    from contextclaw.db.models import Repository
    from contextclaw.indexer.index import index_repository
    from contextclaw.queue.rabbitmq import IndexingJobMessage, QueuePublisher
    from contextclaw.settings import settings

    action = payload.get("action", "")
    installation = payload.get("installation", {})
    repos = payload.get("repositories", [])
    print(f"[webhook] installation: {action} ({len(repos)} repos)")

    if action == "created" or action == "added":
        session_gen = get_session()
        async with session_gen as session:
            for r in repos:
                result = await session.execute(
                    select(Repository).where(
                        Repository.provider == "github",
                        Repository.external_id == str(r.get("id")),
                    )
                )
                repo = result.scalar_one_or_none()
                if not repo:
                    continue

                if settings.rabbitmq_url and settings.rabbitmq_url != "amqp://guest:guest@localhost:5672/":
                    pub = QueuePublisher()
                    await pub.connect()
                    await pub.publish_indexing(
                        IndexingJobMessage(
                            repository_id=str(repo.id),
                            project_id=str(repo.project_id),
                            clone_url=repo.clone_url or f"https://github.com/{repo.full_name}.git",
                            ref=repo.default_branch,
                        )
                    )
                    await pub.close()
                else:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None, lambda r=repo: index_repository(r)
                    )
                print(f"[webhook] indexing triggered for {r.get('full_name')}")


def _get_handler(event: str):
    return {
        "push": _handle_push,
        "pull_request": _handle_pull_request,
        "issues": _handle_issues,
        "installation": _handle_installation,
        "installation_repositories": _handle_installation,
    }.get(event)
