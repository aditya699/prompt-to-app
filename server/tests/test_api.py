"""End to end through the HTTP API with the fake builder: prompt -> build -> deploy -> URL."""

from __future__ import annotations

import asyncio

import httpx

from app.container import Container
from tests.conftest import parse_sse

PROMPT = "Create a web app that will help me track my workout."


async def create(client: httpx.AsyncClient, prompt: str = PROMPT) -> dict:
    response = await client.post("/api/projects", json={"prompt": prompt})
    assert response.status_code == 202, response.text
    return response.json()


async def test_health(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/health")).json()
    assert body == {
        "status": "ok",
        "builder": "fake",
        "model": None,
        "deployer": "static",
        "sandbox": False,
        "max_concurrent_builds": 1,
    }
    examples = (await client.get("/api/examples")).json()
    assert examples and {"label", "prompt"} <= examples[0].keys()


async def test_prompt_becomes_a_live_app(client: httpx.AsyncClient, container: Container) -> None:
    project = await create(client)
    assert project["name"] == "Track My Workout"
    assert project["slug"].startswith("track-my-workout-")
    assert project["latest_build"]["status"] in ("queued", "building")

    await container.runner.wait_idle()

    project = (await client.get(f"/api/projects/{project['id']}")).json()
    assert project["status"] == "live"
    assert project["url"] == f"http://test/apps/{project['slug']}/"
    assert project["latest_build"]["status"] == "live"
    assert project["latest_build"]["cost_usd"] == 0.0

    page = await client.get(f"/apps/{project['slug']}/")
    assert page.status_code == 200
    assert "Track My Workout" in page.text and "track my workout" in page.text


async def test_build_log_replays_after_the_build(
    client: httpx.AsyncClient, container: Container
) -> None:
    project = await create(client)
    await container.runner.wait_idle()
    build_id = project["latest_build"]["id"]

    response = await client.get(f"/api/builds/{build_id}/events")
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert events[0]["type"] == "status"
    assert any(e["type"] == "tool" and e["text"] == "Write dist/index.html" for e in events)
    assert events[-1]["type"] == "done"
    assert events[-1]["data"]["status"] == "live"
    assert events[-1]["data"]["url"].endswith(f"/apps/{project['slug']}/")

    tail = parse_sse((await client.get(f"/api/builds/{build_id}/events?after=3")).text)
    assert tail[0]["seq"] == 4


async def test_build_log_streams_live(client: httpx.AsyncClient, container: Container) -> None:
    container.builder.step_delay = 0.02  # type: ignore[attr-defined]
    project = await create(client)
    response = await client.get(f"/api/builds/{project['latest_build']['id']}/events")
    events = parse_sse(response.text)
    assert events[-1]["type"] == "done" and events[-1]["data"]["status"] == "live"
    assert len(events) >= 6


async def test_follow_up_resumes_the_session(
    client: httpx.AsyncClient, container: Container
) -> None:
    project = await create(client)
    await container.runner.wait_idle()
    first = (await client.get(f"/api/projects/{project['id']}")).json()["latest_build"]

    response = await client.post(
        f"/api/projects/{project['id']}/builds", json={"prompt": "Add a weekly chart"}
    )
    assert response.status_code == 202
    assert response.json()["number"] == 2
    await container.runner.wait_idle()

    detail = (await client.get(f"/api/projects/{project['id']}")).json()
    assert [b["status"] for b in detail["builds"]] == ["live", "live"]
    page = (await client.get(f"/apps/{project['slug']}/")).text
    assert "Add a weekly chart" in page
    assert first["id"] != detail["latest_build"]["id"]


async def test_failed_first_build(client: httpx.AsyncClient, container: Container) -> None:
    project = await create(client, "An app that should please fail to build")
    await container.runner.wait_idle()
    detail = (await client.get(f"/api/projects/{project['id']}")).json()
    assert detail["status"] == "failed" and detail["url"] is None
    assert detail["latest_build"]["error"] == "Fake failure for tests."
    events = parse_sse(
        (await client.get(f"/api/builds/{detail['latest_build']['id']}/events")).text
    )
    assert events[-2]["type"] == "error"
    assert events[-1]["data"]["status"] == "failed"


async def test_failed_follow_up_keeps_the_app_online(
    client: httpx.AsyncClient, container: Container
) -> None:
    project = await create(client)
    await container.runner.wait_idle()
    await client.post(f"/api/projects/{project['id']}/builds", json={"prompt": "please fail now"})
    await container.runner.wait_idle()
    detail = (await client.get(f"/api/projects/{project['id']}")).json()
    assert detail["status"] == "live"
    assert [b["status"] for b in detail["builds"]] == ["live", "failed"]
    assert (await client.get(f"/apps/{project['slug']}/")).status_code == 200


async def test_one_build_at_a_time_per_project(
    client: httpx.AsyncClient, container: Container
) -> None:
    container.builder.step_delay = 0.05  # type: ignore[attr-defined]
    project = await create(client)
    second = await client.post(f"/api/projects/{project['id']}/builds", json={"prompt": "More"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"
    await container.runner.wait_idle()


async def test_cancel_a_running_build(client: httpx.AsyncClient, container: Container) -> None:
    container.builder.step_delay = 0.2  # type: ignore[attr-defined]
    project = await create(client)
    build_id = project["latest_build"]["id"]
    for _ in range(50):
        if container.runner.is_running(build_id):
            break
        await asyncio.sleep(0.01)

    response = await client.post(f"/api/builds/{build_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    again = await client.post(f"/api/builds/{build_id}/cancel")
    assert again.status_code == 409


async def test_delete_takes_the_app_offline(
    client: httpx.AsyncClient, container: Container
) -> None:
    project = await create(client)
    await container.runner.wait_idle()
    assert (await client.delete(f"/api/projects/{project['id']}")).status_code == 204
    assert (await client.get(f"/api/projects/{project['id']}")).status_code == 404
    assert (await client.get(f"/apps/{project['slug']}/")).status_code == 404
    assert not (container.settings.workspaces_dir / project["slug"]).exists()


async def test_validation_and_lookups(client: httpx.AsyncClient, container: Container) -> None:
    assert (await client.post("/api/projects", json={"prompt": "hi"})).status_code == 422
    assert (await client.get("/api/projects/999")).status_code == 404
    assert (await client.get("/api/builds/999/events")).status_code == 404

    project = await create(client)
    await container.runner.wait_idle()
    by_slug = (await client.get(f"/api/projects/by-slug/{project['slug']}")).json()
    assert by_slug["id"] == project["id"]
    listed = (await client.get("/api/projects")).json()
    assert [p["id"] for p in listed] == [project["id"]]


async def test_tls_check_only_allows_real_apps(
    client: httpx.AsyncClient, container: Container
) -> None:
    project = await create(client)
    known = await client.get(f"/api/tls-check?domain={project['slug']}.apps.example.com")
    assert known.status_code == 200
    unknown = await client.get("/api/tls-check?domain=nope-1234.apps.example.com")
    assert unknown.status_code == 404
    await container.runner.wait_idle()
