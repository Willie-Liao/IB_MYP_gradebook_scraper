"""URL parsing helpers for ManageBac gradebook links."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse


def normalize_gradebook_url(url: str) -> str:
    """Strip whitespace and ensure the URL has an https:// scheme."""
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("Gradebook URL is empty")
    if cleaned.startswith("//"):
        return f"https:{cleaned}"
    if not cleaned.startswith(("http://", "https://")):
        return f"https://{cleaned}"
    return cleaned


def parse_school_from_url(task_url: str) -> tuple[str, str]:
    """Extract school_code and domain from a ManageBac URL.

    Example: https://jcid.managebac.cn/teacher/... -> ("jcid", "managebac.cn")
    """
    parsed = urlparse(normalize_gradebook_url(task_url))
    host = parsed.netloc
    if not host or "." not in host:
        raise ValueError(f"Could not parse school host from URL: {task_url}")
    school_code, domain = host.split(".", 1)
    return school_code, domain


def parse_class_term_ids(url: str) -> tuple[str, str | None] | None:
    """Extract class_id and optional term_id from a gradebook URL."""
    path = urlparse(normalize_gradebook_url(url)).path
    match = re.search(r"/classes/(\d+)/gradebook/term/(\d+)", path)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"/classes/(\d+)/gradebook/(\d+)", path)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"/classes/(\d+)/gradebook/(?:myp-term-grades|tasks)/?$", path)
    if match:
        return match.group(1), None
    return None


_TERM_ID_PATTERN = re.compile(r"/gradebook/term/(\d+)")


def extract_term_id_from_html(html: str) -> str | None:
    """Discover term_id from links embedded in a gradebook page."""
    match = _TERM_ID_PATTERN.search(html)
    return match.group(1) if match else None


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


def resolve_gradebook_urls(
    gradebook_url: str,
    term_id: str | None = None,
) -> tuple[str, str, str, str, str]:
    """Resolve base URL and both page URLs from any gradebook link.

    Returns:
        (base_url, term_grades_url, tasks_url, class_label, term_label)
    """
    normalized = normalize_gradebook_url(gradebook_url)
    school_code, domain = parse_school_from_url(normalized)
    base_url = build_base_url(school_code, domain)
    ids = parse_class_term_ids(normalized)
    if not ids:
        raise ValueError(f"Could not parse class/term IDs from URL: {gradebook_url}")
    class_id, parsed_term_id = ids
    resolved_term_id = term_id or parsed_term_id
    if not resolved_term_id:
        raise ValueError(
            f"Term ID not in URL; fetch the page and call extract_term_id_from_html: {gradebook_url}"
        )
    term_grades_url = build_term_grades_url(base_url, class_id, resolved_term_id)
    tasks_url = build_tasks_url(base_url, class_id, resolved_term_id)
    return (
        base_url,
        term_grades_url,
        tasks_url,
        f"class_{class_id}",
        f"term_{resolved_term_id}",
    )
