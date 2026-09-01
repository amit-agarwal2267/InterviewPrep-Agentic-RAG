import asyncio

from google.oauth2 import service_account
from googleapiclient.discovery import build

from interview_prep_qna.core.config import get_settings


def _get_service():
    settings = get_settings()
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


def _range_for_gid(service, spreadsheet_id: str, sheet_gid: int) -> str:
    metadata = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
        .execute()
    )
    for sheet in metadata.get("sheets", []):
        properties = sheet["properties"]
        if properties.get("sheetId") == sheet_gid:
            escaped_title = properties["title"].replace("'", "''")
            return f"'{escaped_title}'!A1:Z1000"
    raise ValueError(f"Spreadsheet has no tab with gid {sheet_gid}")


def _fetch_all_rows(
    spreadsheet_id: str, range_: str | None, sheet_gid: int | None
) -> list[dict[str, str]]:
    """Full resync — used at startup or manually, not per-edit."""
    service = _get_service()
    if sheet_gid is not None:
        range_ = _range_for_gid(service, spreadsheet_id, sheet_gid)
    if range_ is None:
        range_ = "Sheet1!A1:Z1000"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []
    headers, rows = values[0], values[1:]
    return [dict(zip(headers, row)) for row in rows]


async def fetch_all_rows(
    spreadsheet_id: str,
    range_: str | None = "Sheet1!A1:Z1000",
    sheet_gid: int | None = None,
) -> list[dict[str, str]]:
    """Fetch all sheet rows without blocking the async event loop."""
    return await asyncio.to_thread(_fetch_all_rows, spreadsheet_id, range_, sheet_gid)
