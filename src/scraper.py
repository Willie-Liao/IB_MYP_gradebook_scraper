"""Main orchestrator module for ManageBac Gradebook Scraper."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from tqdm import tqdm

from .auth import Authenticator, SessionManager
from .exceptions import AuthenticationError, ScraperError
from .extractors import ScoreExtractor, StudentExtractor, TaskExtractor, TermGradeExtractor
from .models import GradebookData, Score, Student, Task, TermGrade
from .url_utils import parse_school_from_url, resolve_gradebook_urls

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    return " ".join(name.upper().split())


def _filter_tasks_with_scores(tasks: list[Task], scores: list[Score]) -> list[Task]:
    """Keep only tasks that produced criterion-based scores."""
    scored_task_ids = {score.task_id for score in scores}
    return [task for task in tasks if task.id in scored_task_ids]


class GradebookScraper:
    """Orchestrates authentication and two-page gradebook extraction."""

    def __init__(
        self,
        school_code: str,
        email: str,
        password: str,
        domain: str = "managebac.cn",
    ):
        self.school_code = school_code
        self.email = email
        self.password = password
        self.domain = domain
        self.base_url = f"https://{school_code}.{domain}"
        self._authenticator: Authenticator | None = None
        self._session_manager: SessionManager | None = None

    @classmethod
    def from_gradebook_url(
        cls, gradebook_url: str, email: str, password: str
    ) -> GradebookScraper:
        school_code, domain = parse_school_from_url(gradebook_url)
        return cls(school_code, email, password, domain)

    def authenticate(self) -> None:
        tqdm.write("Authenticating with ManageBac...")
        self._authenticator = Authenticator(
            self.school_code, self.email, self.password, self.domain
        )
        session = self._authenticator.login()
        self._session_manager = SessionManager(session, self._authenticator)
        tqdm.write("Authentication successful!")

    @property
    def session_manager(self) -> SessionManager:
        if self._session_manager is None:
            self.authenticate()
        assert self._session_manager is not None
        return self._session_manager

    def fetch_data(self, gradebook_url: str) -> GradebookData:
        """Fetch term grades (roster + A-D) then tasks (scores + comments)."""
        tqdm.write(f"Starting gradebook scrape for: {gradebook_url}")

        try:
            _, term_grades_url, tasks_url, class_name, term_name = resolve_gradebook_urls(
                gradebook_url
            )
        except ValueError as e:
            raise ScraperError(str(e)) from e

        tqdm.write("Fetching term grades page...")
        term_soup = self._fetch_page(term_grades_url)
        term_grades = self._safe_extract(TermGradeExtractor.extract, term_soup, "term grades")
        tqdm.write(f"  Found {len(term_grades)} students on term grades page")

        tqdm.write("Fetching tasks page...")
        tasks_soup = self._fetch_page(tasks_url)
        task_students = self._safe_extract(StudentExtractor.extract, tasks_soup, "task students")
        tasks = self._safe_extract(TaskExtractor.extract, tasks_soup, "tasks")
        tqdm.write(f"  Found {len(tasks)} tasks")

        students = self._merge_students(term_grades, task_students)
        scores = self._safe_extract(
            lambda soup: ScoreExtractor.extract(soup, students, tasks),
            tasks_soup,
            "scores",
        )
        tqdm.write(f"  Found {len(scores)} scores")

        tasks_before = len(tasks)
        tasks = _filter_tasks_with_scores(tasks, scores)
        skipped = tasks_before - len(tasks)
        if skipped:
            tqdm.write(f"  Skipped {skipped} tasks without criterion marks")

        return GradebookData(
            students=students,
            tasks=tasks,
            scores=scores,
            term_grades=term_grades,
            class_name=class_name,
            term_name=term_name,
        )

    def _merge_students(
        self, term_grades: list[TermGrade], task_students: list[Student]
    ) -> list[Student]:
        task_ids_by_name = {_normalize_name(s.name): s.id for s in task_students}
        students: list[Student] = []
        seen_names: set[str] = set()

        for tg in term_grades:
            norm = _normalize_name(tg.student_name)
            if norm in seen_names:
                continue
            seen_names.add(norm)
            student_id = tg.user_id or task_ids_by_name.get(norm) or self._slug_id(tg.student_name)
            students.append(Student(id=student_id, name=tg.student_name))

        for task_student in task_students:
            norm = _normalize_name(task_student.name)
            if norm not in seen_names:
                seen_names.add(norm)
                students.append(task_student)

        return students

    @staticmethod
    def _slug_id(name: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_").lower()
        return slug or "unknown_student"

    def _fetch_page(self, url: str) -> BeautifulSoup:
        try:
            response = self.session_manager.get(url)
            return BeautifulSoup(response.content, "lxml")
        except AuthenticationError:
            raise
        except Exception as e:
            raise ScraperError(f"Failed to fetch page {url}: {e}") from e

    @staticmethod
    def _safe_extract(func, soup: BeautifulSoup, label: str):
        try:
            return func(soup)
        except Exception as e:
            logger.error(f"Error extracting {label}: {e}")
            return []
