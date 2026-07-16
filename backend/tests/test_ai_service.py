import pytest
from fastapi import HTTPException

from app.services import ai_service


class FakeResponse:
    status_code = 200
    text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "reasoning": "This trace must never be graded.",
                        "content": '{"feedback": "Final answer only"}',
                    }
                }
            ],
            "usage": {"total_tokens": 12},
        }


class FakeClient:
    last_json = None

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, _url, *, headers, json):
        assert headers == {"Content-Type": "application/json"}
        self.__class__.last_json = json
        return FakeResponse()


@pytest.mark.asyncio
async def test_call_ai_uses_only_final_content(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "http://ollama.test/v1")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", FakeClient)

    result = await ai_service.call_ai(
        system_prompt="You are a concise grading assistant.",
        user_prompt="Grade this sufficiently long student submission.",
        feature="test_grading",
        db=None,
    )

    assert result == '{"feedback": "Final answer only"}'
    assert FakeClient.last_json["model"] == "test-model"


def test_extract_json_payload_fenced_with_leading_newlines():
    # The live repro shape from deepseek-r1 via Ollama
    content = '\n\n```json\n{"structure_score": 5}\n```'
    assert ai_service.extract_json_payload(content) == '{"structure_score": 5}'


def test_extract_json_payload_think_block_then_fence():
    content = '<think>\nreasoning trace\n</think>\n```json\n{"a": 1}\n```'
    assert ai_service.extract_json_payload(content) == '{"a": 1}'


def test_extract_json_payload_bare_json_passthrough():
    content = '{"a": 1, "b": [2, 3]}'
    assert ai_service.extract_json_payload(content) == content


def test_extract_json_payload_json_surrounded_by_prose():
    content = 'Here is the grading result:\n{"a": 1}\nHope that helps!'
    assert ai_service.extract_json_payload(content) == '{"a": 1}'


def test_extract_json_payload_array_surrounded_by_prose():
    content = "Result:\n[1, 2, 3]\nDone."
    assert ai_service.extract_json_payload(content) == "[1, 2, 3]"


def test_extract_json_payload_trailing_prose_after_json():
    # "Extra data" shape observed live: valid JSON followed by more text
    content = '{"a": 1} Some additional commentary from the model.'
    assert ai_service.extract_json_payload(content) == '{"a": 1}'


def test_extract_json_payload_no_json_returns_stripped_text():
    assert ai_service.extract_json_payload("  no json here  ") == "no json here"


class FencedFakeResponse(FakeResponse):
    def json(self):
        return {
            "choices": [
                {"message": {"content": '\n\n```json\n{"feedback": "ok"}\n```'}}
            ],
            "usage": {"total_tokens": 12},
        }


class FencedFakeClient(FakeClient):
    async def post(self, _url, *, headers, json):
        self.__class__.last_json = json
        return FencedFakeResponse()


@pytest.mark.asyncio
async def test_call_ai_json_mode_unwraps_fenced_content(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "http://ollama.test/v1")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", FencedFakeClient)

    result = await ai_service.call_ai(
        system_prompt="You are a concise grading assistant.",
        user_prompt="Grade this sufficiently long student submission.",
        feature="test_grading",
        db=None,
        json_mode=True,
    )

    assert result == '{"feedback": "ok"}'


@pytest.mark.asyncio
async def test_call_ai_without_json_mode_leaves_content_untouched(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "http://ollama.test/v1")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", FencedFakeClient)

    result = await ai_service.call_ai(
        system_prompt="You are a concise grading assistant.",
        user_prompt="Grade this sufficiently long student submission.",
        feature="test_grading",
        db=None,
        json_mode=False,
    )

    assert result == '\n\n```json\n{"feedback": "ok"}\n```'


@pytest.mark.asyncio
async def test_ai_config_is_validated_only_when_called(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "not-a-url")

    with pytest.raises(HTTPException, match="Invalid local AI configuration"):
        await ai_service.call_ai(
            system_prompt="You are a concise grading assistant.",
            user_prompt="Grade this sufficiently long student submission.",
            feature="test_grading",
            db=None,
        )
