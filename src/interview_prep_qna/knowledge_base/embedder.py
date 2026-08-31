import asyncio
from functools import lru_cache
from time import perf_counter

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_client


@lru_cache(maxsize=2)
def _get_client(task_type: str) -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.google_genai_embedding_model,
        google_api_key=settings.google_genai_api_key.get_secret_value(),
        task_type=task_type,
        output_dimensionality=768,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await _embed(texts, "RETRIEVAL_DOCUMENT")


async def embed_query(text: str) -> list[float]:
    return (await _embed([text], "RETRIEVAL_QUERY"))[0]


async def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    settings = get_settings()
    character_count = sum(len(value) for value in texts)
    estimated_tokens = max(1, round(character_count / 4)) if texts else 0
    estimated_cost = None
    if settings.google_genai_embedding_cost_per_million_tokens is not None:
        estimated_cost = (
            estimated_tokens
            * settings.google_genai_embedding_cost_per_million_tokens
            / 1_000_000
        )

    cost_details = (
        {"input": estimated_cost, "total": estimated_cost}
        if estimated_cost is not None
        else None
    )
    langfuse = get_langfuse_client()
    with langfuse.start_as_current_observation(
        name="gemini-embedding",
        as_type="embedding",
        input={
            "text_count": len(texts),
            "character_count": character_count,
            "content_recorded": False,
        },
        model=settings.google_genai_embedding_model,
        model_parameters={"task_type": task_type, "output_dimensionality": 768},
        usage_details={"input": estimated_tokens, "total": estimated_tokens},
        cost_details=cost_details,
        metadata={"usage_is_estimated": True, "cost_is_estimated": True},
    ) as observation:
        started_at = perf_counter()
        try:
            client = _get_client(task_type)
            if task_type == "RETRIEVAL_QUERY":
                vectors = [await asyncio.to_thread(client.embed_query, texts[0])]
            else:
                vectors = await asyncio.to_thread(client.embed_documents, texts)
        except Exception as exc:
            observation.update(
                level="ERROR",
                status_message=f"{type(exc).__name__}: {exc}",
                output={"status": "failed"},
            )
            raise

        observation.update(
            output={
                "vector_count": len(vectors),
                "dimensions": [len(vector) for vector in vectors],
            },
            metadata={
                "latency_ms": round((perf_counter() - started_at) * 1000, 2),
                "usage_is_estimated": True,
                "cost_is_estimated": True,
            },
        )
        return vectors
