"""Tests for ManageBac gradebook URL parsing."""

from src.url_utils import (
    extract_term_id_from_html,
    normalize_gradebook_url,
    parse_class_term_ids,
    resolve_gradebook_urls,
)


def test_normalize_gradebook_url_adds_scheme() -> None:
    assert normalize_gradebook_url(
        "jcid.managebac.cn/teacher/classes/1/gradebook/term/2/tasks"
    ).startswith("https://")


def test_parse_class_term_ids_with_term_segment() -> None:
    url = "https://jcid.managebac.cn/teacher/classes/11423947/gradebook/term/106884/tasks"
    assert parse_class_term_ids(url) == ("11423947", "106884")


def test_parse_class_term_ids_without_term_segment() -> None:
    url = "https://jcid.managebac.cn/teacher/classes/11423947/gradebook/myp-term-grades"
    assert parse_class_term_ids(url) == ("11423947", None)


def test_extract_term_id_from_html() -> None:
    html = """
    <a href="/teacher/classes/11423947/gradebook/term/106884/tasks">Tasks</a>
    """
    assert extract_term_id_from_html(html) == "106884"


def test_resolve_gradebook_urls_with_explicit_term_id() -> None:
    url = "https://jcid.managebac.cn/teacher/classes/11423947/gradebook/myp-term-grades"
    _, term_url, tasks_url, class_name, term_name = resolve_gradebook_urls(
        url, term_id="106884"
    )
    assert "term/106884/myp-term-grades" in term_url
    assert "term/106884/tasks" in tasks_url
    assert class_name == "class_11423947"
    assert term_name == "term_106884"
