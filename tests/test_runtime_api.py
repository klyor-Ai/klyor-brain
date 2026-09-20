from fastapi.testclient import TestClient

import brain.engine as engine_module
from brain.engine import KlyorBrain
from runtime.api import app


client = TestClient(app)


def test_health_and_status_endpoints_exist():
    health = client.get("/api/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["ok"] is True

    status = client.get("/api/status")
    assert status.status_code == 200
    assert "status" in status.json()

    stats = client.get("/api/stats")
    assert stats.status_code == 200
    assert stats.json()["training_examples"] > 0


def test_chat_and_evolution_endpoints_are_live():
    chat = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "1 + 1"}]},
    )
    assert chat.status_code == 200
    assert chat.json()["message"] == "2"

    evolution = client.get("/api/evolution")
    assert evolution.status_code == 200
    payload = evolution.json()
    assert "generation" in payload
    assert "population" in payload
    assert "history" in payload

    run = client.post("/api/evolution/run")
    assert run.status_code == 200
    assert "generation" in run.json()


def test_general_knowledge_questions_are_answered():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "what is photosynthesis"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "photosynthesis" in payload["message"].lower()


def test_short_natural_questions_and_feelings_are_understood():
    for prompt, capability, expected in (
        ("10 times 10", "mathematics", "100"),
        ("10x10", "mathematics", "100"),
        ("what is lol", "language", "internet shorthand"),
        ("what is empathy", "relationships", "understand or share"),
        ("I'm stressed", "conversation", "small and concrete"),
    ):
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": prompt}]},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["capability"] == capability
        assert expected in payload["message"].lower()
        assert payload["status"] == "ready"


def test_duckduckgo_results_are_temporary(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "RelatedTopics": [
                    {
                        "Name": "Science",
                        "Topics": [
                            {
                                "Text": (
                                    "Orbital mechanics studies the motion "
                                    "of objects in space."
                                )
                            }
                        ],
                    }
                ]
            }

    calls = []

    def fake_get(url, params, timeout):
        calls.append(params["q"])
        return FakeResponse()

    monkeypatch.setattr(engine_module.httpx, "get", fake_get)

    brain = KlyorBrain()

    first = brain.answer("what is orbital mechanics")
    second = brain.answer("what is orbital mechanics")

    assert first.capability == "web"
    assert first.response == (
        "Orbital mechanics studies the motion of objects in space."
    )

    # Web results are temporary evidence and must not automatically
    # become permanent training data.
    assert second.capability == "web"
    assert second.response == first.response

    # Both requests reached the temporary web fallback because the
    # result was deliberately not promoted into local knowledge.
    assert len(calls) == 2

def test_builder_mode_builds_modifies_and_previews_same_project():
    client.post("/api/project/reset")
    build = client.post(
        "/api/chat",
        json={
            "mode": "builder",
            "messages": [{"role": "user", "content": "Build me a modern developer portfolio called Trevon"}],
        },
    )
    assert build.status_code == 200
    assert build.json()["capability"] == "web-builder"
    assert set(build.json()["project"]["files"]) == {"index.html", "styles.css", "script.js"}

    before = client.get("/api/project/file?path=styles.css").json()["content"]
    modify = client.post(
        "/api/chat",
        json={
            "mode": "builder",
            "messages": [{"role": "user", "content": "Make the hero section significantly better."}],
        },
    )
    assert modify.status_code == 200
    assert modify.json()["capability"] == "project-modification"
    after = client.get("/api/project/file?path=styles.css").json()["content"]
    assert after != before
    assert client.get("/api/project/validation").json()["valid"] is True
    assert client.get("/preview/").status_code == 200


def test_learning_rejects_low_confidence_and_failure_answers():
    from brain.learning import LearningCandidate, is_valid_candidate

    assert not is_valid_candidate(
        LearningCandidate(
            instruction="unknown",
            response="This is a perfectly reasonable answer.",
            source="web",
            confidence=0.50,
        )
    )

    assert not is_valid_candidate(
        LearningCandidate(
            instruction="unknown",
            response="I couldn't retrieve web results for that request.",
            source="web",
            confidence=0.99,
        )
    )

    assert is_valid_candidate(
        LearningCandidate(
            instruction="what is a nebula",
            response=(
                "A nebula is a large cloud of gas and dust in space. "
                "Some nebulae are regions where new stars form."
            ),
            source="web",
            confidence=0.95,
        )
    )
