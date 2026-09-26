from backend.tasks import list_tasks_for_user, task_priority, task_summary


def test_list_tasks_only_returns_owner_tasks():
    rows = [{"user_id": "u1", "title": "One"}, {"user_id": "u2", "title": "Two"}]
    assert list_tasks_for_user(rows, "u1") == [rows[0]]


def test_summary_has_safe_fallback_title():
    assert task_summary({}) == "Untitled task (open)"


def test_priority_defaults_to_normal():
    assert task_priority({}) == 2
