from notion_client import AsyncClient

from interview_prep_qna.core.config import get_settings


def _property_text(prop: dict) -> str:
    prop_type = prop.get("type")
    value = prop.get(prop_type)
    if prop_type in {"title", "rich_text"}:
        return "".join(item.get("plain_text", "") for item in value or [])
    if prop_type in {"select", "status"}:
        return (value or {}).get("name", "")
    if prop_type == "multi_select":
        return ", ".join(item.get("name", "") for item in value or [])
    if prop_type == "people":
        return ", ".join(
            person.get("name") or person.get("person", {}).get("email", "")
            for person in value or []
        )
    if prop_type == "date" and value:
        end = f" to {value['end']}" if value.get("end") else ""
        return f"{value.get('start', '')}{end}"
    if prop_type in {"number", "checkbox", "url", "email", "phone_number"}:
        return "" if value is None else str(value)
    if prop_type in {"formula", "rollup"} and isinstance(value, dict):
        nested_type = value.get("type")
        nested_value = value.get(nested_type)
        if nested_type == "array":
            return ", ".join(
                text for item in nested_value or [] if (text := _property_text(item))
            )
        return "" if nested_value is None else str(nested_value)
    return ""


async def fetch_page_content(page_id: str) -> tuple[str, str, list[str]]:
    notion = AsyncClient(auth=get_settings().notion_token.get_secret_value())
    page = await notion.pages.retrieve(page_id)
    title = page_id
    property_parts = []
    for name, prop in page.get("properties", {}).items():
        value = _property_text(prop)
        if prop.get("type") == "title" and prop.get("title"):
            title = prop["title"][0].get("plain_text", page_id)
        elif value:
            property_parts.append(f"{name}: {value}")

    text_parts, image_urls = property_parts, []
    cursor = None
    while True:
        blocks = await notion.blocks.children.list(
            block_id=page_id, start_cursor=cursor
        )
        for block in blocks["results"]:
            btype = block["type"]
            block_data = block.get(btype, {})
            if rich_text := block_data.get("rich_text"):
                text_parts.append("".join(r.get("plain_text", "") for r in rich_text))
            elif btype == "image":
                source = block_data.get("file", block_data.get("external", {}))
                if url := source.get("url"):
                    image_urls.append(url)
        if not blocks.get("has_more"):
            break
        cursor = blocks.get("next_cursor")

    return title, "\n".join(text_parts), image_urls
