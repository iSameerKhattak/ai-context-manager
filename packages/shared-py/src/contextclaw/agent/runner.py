from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from contextclaw.agent.tools import Tool, get_tools
from contextclaw.llm import router as llm_router
from contextclaw.models import AgentEventKind, AgentType


async def run_agent(
    session_id: UUID,
    project_id: str,
    agent_type: str,
    input_data: dict[str, Any],
    on_event: Any = None,
) -> dict[str, Any]:
    """Run an agent and return its output.

    *on_event* is an optional async callable ``on_event(session_id, kind, payload)``
    used to persist events as they happen.
    """
    from contextclaw.db.engine import get_session
    from contextclaw.db.models import AgentSession, AgentEvent as DBAgentEvent

    session_gen = get_session()

    async def _emit(kind: str, payload: dict[str, Any]) -> None:
        if on_event:
            await on_event(session_id, kind, payload)

    await _emit("step", {"message": f"Starting {agent_type} agent..."})

    try:
        if agent_type == AgentType.REPO.value:
            output = await _run_repo_agent(project_id, input_data, _emit)
        elif agent_type == AgentType.DOC.value:
            output = await _run_doc_agent(project_id, input_data, _emit)
        elif agent_type == AgentType.MEMORY.value:
            output = await _run_memory_agent(project_id, input_data, _emit)
        elif agent_type == AgentType.ARCHITECTURE.value:
            output = await _run_architecture_agent(project_id, input_data, _emit)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        await _emit("step", {"message": "Agent completed successfully", "output": output})
        return {"status": "completed", "output": output}

    except Exception as exc:
        await _emit("error", {"message": str(exc)})
        return {"status": "failed", "error": str(exc)}


# ── Repo Explorer Agent ────────────────────────────────────────────


async def _run_repo_agent(
    project_id: str,
    input_data: dict[str, Any],
    emit: Any,
) -> dict[str, Any]:
    """Analyze a repository's structure and provide a summary."""
    await emit("step", {"message": "Analyzing repository structure..."})

    tools = get_tools()
    repo_path = input_data.get("repo_path", "")

    # List top-level files
    files_result = await tools["list_files"].run(repo_path=repo_path, path=".")
    await emit("tool_call", {"tool": "list_files", "result": files_result})

    # Search for key architectural patterns
    search_queries = [
        "entry point main server app",
        "configuration settings environment",
        "database models schema",
        "API routes endpoints handlers",
    ]

    findings: list[dict[str, Any]] = []
    for query in search_queries:
        await emit("step", {"message": f"Searching: {query}"})
        results = await tools["search"].run(query=query, project_id=project_id, k=5)
        if results:
            findings.append({"query": query, "results": results})

    # Generate summary via LLM
    context_parts = [
        f"Top-level files: {json.dumps(files_result[:20], indent=2)}"
    ]
    for f in findings:
        context_parts.append(f"Search findings for '{f['query']}':")
        for r in f["results"][:3]:
            context_parts.append(f"  - {r['path']}: {r['snippet'][:200]}")

    summary_prompt = (
        "You are a codebase analyst. Summarize the structure of this repository "
        "based on the file listing and search results below. "
        "Identify the main components, architecture patterns, and technologies used."
    )

    result = llm_router.rag_complete(
        system_prompt=summary_prompt,
        context_chunks=[{"snippet": p} for p in context_parts],
        user_query="Summarize this repository's architecture.",
    )

    return {
        "summary": result or "No summary generated.",
        "files_found": len(files_result) if isinstance(files_result, list) else 0,
        "patterns": [f["query"] for f in findings],
    }


# ── Documenter Agent ───────────────────────────────────────────────


async def _run_doc_agent(
    project_id: str,
    input_data: dict[str, Any],
    emit: Any,
) -> dict[str, Any]:
    """Generate documentation for a specific area of the codebase."""
    topic = input_data.get("topic", "the codebase")
    await emit("step", {"message": f"Researching: {topic}"})

    tools = get_tools()

    queries = [
        topic,
        f"{topic} implementation",
        f"{topic} usage example",
    ]

    evidence: list[dict[str, Any]] = []
    for query in queries:
        await emit("step", {"message": f"Searching for '{query}'..."})
        results = await tools["search"].run(query=query, project_id=project_id, k=5)
        evidence.extend(results)

    await emit("step", {"message": "Generating documentation..."})

    context_parts = []
    for r in evidence[:10]:
        context_parts.append(f"File: {r['path']}")
        context_parts.append(f"```\n{r['snippet']}\n```")

    doc_prompt = (
        "You are a technical writer. Based on the code snippets below, "
        "write clear documentation about the topic the user asked about. "
        "Include code examples, explain key concepts, and note any important patterns."
    )

    result = llm_router.rag_complete(
        system_prompt=doc_prompt,
        context_chunks=[{"snippet": p} for p in context_parts],
        user_query=f"Write documentation about: {topic}",
    )

    await emit("tool_call", {
        "tool": "memory_write",
        "note": "Storing documentation reference in project memory",
    })

    return {
        "documentation": result or "No documentation generated.",
        "sources_consulted": list(set(r["path"] for r in evidence)),
    }


# ── Memory Extraction Agent ────────────────────────────────────────


async def _run_memory_agent(
    project_id: str,
    input_data: dict[str, Any],
    emit: Any,
) -> dict[str, Any]:
    """Extract and store memory facts from the codebase."""
    await emit("step", {"message": "Scanning codebase for knowledge..."})

    tools = get_tools()

    existing = await tools["memory_read"].run(project_id=project_id)
    await emit("tool_call", {
        "tool": "memory_read",
        "existing_facts_count": len(existing),
    })

    search_queries = [
        "architecture decision pattern design",
        "configuration environment variable setup",
        "API endpoint route handler",
        "database model schema migration",
    ]

    facts_found: list[str] = []
    for query in search_queries:
        await emit("step", {"message": f"Analyzing: {query}"})
        results = await tools["search"].run(query=query, project_id=project_id, k=5)

        if not results:
            continue

        context = "\n".join(f"- {r['path']}: {r['snippet'][:200]}" for r in results[:3])

        extract_prompt = (
            "Extract up to 3 concise, factual statements from the code context below. "
            "Each statement should be a single sentence describing a concrete fact "
            "about the codebase (architecture decisions, tech stack, patterns, etc.). "
            "Return only the facts as a numbered list, nothing else."
        )

        extraction = llm_router.rag_complete(
            system_prompt=extract_prompt,
            context_chunks=[{"snippet": context}],
            user_query=f"Extract facts about: {query}",
        )

        if extraction:
            for line in extraction.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    fact = line.split(". ", 1)[-1] if ". " in line else line
                    fact = fact.lstrip("- ")
                    if fact and len(fact) > 20:
                        facts_found.append(fact)

    # Store extracted facts
    stored_facts = []
    for fact in facts_found[:10]:
        await emit("tool_call", {"tool": "memory_write", "fact": fact})
        result = await tools["memory_write"].run(
            project_id=project_id,
            statement=fact,
            scope="project",
            confidence=0.7,
        )
        stored_facts.append(result)

    return {
        "facts_extracted": len(facts_found),
        "facts_stored": len(stored_facts),
        "new_facts": facts_found[:10],
        "existing_facts_count": len(existing),
    }


# ── Architecture Agent ─────────────────────────────────────────────


async def _run_architecture_agent(
    project_id: str,
    input_data: dict[str, Any],
    emit: Any,
) -> dict[str, Any]:
    """Analyze the overall architecture of a project."""
    await emit("step", {"message": "Analyzing project architecture..."})

    tools = get_tools()

    searches = [
        ("service boundaries", "service module class interface"),
        ("data flow", "pipeline handler processor worker"),
        ("dependencies", "import require dependency library"),
        ("deployment", "docker compose deploy config"),
    ]

    components: list[dict[str, Any]] = []
    for label, query in searches:
        await emit("step", {"message": f"Analyzing {label}..."})
        results = await tools["search"].run(query=query, project_id=project_id, k=5)
        if results:
            components.append({
                "area": label,
                "files": [r["path"] for r in results[:5]],
                "snippets": [r["snippet"][:200] for r in results[:3]],
            })

    await emit("step", {"message": "Synthesizing architecture overview..."})

    context_parts = []
    for comp in components:
        context_parts.append(f"\n### {comp['area']}")
        for path in comp["files"]:
            context_parts.append(f"- {path}")

    arch_prompt = (
        "You are a software architect. Based on the code structure below, "
        "describe the overall architecture of this project. Include: "
        "1) Main components and services, 2) How they communicate, "
        "3) Tech stack, 4) Key architectural decisions."
    )

    result = llm_router.rag_complete(
        system_prompt=arch_prompt,
        context_chunks=[{"snippet": p} for p in context_parts],
        user_query="Describe the architecture of this project.",
    )

    return {
        "architecture": result or "No analysis generated.",
        "components_identified": len(components),
        "areas_analyzed": [c["area"] for c in components],
    }
