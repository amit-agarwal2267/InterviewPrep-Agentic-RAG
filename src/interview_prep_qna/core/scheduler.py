from apscheduler.schedulers.asyncio import AsyncIOScheduler

from interview_prep_qna.knowledge_base.loaders.notion_poller import poll_notion_changes


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        poll_notion_changes,
        "interval",
        minutes=30,
        id="poll-notion",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    return scheduler
