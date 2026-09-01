import pytest

from interview_prep_qna.core.agent.write_back import WriteBackNode


@pytest.mark.asyncio
async def test_write_back_ingests_only_consented_clarifications() -> None:
    ingested: list[dict] = []

    async def ingest(**kwargs) -> bool:
        ingested.append(kwargs)
        return True

    state = await WriteBackNode(ingestion_pipeline=ingest)(
        {
            "query": "Why did I choose Tavily?",
            "draft_response": "Generic answer that must not be persisted.",
            "route": "write_back",
            "interrogation": {
                "id": "session-1",
                "phase": "ready_to_write",
                "consent_granted": True,
                "clarifications": [
                    {
                        "question": "What requirement led to this choice?",
                        "answer": "Source URLs and a LangChain integration.",
                    }
                ],
            },
        }
    )

    assert state["route"] == "complete"
    assert state["response"] == "Information saved."
    assert state["write_back"]["source_id"] == "interrogation:session-1"
    assert ingested[0]["source_type"] == "correction"
    assert "Source URLs" in ingested[0]["content"]
    assert "Generic answer" not in ingested[0]["content"]


@pytest.mark.asyncio
async def test_write_back_rejects_missing_consent() -> None:
    async def ingest(**kwargs) -> bool:
        raise AssertionError("ingestion must not run")

    with pytest.raises(PermissionError, match="explicit consent"):
        await WriteBackNode(ingestion_pipeline=ingest)(
            {
                "query": "Why Tavily?",
                "interrogation": {
                    "id": "session-1",
                    "phase": "ready_to_write",
                    "consent_granted": False,
                    "clarifications": [{"question": "Why?", "answer": "Citations"}],
                },
            }
        )


@pytest.mark.asyncio
async def test_write_back_reports_unchanged_document() -> None:
    async def ingest(**kwargs) -> bool:
        return False

    state = await WriteBackNode(ingestion_pipeline=ingest)(
        {
            "query": "Why Tavily?",
            "interrogation": {
                "id": "session-1",
                "phase": "ready_to_write",
                "consent_granted": True,
                "clarifications": [{"question": "Why?", "answer": "Citations"}],
            },
        }
    )

    assert state["response"] == "Information was already up to date."
    assert state["write_back"]["changed"] is False
