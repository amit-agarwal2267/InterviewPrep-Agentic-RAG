import hashlib
import json

from sqlalchemy import text

from interview_prep_qna.db.client.postgres import get_session
from interview_prep_qna.knowledge_base.embedder import embed_texts
from interview_prep_qna.knowledge_base.splitter import split_content
from interview_prep_qna.observability import get_langfuse_client


async def ingest_document(
    source_type: str,
    source_id: str,
    title: str,
    url: str | None,
    content: str,
    image_urls: list[str] | None = None,
) -> bool:
    with get_langfuse_client().start_as_current_observation(
        name="ingest-document",
        as_type="span",
        input={
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "content_characters": len(content),
            "image_count": len(image_urls or []),
            "content_recorded": False,
        },
        metadata={"source_type": source_type},
    ) as observation:
        try:
            changed = await _ingest_document(
                source_type=source_type,
                source_id=source_id,
                title=title,
                url=url,
                content=content,
                image_urls=image_urls,
            )
        except Exception as exc:
            observation.update(
                level="ERROR",
                status_message=f"{type(exc).__name__}: {exc}",
                output={"status": "failed"},
            )
            raise
        observation.update(output={"status": "ingested" if changed else "unchanged"})
        return changed


async def _ingest_document(
    source_type: str,
    source_id: str,
    title: str,
    url: str | None,
    content: str,
    image_urls: list[str] | None = None,
) -> bool:
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    chunk_type = "code" if source_type == "github" else "text"

    async with get_session() as session:
        existing = await session.execute(
            text(
                "SELECT content_hash FROM documents WHERE source_type = :st AND source_id = :sid"
            ),
            {"st": source_type, "sid": source_id},
        )
        if existing.scalar_one_or_none() == content_hash:
            return False

        doc_row = await session.execute(
            text("""
            INSERT INTO documents (source_type, source_id, title, url, content_hash)
            VALUES (:st, :sid, :title, :url, :hash)
            ON CONFLICT (source_type, source_id)
            DO UPDATE SET title = :title, url = :url, content_hash = :hash, updated_at = NOW()
            RETURNING id, content_hash
        """),
            {
                "st": source_type,
                "sid": source_id,
                "title": title,
                "url": url,
                "hash": content_hash,
            },
        )
        doc = doc_row.fetchone()

        await session.execute(
            text("DELETE FROM chunks WHERE document_id = :did"), {"did": doc.id}
        )

        chunks = split_content(content, chunk_type)
        if not chunks:
            await session.commit()
            return True

        vectors = await embed_texts([c["content"] for c in chunks])

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            await session.execute(
                text("""
                INSERT INTO chunks (document_id, content, embedding, chunk_index, chunk_type, embedding_input_type, metadata)
                VALUES (:did, :content, :emb, :idx, :ctype, 'text', :meta)
            """),
                {
                    "did": doc.id,
                    "content": chunk["content"],
                    "emb": str(vector),
                    "idx": idx,
                    "ctype": chunk_type,
                    "meta": json.dumps(chunk["metadata"]),
                },
            )

        await session.commit()
        return True
