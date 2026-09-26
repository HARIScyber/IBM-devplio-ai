"""Fictional task service."""


def list_tasks_for_user(tasks: list[dict], user_id: str) -> list[dict]:
    """Return tasks owned by one user."""
    return [task for task in tasks if task.get("user_id") == user_id]


def task_summary(task: dict) -> str:
    """Render one task label."""
    title = task.get("title") or "Untitled task"
    return f"{title} ({task.get('status', 'open')})"


def task_priority(task: dict) -> int:
    """Return priority, defaulting to normal priority."""
    return int(task.get("priority", 2))
