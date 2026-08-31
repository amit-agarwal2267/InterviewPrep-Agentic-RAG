from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from interview_prep_qna.observability import get_langfuse_client

prose_splitter = RecursiveCharacterTextSplitter(chunk_size=768, chunk_overlap=100)

code_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
)


def split_content(content: str, chunk_type: str) -> list[dict]:
    with get_langfuse_client().start_as_current_observation(
        name="chunk-content",
        as_type="span",
        input={"content_characters": len(content), "chunk_type": chunk_type},
    ) as observation:
        try:
            if chunk_type == "code":
                docs = code_splitter.split_text(content)
                result = [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in docs
                ]
            else:
                chunks = prose_splitter.split_text(content)
                result = [{"content": chunk, "metadata": {}} for chunk in chunks]
        except Exception as exc:
            observation.update(
                level="ERROR", status_message=f"{type(exc).__name__}: {exc}"
            )
            raise

        sizes = [len(chunk["content"]) for chunk in result]
        observation.update(
            output={"chunk_count": len(result)},
            metadata={
                "empty_chunks": sum(not chunk["content"].strip() for chunk in result),
                "minimum_chunk_characters": min(sizes, default=0),
                "maximum_chunk_characters": max(sizes, default=0),
                "average_chunk_characters": (
                    round(sum(sizes) / len(sizes), 2) if sizes else 0
                ),
                "configured_chunk_size": 768 if chunk_type != "code" else None,
                "configured_chunk_overlap": 100 if chunk_type != "code" else None,
            },
        )
        return result
