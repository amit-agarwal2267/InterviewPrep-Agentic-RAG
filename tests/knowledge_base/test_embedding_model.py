import json

import pytest

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.knowledge_base.embedder import embed_texts


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_model_returns_real_vectors() -> None:
    inputs = [
        "Python decorators extend function behavior.",
        "PostgreSQL indexes speed up selective queries.",
    ]
    vectors = await embed_texts(inputs)

    assert len(vectors) == len(inputs)
    assert all(len(vector) == 768 for vector in vectors)
    assert all(isinstance(value, float) for vector in vectors for value in vector)
    print(
        "\nActual embedding response:\n",
        json.dumps(
            {
                "model": get_settings().google_genai_embedding_model,
                "dimensions": [len(vector) for vector in vectors],
                "first_10_values": [vector[:10] for vector in vectors],
            },
            indent=2,
        ),
    )
