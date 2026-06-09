"""Tests for gradebook scraper orchestration helpers."""

from src.models import Score, Task
from src.scraper import _filter_tasks_with_scores


def test_filter_tasks_with_scores_drops_non_criterion_tasks() -> None:
    tasks = [
        Task(id="1", name="Criteria A Dancing", link="/tasks/1"),
        Task(id="2", name="Culture Trip", link="/tasks/2"),
    ]
    scores = [
        Score(student_id="s1", task_id="1", criterion="A", score=6, comment=None),
    ]

    filtered = _filter_tasks_with_scores(tasks, scores)

    assert len(filtered) == 1
    assert filtered[0].id == "1"
    assert filtered[0].name == "Criteria A Dancing"
