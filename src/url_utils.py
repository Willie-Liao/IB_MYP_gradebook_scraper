"""URL parsing helpers for ManageBac gradebook links."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse


def parse_school_from_url(task_url: str) -> tuple[str, str]:
    """Extract school_code and domain from a ManageBac URL.

    Example: https://jcid.managebac.cn/teacher/... -> ("jcid", "managebac.cn")
    """
    parsed = urlparse(task_url)
    host = parsed.netloc or task_url.split("/")[2]
    school_code, domain = host.split(".", 1)
    return school_code, domain


def parse_class_term_ids(url: str) -> tuple[str, str] | None:
    """Extract class_id and term_id from a gradebook URL."""
    path = urlparse(url).path
    match = re.search(r"/classes/(\d+)/gradebook/term/(\d+)", path)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"/classes/(\d+)/gradebook/(\d+)", path)
    if match:
        return match.group(1), match.group(2)
    return None


def build_base_url(school_code: str, domain: str) -> str:
    """Build the school base URL."""
    return f"https://{school_code}.{domain}"


def build_term_grades_url(base_url: str, class_id: str, term_id: str) -> str:
    """Build the MYP term grades page URL."""
    path = f"/teacher/classes/{class_id}/gradebook/term/{term_id}/myp-term-grades"
    return urljoin(base_url, path)


def build_tasks_url(base_url: str, class_id: str, term_id: str) -> str:
    """Build the tasks gradebook page URL."""
    path = f"/teacher/classes/{class_id}/gradebook/term/{term_id}/tasks"
    return urljoin(base_url, path)


def resolve_gradebook_urls(gradebook_url: str) -> tuple[str, str, str, str, str]:
    """Resolve base URL and both page URLs from any gradebook link.

    Returns:
        (base_url, term_grades_url, tasks_url, class_label, term_label)
    """
    school_code, domain = parse_school_from_url(gradebook_url)
    base_url = build_base_url(school_code, domain)
    ids = parse_class_term_ids(gradebook_url)
    if not ids:
        raise ValueError(f"Could not parse class/term IDs from URL: {gradebook_url}")
    class_id, term_id = ids
    term_grades_url = build_term_grades_url(base_url, class_id, term_id)
    tasks_url = build_tasks_url(base_url, class_id, term_id)
    return (
        base_url,
        term_grades_url,
        tasks_url,
        f"class_{class_id}",
        f"term_{term_id}",
    )
